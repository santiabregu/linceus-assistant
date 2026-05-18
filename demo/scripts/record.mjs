// Grabación determinística frame-a-frame del demo Linceus Assistant.
//
// Estrategia (ver docs/recording-guide.md):
//   1. Override de requestAnimationFrame / timers / performance.now con un
//      reloj virtual, inyectado vía addInitScript ANTES de que se cargue React.
//   2. Borrado de Element.prototype.animate para deshabilitar WAAPI y forzar
//      el animador JS de Framer Motion (que sí usa rAF).
//   3. Para cada tick (1/FPS s), avanzamos el reloj virtual, disparamos los
//      rAF/timers vencidos, tomamos un screenshot JPEG y lo pasamos a ffmpeg.
//
// Sólo se activa cuando la URL contiene ?record, así que el dev server normal
// sigue funcionando intacto.

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');
const RECORDINGS_DIR = path.join(PROJECT_ROOT, 'recordings');

const PORT = Number(process.env.PORT) || 5173;
const FPS = Number(process.env.FPS) || 60;
const FRAME_MS = 1000 / FPS;
const DURATION_S = Number(process.env.DURATION) || 181; // 180 s + 1 s de cola
const TOTAL_FRAMES = Math.round(DURATION_S * FPS);
const VIEWPORT = { width: 1920, height: 1080 };
const FFMPEG_BIN = process.env.FFMPEG_BIN || 'ffmpeg';

const url = `http://localhost:${PORT}/?record`;

const initScript = `
(() => {
  if (!new URLSearchParams(location.search).has('record')) return;

  // ── 1. Deshabilitar WAAPI para forzar el animador JS de Framer Motion ──
  try { delete Element.prototype.animate; } catch (e) {}
  try { delete HTMLElement.prototype.animate; } catch (e) {}

  // ── 2. Reloj virtual ──
  let vt = 0;
  const origPerfNow = performance.now.bind(performance);
  performance.now = () => vt;
  const DATE_EPOCH = 1700000000000;
  const _Date = Date;
  Date.now = () => Math.floor(vt) + DATE_EPOCH;

  // ── 3. requestAnimationFrame / cancelAnimationFrame ──
  const rafQueue = new Map();
  let nextRafId = 1;
  window.requestAnimationFrame = (cb) => {
    const id = nextRafId++;
    rafQueue.set(id, cb);
    return id;
  };
  window.cancelAnimationFrame = (id) => rafQueue.delete(id);

  // ── 4. setTimeout / setInterval (con virtual fireAt) ──
  const timers = new Map();
  let nextTimerId = 1;
  const _origSetTimeout = window.setTimeout;
  const _origSetInterval = window.setInterval;
  const _origClearTimeout = window.clearTimeout;
  const _origClearInterval = window.clearInterval;

  window.setTimeout = (cb, delay = 0, ...args) => {
    if (typeof cb !== 'function') return _origSetTimeout(cb, delay, ...args);
    const id = nextTimerId++;
    timers.set(id, { fireAt: vt + Number(delay || 0), period: 0, cb, args });
    return id;
  };
  window.clearTimeout = (id) => { timers.delete(id); };
  window.setInterval = (cb, delay = 0, ...args) => {
    if (typeof cb !== 'function') return _origSetInterval(cb, delay, ...args);
    const id = nextTimerId++;
    const period = Math.max(1, Number(delay || 0));
    timers.set(id, { fireAt: vt + period, period, cb, args });
    return id;
  };
  window.clearInterval = (id) => { timers.delete(id); };

  // ── 5. queueMicrotask y Promise siguen siendo reales; no las tocamos ──

  // ── 6. API que llama el recorder ──
  window.__tick = (deltaMs) => {
    vt += deltaMs;

    // Disparar timers vencidos. Loop de protección por si un cb mete otro
    // setTimeout(0) que vence al instante (limitamos 32 vueltas).
    for (let pass = 0; pass < 32; pass++) {
      const due = [];
      for (const [id, t] of timers) {
        if (t.fireAt <= vt) due.push([id, t]);
      }
      if (due.length === 0) break;
      due.sort((a, b) => a[1].fireAt - b[1].fireAt);
      for (const [id, t] of due) {
        if (t.period > 0) {
          // reschedule antes de invocar, por si el cb hace clearInterval
          t.fireAt += t.period;
        } else {
          timers.delete(id);
        }
        try { t.cb(...t.args); } catch (err) { console.error(err); }
      }
    }

    // Disparar todos los rAF encolados. Los cb pueden encolar nuevos rAF;
    // sólo disparamos los que ya estaban antes para no entrar en bucle.
    const callbacks = [...rafQueue.entries()];
    rafQueue.clear();
    for (const [, cb] of callbacks) {
      try { cb(vt); } catch (err) { console.error(err); }
    }
  };

  // ── 7. Ocultar HUD del demo cuando se graba ──
  const css = document.createElement('style');
  css.textContent = \`
    /* HUD superior del demo (controles + label de escena) */
    body .absolute.top-3.left-3.right-3 { display: none !important; }
  \`;
  // El head puede no existir aún; lo añadimos cuando exista.
  const attach = () => {
    if (document.head) document.head.appendChild(css);
    else _origSetTimeout(attach, 0);
  };
  attach();
})();
`;

