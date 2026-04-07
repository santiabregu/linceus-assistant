/* ====================================================================
   LinceUS Admin Panel - JavaScript
   Navegacion: Centros → Titulaciones → Asignaturas → Planes/Chunks
   + Profesores, Horarios, Conversaciones, Feedback
   ==================================================================== */

(function () {
  "use strict";

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
        `<div class="section-header"><h2>Centros disponibles</h2><span class="count-badge">${centros.length}</span></div>` +
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
            <div class="card-badge" style="margin-top:12px">${c.activo ? "Activo" : "Inactivo"}</div>
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
    } catch (err) {
      showEmpty("triangle-exclamation", "Error cargando centros: " + err.message);
    }
  }

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
        showEmpty("graduation-cap", "No hay titulaciones para este centro");
        return;
      }

      const html =
        `<div class="section-header"><h2>Titulaciones</h2><span class="count-badge">${titulaciones.length}</span></div>` +
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
            <div class="card-badge" style="margin-top:12px">${t.activa ? "Activa" : "Inactiva"}</div>
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
        showEmpty("book", "No hay asignaturas para esta titulacion");
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

      let html = `<div class="section-header"><h2>Asignaturas</h2><span class="count-badge">${asignaturas.length}</span></div>`;

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
    } catch (err) {
      showEmpty("triangle-exclamation", "Error cargando asignaturas: " + err.message);
    }
  }

  // ─── Asignatura detail modal ─────────────────────────────────────

  async function openAsignaturaDetail(id) {
    openModal("Cargando...", '<div class="loading"><i class="fa-solid fa-spinner fa-spin"></i></div>');
    try {
      const [asig, planes] = await Promise.all([
        fetchJSON(API("/api/admin/asignaturas/" + id)),
        fetchJSON(API("/api/admin/planes_docentes?asignatura_id=" + id)),
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

      $modalTitle.textContent = asig.nombre;
      $modalBody.innerHTML = html;

      // Bind chunk buttons
      $modalBody.querySelectorAll(".btn-ver-chunks").forEach((btn) =>
        btn.addEventListener("click", () => loadChunksInModal(btn.dataset.planId))
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
  //  PROFESORES
  // ═══════════════════════════════════════════════════════════════════

  async function loadProfesores(departamento) {
    showLoading();
    setActiveTab("profesores");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "profesores", label: "Profesores" },
    ]);

    try {
      const [deptos, profes] = await Promise.all([
        fetchJSON(API("/api/admin/departamentos")),
        fetchJSON(API(departamento ? "/api/admin/profesores?departamento=" + encodeURIComponent(departamento) : "/api/admin/profesores")),
      ]);

      let html = `<div class="section-header"><h2>Profesores</h2><span class="count-badge">${profes.length}</span></div>`;

      // Filtro departamento
      html += `<div class="filters">
        <label>Departamento:</label>
        <select id="filter-depto">
          <option value="">Todos</option>
          ${deptos.map((d) => `<option value="${esc(d.departamento)}" ${d.departamento === departamento ? "selected" : ""}>${esc(d.departamento)} (${d.num_profesores})</option>`).join("")}
        </select>
      </div>`;

      if (!profes.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-user-tie"></i><p>No hay profesores</p></div>';
      } else {
        html += `<div class="data-table-container"><table class="data-table">
          <thead><tr>
            <th>Nombre</th><th>Departamento</th><th>Categoria</th>
            <th>Email</th><th>Despacho</th><th>Perfil</th>
          </tr></thead><tbody>`;
        profes.forEach((p) => {
          html += `<tr>
            <td><strong>${esc(p.apellidos)}, ${esc(p.nombre)}</strong></td>
            <td>${esc(p.departamento)}</td>
            <td>${esc(p.categoria_academica) || "-"}</td>
            <td>${p.email ? `<a href="mailto:${esc(p.email)}">${esc(p.email)}</a>` : "-"}</td>
            <td>${esc(p.despacho) || "-"}</td>
            <td>${p.enlace_perfil ? `<a href="${esc(p.enlace_perfil)}" target="_blank"><i class="fa-solid fa-external-link"></i></a>` : "-"}</td>
          </tr>`;
        });
        html += "</tbody></table></div>";
      }

      $main.innerHTML = html;

      document.getElementById("filter-depto").addEventListener("change", (e) => {
        loadProfesores(e.target.value || undefined);
      });
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  //  HORARIOS
  // ═══════════════════════════════════════════════════════════════════

  async function loadHorarios() {
    showLoading();
    setActiveTab("horarios");
    setBreadcrumb([
      { view: "home", label: '<i class="fa-solid fa-house"></i> Inicio' },
      { view: "horarios", label: "Horarios" },
    ]);

    try {
      const horarios = await fetchJSON(API("/api/admin/horarios"));

      let html = `<div class="section-header"><h2>Horarios</h2><span class="count-badge">${horarios.length}</span></div>`;

      if (!horarios.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-clock"></i><p>No hay horarios en la base de datos</p></div>';
      } else {
        // Agrupar por asignatura
        const porAsig = {};
        horarios.forEach((h) => {
          const key = h.asignatura_nombre || "?";
          if (!porAsig[key]) porAsig[key] = { codigo: h.asignatura_codigo, items: [] };
          porAsig[key].items.push(h);
        });

        const dias = { 1: "Lunes", 2: "Martes", 3: "Miercoles", 4: "Jueves", 5: "Viernes", 6: "Sabado" };

        html += `<div class="data-table-container"><table class="data-table">
          <thead><tr>
            <th>Asignatura</th><th>Grupo</th><th>Dia</th>
            <th>Hora inicio</th><th>Hora fin</th><th>Aula</th><th>Tipo</th>
          </tr></thead><tbody>`;

        Object.keys(porAsig)
          .sort()
          .forEach((nombre) => {
            const info = porAsig[nombre];
            info.items.forEach((h) => {
              html += `<tr>
                <td><strong>${esc(nombre)}</strong><br><small style="color:#777">${esc(info.codigo)}</small></td>
                <td>${esc(h.grupo_numero)}</td>
                <td>${dias[h.dia_semana] || esc(h.dia_semana)}</td>
                <td>${esc(h.hora_inicio)}</td>
                <td>${esc(h.hora_fin)}</td>
                <td>${esc(h.aula) || "-"}</td>
                <td>${esc(h.tipo_sesion) || "-"}</td>
              </tr>`;
            });
          });

        html += "</tbody></table></div>";
      }

      $main.innerHTML = html;
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  //  CONVERSACIONES
  // ═══════════════════════════════════════════════════════════════════

  let convPage = 0;
  const CONV_LIMIT = 50;

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
        API(`/api/admin/conversaciones?limit=${CONV_LIMIT}&offset=${page * CONV_LIMIT}`)
      );
      const totalPages = Math.ceil(data.total / CONV_LIMIT);

      let html = `<div class="section-header"><h2>Conversaciones</h2><span class="count-badge">${data.total} total</span></div>`;

      if (!data.rows.length) {
        html += '<div class="empty-state"><i class="fa-solid fa-comments"></i><p>No hay conversaciones registradas</p></div>';
      } else {
        html += `<div class="data-table-container"><table class="data-table">
          <thead><tr>
            <th>Fecha</th><th>Sesion</th><th>Mensaje usuario</th>
            <th>Respuesta</th><th>Intent</th><th>Conf.</th>
          </tr></thead><tbody>`;

        data.rows.forEach((r) => {
          const date = r.created_at ? new Date(r.created_at).toLocaleString("es-ES") : "-";
          html += `<tr>
            <td style="white-space:nowrap;font-size:12px">${date}</td>
            <td style="font-size:11px;font-family:monospace">${esc((r.session_id || "").substring(0, 8))}...</td>
            <td class="truncate">${esc(r.user_message)}</td>
            <td class="truncate">${esc(r.bot_response)}</td>
            <td><span class="tag tag-obligatoria" style="font-size:9px">${esc(r.intent) || "?"}</span></td>
            <td>${r.confidence != null ? (r.confidence * 100).toFixed(0) + "%" : "-"}</td>
          </tr>`;
        });

        html += "</tbody></table></div>";

        // Pagination
        html += `<div class="pagination">
          <button id="conv-prev" ${page <= 0 ? "disabled" : ""}><i class="fa-solid fa-chevron-left"></i> Anterior</button>
          <span class="page-info">Pagina ${page + 1} de ${totalPages || 1}</span>
          <button id="conv-next" ${page + 1 >= totalPages ? "disabled" : ""}>Siguiente <i class="fa-solid fa-chevron-right"></i></button>
        </div>`;
      }

      $main.innerHTML = html;

      const prev = document.getElementById("conv-prev");
      const next = document.getElementById("conv-next");
      if (prev) prev.addEventListener("click", () => loadConversaciones(convPage - 1));
      if (next) next.addEventListener("click", () => loadConversaciones(convPage + 1));
    } catch (err) {
      showEmpty("triangle-exclamation", "Error: " + err.message);
    }
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

  // ─── Init ────────────────────────────────────────────────────────
  checkHealth();
  loadCentros();
})();
