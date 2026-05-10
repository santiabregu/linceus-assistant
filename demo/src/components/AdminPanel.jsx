import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Réplica del admin.html: top bar, header, tabs y vistas Home/Profesores/Conversaciones/Stats.

function TopBar({ active }) {
  return (
    <div className="bg-[#be0f2e] text-white text-base px-10 py-3.5 flex gap-10">
      <span className="flex items-center gap-2.5 cursor-pointer font-semibold">
        <i className="fa-solid fa-arrow-left" /> Volver al sitio
      </span>
      <span
        className={`flex items-center gap-2.5 cursor-pointer font-semibold ${
          active === 'stats' ? 'underline' : ''
        }`}
      >
        <i className="fa-solid fa-chart-bar" /> Estadísticas
      </span>
    </div>
  );
}

function Header() {
  return (
    <header className="px-10 py-6 flex items-center justify-between bg-white">
      <div className="flex items-center gap-5">
        <img src="/logo-us.png" alt="Universidad de Sevilla" style={{ height: 64 }} />
        <div>
          <h1 className="text-3xl font-semibold text-gray-800 leading-tight">
            Panel de Administracion
          </h1>
          <span className="text-sm text-gray-500">
            LinceUS - Gestion de datos academicos
          </span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-base text-green-600 flex items-center gap-2">
          <i className="fa-solid fa-circle text-[10px]" /> Conectado
        </div>
        <button className="px-4 py-2 border border-gray-300 rounded text-base text-gray-700">
          <i className="fa-solid fa-right-from-bracket mr-1" /> Salir
        </button>
      </div>
    </header>
  );
}

function NavTabs({ active }) {
  // Réplica fiel del admin real:
  // - Breadcrumb "Centros" (o el actual) a la izquierda
  // - Tabs CENTROS · PROFESORES · HORARIOS · CONVERSACIONES · FEEDBACK a la derecha
  const tabs = [
    { id: 'home', icon: 'fa-house', label: 'CENTROS' },
    { id: 'profesores', icon: 'fa-user', label: 'PROFESORES' },
    { id: 'horarios', icon: 'fa-clock', label: 'HORARIOS' },
    { id: 'conversaciones', icon: 'fa-comments', label: 'CONVERSACIONES' },
    { id: 'feedback', icon: 'fa-star', label: 'FEEDBACK' },
  ];
  // Asignaturas es sub-vista bajo CENTROS, así que la pestaña activa sigue
  // siendo "home" cuando se está en esa vista.
  const activeTab = active === 'asignaturas' ? 'home' : active;
  const isAsignaturas = active === 'asignaturas';
  const breadcrumb = {
    home: 'Centros',
    profesores: 'Profesores',
    horarios: 'Horarios',
    conversaciones: 'Conversaciones',
    stats: 'Estadísticas',
  }[active] || 'Centros';
  return (
    <nav className="border-b-2 border-[#be0f2e] bg-white px-10 py-5 flex items-center justify-between text-[15px] font-semibold">
      <div className="flex items-center gap-2.5 text-gray-700">
        {isAsignaturas ? (
          <>
            <i className="fa-solid fa-house" /> Centros
            <span className="text-gray-400">›</span>
            <span>ETSII</span>
            <span className="text-gray-400">›</span>
            <span>Ingeniería del Software</span>
            <span className="text-gray-400">›</span>
            <span className="text-[#be0f2e]">Asignaturas</span>
          </>
        ) : (
          <>
            <i className="fa-solid fa-house" /> {breadcrumb}
          </>
        )}
      </div>
      <div className="flex gap-8">
        {tabs.map((t) => (
          <a
            key={t.id}
            className={`flex items-center gap-2 ${
              activeTab === t.id ? 'text-[#be0f2e]' : 'text-gray-600'
            }`}
          >
            <i className={`fa-solid ${t.icon}`} /> {t.label}
          </a>
        ))}
      </div>
    </nav>
  );
}

