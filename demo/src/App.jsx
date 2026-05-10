import React, { useEffect, useReducer, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { timeline, totalDuration, SCENARIO_W, SCENARIO_H } from './timeline.js';
import ChatWidget from './components/ChatWidget.jsx';
import PaginaPrincipal from './components/PaginaPrincipal.jsx';
import AdminPanel from './components/AdminPanel.jsx';
import Cursor from './components/Cursor.jsx';

// ─── Estado del demo ─────────────────────────────────────────────────────
const initialState = {
  sceneIdx: 0,
  sceneStart: 0,
  stage: 'web',
  chatOpen: false,
  messages: [],
  inputBuffer: '',
  botTyping: false,
  contexto: 'GII-IS',
  adminView: 'home',
  cursor: { x: SCENARIO_W - 100, y: SCENARIO_H - 100 },
  cursorClick: 0, // contador, cada click incrementa
  camera: { scale: 1, x: 0, y: 0 },
  playing: true,
  finished: false,
  showOnboarding: false,
  selectedTitulacion: null, // null | 'GII-IS' | 'GII-TI' | 'GII-IC'
};

function reducer(state, action) {
  switch (action.type) {
    case 'TICK':
      return { ...state, t: action.t };
    case 'SET_SCENE':
      return {
        ...state,
        sceneIdx: action.idx,
        sceneStart: action.now,
        camera: action.scene.camera,
        stage: action.scene.stage,
        chatOpen: action.scene.chatOpen,
      };
    case 'OPEN_CHAT':
      return { ...state, chatOpen: true, showOnboarding: true };
    case 'SELECT_TITULACION':
      return {
        ...state,
        showOnboarding: false,
        selectedTitulacion: action.payload,
        contexto: action.payload,
      };
    case 'CLEAR_MESSAGES':
      return {
        ...state,
        messages: [],
        inputBuffer: '',
        botTyping: false,
        showOnboarding: false,
        selectedTitulacion: null,
      };
    case 'USER_TYPE':
      return { ...state, inputBuffer: action.payload };
    case 'USER_SEND':
      return {
        ...state,
        messages: [...state.messages, { from: 'user', text: state.inputBuffer }],
        inputBuffer: '',
      };
    case 'BOT_TYPING':
      return { ...state, botTyping: true };
    case 'BOT_MESSAGE':
      return {
        ...state,
        botTyping: false,
        messages: [...state.messages, { from: 'bot', text: action.payload }],
      };
    case 'CHANGE_CONTEXT':
      return { ...state, contexto: action.payload };
    case 'ADMIN_VIEW':
      return { ...state, adminView: action.payload };
    case 'CURSOR_MOVE':
      return { ...state, cursor: action.payload };
    case 'CURSOR_CLICK':
      return { ...state, cursorClick: state.cursorClick + 1 };
    case 'TOGGLE_PLAY':
      return { ...state, playing: !state.playing };
    case 'RESET':
      return { ...initialState };
    case 'FINISHED':
      return { ...state, finished: true, playing: false };
    default:
      return state;
  }
}

// ─── Acción → dispatch ──────────────────────────────────────────────────
function applyAction(action, dispatch, state) {
  switch (action.type) {
    case 'openChat':
      dispatch({ type: 'OPEN_CHAT' });
      break;
    case 'userType':
      // Tipeo carácter a carácter, simulado con setInterval
      typeText(action.payload, dispatch);
      break;
    case 'userSend':
      dispatch({ type: 'USER_SEND' });
      break;
    case 'botTyping':
      dispatch({ type: 'BOT_TYPING' });
      break;
    case 'botMessage':
      dispatch({ type: 'BOT_MESSAGE', payload: action.payload });
      break;
    case 'changeContext':
      dispatch({ type: 'CHANGE_CONTEXT', payload: action.payload });
      break;
    case 'adminView':
      dispatch({ type: 'ADMIN_VIEW', payload: action.payload });
      break;
    case 'cursorMove':
      dispatch({ type: 'CURSOR_MOVE', payload: action.payload });
      break;
    case 'cursorClick':
      dispatch({ type: 'CURSOR_CLICK' });
      break;
    case 'selectTitulacion':
      dispatch({ type: 'SELECT_TITULACION', payload: action.payload });
      break;
    case 'clearMessages':
      dispatch({ type: 'CLEAR_MESSAGES' });
      break;
    default:
      console.warn('Acción desconocida', action);
  }
}

function typeText(text, dispatch) {
  let i = 0;
  // Velocidad de tipeo: ~28 caracteres por segundo
  const interval = setInterval(() => {
    i += 1;
    dispatch({ type: 'USER_TYPE', payload: text.slice(0, i) });
    if (i >= text.length) clearInterval(interval);
  }, 35);
}

// ─── Componente principal ───────────────────────────────────────────────
export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const startedRef = useRef(performance.now());
  const elapsedAtPauseRef = useRef(0);
  const firedActionsRef = useRef(new Set());
  const [debug, setDebug] = useState(true);
  const [showOverlay, setShowOverlay] = useState(true);
  const [, force] = useState(0);
  const [fitScale, setFitScale] = useState(1);

  // Ajusta el escenario 1920x1080 para que SIEMPRE encaje centrado en la ventana
  useEffect(() => {
    const compute = () => {
      const sx = window.innerWidth / SCENARIO_W;
      const sy = window.innerHeight / SCENARIO_H;
      setFitScale(Math.min(sx, sy));
    };
    compute();
    window.addEventListener('resize', compute);
    return () => window.removeEventListener('resize', compute);
  }, []);

  // Reloj principal (rAF)
  useEffect(() => {
    let raf;
    const loop = () => {
      if (state.playing) {
        const now = performance.now();
        const elapsed = elapsedAtPauseRef.current + (now - startedRef.current);

        // Determinar escena actual
        let acc = 0;
        let sceneIdx = 0;
        for (let i = 0; i < timeline.length; i++) {
          if (elapsed < acc + timeline[i].duration) {
            sceneIdx = i;
            break;
          }
          acc += timeline[i].duration;
          if (i === timeline.length - 1) {
            sceneIdx = i;
            acc -= timeline[i].duration; // último
          }
        }

        const scene = timeline[sceneIdx];
        const sceneElapsed = elapsed - acc;

        // Si cambió la escena, configurar
        if (sceneIdx !== state.sceneIdx) {
          dispatch({ type: 'SET_SCENE', idx: sceneIdx, now: acc, scene });
          firedActionsRef.current = new Set();
        }

        // Disparar acciones de la escena cuyo `at` ya se haya alcanzado
        for (const action of scene.actions) {
          const key = `${sceneIdx}:${action.at}:${action.type}`;
          if (sceneElapsed >= action.at && !firedActionsRef.current.has(key)) {
            firedActionsRef.current.add(key);
            applyAction(action, dispatch, state);
          }
        }

        // Final del demo
        if (elapsed >= totalDuration && !state.finished) {
          dispatch({ type: 'FINISHED' });
        }
      }
      force((n) => n + 1);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.playing, state.sceneIdx]);

  // Atajos: espacio = play/pause, R = reset
  useEffect(() => {
    const onKey = (e) => {
      if (e.code === 'Space') {
        e.preventDefault();
        if (state.playing) {
          // Pausa: guarda elapsed actual
          const now = performance.now();
          elapsedAtPauseRef.current += now - startedRef.current;
        } else {
          startedRef.current = performance.now();
        }
        dispatch({ type: 'TOGGLE_PLAY' });
      } else if (e.code === 'KeyR') {
        elapsedAtPauseRef.current = 0;
        startedRef.current = performance.now();
        firedActionsRef.current = new Set();
        dispatch({ type: 'RESET' });
      } else if (e.code === 'KeyD') {
        setDebug((d) => !d);
      } else if (e.code === 'KeyH') {
        setShowOverlay((s) => !s);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [state.playing]);

  const currentScene = timeline[state.sceneIdx] || timeline[0];

  return (
    <div className="w-screen h-screen relative bg-black overflow-hidden flex items-center justify-center">
      {/* Wrapper centrado, dimensionado al fit calculado */}
      <div
        style={{
          width: SCENARIO_W * fitScale,
          height: SCENARIO_H * fitScale,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Cámara: centra en (target.x, target.y) del escenario y aplica zoom */}
        {(() => {
          // Si la escena define un target, lo usamos. Si no, centro del escenario.
          const targetX = state.camera.targetX ?? SCENARIO_W / 2;
          const targetY = state.camera.targetY ?? SCENARIO_H / 2;
          const zoom = state.camera.scale ?? 1;
          // Para centrar (targetX, targetY) en el medio del wrapper escalado,
          // calculamos cuánto desplazar el escenario (en píxeles del escenario)
          // y luego lo multiplicamos por fitScale para coordenadas del viewport.
          const offsetX = (SCENARIO_W / 2 - targetX) * zoom * fitScale;
          const offsetY = (SCENARIO_H / 2 - targetY) * zoom * fitScale;
          return (
            <motion.div
              className="absolute top-0 left-0"
              style={{
                width: SCENARIO_W,
                height: SCENARIO_H,
                transformOrigin: '0 0',
              }}
              animate={{
                scale: fitScale * zoom,
                x: offsetX,
                y: offsetY,
              }}
              transition={{ duration: 1.4, ease: [0.4, 0, 0.2, 1] }}
            >
          {/* Escenario absoluto 1920x1080 */}
          <div className="relative w-full h-full overflow-hidden bg-white">
            {state.stage === 'web' ? (
              <PaginaPrincipal />
            ) : (
              <AdminPanel view={state.adminView} />
            )}

            {/* Widget flotante (solo si stage=web) */}
            {state.stage === 'web' && (
              <ChatWidget
                open={state.chatOpen}
                messages={state.messages}
                inputBuffer={state.inputBuffer}
                botTyping={state.botTyping}
                contexto={state.contexto}
                showOnboarding={state.showOnboarding}
                selectedTitulacion={state.selectedTitulacion}
              />
            )}

            {/* Cursor virtual */}
            <Cursor
              position={state.cursor}
              clicking={state.cursorClick > 0 && state.cursorClick % 2 !== 0}
            />
          </div>
        </motion.div>
          );
        })()}
      </div>

      {/* Overlay HUD (visible siempre, ocultar con H) */}
      {showOverlay && (
        <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none z-[100]">
          <div className="bg-black/70 text-white px-3 py-1.5 rounded text-xs font-mono">
            Escena {state.sceneIdx + 1}/{timeline.length} · {currentScene.label}
          </div>
          <div className="flex gap-2 pointer-events-auto">
            <button
              onClick={() => {
                if (state.playing) {
                  const now = performance.now();
                  elapsedAtPauseRef.current += now - startedRef.current;
                } else {
                  startedRef.current = performance.now();
                }
                dispatch({ type: 'TOGGLE_PLAY' });
              }}
              className="bg-black/70 text-white px-3 py-1.5 rounded text-xs"
            >
              {state.playing ? '⏸ Pausa (Space)' : '▶ Play (Space)'}
            </button>
            <button
              onClick={() => {
                elapsedAtPauseRef.current = 0;
                startedRef.current = performance.now();
                firedActionsRef.current = new Set();
                dispatch({ type: 'RESET' });
              }}
              className="bg-black/70 text-white px-3 py-1.5 rounded text-xs"
            >
              ⏮ Reset (R)
            </button>
            <button
              onClick={() => setShowOverlay(false)}
              className="bg-black/70 text-white px-3 py-1.5 rounded text-xs"
              title="Ocultar HUD para grabar (H)"
            >
              👁 Ocultar (H)
            </button>
          </div>
        </div>
      )}

      {/* Mensaje al final */}
      {state.finished && (
        <div className="absolute inset-0 bg-black/80 flex items-center justify-center text-white text-2xl font-display">
          Demo completado · pulsa R para reiniciar
        </div>
      )}
    </div>
  );
}
