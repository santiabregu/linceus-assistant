/* ====================================================================
   LinceUS Admin Panel - JavaScript
   Navegacion: Centros → Titulaciones → Asignaturas → Planes/Chunks
   + Profesores, Horarios, Conversaciones, Feedback
   ==================================================================== */

(function () {
  "use strict";

  // ─── Auth ────────────────────────────────────────────────────────────
  const SUPABASE_URL = "https://ejekixebxeaidmhslwjs.supabase.co";
  const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqZWtpeGVieGVhaWRtaHNsd2pzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTg0ODYzNDYsImV4cCI6MjA3NDA2MjM0Nn0.TRELbRomO7ERtlDG35MEvCho_voWP-Xfsi1cABqVjCs";
  const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  supabase.auth.getSession().then(({ data: { session } }) => {
    if (!session) window.location.href = "login.html";
  });

  document.getElementById("btn-logout").addEventListener("click", async () => {
    await supabase.auth.signOut();
    window.location.href = "login.html";
  });

  // Config
  const API_BASE = (function () {
    const h = window.location.hostname;
    if (h === "localhost" || h === "127.0.0.1") return "http://localhost:5050";
    return ""; // En produccion, nginx hace proxy
  })();

  const API = (path) => API_BASE + path;

  // ─── DOM refs ────────────────────────────────────────────────────
  const $main = document.getElementById("main-content");
  const $breadcrumb = document.getElementById("breadcrumb");
  const $loading = document.getElementById("loading");
  const $status = document.getElementById("connection-status");
  const $modalOverlay = document.getElementById("modal-overlay");
  const $modalTitle = document.getElementById("modal-title");
  const $modalBody = document.getElementById("modal-body");
  let currentView = "home";
  let statsCache = null;

  // Helpers
  async function fetchJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw Object.assign(new Error(data.error || `HTTP ${res.status}`), { status: res.status, data });
    return data;
  }

  async function deleteJSON(url) {
    const res = await fetch(url, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw Object.assign(new Error(data.error || `HTTP ${res.status}`), { status: res.status, data });
    return data;
  }

  function esc(str) {
    if (str == null) return "";
    const d = document.createElement("div");
    d.textContent = String(str);
    return d.innerHTML;
  }

  function gridClass(count) {
    if (count <= 1) return "items-1";
    if (count <= 2) return "items-2";
    if (count <= 3) return "items-3";
    if (count <= 4) return "items-4";
    if (count <= 6) return "items-6";
    return "items-many";
  }

  function tipologiaTag(tipo) {
    if (!tipo) return "";
    const t = tipo.toUpperCase();
    if (t.includes("BASICA")) return '<span class="tag tag-basica">F. Basica</span>';
    if (t.includes("OPTATIVA")) return '<span class="tag tag-optativa">Optativa</span>';
    return '<span class="tag tag-obligatoria">Obligatoria</span>';
  }

  function estadoTag(estado) {
    if (!estado) return "";
    const e = estado.toLowerCase();
    if (e === "completado") return '<span class="tag tag-completado">Completado</span>';
    if (e === "error") return '<span class="tag tag-error">Error</span>';
    return '<span class="tag tag-pendiente">' + esc(estado) + "</span>";
  }

  function showLoading() {
    $main.innerHTML =
      '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Cargando datos...</div>';
  }

  function showEmpty(icon, msg) {
    $main.innerHTML = `<div class="empty-state"><i class="fa-solid fa-${icon}"></i><p>${msg}</p></div>`;
  }

  // Breadcrumb 

  function setBreadcrumb(crumbs) {
    $breadcrumb.innerHTML = crumbs
      .map(
        (c, i) =>
          (i > 0 ? '<span class="separator"><i class="fa-solid fa-chevron-right"></i></span>' : "") +
          `<a href="#" data-view="${esc(c.view)}" ${c.data || ""} class="crumb${i === crumbs.length - 1 ? " active" : ""}">${c.label}</a>`
      )
      .join("");

    $breadcrumb.querySelectorAll(".crumb").forEach((el) =>
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const v = el.dataset.view;
        if (v === "home") loadCentros();
        else if (v === "titulaciones") loadTitulaciones(el.dataset.centroId, el.dataset.centroNombre);
        else if (v === "asignaturas") loadAsignaturas(el.dataset.titulacionId, el.dataset.titulacionNombre);
      })
    );
  }

  // ─── Tabs ────────────────────────────────────────────────────────

  document.querySelectorAll(".nav-tabs .tab").forEach((tab) =>
    tab.addEventListener("click", (e) => {
      e.preventDefault();
      document.querySelectorAll(".nav-tabs .tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const view = tab.dataset.view;
      if (view === "home") loadCentros();
      else if (view === "profesores") loadProfesores();
      else if (view === "horarios") loadHorarios();
      else if (view === "conversaciones") loadConversaciones();
      else if (view === "feedback") loadFeedback();
    })
  );

  document.getElementById("btn-stats").addEventListener("click", (e) => {
    e.preventDefault();
    loadStats();
  });

  // ─── Modal ───────────────────────────────────────────────────────

  function openModal(title, html) {
    $modalTitle.textContent = title;
    $modalBody.innerHTML = html;
    $modalOverlay.classList.add("open");
  }

  function closeModal() {
    $modalOverlay.classList.remove("open");
  }

  document.getElementById("modal-close").addEventListener("click", closeModal);
  $modalOverlay.addEventListener("click", (e) => {
    if (e.target === $modalOverlay) closeModal();
  });

  // health check

  async function checkHealth() {
    try {
      await fetchJSON(API("/api/admin/health"));
      $status.className = "connection-status ok";
      $status.innerHTML = '<i class="fa-solid fa-circle"></i> Conectado';
    } catch {
      $status.className = "connection-status error";
      $status.innerHTML = '<i class="fa-solid fa-circle"></i> Sin conexion';
    }
  }

  // stats admin

  async function loadStats() {
    showLoading();
    try {
      const stats = await fetchJSON(API("/api/admin/stats"));
      statsCache = stats;
      const items = [
        { label: "Centros", value: stats.centros, icon: "building-columns" },
        { label: "Titulaciones", value: stats.titulaciones, icon: "graduation-cap" },
        { label: "Asignaturas", value: stats.asignaturas, icon: "book" },
        { label: "Profesores", value: stats.profesores, icon: "user-tie" },
        { label: "Grupos", value: stats.grupos, icon: "users" },
        { label: "Horarios", value: stats.horarios, icon: "clock" },
        { label: "Planes docentes", value: stats.planes_docentes, icon: "file-pdf" },
        { label: "Chunks RAG", value: stats.chunks, icon: "puzzle-piece" },
        { label: "Conversaciones", value: stats.conversaciones, icon: "comments" },
        { label: "Feedback", value: stats.feedback, icon: "star" },
      ];

      setBreadcrumb([
        { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
        { view: "stats", label: "Estadisticas" },
      ]);

      $main.innerHTML =
        '<div class="section-header"><h2>Estadisticas generales</h2></div>' +
        '<div class="stats-grid">' +
        items
          .map(
            (i) =>
              `<div class="stat-card"><div class="stat-number">${i.value}</div><div class="stat-label"><i class="fa-solid fa-${i.icon}"></i> ${i.label}</div></div>`
          )
          .join("") +
        "</div>";
    } catch (err) {
      showEmpty("triangle-exclamation", "Error cargando estadisticas: " + err.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  //  CENTROS
  // ═══════════════════════════════════════════════════════════════════

  async function loadCentros() {
    showLoading();
    setActiveTab("home");
    setBreadcrumb([{ view: "home", label: '<i class="fa-solid fa-house"></i> Centros' }]);

    try {
      const centros = await fetchJSON(API("/api/admin/centros"));
      if (!centros.length) {
        showEmpty("building-columns", "No hay centros en la base de datos");
        return;
      }

      const html =
        `<div class="section-header"><h2>Centros disponibles</h2><span class="count-badge">${centros.length}</span><button class="btn-crear" id="btn-nuevo-centro"><i class="fa-solid fa-plus"></i> Nuevo centro</button></div>` +
        `<div class="card-grid ${gridClass(centros.length)}">` +
        centros
          .map(
            (c) => `
          <div class="entity-card" data-centro-id="${esc(c.id)}" data-centro-nombre="${esc(c.nombre)}">
            <div class="card-icon"><i class="fa-solid fa-building-columns"></i></div>
            <div class="card-title">${esc(c.nombre)}</div>
            <div class="card-subtitle">${esc(c.codigo)}</div>
            <div class="card-meta">
              <span><i class="fa-solid fa-graduation-cap"></i> ${c.num_titulaciones} titulaciones</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px">
              <div class="card-badge">${c.activo ? "Activo" : "Inactivo"}</div>
              <button class="btn-delete" data-delete-centro="${esc(c.id)}" title="Eliminar centro"><i class="fa-solid fa-trash"></i></button>
            </div>
          </div>`
          )
          .join("") +
        "</div>";

      $main.innerHTML = html;

      $main.querySelectorAll(".entity-card").forEach((card) =>
        card.addEventListener("click", () => {
          loadTitulaciones(card.dataset.centroId, card.dataset.centroNombre);
        })
      );

      $main.querySelectorAll(".btn-delete[data-delete-centro]").forEach((btn) =>
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const id = btn.dataset.deleteCentro;
          const nombre = btn.closest(".entity-card").dataset.centroNombre;
          if (!confirm(`¿Eliminar el centro "${nombre}" y todas sus titulaciones y asignaturas?`)) return;
          try {
            await deleteJSON(API("/api/admin/centros/" + id));
            loadCentros();
          } catch (err) { alert("Error: " + err.message); }
        })
      );

      document.getElementById("btn-nuevo-centro")?.addEventListener("click", () => abrirFormCentro());
    } catch (err) {
      showEmpty("triangle-exclamation", "Error cargando centros: " + err.message);
    }
  }

  // También mostramos botón cuando no hay centros
  // (el showEmpty no tiene botón, así que lo manejamos aquí)

  // ═══════════════════════════════════════════════════════════════════
  //  TITULACIONES
  // ═══════════════════════════════════════════════════════════════════

  async function loadTitulaciones(centroId, centroNombre) {
    showLoading();
    setActiveTab("home");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Centros' },
      {
        view: "titulaciones",
        label: centroNombre || "Titulaciones",
        data: `data-centro-id="${esc(centroId)}" data-centro-nombre="${esc(centroNombre)}"`,
      },
    ]);

    try {
      const url = centroId
        ? API("/api/admin/titulaciones?centro_id=" + centroId)
        : API("/api/admin/titulaciones");
      const titulaciones = await fetchJSON(url);

      if (!titulaciones.length) {
        $main.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-graduation-cap"></i>
            <p>No hay titulaciones para este centro</p>
            <button class="btn-crear" id="btn-sync-tits" style="margin-top:12px">
              <i class="fa-solid fa-rotate"></i> Sincronizar titulaciones desde Sevius
            </button>
          </div>`;
        document.getElementById("btn-sync-tits")?.addEventListener("click", () =>
          abrirFormSyncTitulaciones(centroId, centroNombre)
        );
        return;
      }

      const html =
        `<div class="section-header"><h2>Titulaciones</h2><span class="count-badge">${titulaciones.length}</span><button class="btn-crear" id="btn-sync-tits"><i class="fa-solid fa-rotate"></i> Sincronizar desde Sevius</button><button class="btn-crear" id="btn-nueva-tit"><i class="fa-solid fa-plus"></i> Nueva titulacion</button></div>` +
        `<div class="card-grid ${gridClass(titulaciones.length)}">` +
        titulaciones
          .map(
            (t) => `
          <div class="entity-card" data-titulacion-id="${esc(t.id)}" data-titulacion-nombre="${esc(t.nombre)}">
            <div class="card-icon"><i class="fa-solid fa-graduation-cap"></i></div>
            <div class="card-title">${esc(t.nombre)}</div>
            <div class="card-subtitle">${esc(t.codigo)} ${t.nombre_corto ? "- " + esc(t.nombre_corto) : ""}</div>
            <div class="card-meta">
              <span><i class="fa-solid fa-book"></i> ${t.num_asignaturas} asignaturas</span>
              <span><i class="fa-solid fa-award"></i> ${t.creditos_totales || "?"} ECTS</span>
              <span><i class="fa-solid fa-calendar"></i> ${t.duracion_anios || "?"} anos</span>
              <span><i class="fa-solid fa-file-alt"></i> Plan ${t.plan_estudios_anio || "?"}</span>
            </div>
            <div style="display:flex;justify-content:space-between;align-items:center;margin-top:12px">
              <div class="card-badge">${t.activa ? "Activa" : "Inactiva"}</div>
              <button class="btn-delete" data-delete-tit="${esc(t.id)}" title="Eliminar titulacion"><i class="fa-solid fa-trash"></i></button>
            </div>
          </div>`
          )
          .join("") +
        "</div>";

      $main.innerHTML = html;

      $main.querySelectorAll(".entity-card").forEach((card) =>
        card.addEventListener("click", () => {
          loadAsignaturas(card.dataset.titulacionId, card.dataset.titulacionNombre);
        })
      );

      $main.querySelectorAll(".btn-delete[data-delete-tit]").forEach((btn) =>
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const id = btn.dataset.deleteTit;
          const nombre = btn.closest(".entity-card").dataset.titulacionNombre;
          if (!confirm(`¿Eliminar la titulacion "${nombre}" y todas sus asignaturas?`)) return;
          try {
            await deleteJSON(API("/api/admin/titulaciones/" + id));
            loadTitulaciones(centroId, centroNombre);
          } catch (err) { alert("Error: " + err.message); }
        })
      );

      document.getElementById("btn-sync-tits")?.addEventListener("click", () => abrirFormSyncTitulaciones(centroId, centroNombre));
      document.getElementById("btn-nueva-tit")?.addEventListener("click", () => abrirFormTitulacion(centroId, centroNombre));
    } catch (err) {
      showEmpty("triangle-exclamation", "Error cargando titulaciones: " + err.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  //  ASIGNATURAS
  // ═══════════════════════════════════════════════════════════════════

  async function loadAsignaturas(titulacionId, titulacionNombre) {
    showLoading();
    setActiveTab("home");

    // Encontramos centro para el breadcrumb
    let centroId = null,
      centroNombre = null;
    try {
      const tits = await fetchJSON(API("/api/admin/titulaciones"));
      const tit = tits.find((t) => t.id === titulacionId);
      if (tit) {
        // Necesitamos el centro
        const centros = await fetchJSON(API("/api/admin/centros"));
        if (centros.length) {
          centroId = centros[0].id;
          centroNombre = centros[0].nombre;
        }
      }
    } catch {}

    const crumbs = [{ view: "home", label: '<i class="fa-solid fa-house"></i> Centros' }];
    if (centroId) {
      crumbs.push({
        view: "titulaciones",
        label: centroNombre || "Centro",
        data: `data-centro-id="${esc(centroId)}" data-centro-nombre="${esc(centroNombre)}"`,
      });
    }
    crumbs.push({
      view: "asignaturas",
      label: titulacionNombre || "Asignaturas",
      data: `data-titulacion-id="${esc(titulacionId)}" data-titulacion-nombre="${esc(titulacionNombre)}"`,
    });
    setBreadcrumb(crumbs);

    try {
      const url = titulacionId
        ? API("/api/admin/asignaturas?titulacion_id=" + titulacionId)
        : API("/api/admin/asignaturas");
      const asignaturas = await fetchJSON(url);

      if (!asignaturas.length) {
        $main.innerHTML = `
          <div class="empty-state">
            <i class="fa-solid fa-book"></i>
            <p>No hay asignaturas para esta titulacion</p>
            <button class="btn-crear" id="btn-sync-asigs-empty" style="margin-top:12px">
              <i class="fa-solid fa-rotate"></i> Sincronizar asignaturas desde Sevius
            </button>
          </div>`;
        document.getElementById("btn-sync-asigs-empty")?.addEventListener("click", () =>
          abrirFormSyncAsignaturas(titulacionId, titulacionNombre)
        );
        return;
      }

      // Agrupar por curso
      const grupos = {};
      asignaturas.forEach((a) => {
        const c = a.curso || 0;
        if (!grupos[c]) grupos[c] = [];
        grupos[c].push(a);
      });

      const cursoNames = { 1: "1er Curso", 2: "2o Curso", 3: "3er Curso", 4: "4o Curso", 0: "Sin curso" };

      let html = `<div class="section-header"><h2>Asignaturas</h2><span class="count-badge">${asignaturas.length}</span><button class="btn-crear" id="btn-vectorizar"><i class="fa-solid fa-cube"></i> Vectorizar planes docentes</button><button class="btn-crear" id="btn-enrich-asigs"><i class="fa-solid fa-wand-magic-sparkles"></i> Enriquecer datos (us.es)</button><button class="btn-crear" id="btn-cargar-docencia" title="Popula la tabla profesor_asignatura con la docencia declarada en us.es"><i class="fa-solid fa-chalkboard-user"></i> Cargar docencia</button><button class="btn-crear" id="btn-sync-asigs"><i class="fa-solid fa-rotate"></i> Sincronizar desde Sevius</button></div>`;

      Object.keys(grupos)
        .sort((a, b) => a - b)
        .forEach((curso) => {
          const items = grupos[curso];
          html += `<div class="curso-group">`;
          html += `<div class="curso-group-title"><i class="fa-solid fa-layer-group"></i> ${cursoNames[curso] || "Curso " + curso} (${items.length})</div>`;
          html += `<div class="card-grid ${gridClass(items.length)}">`;
          items.forEach((a) => {
            html += `
            <div class="entity-card" data-asignatura-id="${esc(a.id)}" data-titulacion-id="${esc(titulacionId)}">
              <div style="display:flex;justify-content:space-between;align-items:start">
                <div class="card-title" style="flex:1">${esc(a.nombre)}</div>
                ${tipologiaTag(a.tipologia)}
              </div>
              <div class="card-subtitle">${esc(a.codigo)}</div>
              <div class="card-meta">
                <span><i class="fa-solid fa-award"></i> ${a.creditos} ECTS</span>
                <span><i class="fa-solid fa-clock"></i> ${esc(a.duracion)}</span>
              </div>
              <div style="display:flex;justify-content:flex-end;margin-top:8px">
                <button class="btn-delete" data-delete-asig="${esc(a.id)}" data-asig-nombre="${esc(a.nombre)}" title="Eliminar asignatura"><i class="fa-solid fa-trash"></i></button>
              </div>
            </div>`;
          });
          html += "</div></div>";
        });

      $main.innerHTML = html;

      // Click en asignatura -> ver detalle + planes docentes
      $main.querySelectorAll(".entity-card").forEach((card) =>
        card.addEventListener("click", () => {
          openAsignaturaDetail(card.dataset.asignaturaId);
        })
      );

      $main.querySelectorAll(".btn-delete[data-delete-asig]").forEach((btn) =>
        btn.addEventListener("click", async (e) => {
          e.stopPropagation();
          const id = btn.dataset.deleteAsig;
          const nombre = btn.dataset.asigNombre;
          if (!confirm(`¿Eliminar la asignatura "${nombre}"?`)) return;
          try {
            await deleteJSON(API("/api/admin/asignaturas/" + id));
            loadAsignaturas(titulacionId, titulacionNombre);
          } catch (err) { alert("Error: " + err.message); }
        })
      );

      document.getElementById("btn-enrich-asigs")?.addEventListener("click", () =>
        abrirEnrichAsignaturas(titulacionId, titulacionNombre)
      );
      document.getElementById("btn-sync-asigs")?.addEventListener("click", () =>
        abrirFormSyncAsignaturas(titulacionId, titulacionNombre)
      );
      document.getElementById("btn-vectorizar")?.addEventListener("click", () =>
        abrirFormVectorizar(titulacionId, titulacionNombre)
      );
      document.getElementById("btn-cargar-docencia")?.addEventListener("click", () =>
        abrirCargarDocencia(titulacionId, titulacionNombre)
      );
    } catch (err) {
      showEmpty("triangle-exclamation", "Error cargando asignaturas: " + err.message);
    }
  }

  // ─── Asignatura detail modal ─────────────────────────────────────

  async function openAsignaturaDetail(id) {
    openModal("Cargando...", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i></div>');
    try {
      const [asig, planes, profes] = await Promise.all([
        fetchJSON(API("/api/admin/asignaturas/" + id)),
        fetchJSON(API("/api/admin/planes_docentes?asignatura_id=" + id)),
        fetchJSON(API("/api/admin/asignaturas/" + id + "/profesores")),
      ]);

      let html = `<div class="detail-grid">
        <div class="detail-field"><div class="field-label">Codigo</div><div class="field-value">${esc(asig.codigo)}</div></div>
        <div class="detail-field"><div class="field-label">Nombre</div><div class="field-value">${esc(asig.nombre)}</div></div>
        <div class="detail-field"><div class="field-label">Titulacion</div><div class="field-value">${esc(asig.titulacion_nombre)} (${esc(asig.titulacion_codigo)})</div></div>
        <div class="detail-field"><div class="field-label">Curso</div><div class="field-value">${asig.curso || "?"}</div></div>
        <div class="detail-field"><div class="field-label">Creditos</div><div class="field-value">${asig.creditos} ECTS</div></div>
        <div class="detail-field"><div class="field-label">Duracion</div><div class="field-value">${esc(asig.duracion)}</div></div>
        <div class="detail-field"><div class="field-label">Tipologia</div><div class="field-value">${tipologiaTag(asig.tipologia)}</div></div>
        <div class="detail-field"><div class="field-label">Nombre normalizado</div><div class="field-value">${esc(asig.nombre_normalizado)}</div></div>
        <div class="detail-field"><div class="field-label">Activa</div><div class="field-value">${asig.activa ? "Si" : "No"}</div></div>
      </div>`;

      if (planes.length) {
        html += `<h3 style="margin:24px 0 12px;font-family:'Raleway',sans-serif;font-weight:600;font-size:16px">Planes docentes (${planes.length})</h3>`;
        planes.forEach((p) => {
          html += `
          <div style="background:#f8f8f8;padding:14px;border-radius:6px;margin-bottom:10px;border:1px solid #e0e0e0">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
              <strong>${esc(p.curso_academico)} - Grupo ${esc(p.grupo)}</strong>
              ${estadoTag(p.estado_rag)}
            </div>
            <div style="font-size:12px;color:#777">
              Coordinador: ${esc(p.coordinador_nombre) || "N/A"} | Chunks: ${p.num_chunks}
              ${p.url_documento ? ' | <a href="' + esc(p.url_documento) + '" target="_blank">Ver PDF</a>' : ""}
            </div>
            ${p.num_chunks > 0 ? `<button class="btn-ver-chunks" data-plan-id="${esc(p.id)}" style="margin-top:8px;padding:6px 12px;font-size:12px;background:var(--us-red);color:#fff;border:none;border-radius:4px;cursor:pointer">Ver chunks reconstruidos</button>` : ""}
          </div>`;
        });
      } else {
        html += '<p style="margin-top:20px;color:#777;font-size:13px">No hay planes docentes procesados para esta asignatura.</p>';
      }

      html += `<h3 style="margin:24px 0 12px;font-family:'Raleway',sans-serif;font-weight:600;font-size:16px"><i class="fa-solid fa-user-tie"></i> Profesores (${profes.length})</h3>`;
      if (profes.length) {
        html += '<div class="data-table-container"><table class="data-table"><thead><tr><th>Nombre</th><th>Departamento</th><th>Email</th><th>Despacho</th><th>Año acad.</th></tr></thead><tbody>';
        profes.forEach((p) => {
          const fullName = p.apellidos ? `${esc(p.apellidos)}, ${esc(p.nombre)}` : esc(p.nombre || p.nombre_completo);
          html += `<tr data-profesor-id="${esc(p.id)}" style="cursor:pointer">
            <td><strong>${fullName}</strong>${p.es_coordinador ? ' <span style="background:#fee;color:#c00;font-size:10px;padding:2px 6px;border-radius:3px;margin-left:4px">COORD</span>' : ""}</td>
            <td>${esc(p.departamento_siglas || p.departamento_nombre) || "-"}</td>
            <td>${p.email ? `<a href="mailto:${esc(p.email)}">${esc(p.email)}</a>` : "-"}</td>
            <td>${esc(p.despacho) || "-"}</td>
            <td style="font-size:12px;color:#777">${esc(p.curso_academico || "-")}</td>
          </tr>`;
        });
        html += "</tbody></table></div>";
      } else {
        html += '<p style="color:#777;font-size:13px">Sin profesorado registrado en profesor_asignatura. Ejecuta "Cargar docencia" desde la vista de titulación.</p>';
      }

      $modalTitle.textContent = asig.nombre;
      $modalBody.innerHTML = html;

      // Bind chunk buttons
      $modalBody.querySelectorAll(".btn-ver-chunks").forEach((btn) =>
        btn.addEventListener("click", () => loadChunksInModal(btn.dataset.planId))
      );
      // Click en fila de profesor -> abrir detalle
      $modalBody.querySelectorAll("tr[data-profesor-id]").forEach((tr) =>
        tr.addEventListener("click", (e) => {
          if (e.target.tagName === "A") return;
          openProfesorDetail(tr.dataset.profesorId);
        })
      );
    } catch (err) {
      $modalBody.innerHTML = '<p style="color:red">Error: ' + esc(err.message) + "</p>";
    }
  }

  async function loadChunksInModal(planId) {
    $modalBody.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Cargando chunks...</div>';
    try {
      const chunks = await fetchJSON(API("/api/admin/planes_docentes/" + planId + "/chunks"));
      if (!chunks.length) {
        $modalBody.innerHTML = '<p style="color:#777">No hay chunks para este plan.</p>';
        return;
      }

      // Agrupar por seccion
      const secciones = {};
      chunks.forEach((c) => {
        const s = c.seccion || "Sin seccion";
        if (!secciones[s]) secciones[s] = [];
        secciones[s].push(c);
      });

      let html = `<p style="margin-bottom:16px;font-size:13px;color:#777">${chunks.length} chunks del proyecto docente reconstruido. Haz clic en una seccion para expandir.</p>`;
      html += '<div class="chunk-list">';

      Object.keys(secciones).forEach((sec) => {
        const items = secciones[sec];
        items.forEach((chunk, i) => {
          const sub = chunk.subseccion ? ` / ${esc(chunk.subseccion)}` : "";
          html += `
          <div class="chunk-item">
            <div class="chunk-header" data-chunk-id="${esc(chunk.id)}">
              <span class="chunk-section">${esc(sec)}${sub}</span>
              <span class="chunk-meta">${chunk.longitud} caracteres</span>
            </div>
            <div class="chunk-body" id="chunk-${esc(chunk.id)}">${esc(chunk.contenido)}</div>
          </div>`;
        });
      });

      html += "</div>";
      $modalBody.innerHTML = html;

      // Toggle chunks
      $modalBody.querySelectorAll(".chunk-header").forEach((hdr) =>
        hdr.addEventListener("click", () => {
          const body = document.getElementById("chunk-" + hdr.dataset.chunkId);
          if (body) body.classList.toggle("open");
        })
      );
    } catch (err) {
      $modalBody.innerHTML = '<p style="color:red">Error: ' + esc(err.message) + "</p>";
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  //  PROFESORES (Centros -> Departamentos -> Profesores)
  // ═══════════════════════════════════════════════════════════════════

  async function loadProfesores() {
    showLoading();
    setActiveTab("profesores");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "profesores", label: "Profesores" },
    ]);

    try {
      const centros = await fetchJSON(API("/api/admin/centros"));
      if (!centros.length) {
        showEmpty("building-columns", "No hay centros en la base de datos");
        return;
      }

      // Numero de profesores por centro (via profesores.centro_id o depto.centro_id)
      const conteos = await Promise.all(
        centros.map((c) =>
          fetchJSON(API("/api/admin/profesores?centro_id=" + c.id)).then((p) => p.length).catch(() => 0)
        )
      );

      const html =
        `<div class="section-header"><h2>Profesores por centro</h2><span class="count-badge">${centros.length}</span></div>` +
        `<div class="card-grid ${gridClass(centros.length)}">` +
        centros.map((c, i) => `
          <div class="entity-card" data-centro-id="${esc(c.id)}" data-centro-nombre="${esc(c.nombre)}" data-centro-codigous="${esc(c.codigo_us || "")}">
            <div class="card-icon"><i class="fa-solid fa-building-columns"></i></div>
            <div class="card-title">${esc(c.nombre)}</div>
            <div class="card-subtitle">${esc(c.codigo)}</div>
            <div class="card-meta">
              <span><i class="fa-solid fa-user-tie"></i> ${conteos[i]} profesores</span>
              <span><i class="fa-solid fa-graduation-cap"></i> ${c.num_titulaciones} titulaciones</span>
            </div>
          </div>`).join("") +
        "</div>";

      $main.innerHTML = html;

      $main.querySelectorAll(".entity-card").forEach((card) =>
        card.addEventListener("click", () =>
          loadDepartamentosCentro(card.dataset.centroId, card.dataset.centroNombre, card.dataset.centroCodigous)
        )
      );
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function loadDepartamentosCentro(centroId, centroNombre, centroCodigoUs) {
    showLoading();
    setActiveTab("profesores");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "profesores", label: "Profesores" },
      { view: "centro-profs", label: centroNombre || "Centro" },
    ]);

    try {
      const data = await fetchJSON(API("/api/admin/centros/" + centroId + "/departamentos"));
      const deptos = data.departamentos || [];
      const sinDepto = data.sin_departamento || { num_profesores: 0 };

      let html = `
        <div class="section-header">
          <h2>${esc(centroNombre)}</h2>
          <span class="count-badge">${deptos.length} departamentos</span>
          <button class="btn-crear" id="btn-enrich-centro">
            <i class="fa-solid fa-wand-magic-sparkles"></i> Enriquecer desde us.es
          </button>
          <button class="btn-crear" id="btn-refresh-enlaces" title="Busca cada profesor en el directorio PDI de us.es y guarda su enlace de perfil. Necesario para cargar docencia.">
            <i class="fa-solid fa-link"></i> Refrescar enlaces us.es
          </button>
        </div>`;

      if (!deptos.length && !sinDepto.num_profesores) {
        html += `<div class="empty-state">
          <i class="fa-solid fa-users"></i>
          <p>No hay departamentos ni profesores para este centro.</p>
          <p style="font-size:12px;margin-top:8px">Usa "Enriquecer desde us.es" para poblar.</p>
        </div>`;
      } else {
        const tiles = deptos.map((d) => `
          <div class="entity-card" data-depto-id="${esc(d.id)}" data-depto-nombre="${esc(d.nombre)}" data-centro-id="${esc(centroId)}" data-centro-nombre="${esc(centroNombre)}">
            <div class="card-icon"><i class="fa-solid fa-sitemap"></i></div>
            <div class="card-title">${esc(d.nombre)}</div>
            <div class="card-subtitle">${esc(d.siglas || "")}</div>
            <div class="card-meta">
              <span><i class="fa-solid fa-user-tie"></i> ${d.num_profesores} profesores</span>
            </div>
          </div>`).join("");

        const sinDeptoTile = sinDepto.num_profesores > 0 ? `
          <div class="entity-card depto-sin" data-sin-depto="1" data-centro-id="${esc(centroId)}" data-centro-nombre="${esc(centroNombre)}">
            <div class="card-icon"><i class="fa-solid fa-question"></i></div>
            <div class="card-title">Sin departamento</div>
            <div class="card-subtitle">Profesores sin departamento asignado</div>
            <div class="card-meta">
              <span><i class="fa-solid fa-user-tie"></i> ${sinDepto.num_profesores} profesores</span>
            </div>
          </div>` : "";

        html += `<div class="card-grid ${gridClass(deptos.length + (sinDepto.num_profesores > 0 ? 1 : 0))}">${tiles}${sinDeptoTile}</div>`;
      }

      $main.innerHTML = html;

      $main.querySelectorAll(".entity-card[data-depto-id]").forEach((card) =>
        card.addEventListener("click", () =>
          loadProfesoresDepto(card.dataset.deptoId, card.dataset.deptoNombre, card.dataset.centroId, card.dataset.centroNombre)
        )
      );
      $main.querySelectorAll(".entity-card[data-sin-depto]").forEach((card) =>
        card.addEventListener("click", () =>
          loadProfesoresSinDepto(card.dataset.centroId, card.dataset.centroNombre)
        )
      );
      document.getElementById("btn-enrich-centro")?.addEventListener("click", () =>
        abrirEnrichCentro(centroId, centroNombre, centroCodigoUs)
      );
      document.getElementById("btn-refresh-enlaces")?.addEventListener("click", () =>
        abrirRefreshEnlaces(centroId, centroNombre)
      );
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function loadProfesoresDepto(deptoId, deptoNombre, centroId, centroNombre) {
    showLoading();
    setActiveTab("profesores");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "profesores", label: "Profesores" },
      { view: "centro-profs", label: centroNombre || "Centro" },
      { view: "depto-profs", label: deptoNombre || "Departamento" },
    ]);

    try {
      const profes = await fetchJSON(API("/api/admin/profesores?departamento_id=" + deptoId));
      renderTablaProfesores(profes, {
        titulo: deptoNombre,
        count: profes.length,
        onBack: () => loadDepartamentosCentro(centroId, centroNombre, null),
        enrichBtn: {
          label: "Enriquecer desde us.es",
          handler: () => abrirEnrichDepto(deptoId, deptoNombre, centroId, centroNombre),
        },
      });
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function loadProfesoresSinDepto(centroId, centroNombre) {
    showLoading();
    setActiveTab("profesores");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "profesores", label: "Profesores" },
      { view: "centro-profs", label: centroNombre || "Centro" },
      { view: "sin-depto", label: "Sin departamento" },
    ]);

    try {
      const profes = await fetchJSON(API(`/api/admin/profesores?centro_id=${centroId}&sin_departamento=1`));
      renderTablaProfesores(profes, {
        titulo: "Sin departamento",
        count: profes.length,
      });
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  function renderTablaProfesores(profes, opts) {
    const enrichBtnHtml = opts.enrichBtn
      ? `<button class="btn-crear" id="btn-enrich-depto"><i class="fa-solid fa-wand-magic-sparkles"></i> ${esc(opts.enrichBtn.label)}</button>`
      : "";

    let html = `<div class="section-header"><h2>${esc(opts.titulo)}</h2><span class="count-badge">${opts.count}</span>${enrichBtnHtml}</div>`;

    if (!profes.length) {
      html += '<div class="empty-state"><i class="fa-solid fa-user-tie"></i><p>No hay profesores.</p></div>';
    } else {
      html += `<div class="data-table-container"><table class="data-table">
        <thead><tr>
          <th>Nombre</th><th>Departamento</th><th>Categoria</th>
          <th>Email</th><th>Despacho</th><th>Perfil</th>
        </tr></thead><tbody>`;
      profes.forEach((p) => {
        const fullName = p.apellidos ? `${esc(p.apellidos)}, ${esc(p.nombre)}` : esc(p.nombre || p.nombre_completo);
        html += `<tr data-profesor-id="${esc(p.id)}" style="cursor:pointer">
          <td><strong>${fullName}</strong></td>
          <td>${esc(p.departamento_nombre || p.departamento_siglas) || "-"}</td>
          <td>${esc(p.categoria_academica) || "-"}</td>
          <td>${p.email ? `<a href="mailto:${esc(p.email)}">${esc(p.email)}</a>` : "-"}</td>
          <td>${esc(p.despacho) || "-"}</td>
          <td>${p.enlace_perfil ? `<a href="${esc(p.enlace_perfil)}" target="_blank" rel="noreferrer"><i class="fa-solid fa-external-link"></i></a>` : "-"}</td>
        </tr>`;
      });
      html += "</tbody></table></div>";
    }

    $main.innerHTML = html;

    $main.querySelectorAll("tr[data-profesor-id]").forEach((tr) =>
      tr.addEventListener("click", (e) => {
        if (e.target.tagName === "A") return;
        openProfesorDetail(tr.dataset.profesorId);
      })
    );

    if (opts.enrichBtn) {
      document.getElementById("btn-enrich-depto")?.addEventListener("click", opts.enrichBtn.handler);
    }
  }

  async function openProfesorDetail(id) {
    openModal("Cargando...", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i></div>');
    try {
      const [p, asigs] = await Promise.all([
        fetchJSON(API("/api/admin/profesores/" + id)),
        fetchJSON(API("/api/admin/profesores/" + id + "/asignaturas")),
      ]);
      const fullName = p.apellidos ? `${p.apellidos}, ${p.nombre}` : (p.nombre_completo || p.nombre);
      $modalTitle.textContent = fullName;

      let html = `<div class="detail-grid">
        <div class="detail-field"><div class="field-label">Centro</div><div class="field-value">${esc(p.centro_nombre) || "-"}</div></div>
        <div class="detail-field"><div class="field-label">Departamento</div><div class="field-value">${esc(p.departamento_nombre) || "Sin departamento"}</div></div>
        <div class="detail-field"><div class="field-label">Categoria</div><div class="field-value">${esc(p.categoria_academica) || "-"}</div></div>
        <div class="detail-field"><div class="field-label">Email</div><div class="field-value">${p.email ? `<a href="mailto:${esc(p.email)}">${esc(p.email)}</a>` : "-"}</div></div>
        <div class="detail-field"><div class="field-label">Telefono</div><div class="field-value">${esc(p.telefono) || "-"}</div></div>
        <div class="detail-field"><div class="field-label">Despacho</div><div class="field-value">${esc(p.despacho) || "-"}</div></div>
        <div class="detail-field"><div class="field-label">ORCID</div><div class="field-value">${esc(p.orcid) || "-"}</div></div>
        <div class="detail-field"><div class="field-label">Web personal</div><div class="field-value">${p.web_personal ? `<a href="${esc(p.web_personal)}" target="_blank" rel="noreferrer">${esc(p.web_personal)}</a>` : "-"}</div></div>
        <div class="detail-field"><div class="field-label">Perfil us.es</div><div class="field-value">${p.enlace_perfil ? `<a href="${esc(p.enlace_perfil)}" target="_blank" rel="noreferrer">Ver perfil</a>` : "-"}</div></div>
      </div>`;

      html += `<h3 style="margin:24px 0 12px;font-family:'Raleway',sans-serif;font-weight:600;font-size:16px"><i class="fa-solid fa-chalkboard-user"></i> Asignaturas que imparte (${asigs.length})</h3>`;
      if (asigs.length) {
        html += '<div class="data-table-container"><table class="data-table"><thead><tr><th>Código</th><th>Asignatura</th><th>Titulación</th><th>Curso</th><th>Año acad.</th></tr></thead><tbody>';
        asigs.forEach((a) => {
          html += `<tr data-asignatura-id="${esc(a.id)}" style="cursor:pointer">
            <td><code>${esc(a.codigo)}</code></td>
            <td><strong>${esc(a.nombre)}</strong>${a.es_coordinador ? ' <span style="background:#fee;color:#c00;font-size:10px;padding:2px 6px;border-radius:3px;margin-left:4px">COORD</span>' : ""}</td>
            <td>${esc(a.titulacion_codigo || "-")}</td>
            <td>${a.curso || "-"}</td>
            <td style="font-size:12px;color:#777">${esc(a.curso_academico || "-")}</td>
          </tr>`;
        });
        html += "</tbody></table></div>";
      } else {
        html += '<p style="color:#777;font-size:13px">Sin docencia registrada. Ejecuta "Cargar docencia" desde la vista de titulación.</p>';
      }

      $modalBody.innerHTML = html;

      // Click en fila de asignatura -> abrir detalle
      $modalBody.querySelectorAll("tr[data-asignatura-id]").forEach((tr) =>
        tr.addEventListener("click", () => openAsignaturaDetail(tr.dataset.asignaturaId))
      );
    } catch (err) {
      $modalBody.innerHTML = '<p style="color:red">Error: ' + esc(err.message) + "</p>";
    }
  }

  // ─── Enrich desde us.es ─────────────────────────────────────────

  async function abrirEnrichCentro(centroId, centroNombre, codigoUs) {
    const sugerido = codigoUs || normalizarSlug(centroNombre);
    openModal("Enriquecer centro desde us.es", `
      <p style="font-size:13px;color:#555;margin-bottom:14px">
        Se scrapeara la pagina del centro en us.es para descubrir departamentos
        y profesores, y se enriquecera la base de datos (email, categoria,
        enlace de perfil).
      </p>
      <div class="form-field">
        <label>Slug del centro en us.es <span class="required">*</span></label>
        <input type="text" id="enrich-slug" value="${esc(sugerido)}" placeholder="escuela-tecnica-superior-de-ingenieria-informatica">
        <p style="font-size:11px;color:#777;margin-top:4px">URL: https://www.us.es/centros/<strong id="enrich-slug-preview">${esc(sugerido)}</strong></p>
      </div>
      <div class="form-field">
        <label>Nombre del centro para busqueda PDI</label>
        <input type="text" id="enrich-nombre" value="${esc(centroNombre)}" placeholder="nombre para filtrar en el directorio">
        <p style="font-size:11px;color:#777;margin-top:4px">
          Puede ser una coincidencia parcial (ej: "escuela tecnica superior de ingenieria informatica").
        </p>
      </div>
      <div id="enrich-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-enrich-submit"><i class="fa-solid fa-wand-magic-sparkles"></i> Enriquecer</button>
      </div>`);

    document.getElementById("enrich-slug").addEventListener("input", (e) => {
      const p = document.getElementById("enrich-slug-preview");
      if (p) p.textContent = e.target.value;
    });

    document.getElementById("btn-enrich-submit").addEventListener("click", async () => {
      const slug = document.getElementById("enrich-slug").value.trim();
      const nombre = document.getElementById("enrich-nombre").value.trim();
      const $msg = document.getElementById("enrich-msg");
      const $btn = document.getElementById("btn-enrich-submit");
      if (!slug) { $msg.innerHTML = formError("Slug obligatorio"); return; }
      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Scrapeando us.es... (puede tardar varios minutos)</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/centros/" + centroId + "/enrich_profesores"), {
          codigo_us: slug,
          nombre_us: nombre,
        });
        const p = res.profesores || {};
        let html = `<div class="form-success">
          <strong>${(res.departamentos_encontrados || []).length}</strong> departamentos sincronizados.<br>
          <strong>${p.creados || 0}</strong> profesores creados,
          <strong>${p.actualizados || 0}</strong> actualizados
          (${p.total_encontrados || 0} encontrados en us.es).
        </div>`;
        if ((p.errores || []).length) {
          html += `<div class="form-error">${p.errores.length} errores. Ver consola.</div>`;
          console.warn("Errores enriquecimiento:", p.errores);
        }
        $msg.innerHTML = html;
        $btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cerrar';
        $btn.disabled = false;
        $btn.onclick = () => { closeModal(); loadDepartamentosCentro(centroId, centroNombre, slug); };
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
      }
    });
  }

  async function abrirEnrichDepto(deptoId, deptoNombre, centroId, centroNombre) {
    openModal("Enriquecer departamento desde us.es", `
      <p style="font-size:13px;color:#555;margin-bottom:14px">
        Se buscaran en el directorio PDI de us.es los profesores cuyo
        departamento coincida con <strong>${esc(deptoNombre)}</strong> y cuyo
        centro sea <strong>${esc(centroNombre)}</strong>.
      </p>
      <div id="enrich-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-enrich-depto-submit">
          <i class="fa-solid fa-wand-magic-sparkles"></i> Enriquecer
        </button>
      </div>`);

    document.getElementById("btn-enrich-depto-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("enrich-msg");
      const $btn = document.getElementById("btn-enrich-depto-submit");
      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Scrapeando us.es...</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/departamentos/" + deptoId + "/enrich_profesores"), {});
        const p = res.profesores || {};
        let html = `<div class="form-success">
          <strong>${p.creados || 0}</strong> creados,
          <strong>${p.actualizados || 0}</strong> actualizados
          (${p.total_encontrados || 0} encontrados en us.es).
        </div>`;
        if ((p.errores || []).length) {
          html += `<div class="form-error">${p.errores.length} errores. Ver consola.</div>`;
          console.warn("Errores enriquecimiento:", p.errores);
        }
        $msg.innerHTML = html;
        $btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cerrar';
        $btn.disabled = false;
        $btn.onclick = () => { closeModal(); loadProfesoresDepto(deptoId, deptoNombre, centroId, centroNombre); };
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
      }
    });
  }

  async function abrirRefreshEnlaces(centroId, centroNombre) {
    openModal("Refrescar enlaces us.es", `
      <p style="font-size:13px;color:#555;margin-bottom:14px">
        Por cada profesor del centro que no tenga enlace al directorio PDI de
        us.es, se buscara su perfil por nombre y se guardara el enlace.
        Esto es <strong>prerequisito</strong> para "Cargar docencia" (tabla
        profesor_asignatura).
      </p>
      <p style="font-size:12px;color:#777;margin-bottom:14px">
        Puede tardar varios minutos segun el numero de profesores.
      </p>
      <div id="refresh-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-refresh-submit">
          <i class="fa-solid fa-link"></i> Refrescar enlaces
        </button>
      </div>`);

    document.getElementById("btn-refresh-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("refresh-msg");
      const $btn = document.getElementById("btn-refresh-submit");
      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Buscando en us.es... (puede tardar)</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/centros/" + centroId + "/refresh_enlaces_us"), {});
        const noEnc = res.no_encontrados || [];
        let html = `<div class="form-success">
          <strong>${res.ya_con_enlace_us || 0}</strong> ya tenian enlace us.es.<br>
          <strong>${res.resueltos || 0}</strong> enlaces nuevos resueltos.<br>
          <strong>${noEnc.length}</strong> sin resolver (0 o >1 coincidencias).
        </div>`;
        if (noEnc.length) {
          const lista = noEnc.slice(0, 15).map((x) =>
            `<li>${esc(x.nombre || x.id)} \u2014 ${esc(x.motivo || "")}</li>`
          ).join("");
          html += `<details style="margin-top:8px">
            <summary style="cursor:pointer;font-size:12px">Ver no resueltos (${noEnc.length})</summary>
            <ul style="font-size:12px;margin-top:6px">${lista}</ul>
          </details>`;
          console.warn("No resueltos:", noEnc);
        }
        $msg.innerHTML = html;
        $btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cerrar';
        $btn.disabled = false;
        $btn.onclick = () => closeModal();
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
      }
    });
  }

  async function abrirCargarDocencia(titulacionId, titulacionNombre) {
    openModal("Cargar docencia desde us.es", `
      <p style="font-size:13px;color:#555;margin-bottom:14px">
        Para cada profesor del centro con enlace us.es, se scrapeara su
        seccion <strong>"Asignaturas que imparte"</strong> y se poblara la
        tabla <code>profesor_asignatura</code> de <strong>${esc(titulacionNombre)}</strong>.
      </p>
      <p style="font-size:12px;color:#777;margin-bottom:14px">
        <strong>Requisito:</strong> los profesores del centro deben tener su
        enlace us.es guardado. Si no, ejecuta antes
        <em>"Refrescar enlaces us.es"</em> desde la pesta\u00f1a Profesores.
      </p>
      <div id="docencia-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-docencia-submit">
          <i class="fa-solid fa-chalkboard-user"></i> Cargar docencia
        </button>
      </div>`);

    document.getElementById("btn-docencia-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("docencia-msg");
      const $btn = document.getElementById("btn-docencia-submit");
      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Scrapeando perfiles us.es... (puede tardar varios minutos)</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/titulaciones/" + titulacionId + "/sync_docencia"), {});
        const noMatch = res.ejemplos_no_matcheadas || [];
        let html = `<div class="form-success">
          <strong>${res.total_profes || 0}</strong> profesores procesados,
          <strong>${res.profes_con_docencia || 0}</strong> con docencia.<br>
          <strong>${res.relaciones_creadas || 0}</strong> relaciones creadas,
          <strong>${res.ya_existentes || 0}</strong> ya existentes.<br>
          <strong>${res.no_matcheadas_en_titulacion || 0}</strong> asignaturas us.es
          no matcheadas con esta titulacion (otras carreras).
        </div>`;
        if (noMatch.length) {
          const lista = noMatch.map((x) =>
            `<li><code>${esc(x.codigo_us)}</code> \u2014 ${esc(x.nombre_us)} <em>(${esc(x.titulacion_slug)})</em></li>`
          ).join("");
          html += `<details style="margin-top:8px">
            <summary style="cursor:pointer;font-size:12px">Ver ejemplos no matcheados (${noMatch.length})</summary>
            <ul style="font-size:12px;margin-top:6px">${lista}</ul>
          </details>`;
        }
        if ((res.errores || []).length) {
          html += `<div class="form-error">${res.errores.length} errores. Ver consola.</div>`;
          console.warn("Errores sync docencia:", res.errores);
        }
        $msg.innerHTML = html;
        $btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cerrar';
        $btn.disabled = false;
        $btn.onclick = () => closeModal();
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
      }
    });
  }

  function normalizarSlug(texto) {
    if (!texto) return "";
    return texto
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  }

  // ═══════════════════════════════════════════════════════════════════
  //  HORARIOS (Centros -> Titulaciones -> Tabla)
  // ═══════════════════════════════════════════════════════════════════

  const DIAS_SEMANA = { 1: "Lunes", 2: "Martes", 3: "Miércoles", 4: "Jueves", 5: "Viernes", 6: "Sábado" };

  function horariosDisclaimerHTML() {
    return `<div class="disclaimer">
      <i class="fa-solid fa-circle-info"></i>
      <div>
        <strong>Extracción de horarios dependiente de centro.</strong>
        Cada centro publica sus horarios en un formato distinto (PDF, web propia, etc.),
        por lo que la extracción automática requiere un extractor específico en
        <code>admin/horarios_extractores/</code>. Actualmente solo ETSII está soportada;
        añadir un nuevo centro requiere crear un extractor equivalente.
      </div>
    </div>`;
  }

  async function loadHorarios() {
    showLoading();
    setActiveTab("horarios");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "horarios", label: "Horarios" },
    ]);

    try {
      const centros = await fetchJSON(API("/api/admin/horarios/centros"));
      if (!centros.length) {
        showEmpty("building-columns", "No hay centros en la base de datos");
        return;
      }

      const cards = centros.map((c) => {
        const badge = c.extraccion_soportada
          ? '<span class="tag tag-completado">Extracción disponible</span>'
          : '<span class="tag tag-pendiente">Extracción no soportada</span>';
        return `
          <div class="entity-card" data-centro-id="${esc(c.id)}" data-centro-codigo="${esc(c.codigo)}" data-centro-nombre="${esc(c.nombre)}" data-extraccion="${c.extraccion_soportada ? "1" : "0"}">
            <div class="card-icon"><i class="fa-solid fa-building-columns"></i></div>
            <div class="card-title">${esc(c.nombre)}</div>
            <div class="card-subtitle">${esc(c.codigo)}</div>
            <div class="card-meta">
              <span><i class="fa-solid fa-clock"></i> ${c.num_horarios} horarios</span>
              <span><i class="fa-solid fa-graduation-cap"></i> ${c.num_titulaciones} titulaciones</span>
            </div>
            <div style="margin-top:10px">${badge}</div>
          </div>`;
      }).join("");

      $main.innerHTML =
        `<div class="section-header"><h2>Horarios por centro</h2><span class="count-badge">${centros.length}</span></div>` +
        horariosDisclaimerHTML() +
        `<div class="card-grid ${gridClass(centros.length)}">${cards}</div>`;

      $main.querySelectorAll(".entity-card").forEach((card) =>
        card.addEventListener("click", () =>
          loadTitulacionesHorarios(
            card.dataset.centroId, card.dataset.centroCodigo,
            card.dataset.centroNombre, card.dataset.extraccion === "1"
          )
        )
      );
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function loadTitulacionesHorarios(centroId, centroCodigo, centroNombre, extraccionSoportada) {
    showLoading();
    setActiveTab("horarios");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "horarios", label: "Horarios" },
      { view: "centro-horarios", label: centroNombre || "Centro" },
    ]);

    try {
      const tits = await fetchJSON(API("/api/admin/horarios/titulaciones?centro_id=" + centroId));

      const btnGenerar = extraccionSoportada
        ? `<button class="btn-crear" id="btn-gen-horarios"><i class="fa-solid fa-wand-magic-sparkles"></i> Generar horarios</button>`
        : "";

      let html = `<div class="section-header"><h2>${esc(centroNombre)} — Horarios</h2><span class="count-badge">${tits.length} titulaciones</span>${btnGenerar}</div>`;
      html += horariosDisclaimerHTML();

      if (!extraccionSoportada) {
        html += `<div class="form-error" style="margin-bottom:16px">
          <i class="fa-solid fa-triangle-exclamation"></i>
          Este centro no tiene extractor de horarios. Para añadirlo crea un módulo en <code>admin/horarios_extractores/</code> y regístralo.
        </div>`;
      }

      if (!tits.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-graduation-cap"></i><p>No hay titulaciones en este centro</p></div>';
      } else {
        html += `<div class="card-grid ${gridClass(tits.length)}">` +
          tits.map((t) => `
            <div class="entity-card" data-tit-id="${esc(t.id)}" data-tit-nombre="${esc(t.nombre)}" data-centro-id="${esc(centroId)}" data-centro-nombre="${esc(centroNombre)}" data-centro-codigo="${esc(centroCodigo)}" data-extraccion="${extraccionSoportada ? "1" : "0"}">
              <div class="card-icon"><i class="fa-solid fa-graduation-cap"></i></div>
              <div class="card-title">${esc(t.nombre)}</div>
              <div class="card-subtitle">${esc(t.codigo)}</div>
              <div class="card-meta">
                <span><i class="fa-solid fa-clock"></i> ${t.num_horarios} horarios</span>
                <span><i class="fa-solid fa-users"></i> ${t.num_grupos} grupos</span>
              </div>
            </div>`).join("") +
          "</div>";
      }

      $main.innerHTML = html;

      $main.querySelectorAll(".entity-card[data-tit-id]").forEach((card) =>
        card.addEventListener("click", () =>
          loadHorariosTabla(card.dataset.titId, card.dataset.titNombre, card.dataset.centroId, card.dataset.centroNombre, card.dataset.centroCodigo, card.dataset.extraccion === "1")
        )
      );
      document.getElementById("btn-gen-horarios")?.addEventListener("click", () =>
        abrirGenerarHorarios(centroId, centroCodigo, centroNombre)
      );
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function loadHorariosTabla(titId, titNombre, centroId, centroNombre, centroCodigo, extraccionSoportada) {
    showLoading();
    setActiveTab("horarios");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "horarios", label: "Horarios" },
      { view: "centro-horarios", label: centroNombre || "Centro" },
      { view: "tit-horarios", label: titNombre || "Titulación" },
    ]);

    try {
      const horarios = await fetchJSON(API("/api/admin/horarios?titulacion_id=" + titId));
      let html = `<div class="section-header"><h2>${esc(titNombre)}</h2><span class="count-badge">${horarios.length}</span></div>`;

      if (!horarios.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-clock"></i><p>No hay horarios para esta titulación</p></div>';
      } else {
        // Agrupar por curso y grupo
        const porCursoGrupo = {};
        horarios.forEach((h) => {
          const key = `${h.curso || 0}|${h.grupo_numero}`;
          if (!porCursoGrupo[key]) porCursoGrupo[key] = { curso: h.curso || 0, grupo: h.grupo_numero, items: [] };
          porCursoGrupo[key].items.push(h);
        });

        const keys = Object.keys(porCursoGrupo).sort();
        keys.forEach((k) => {
          const info = porCursoGrupo[k];
          html += `<div class="curso-group">`;
          html += `<div class="curso-group-title"><i class="fa-solid fa-layer-group"></i> Curso ${info.curso} · Grupo ${esc(info.grupo)} (${info.items.length} horarios)</div>`;
          html += `<div class="data-table-container"><table class="data-table"><thead><tr>
            <th>Asignatura</th><th>Día</th><th>Inicio</th><th>Fin</th><th>Aula</th>
          </tr></thead><tbody>`;
          info.items.forEach((h) => {
            html += `<tr>
              <td><strong>${esc(h.asignatura_nombre)}</strong><br><small style="color:#777">${esc(h.asignatura_codigo)}</small></td>
              <td>${DIAS_SEMANA[h.dia_semana] || esc(h.dia_semana)}</td>
              <td>${esc(h.hora_inicio)}</td>
              <td>${esc(h.hora_fin)}</td>
              <td>${esc(h.aula) || "-"}</td>
            </tr>`;
          });
          html += "</tbody></table></div></div>";
        });
      }

      $main.innerHTML = html;
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function abrirGenerarHorarios(centroId, centroCodigo, centroNombre) {
    openModal("Generar horarios — " + centroNombre, `
      <p style="font-size:13px;color:#555;margin-bottom:14px">
        Ejecuta el extractor de horarios del centro <strong>${esc(centroNombre)}</strong>.
        Descarga el PDF oficial, extrae los horarios y los inserta en la base de datos.
      </p>
      <div class="form-field">
        <label>Curso académico</label>
        <input type="text" id="gen-curso" value="2025-26" placeholder="2025-26">
      </div>
      <label style="display:flex;gap:8px;align-items:center;margin:12px 0;font-size:13px">
        <input type="checkbox" id="gen-limpiar">
        Borrar horarios existentes del centro antes de insertar
      </label>
      <div class="disclaimer" style="margin:14px 0">
        <i class="fa-solid fa-clock"></i>
        <div>Este proceso tarda ~30-60s. No cierres la ventana.</div>
      </div>
      <div id="gen-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-gen-submit"><i class="fa-solid fa-play"></i> Generar</button>
      </div>`);

    document.getElementById("btn-gen-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("gen-msg");
      const $btn = document.getElementById("btn-gen-submit");
      const curso = document.getElementById("gen-curso").value.trim();
      const limpiar = document.getElementById("gen-limpiar").checked;

      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Descargando PDF y procesando...</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/horarios/generar"), {
          centro_id: centroId,
          curso_academico: curso,
          limpiar,
        });

        let html = `<div class="form-success">
          <strong>${res.horarios_insertados || 0}</strong> horarios insertados,
          <strong>${res.grupos_clase_insertados || 0}</strong> grupos_clase nuevos,
          <strong>${res.aulas_insertadas || 0}</strong> aulas nuevas.<br>
          Titulaciones procesadas: ${(res.titulaciones_procesadas || []).join(", ") || "-"}.
        </div>`;
        if ((res.alias_no_resueltos || []).length) {
          html += `<div class="form-error" style="margin-top:10px">
            <strong>Alias no resueltos:</strong> ${res.alias_no_resueltos.join(", ")}<br>
            <small>(son asignaturas cuya abreviatura no está en el diccionario de alias; revisa <code>actions/shared/config.py</code>)</small>
          </div>`;
        }
        $msg.innerHTML = html;
        $btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cerrar';
        $btn.disabled = false;
        $btn.onclick = () => { closeModal(); loadTitulacionesHorarios(centroId, centroCodigo, centroNombre, true); };
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
      }
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  //  CONVERSACIONES
  // ═══════════════════════════════════════════════════════════════════

  let convPage = 0;
  const CONV_LIMIT = 30;

  function _fmtFecha(ts) {
    return ts ? new Date(ts).toLocaleString("es-ES") : "-";
  }

  function _fmtDuracion(inicio, fin) {
    if (!inicio || !fin) return "-";
    const s = Math.max(1, Math.round((new Date(fin) - new Date(inicio)) / 1000));
    if (s < 60) return s + "s";
    const m = Math.round(s / 60);
    if (m < 60) return m + " min";
    return (m / 60).toFixed(1) + " h";
  }

  async function loadConversaciones(page) {
    if (page === undefined) page = 0;
    convPage = page;
    showLoading();
    setActiveTab("conversaciones");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "conversaciones", label: "Conversaciones" },
    ]);

    try {
      const data = await fetchJSON(
        API(`/api/admin/conversaciones/sesiones?limit=${CONV_LIMIT}&offset=${page * CONV_LIMIT}`)
      );
      const totalPages = Math.ceil(data.total / CONV_LIMIT);

      let html = `<div class="section-header">
        <h2>Conversaciones</h2>
        <span class="count-badge">${data.total} sesiones</span>
        <button class="btn-crear" id="btn-export-all"><i class="fa-solid fa-download"></i> Exportar esta página</button>
      </div>`;

      if (!data.rows.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-comments"></i><p>No hay conversaciones registradas</p></div>';
      } else {
        html += `<div class="data-table-container"><table class="data-table">
          <thead><tr>
            <th title="Revisada">✓</th>
            <th>Sesión</th><th>Mensajes</th><th>Primer mensaje</th>
            <th>Último mensaje</th><th>Inicio</th><th>Duración</th>
          </tr></thead><tbody>`;
        data.rows.forEach((r) => {
          const shortId = (r.session_id || "").substring(0, 14);
          const checked = r.revisada ? "checked" : "";
          html += `<tr data-session-id="${esc(r.session_id)}" class="${r.revisada ? 'row-revisada' : ''}" style="cursor:pointer">
            <td style="text-align:center" class="col-revisada">
              <input type="checkbox" class="chk-revisada" ${checked}
                     data-session-id="${esc(r.session_id)}"
                     title="Marcar como revisada" />
            </td>
            <td style="font-size:11px;font-family:monospace">${esc(shortId)}…</td>
            <td><strong>${r.num_mensajes}</strong></td>
            <td class="truncate">${esc(r.primer_mensaje)}</td>
            <td class="truncate">${esc(r.ultimo_mensaje)}</td>
            <td style="white-space:nowrap;font-size:12px">${_fmtFecha(r.inicio)}</td>
            <td>${_fmtDuracion(r.inicio, r.fin)}</td>
          </tr>`;
        });
        html += "</tbody></table></div>";

        html += `<div class="pagination">
          <button id="conv-prev" ${page <= 0 ? "disabled" : ""}><i class="fa-solid fa-chevron-left"></i> Anterior</button>
          <span class="page-info">Página ${page + 1} de ${totalPages || 1}</span>
          <button id="conv-next" ${page + 1 >= totalPages ? "disabled" : ""}>Siguiente <i class="fa-solid fa-chevron-right"></i></button>
        </div>`;
      }

      $main.innerHTML = html;

      $main.querySelectorAll("tr[data-session-id]").forEach((tr) =>
        tr.addEventListener("click", (e) => {
          // Evita navegar cuando el click es sobre el checkbox.
          if (e.target.closest(".col-revisada")) return;
          loadSesionChat(tr.dataset.sessionId);
        })
      );

      $main.querySelectorAll(".chk-revisada").forEach((chk) => {
        chk.addEventListener("click", (e) => e.stopPropagation());
        chk.addEventListener("change", async (e) => {
          const sid = chk.dataset.sessionId;
          const revisada = chk.checked;
          chk.disabled = true;
          try {
            const res = await fetch(
              API("/api/admin/conversaciones/sesiones/" + encodeURIComponent(sid) + "/revisada"),
              { method: "PATCH", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ revisada }) }
            );
            if (!res.ok) throw new Error("HTTP " + res.status);
            const tr = chk.closest("tr");
            if (tr) tr.classList.toggle("row-revisada", revisada);
          } catch (err) {
            chk.checked = !revisada;
            alert("Error marcando como revisada: " + err.message);
          } finally {
            chk.disabled = false;
          }
        });
      });

      const prev = document.getElementById("conv-prev");
      const next = document.getElementById("conv-next");
      if (prev) prev.addEventListener("click", () => loadConversaciones(convPage - 1));
      if (next) next.addEventListener("click", () => loadConversaciones(convPage + 1));
      document.getElementById("btn-export-all")?.addEventListener("click", () => exportarSesionesPagina(data.rows));
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  async function exportarSesionesPagina(sesiones) {
    if (!sesiones?.length) return;
    const $btn = document.getElementById("btn-export-all");
    if ($btn) {
      $btn.disabled = true;
      $btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Exportando...';
    }

    try {
      const detalles = await Promise.all(
        sesiones.map((s) =>
          fetchJSON(API("/api/admin/conversaciones/sesiones/" + encodeURIComponent(s.session_id)))
            .then((d) => ({ session_id: s.session_id, mensajes: d.mensajes || [] }))
        )
      );

      let contenido = `# Export de ${detalles.length} sesiones\n\n_Generado ${new Date().toLocaleString("es-ES")}_\n\n---\n\n`;
      detalles.forEach((d, idx) => {
        const msgs = d.mensajes;
        contenido += `# Sesión ${idx + 1}: ${d.session_id}\n\n`;
        if (msgs.length) {
          contenido += `**Inicio:** ${_fmtFecha(msgs[0].created_at)}  \n`;
          contenido += `**Fin:** ${_fmtFecha(msgs[msgs.length - 1].created_at)}  \n`;
          contenido += `**Intercambios:** ${msgs.length}\n\n`;
        }
        msgs.forEach((m, i) => {
          contenido += `## Intercambio ${i + 1} — ${_fmtFecha(m.created_at)}\n\n`;
          contenido += `**Usuario:**\n\n${m.user_message || ""}\n\n`;
          contenido += `**Bot:**\n\n${m.bot_response || ""}\n\n---\n\n`;
        });
        contenido += "\n";
      });

      const blob = new Blob([contenido], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `conversaciones_${new Date().toISOString().slice(0, 10)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } finally {
      if ($btn) {
        $btn.disabled = false;
        $btn.innerHTML = '<i class="fa-solid fa-download"></i> Exportar esta página';
      }
    }
  }

  async function loadSesionChat(sessionId) {
    showLoading();
    setActiveTab("conversaciones");
    const shortId = (sessionId || "").substring(0, 14);
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "conversaciones", label: "Conversaciones" },
      { view: "sesion", label: "Sesión " + shortId + "…" },
    ]);

    try {
      const data = await fetchJSON(API("/api/admin/conversaciones/sesiones/" + encodeURIComponent(sessionId)));
      const msgs = data.mensajes || [];

      let html = `<div class="section-header">
        <h2>Sesión ${esc(shortId)}…</h2>
        <span class="count-badge">${msgs.length} intercambios</span>
        <button class="btn-crear" id="btn-export-md"><i class="fa-solid fa-file-lines"></i> Exportar .md</button>
        <button class="btn-crear" id="btn-export-txt"><i class="fa-solid fa-file"></i> Exportar .txt</button>
        <button class="btn-crear" id="btn-back-conv"><i class="fa-solid fa-arrow-left"></i> Volver</button>
      </div>
      <div class="chat-log">`;

      if (!msgs.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-comments"></i><p>Sin mensajes</p></div>';
      } else {
        msgs.forEach((m) => {
          const ts = _fmtFecha(m.created_at);
          html += `
            <div class="chat-row chat-user">
              <div class="chat-bubble chat-bubble-user">${esc(m.user_message)}</div>
              <div class="chat-ts">${esc(ts)}</div>
            </div>
            <div class="chat-row chat-bot">
              <div class="chat-bubble chat-bubble-bot">${esc(m.bot_response)}</div>
            </div>`;
        });
      }

      html += "</div>";
      $main.innerHTML = html;

      document.getElementById("btn-back-conv")?.addEventListener("click", () => loadConversaciones(convPage));
      document.getElementById("btn-export-md")?.addEventListener("click", () => exportarSesion(sessionId, msgs, "md"));
      document.getElementById("btn-export-txt")?.addEventListener("click", () => exportarSesion(sessionId, msgs, "txt"));
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  function exportarSesion(sessionId, msgs, formato) {
    const shortId = (sessionId || "").substring(0, 14);
    let contenido = "";

    if (formato === "md") {
      contenido = `# Sesión ${sessionId}\n\n`;
      if (msgs.length) {
        contenido += `**Inicio:** ${_fmtFecha(msgs[0].created_at)}  \n`;
        contenido += `**Fin:** ${_fmtFecha(msgs[msgs.length - 1].created_at)}  \n`;
        contenido += `**Intercambios:** ${msgs.length}\n\n---\n\n`;
      }
      msgs.forEach((m, i) => {
        contenido += `## Intercambio ${i + 1} — ${_fmtFecha(m.created_at)}\n\n`;
        contenido += `**Usuario:**\n\n${m.user_message || ""}\n\n`;
        contenido += `**Bot:**\n\n${m.bot_response || ""}\n\n---\n\n`;
      });
    } else {
      contenido = `Sesion: ${sessionId}\n`;
      if (msgs.length) {
        contenido += `Inicio: ${_fmtFecha(msgs[0].created_at)}\n`;
        contenido += `Fin: ${_fmtFecha(msgs[msgs.length - 1].created_at)}\n`;
        contenido += `Intercambios: ${msgs.length}\n`;
      }
      contenido += "\n" + "=".repeat(60) + "\n\n";
      msgs.forEach((m, i) => {
        contenido += `[${_fmtFecha(m.created_at)}]\n`;
        contenido += `Usuario: ${m.user_message || ""}\n\n`;
        contenido += `Bot: ${m.bot_response || ""}\n\n`;
        contenido += "-".repeat(60) + "\n\n";
      });
    }

    const mime = formato === "md" ? "text/markdown" : "text/plain";
    const ext = formato;
    const blob = new Blob([contenido], { type: `${mime};charset=utf-8` });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `sesion_${shortId}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ═══════════════════════════════════════════════════════════════════
  //  FEEDBACK
  // ═══════════════════════════════════════════════════════════════════

  let fbPage = 0;
  const FB_LIMIT = 50;

  async function loadFeedback(page) {
    if (page === undefined) page = 0;
    fbPage = page;
    showLoading();
    setActiveTab("feedback");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "feedback", label: "Feedback" },
    ]);

    try {
      const data = await fetchJSON(
        API(`/api/admin/feedback?limit=${FB_LIMIT}&offset=${page * FB_LIMIT}`)
      );
      const totalPages = Math.ceil(data.total / FB_LIMIT);

      let html = `<div class="section-header"><h2>Feedback de usuarios</h2><span class="count-badge">${data.total} total</span></div>`;

      if (!data.rows.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-star"></i><p>No hay feedback registrado</p></div>';
      } else {
        html += `<div class="data-table-container"><table class="data-table">
          <thead><tr>
            <th>Fecha</th><th>Valoracion</th><th>Mensaje usuario</th>
            <th>Respuesta bot</th><th>Comentario</th>
          </tr></thead><tbody>`;

        data.rows.forEach((r) => {
          const date = r.created_at ? new Date(r.created_at).toLocaleString("es-ES") : "-";
          const rating =
            r.rating === 1
              ? '<span class="tag tag-positivo"><i class="fa-solid fa-thumbs-up"></i> Positivo</span>'
              : '<span class="tag tag-negativo"><i class="fa-solid fa-thumbs-down"></i> Negativo</span>';
          html += `<tr>
            <td style="white-space:nowrap;font-size:12px">${date}</td>
            <td>${rating}</td>
            <td class="truncate">${esc(r.last_user_message)}</td>
            <td class="truncate">${esc(r.last_bot_response)}</td>
            <td>${esc(r.comment) || "-"}</td>
          </tr>`;
        });

        html += "</tbody></table></div>";

        html += `<div class="pagination">
          <button id="fb-prev" ${page <= 0 ? "disabled" : ""}><i class="fa-solid fa-chevron-left"></i> Anterior</button>
          <span class="page-info">Pagina ${page + 1} de ${totalPages || 1}</span>
          <button id="fb-next" ${page + 1 >= totalPages ? "disabled" : ""}>Siguiente <i class="fa-solid fa-chevron-right"></i></button>
        </div>`;
      }

      $main.innerHTML = html;

      const prev = document.getElementById("fb-prev");
      const next = document.getElementById("fb-next");
      if (prev) prev.addEventListener("click", () => loadFeedback(fbPage - 1));
      if (next) next.addEventListener("click", () => loadFeedback(fbPage + 1));
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  // ─── Utility ─────────────────────────────────────────────────────

  function setActiveTab(view) {
    document.querySelectorAll(".nav-tabs .tab").forEach((t) => {
      t.classList.toggle("active", t.dataset.view === view);
    });
  }

  // ═══════════════════════════════════════════════════════════════════
  //  FORMULARIOS DE CREACION
  // ═══════════════════════════════════════════════════════════════════

  // ─── Helpers de formulario ───────────────────────────────────────

  function formField(id, label, placeholder, required = true, value = "") {
    return `
      <div class="form-field">
        <label for="${id}">${label}${required ? ' <span class="required">*</span>' : ""}</label>
        <input type="text" id="${id}" placeholder="${placeholder}" value="${esc(value)}" ${required ? "required" : ""}>
      </div>`;
  }

  function formSelect(id, label, options, required = true) {
    const opts = options.map((o) => `<option value="${esc(o.value)}">${esc(o.label)}</option>`).join("");
    return `
      <div class="form-field">
        <label for="${id}">${label}${required ? ' <span class="required">*</span>' : ""}</label>
        <select id="${id}" ${required ? "required" : ""}><option value="">Selecciona...</option>${opts}</select>
      </div>`;
  }

  function formError(msg) {
    return `<div class="form-error"><i class="fa-solid fa-triangle-exclamation"></i> ${esc(msg)}</div>`;
  }

  function formSuccess(msg) {
    return `<div class="form-success"><i class="fa-solid fa-circle-check"></i> ${msg}</div>`;
  }

  // ─── Crear centro ────────────────────────────────────────────────

  async function abrirFormCentro() {
    openModal("Nuevo centro", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Cargando centros de Sevius...</div>');

    let centrosSevius;
    try {
      centrosSevius = await fetchJSON(API("/api/admin/sevius/centros"));
    } catch {
      $modalBody.innerHTML = formError("No se pudo conectar con Sevius");
      return;
    }

    // Filtrar los que ya existen en la BD
    let centrosEnBD = [];
    try {
      centrosEnBD = await fetchJSON(API("/api/admin/centros"));
    } catch {}
    const codigosEnBD = new Set(centrosEnBD.map((c) => c.codigo));

    const opsCentros = centrosSevius.map((c) => ({
      value: c.codigo_sevius + "||" + c.nombre,
      label: c.nombre,
    }));

    $modalBody.innerHTML = `
      <p style="font-size:13px;color:#555;margin-bottom:16px">
        Selecciona el centro de la Universidad de Sevilla que quieres añadir.
      </p>
      <form id="form-centro">
        ${formSelect("centro-sevius", "Centro (desde Sevius)", opsCentros)}
        <div id="centro-preview" style="margin:4px 0 8px;font-size:12px;color:#777"></div>
        ${formField("centro-codigo", "Codigo interno", "ETSII")}
        ${formField("centro-nombre-corto", "Nombre corto (opcional)", "ETSII", false)}
        <div id="form-centro-msg"></div>
        <div class="form-actions">
          <button type="submit" class="btn-submit"><i class="fa-solid fa-floppy-disk"></i> Crear centro</button>
        </div>
      </form>`;

    // Al seleccionar un centro de Sevius, pre-rellenar campos
    document.getElementById("centro-sevius").addEventListener("change", (e) => {
      const val = e.target.value;
      if (!val) return;
      const [codSevius, nombre] = val.split("||");
      // Sugerir codigo: ultima palabra en mayusculas del nombre
      const palabras = nombre.split(" ");
      const sugerencia = palabras[palabras.length - 1].toUpperCase().replace(/[^A-Z0-9]/g, "");
      document.getElementById("centro-codigo").value = sugerencia;
      document.getElementById("centro-nombre-corto").value = sugerencia;

      const $preview = document.getElementById("centro-preview");
      if (codigosEnBD.has(sugerencia)) {
        $preview.innerHTML = `<span style="color:#be0f2e"><i class="fa-solid fa-triangle-exclamation"></i> Un centro con codigo "${sugerencia}" ya existe en la BD</span>`;
      } else {
        $preview.innerHTML = `<span style="color:#2a7a2a"><i class="fa-solid fa-circle-check"></i> ${nombre}</span>`;
      }
    });

    document.getElementById("form-centro").addEventListener("submit", async (e) => {
      e.preventDefault();
      const $msg = document.getElementById("form-centro-msg");
      const $btn = e.target.querySelector("[type=submit]");
      const val = document.getElementById("centro-sevius").value;
      if (!val) { $msg.innerHTML = formError("Selecciona un centro"); return; }
      const [codSevius, nombre] = val.split("||");

      $msg.innerHTML = "";
      $btn.disabled = true;
      $btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creando...';

      try {
        const row = await postJSON(API("/api/admin/centros"), {
          codigo: document.getElementById("centro-codigo").value.trim(),
          nombre: nombre,
          nombre_corto: document.getElementById("centro-nombre-corto").value.trim(),
          codigo_sevius: codSevius,
        });
        $msg.innerHTML = formSuccess(`Centro <strong>${esc(row.nombre)}</strong> creado correctamente.`);
        setTimeout(() => { closeModal(); loadCentros(); }, 1500);
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
        $btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Crear centro';
      }
    });
  }

  // ─── Crear titulacion ────────────────────────────────────────────

  async function abrirFormTitulacion(centroId, centroNombre) {
    // Cargamos centros para el selector
    openModal("Nueva titulacion", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Cargando centros...</div>');
    let centros;
    try {
      centros = await fetchJSON(API("/api/admin/centros"));
    } catch {
      $modalBody.innerHTML = formError("No se pudieron cargar los centros");
      return;
    }

    const opcionesCentros = centros.map((c) => ({ value: c.id, label: c.nombre }));
    $modalBody.innerHTML = `
      <form id="form-tit">
        ${formSelect("tit-centro", "Centro", opcionesCentros)}
        ${formField("tit-codigo", "Codigo", "GII-IS")}
        ${formField("tit-nombre", "Nombre completo", "Grado en Ingenieria Informatica-Ingenieria del Software")}
        ${formField("tit-nombre-corto", "Nombre corto (opcional)", "Ing. Software", false)}
        ${formField("tit-creditos", "Creditos totales", "240", false, "240")}
        ${formField("tit-duracion", "Duracion (anos)", "4", false, "4")}
        <div id="form-tit-msg"></div>
        <div class="form-actions">
          <button type="submit" class="btn-submit"><i class="fa-solid fa-floppy-disk"></i> Crear titulacion</button>
        </div>
      </form>`;

    // Pre-seleccionar centro si venimos de uno
    if (centroId) document.getElementById("tit-centro").value = centroId;

    document.getElementById("form-tit").addEventListener("submit", async (e) => {
      e.preventDefault();
      const $msg = document.getElementById("form-tit-msg");
      const $btn = e.target.querySelector("[type=submit]");
      $msg.innerHTML = "";
      $btn.disabled = true;
      $btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Creando...';

      try {
        const row = await postJSON(API("/api/admin/titulaciones"), {
          centro_id: document.getElementById("tit-centro").value,
          codigo: document.getElementById("tit-codigo").value.trim(),
          nombre: document.getElementById("tit-nombre").value.trim(),
          nombre_corto: document.getElementById("tit-nombre-corto").value.trim(),
          creditos_totales: parseFloat(document.getElementById("tit-creditos").value) || 240,
          duracion_anios: parseInt(document.getElementById("tit-duracion").value) || 4,
        });
        $msg.innerHTML = formSuccess(`Titulacion <strong>${esc(row.nombre)}</strong> creada correctamente.`);
        setTimeout(() => { closeModal(); loadTitulaciones(centroId, centroNombre); }, 1500);
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
        $btn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Crear titulacion';
      }
    });
  }

  // ─── Enriquecer asignaturas desde us.es ──────────────────────────

  async function abrirEnrichAsignaturas(titulacionId, titulacionNombre) {
    openModal("Enriquecer datos desde us.es", `
      <p style="font-size:13px;color:#555;margin-bottom:16px">
        Se buscara <strong>${esc(titulacionNombre)}</strong> en la web de la Universidad de Sevilla
        y se actualizaran <strong>curso, creditos y tipologia</strong> de las asignaturas.
      </p>
      <div id="enrich-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-enrich-submit">
          <i class="fa-solid fa-wand-magic-sparkles"></i> Enriquecer datos
        </button>
      </div>`);

    document.getElementById("btn-enrich-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("enrich-msg");
      const $btn = document.getElementById("btn-enrich-submit");
      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Buscando en us.es y actualizando datos... (puede tardar unos segundos)</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/asignaturas/enrich"), {
          titulacion_id: titulacionId,
        });
        let msg = `<strong>${res.actualizadas.length}</strong> asignaturas actualizadas de ${res.total_bd} totales.`;
        if (res.no_encontradas.length) {
          msg += `<br><strong>${res.no_encontradas.length}</strong> no encontradas en us.es.`;
        }
        $msg.innerHTML = formSuccess(msg);
        setTimeout(() => { closeModal(); loadAsignaturas(titulacionId, titulacionNombre); }, 2000);
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
        $btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Enriquecer datos';
      }
    });
  }

  // ─── Sincronizar titulaciones desde Sevius ───────────────────────

  async function abrirFormSyncTitulaciones(centroId, centroNombre) {
    openModal("Sincronizar titulaciones desde Sevius", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Consultando centro...</div>');

    // Necesitamos el codigo_sevius del centro
    let centro;
    try {
      const centros = await fetchJSON(API("/api/admin/centros"));
      centro = centros.find((c) => c.id === centroId);
    } catch {
      $modalBody.innerHTML = formError("No se pudieron cargar los centros");
      return;
    }

    if (!centro || !centro.codigo_sevius) {
      $modalBody.innerHTML = formError("Este centro no tiene codigo de Sevius asociado. Recrealo seleccionandolo desde Sevius.");
      return;
    }

    // Preview: consultar titulaciones disponibles en Sevius
    let titsSevius;
    try {
      titsSevius = await fetchJSON(API("/api/admin/sevius/titulaciones?codcentro=" + centro.codigo_sevius));
    } catch {
      $modalBody.innerHTML = formError("No se pudo conectar con Sevius");
      return;
    }

    $modalBody.innerHTML = `
      <p style="font-size:13px;color:#555;margin-bottom:16px">
        Se importaran las titulaciones de <strong>${esc(centroNombre)}</strong> desde Sevius.
      </p>
      <div style="margin:12px 0;font-size:13px;color:#2a7a2a">
        <i class="fa-solid fa-circle-check"></i> ${titsSevius.length} titulaciones encontradas en Sevius
      </div>
      <div id="form-sync-tit-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-sync-tit-submit">
          <i class="fa-solid fa-rotate"></i> Sincronizar titulaciones
        </button>
      </div>`;

    document.getElementById("btn-sync-tit-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("form-sync-tit-msg");
      const $btn = document.getElementById("btn-sync-tit-submit");
      $msg.innerHTML = "";
      $btn.disabled = true;
      $btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sincronizando...';

      try {
        const res = await postJSON(API("/api/admin/titulaciones/sync"), {
          centro_id: centroId,
          codigo_sevius: centro.codigo_sevius,
        });
        const msg = `
          <strong>${res.creadas.length}</strong> titulaciones creadas,
          <strong>${res.existentes.length}</strong> ya existian
          (${res.total_sevius} en Sevius).`;
        $msg.innerHTML = formSuccess(msg);
        setTimeout(() => { closeModal(); loadTitulaciones(centroId, centroNombre); }, 2000);
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
        $btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Sincronizar titulaciones';
      }
    });
  }

  // ─── Sincronizar asignaturas desde Sevius ────────────────────────

  async function abrirFormSyncAsignaturas(titulacionId, titulacionNombre) {
    openModal("Sincronizar asignaturas desde Sevius", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Consultando datos...</div>');

    // Buscar la titulacion y su centro para obtener los codigos de Sevius
    let titulacion, centro;
    try {
      const tits = await fetchJSON(API("/api/admin/titulaciones"));
      titulacion = tits.find((t) => t.id === titulacionId);
      if (titulacion) {
        const centros = await fetchJSON(API("/api/admin/centros"));
        centro = centros.find((c) => c.nombre === titulacion.centro_nombre);
      }
    } catch {
      $modalBody.innerHTML = formError("No se pudieron cargar los datos");
      return;
    }

    if (!centro || !centro.codigo_sevius) {
      $modalBody.innerHTML = formError("El centro no tiene codigo de Sevius asociado. Recrealo seleccionandolo desde Sevius.");
      return;
    }
    if (!titulacion || !titulacion.codigo) {
      $modalBody.innerHTML = formError("La titulacion no tiene codigo asociado.");
      return;
    }

    const codcentro = centro.codigo_sevius;
    const codtit = titulacion.codigo;

    // Preview: consultar asignaturas en Sevius
    let asigsSevius;
    try {
      asigsSevius = await fetchJSON(API(`/api/admin/sevius/asignaturas?codcentro=${codcentro}&titulacion=${codtit}`));
    } catch {
      $modalBody.innerHTML = formError("No se pudo conectar con Sevius");
      return;
    }

    $modalBody.innerHTML = `
      <p style="font-size:13px;color:#555;margin-bottom:16px">
        Se importaran las asignaturas de <strong>${esc(titulacionNombre)}</strong> desde Sevius.
      </p>
      <div style="margin:12px 0;font-size:13px;color:#2a7a2a">
        <i class="fa-solid fa-circle-check"></i> ${asigsSevius.length} asignaturas encontradas en Sevius
      </div>
      <div id="form-sync-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="btn-sync-submit">
          <i class="fa-solid fa-rotate"></i> Sincronizar asignaturas
        </button>
      </div>`;

    document.getElementById("btn-sync-submit").addEventListener("click", async () => {
      const $msg = document.getElementById("form-sync-msg");
      const $btn = document.getElementById("btn-sync-submit");
      $msg.innerHTML = "";
      $btn.disabled = true;
      $btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sincronizando...';

      try {
        const res = await postJSON(API("/api/admin/asignaturas/sync"), {
          titulacion_id: titulacionId,
          codcentro: codcentro,
          codigo_titulacion_sevius: codtit,
        });

        const msg = `
          <strong>${res.creadas.length}</strong> asignaturas creadas,
          <strong>${res.existentes.length}</strong> ya existian
          (${res.total_sevius} en Sevius).`;
        $msg.innerHTML = formSuccess(msg);
        setTimeout(() => { closeModal(); loadAsignaturas(titulacionId, titulacionNombre); }, 2000);
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
        $btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Sincronizar asignaturas';
      }
    });
  }

  // ─── Vectorizar planes docentes ──────────────────────────────────

  async function abrirFormVectorizar(titulacionId, titulacionNombre) {
    openModal("Vectorizar planes docentes", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Cargando asignaturas...</div>');

    // Resolver codcentro + codigo titulacion Sevius
    let titulacion, centro;
    try {
      const tits = await fetchJSON(API("/api/admin/titulaciones"));
      titulacion = tits.find((t) => t.id === titulacionId);
      if (titulacion) {
        const centros = await fetchJSON(API("/api/admin/centros"));
        centro = centros.find((c) => c.nombre === titulacion.centro_nombre);
      }
    } catch {
      $modalBody.innerHTML = formError("No se pudieron cargar los datos");
      return;
    }
    if (!centro || !centro.codigo_sevius || !titulacion || !titulacion.codigo) {
      $modalBody.innerHTML = formError("Faltan codigos de Sevius en centro o titulacion");
      return;
    }

    let data;
    try {
      data = await fetchJSON(API("/api/admin/planes_docentes/vectorizables?titulacion_id=" + titulacionId));
    } catch (err) {
      $modalBody.innerHTML = formError("Error cargando asignaturas: " + err.message);
      return;
    }

    const asigs = data.asignaturas || [];
    if (!asigs.length) {
      $modalBody.innerHTML = formError("No hay asignaturas en esta titulacion");
      return;
    }

    const disponibles = asigs.filter((a) => !a.ya_vectorizada);
    const rows = asigs.map((a) => {
      const disabled = a.ya_vectorizada ? "disabled" : "";
      const badge = a.ya_vectorizada
        ? '<span class="tag tag-completado">Ya vectorizada</span>'
        : "";
      return `
        <label class="vec-row ${a.ya_vectorizada ? "vec-done" : ""}">
          <input type="checkbox" class="vec-asig" value="${esc(a.id)}" ${disabled}>
          <span class="vec-name">${esc(a.nombre)}</span>
          <span class="vec-meta">${esc(a.codigo)} · Curso ${a.curso || "?"}</span>
          ${badge}
        </label>`;
    }).join("");

    $modalBody.innerHTML = `
      <p style="font-size:13px;color:#555;margin-bottom:12px">
        Curso <strong>${esc(data.curso_academico)}</strong>. Se scrapearan los grupos
        y se vectorizaran <strong>todos</strong> los planes docentes de cada asignatura seleccionada.
        Las ya vectorizadas en este curso aparecen deshabilitadas.
      </p>
      <div class="vec-toolbar">
        <button type="button" class="btn-secondary" id="vec-select-all">Seleccionar todas (disponibles)</button>
        <button type="button" class="btn-secondary" id="vec-clear">Limpiar</button>
        <span style="margin-left:auto;font-size:12px;color:#777">
          ${disponibles.length} disponibles / ${asigs.length} totales
        </span>
      </div>
      <div class="vec-list">${rows}</div>
      <div id="vec-msg"></div>
      <div class="form-actions">
        <button class="btn-submit" id="vec-submit">
          <i class="fa-solid fa-cube"></i> Vectorizar seleccionadas
        </button>
      </div>`;

    document.getElementById("vec-select-all").addEventListener("click", () => {
      $modalBody.querySelectorAll(".vec-asig:not(:disabled)").forEach((cb) => (cb.checked = true));
    });
    document.getElementById("vec-clear").addEventListener("click", () => {
      $modalBody.querySelectorAll(".vec-asig").forEach((cb) => (cb.checked = false));
    });

    document.getElementById("vec-submit").addEventListener("click", async () => {
      const ids = Array.from($modalBody.querySelectorAll(".vec-asig:checked")).map((cb) => cb.value);
      const $msg = document.getElementById("vec-msg");
      const $btn = document.getElementById("vec-submit");
      if (!ids.length) {
        $msg.innerHTML = formError("Selecciona al menos una asignatura");
        return;
      }
      $msg.innerHTML = '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i> Vectorizando... (puede tardar varios minutos)</div>';
      $btn.disabled = true;

      try {
        const res = await postJSON(API("/api/admin/planes_docentes/vectorize"), {
          titulacion_id: titulacionId,
          codcentro: centro.codigo_sevius,
          codigo_titulacion_sevius: titulacion.codigo,
          asignatura_ids: ids,
        });
        const r = res.resumen;
        let html = `
          <div class="form-success">
            <strong>${r.completado}</strong> completados,
            <strong>${r.sin_cambios}</strong> sin cambios,
            <strong>${r.error}</strong> errores
            (<strong>${r.total_chunks}</strong> chunks insertados).
          </div>
          <div class="vec-results">`;
        res.resultados.forEach((a) => {
          html += `<div class="vec-result-asig"><strong>${esc(a.nombre)} (${esc(a.codigo)})</strong>`;
          if (a.error) {
            html += ` <span style="color:#be0f2e">— ${esc(a.error)}</span>`;
          } else if (!a.grupos.length) {
            html += ` <span style="color:#777">— sin grupos</span>`;
          } else {
            html += "<ul>";
            a.grupos.forEach((g) => {
              const col = g.estado === "completado" ? "#2a7a2a" :
                          g.estado === "error" ? "#be0f2e" : "#777";
              html += `<li style="color:${col}">${esc(g.grupo)}: ${esc(g.estado)} — ${esc(g.accion)}${g.chunks ? ` (${g.chunks} chunks)` : ""}</li>`;
            });
            html += "</ul>";
          }
          html += "</div>";
        });
        html += "</div>";
        $msg.innerHTML = html;
        $btn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cerrar';
        $btn.disabled = false;
        $btn.onclick = () => { closeModal(); loadAsignaturas(titulacionId, titulacionNombre); };
      } catch (err) {
        $msg.innerHTML = formError(err.message);
        $btn.disabled = false;
      }
    });
  }

  // ─── Init ────────────────────────────────────────────────────────
  checkHealth();
  loadCentros();
})();