// ───────────────────── Vista: Home (centros) ─────────────────────
function ViewHome() {
  const centros = [
    {
      nombre: 'Escuela Técnica Superior de Ingeniería Informática',
      siglas: 'ETSII',
      titulaciones: 3,
      activo: true,
    },
    {
      nombre: 'Facultad de Biología',
      siglas: 'BIOLOGÍA',
      titulaciones: 8,
      activo: true,
    },
    {
      nombre: 'Facultad de Matemáticas',
      siglas: 'MATEMÁTICAS',
      titulaciones: 13,
      activo: true,
    },
  ];
  return (
    <div className="p-10">
      <div className="flex justify-between items-center mb-7">
        <h2 className="font-display text-3xl text-gray-800">
          Centros disponibles{' '}
          <span className="ml-2 inline-block text-base bg-[#be0f2e] text-white rounded-full px-3 py-0.5">
            3
          </span>
        </h2>
        <button className="px-5 py-2.5 bg-[#be0f2e] text-white rounded shadow text-base font-semibold">
          + Nuevo centro
        </button>
      </div>
      <div className="grid grid-cols-3 gap-6">
        {centros.map((c) => (
          <div
            key={c.siglas}
            className="bg-white rounded-lg shadow p-7 border border-gray-100"
          >
            <i className="fa-solid fa-building-columns text-4xl text-[#be0f2e] mb-4" />
            <h3 className="font-semibold text-xl leading-tight mb-1">{c.nombre}</h3>
            <div className="text-sm text-gray-500 mb-3">{c.siglas}</div>
            <div className="text-base text-[#059f94] flex items-center gap-2">
              <i className="fa-solid fa-graduation-cap" /> {c.titulaciones} titulaciones
            </div>
            <div className="mt-3">
              <span className="inline-block text-sm bg-[#fdf2f4] text-[#be0f2e] rounded-full px-3 py-0.5">
                Activo
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ───────────────────── Vista: Asignaturas (drill-down) ─────────────
function ViewAsignaturas() {
  const segundo = [
    { c: 'GIIS04114', n: 'Análisis y Diseño de Datos y Algoritmos', tip: 'Obligatoria', ects: 6, dur: 'C2' },
    { c: 'GIIS04115', n: 'Sistemas Operativos', tip: 'Obligatoria', ects: 6, dur: 'C1' },
    { c: 'GIIS04116', n: 'Tecnología Básica de Computadores', tip: 'Obligatoria', ects: 6, dur: 'C1' },
    { c: 'GIIS04117', n: 'Arquitectura e Integración SW', tip: 'Obligatoria', ects: 6, dur: 'C1' },
  ];
  const tercero = [
    { c: 'GIIS05121', n: 'Diseño y Pruebas', tip: 'Obligatoria', ects: 6, dur: 'C1' },
    { c: 'GIIS05122', n: 'Ingeniería de Requisitos', tip: 'Obligatoria', ects: 6, dur: 'C1' },
    { c: 'GIIS05123', n: 'Sistemas Inteligentes', tip: 'Obligatoria', ects: 6, dur: 'C2' },
    { c: 'GIIS05124', n: 'Bases de Datos', tip: 'Obligatoria', ects: 6, dur: 'C1' },
  ];
  const TipologiaTag = ({ t }) => (
    <span className="inline-block text-[11px] bg-[#fdf2f4] text-[#be0f2e] rounded-full px-2 py-0.5">
      {t}
    </span>
  );
  const Card = ({ a }) => (
    <div className="bg-white rounded-lg shadow p-5 border border-gray-100">
      <div className="flex justify-between items-start gap-2">
        <div className="font-semibold text-base text-gray-800 leading-tight">{a.n}</div>
        <TipologiaTag t={a.tip} />
      </div>
      <div className="text-xs text-gray-500 mt-1">{a.c}</div>
      <div className="flex gap-3 text-sm text-gray-600 mt-2.5">
        <span><i className="fa-solid fa-award mr-1" /> {a.ects} ECTS</span>
        <span><i className="fa-solid fa-clock mr-1" /> {a.dur}</span>
      </div>
    </div>
  );
  const ActionBtn = ({ icon, label, primary }) => (
    <button
      className={`px-3.5 py-2.5 rounded text-sm font-semibold flex items-center gap-2 ${
        primary
          ? 'bg-[#be0f2e] text-white shadow'
          : 'bg-white border border-gray-300 text-gray-700'
      }`}
    >
      <i className={`fa-solid ${icon}`} /> {label}
    </button>
  );
  return (
    <div className="p-10">
      <div className="flex items-center justify-between mb-7 flex-wrap gap-3">
        <h2 className="font-display text-3xl text-gray-800">
          Asignaturas{' '}
          <span className="ml-2 inline-block text-base bg-[#be0f2e] text-white rounded-full px-3 py-0.5">
            48
          </span>
        </h2>
        <div className="flex gap-2 flex-wrap">
          <ActionBtn icon="fa-cube" label="Vectorizar planes docentes" primary />
          <ActionBtn icon="fa-wand-magic-sparkles" label="Enriquecer datos (us.es)" />
          <ActionBtn icon="fa-chalkboard-user" label="Cargar docencia" />
          <ActionBtn icon="fa-rotate" label="Sincronizar desde Sevius" />
        </div>
      </div>

      <div className="mb-6">
        <div className="text-base font-semibold text-gray-700 mb-3">
          <i className="fa-solid fa-layer-group mr-2 text-[#be0f2e]" /> 2º Curso (12)
        </div>
        <div className="grid grid-cols-4 gap-4">
          {segundo.map((a) => <Card key={a.c} a={a} />)}
        </div>
      </div>

      <div>
        <div className="text-base font-semibold text-gray-700 mb-3">
          <i className="fa-solid fa-layer-group mr-2 text-[#be0f2e]" /> 3er Curso (12)
        </div>
        <div className="grid grid-cols-4 gap-4">
          {tercero.map((a) => <Card key={a.c} a={a} />)}
        </div>
      </div>
    </div>
  );
}

// ───────────────────── Vista: Horarios (centros) ───────────────────
function ViewHorarios() {
  const centros = [
    { nombre: 'ETSII', titulaciones: 3, horarios: 1335, soportado: true },
    { nombre: 'Facultad de Biología', titulaciones: 8, horarios: 0, soportado: false },
    { nombre: 'Facultad de Matemáticas', titulaciones: 13, horarios: 0, soportado: false },
  ];
  return (
    <div className="p-10">
      <div className="flex justify-between items-center mb-5 flex-wrap gap-3">
        <h2 className="font-display text-3xl text-gray-800">
          Horarios por centro{' '}
          <span className="ml-2 inline-block text-base bg-[#be0f2e] text-white rounded-full px-3 py-0.5">
            3
          </span>
        </h2>
      </div>

      <div className="bg-amber-50 border-l-4 border-amber-400 text-amber-900 px-5 py-3.5 rounded text-base mb-7">
        <i className="fa-solid fa-circle-info mr-2" />
        <strong>Extracción de horarios dependiente de centro.</strong> Cada centro publica
        sus horarios en un formato distinto (PDF, web propia, etc.); para añadir un nuevo
        centro hay que crear un extractor en <code className="bg-white/60 px-1 rounded">admin/horarios_extractores/</code>.
      </div>

      <div className="grid grid-cols-3 gap-6">
        {centros.map((c) => (
          <div
            key={c.nombre}
            className="bg-white rounded-lg shadow p-7 border border-gray-100"
          >
            <i className="fa-solid fa-clock text-4xl text-[#be0f2e] mb-4" />
            <h3 className="font-semibold text-xl leading-tight mb-2">{c.nombre}</h3>
            <div className="text-base text-gray-600 flex items-center gap-2 mb-1">
              <i className="fa-solid fa-graduation-cap" /> {c.titulaciones} titulaciones
            </div>
            <div className="text-base text-gray-600 flex items-center gap-2 mb-3">
              <i className="fa-solid fa-clock" /> {c.horarios} horarios
            </div>
            {c.soportado ? (
              <div className="text-sm text-[#059f94] flex items-center gap-2">
                <i className="fa-solid fa-circle-check" /> Extracción disponible
              </div>
            ) : (
              <div className="text-sm text-gray-400 italic">Sin extractor disponible</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ───────────────────── Vista: Profesores (LSI) ─────────────────────
function ViewProfesores() {
  const profes = [
    { n: 'Álvarez García, Juan Antonio', cat: 'Catedrático de Universidad', email: 'jaalvarez@us.es', desp: 'F1.52' },
    { n: 'Arrévola Maldonado, Carlos', cat: 'Profesor Titular de Universidad', email: 'carrevalo@us.es', desp: 'F1.41' },
    { n: 'Ayala Hernández, Daniel', cat: 'Profesor Permanente Laboral', email: 'dayala1@us.es', desp: 'F1.81' },
    { n: 'Barba Rodríguez, Irene', cat: 'Profesora Titular de Universidad', email: 'irenebr@us.es', desp: 'F0.46' },
    { n: 'Borrego Núñez, Agustín', cat: 'Profesor Titular de Universidad', email: 'aborrego@us.es', desp: 'F1.30' },
    { n: 'Galindo Duarte, José Antonio', cat: 'Profesor Titular de Universidad', email: 'jagalindo@us.es', desp: 'F0.44' },
    { n: 'Parejo Maestre, José Antonio', cat: 'Profesor Titular de Universidad', email: 'japarejo@us.es', desp: 'F1.62' },
    { n: 'Resinas Arias de Reyna, Manuel', cat: 'Profesor Titular de Universidad', email: 'resinas@us.es', desp: 'F1.65' },
  ];
  return (
    <div className="p-10">
      <div className="flex items-center justify-between mb-5">
        <div className="text-base text-gray-500">
          Inicio › ETSII › Ingeniería del Software › <span className="text-[#be0f2e] font-semibold">Profesores</span>
        </div>
        <button className="px-5 py-2.5 bg-[#be0f2e] text-white rounded text-base font-semibold">
          <i className="fa-solid fa-rotate mr-2" /> Enriquecer desde us.es
        </button>
      </div>
      <h2 className="font-display text-2xl mb-5">
        Departamento de Lenguajes y Sistemas Informáticos{' '}
        <span className="ml-2 text-base bg-[#be0f2e] text-white rounded-full px-3 py-0.5">62</span>
      </h2>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-base">
          <thead className="bg-[#be0f2e] text-white">
            <tr>
              <th className="px-4 py-3 text-left">Nombre</th>
              <th className="px-4 py-3 text-left">Categoría</th>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">Despacho</th>
            </tr>
          </thead>
          <tbody>
            {profes.map((p, i) => (
              <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2.5 font-medium text-gray-800">{p.n}</td>
                <td className="px-4 py-2.5 text-gray-600">{p.cat}</td>
                <td className="px-4 py-2.5 text-[#be0f2e]">{p.email}</td>
                <td className="px-4 py-2.5 text-gray-700">{p.desp}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ───────────────────── Vista: Conversaciones ─────────────────────
function ViewConversaciones() {
  const sesiones = [
    { id: 'session_177766…', n: 4, primero: 'GII-IS', ultimo: 'Quiero saber la evaluación de ispp para el grup…', inicio: '1/5/2026, 23:02:07', dur: '9 min', revisada: false },
    { id: 'session_177766…', n: 2, primero: 'GII-IS', ultimo: '¿qué es ADDA?', inicio: '1/5/2026, 21:38:38', dur: '19 s', revisada: true },
    { id: 'session_177755…', n: 4, primero: 'GII-IS', ultimo: 'Háblame de Redes de Computadores', inicio: '30/4/2026, 16:35:28', dur: '1 min', revisada: false },
    { id: 'session_177755…', n: 3, primero: 'GII-IS', ultimo: 'Cuáles son los horarios de matemática discreta?', inicio: '30/4/2026, 16:32:42', dur: '1 min', revisada: false },
    { id: 'session_177746…', n: 1, primero: 'GII-IS', ultimo: 'GII-IS', inicio: '29/4/2026, 12:58:20', dur: '1 s', revisada: false },
    { id: 'session_177732…', n: 1, primero: 'GII-IS', ultimo: 'GII-IS', inicio: '27/4/2026, 23:44:31', dur: '1 s', revisada: false },
  ];
  return (
    <div className="p-10">
      <div className="flex justify-between items-center mb-7">
        <h2 className="font-display text-3xl">
          Conversaciones <span className="ml-2 text-base bg-[#be0f2e] text-white rounded-full px-3 py-0.5">72 sesiones</span>
        </h2>
        <button className="px-5 py-2.5 bg-[#be0f2e] text-white rounded text-base font-semibold">
          <i className="fa-solid fa-download mr-2" /> Exportar esta página
        </button>
      </div>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-base">
          <thead className="bg-[#be0f2e] text-white">
            <tr>
              <th className="px-3 py-3 w-8"><i className="fa-solid fa-check" /></th>
              <th className="px-3 py-3 text-left">Sesión</th>
              <th className="px-3 py-3 text-left">Mensajes</th>
              <th className="px-3 py-3 text-left">Primer mensaje</th>
              <th className="px-3 py-3 text-left">Último mensaje</th>
              <th className="px-3 py-3 text-left">Inicio</th>
              <th className="px-3 py-3 text-left">Duración</th>
            </tr>
          </thead>
          <tbody>
            {sesiones.map((s, i) => (
              <tr
                key={i}
                className={`border-t border-gray-100 ${
                  s.revisada ? 'bg-green-50' : 'hover:bg-gray-50'
                }`}
              >
                <td className="px-3 py-2.5">
                  <input type="checkbox" defaultChecked={s.revisada} readOnly />
                </td>
                <td className="px-3 py-2.5 font-mono text-gray-700">{s.id}</td>
                <td className="px-3 py-2.5 font-bold text-center">{s.n}</td>
                <td className="px-3 py-2.5 text-gray-700">{s.primero}</td>
                <td className={`px-3 py-2.5 ${s.revisada ? 'text-gray-400 line-through' : 'text-gray-800'}`}>{s.ultimo}</td>
                <td className="px-3 py-2.5 text-gray-600">{s.inicio}</td>
                <td className="px-3 py-2.5 text-gray-600">{s.dur}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ───────────────────── Vista: Stats ─────────────────────
function ViewStats() {
  const stats = [
    { v: 3, label: 'Centros', icon: 'fa-building-columns' },
    { v: 24, label: 'Titulaciones', icon: 'fa-graduation-cap' },
    { v: 244, label: 'Asignaturas', icon: 'fa-book' },
    { v: 268, label: 'Profesores', icon: 'fa-user-tie' },
    { v: 267, label: 'Grupos', icon: 'fa-users' },
    { v: 1335, label: 'Horarios', icon: 'fa-clock' },
    { v: 157, label: 'Planes docentes', icon: 'fa-file-pdf' },
    { v: 1352, label: 'Chunks RAG', icon: 'fa-puzzle-piece' },
    { v: 231, label: 'Conversaciones', icon: 'fa-comments' },
    { v: 1, label: 'Feedback', icon: 'fa-star' },
  ];
  return (
    <div className="p-10">
      <h2 className="font-display text-4xl mb-9">Estadísticas generales</h2>
      <div className="grid grid-cols-5 gap-5">
        {stats.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-white rounded-lg shadow p-7 text-center border border-gray-100"
          >
            <div className="text-5xl font-display font-bold text-[#be0f2e]">{s.v}</div>
            <div className="text-sm text-gray-500 mt-3 flex items-center justify-center gap-1.5">
              <i className={`fa-solid ${s.icon}`} /> {s.label.toUpperCase()}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

export default function AdminPanel({ view }) {
  const views = {
    home: <ViewHome />,
    asignaturas: <ViewAsignaturas />,
    horarios: <ViewHorarios />,
    profesores: <ViewProfesores />,
    conversaciones: <ViewConversaciones />,
    stats: <ViewStats />,
  };
  return (
    <div className="w-full h-full bg-[#f5f5f5] flex flex-col font-sans overflow-hidden">
      <TopBar active={view} />
      <Header />
      <NavTabs active={view} />
      <main className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            {views[view] || views.home}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  );
}