async function waitForServer(targetUrl, timeoutMs = 60000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const res = await fetch(targetUrl);
      if (res.ok) return;
    } catch (_) { /* still booting */ }
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`Dev server no responde en ${targetUrl} tras ${timeoutMs} ms`);
}

async function main() {
  if (!existsSync(RECORDINGS_DIR)) await mkdir(RECORDINGS_DIR, { recursive: true });

  const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const outFile = path.join(RECORDINGS_DIR, `linceus-demo-${stamp}.mp4`);

  console.log(`▶  Esperando al dev server en ${url} …`);
  await waitForServer(`http://localhost:${PORT}/`);

  console.log(`▶  Captura determinística: ${TOTAL_FRAMES} frames @ ${FPS} fps  (${VIEWPORT.width}×${VIEWPORT.height})`);
  console.log(`▶  Lanzando ffmpeg (libx264 CRF 14, preset slow, tune animation)`);

  const ffmpegArgs = [
    '-y',
    '-f', 'image2pipe',
    '-vcodec', 'mjpeg',
    '-framerate', String(FPS),
    '-i', '-',
    '-vcodec', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-crf', '14',
    '-preset', 'slow',
    '-tune', 'animation',
    '-r', String(FPS),
    '-movflags', '+faststart',
    outFile,
  ];

  const ffmpeg = spawn(FFMPEG_BIN, ffmpegArgs, {
    stdio: ['pipe', 'ignore', process.env.DEBUG_FFMPEG ? 'inherit' : 'ignore'],
  });
  const ffmpegDone = new Promise((resolve, reject) => {
    ffmpeg.on('error', reject);
    ffmpeg.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`ffmpeg salió con código ${code}`));
    });
  });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: VIEWPORT,
    deviceScaleFactor: 1,
  });
  await context.addInitScript(initScript);
  const page = await context.newPage();
  page.on('pageerror', (e) => console.error('  ⚠ pageerror:', e.message));

  await page.goto(url, { waitUntil: 'domcontentloaded' });

  // Verificación: el override está activo
  const tickType = await page.evaluate(() => typeof window.__tick);
  if (tickType !== 'function') {
    throw new Error('window.__tick no está definido — el addInitScript no se inyectó');
  }
  const waapiAlive = await page.evaluate(() => 'animate' in Element.prototype);
  if (waapiAlive) {
    console.warn('  ⚠ Element.prototype.animate sigue presente, las animaciones de Framer Motion podrían saltar al fotograma 1');
  }

  // Pequeño calentamiento: 2 ticks para que React monte y registre rAF/timers.
  for (let i = 0; i < 4; i++) {
    await page.evaluate((dt) => window.__tick(dt), FRAME_MS);
  }

  const t0 = Date.now();
  let lastLogAt = t0;

  for (let i = 0; i < TOTAL_FRAMES; i++) {
    await page.evaluate((dt) => window.__tick(dt), FRAME_MS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ffmpeg.stdin.write(buf)) {
      await new Promise((r) => ffmpeg.stdin.once('drain', r));
    }

    const now = Date.now();
    if (now - lastLogAt > 5000 || i === TOTAL_FRAMES - 1) {
      const elapsed = (now - t0) / 1000;
      const capFps = (i + 1) / elapsed;
      const videoSec = ((i + 1) / FPS).toFixed(1);
      process.stdout.write(`   ${videoSec}s renderizados  ·  ${elapsed.toFixed(1)}s reales  ·  ${capFps.toFixed(1)} capture-fps\r`);
      lastLogAt = now;
    }
  }
  process.stdout.write('\n');

  await browser.close();
  ffmpeg.stdin.end();
  await ffmpegDone;

  const stats = (await import('node:fs/promises')).then;
  const { statSync } = await import('node:fs');
  const size = statSync(outFile).size;
  const sizeMB = (size / 1024 / 1024).toFixed(1);
  console.log(`✓  Guardado ${path.relative(PROJECT_ROOT, outFile)}  (${sizeMB} MB)`);
}

main().catch((err) => {
  console.error('✗ Grabación abortada:', err);
  process.exit(1);
});
