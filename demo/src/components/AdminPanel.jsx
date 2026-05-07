import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Réplica del admin.html: top bar, header, tabs y vistas Home/Profesores/Conversaciones/Stats.

function TopBar({ active }) {
  return (
    <div className="bg-[#be0f2e] text-white text-sm px-10 py-3 flex gap-8">
      <span className="flex items-center gap-2 cursor-pointer font-semibold">
        <i className="fa-solid fa-arrow-left" /> Volver al sitio
      </span>
      <span
        className={`flex items-center gap-2 cursor-pointer font-semibold ${
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
    <header className="px-10 py-5 flex items-center justify-between bg-white">
      <div className="flex items-center gap-4">
        <img src="/logo-us.png" alt="Universidad de Sevilla" style={{ height: 56 }} />
        <div>
          <h1 className="text-2xl font-semibold text-gray-800 leading-tight">
            Panel de Administracion
          </h1>
          <span className="text-xs text-gray-500">
            LinceUS - Gestion de datos academicos
          </span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-sm text-green-600 flex items-center gap-2">
          <i className="fa-solid fa-circle text-[10px]" /> Conectado
        </div>
        <button className="px-3 py-1.5 border border-gray-300 rounded text-sm text-gray-700">
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
  const breadcrumb = {
    home: 'Centros',
    profesores: 'Profesores',
    horarios: 'Horarios',
    conversaciones: 'Conversaciones',
    stats: 'Estadísticas',
  }[active] || 'Centros';
  return (
    <nav className="border-b-2 border-[#be0f2e] bg-white px-10 py-4 flex items-center justify-between text-[13px] font-semibold">
      <div className="flex items-center gap-2 text-gray-700">
        <i className="fa-solid fa-house" /> {breadcrumb}
      </div>
      <div className="flex gap-8">
        {tabs.map((t) => (
          <a
            key={t.id}
            className={`flex items-center gap-2 ${
              active === t.id ? 'text-[#be0f2e]' : 'text-gray-600'
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="font-display text-2xl text-gray-800">
          Centros disponibles{' '}
          <span className="ml-2 inline-block text-sm bg-[#be0f2e] text-white rounded-full px-3 py-0.5">
            3
          </span>
        </h2>
        <button className="px-4 py-2 bg-[#be0f2e] text-white rounded shadow text-sm font-semibold">
          + Nuevo centro
        </button>
      </div>
      <div className="grid grid-cols-3 gap-6">
        {centros.map((c) => (
          <div
            key={c.siglas}
            className="bg-white rounded-lg shadow p-6 border border-gray-100"
          >
            <i className="fa-solid fa-building-columns text-3xl text-[#be0f2e] mb-3" />
            <h3 className="font-semibold text-lg leading-tight mb-1">{c.nombre}</h3>
            <div className="text-xs text-gray-500 mb-3">{c.siglas}</div>
            <div className="text-sm text-[#059f94] flex items-center gap-2">
              <i className="fa-solid fa-graduation-cap" /> {c.titulaciones} titulaciones
            </div>
            <div className="mt-3">
              <span className="inline-block text-xs bg-[#fdf2f4] text-[#be0f2e] rounded-full px-3 py-0.5">
                Activo
              </span>
            </div>
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
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          Inicio › ETSII › Ingeniería del Software › <span className="text-[#be0f2e] font-semibold">Profesores</span>
        </div>
        <button className="px-4 py-2 bg-[#be0f2e] text-white rounded text-sm font-semibold">
          <i className="fa-solid fa-rotate mr-2" /> Enriquecer desde us.es
        </button>
      </div>
      <h2 className="font-display text-xl mb-4">
        Departamento de Lenguajes y Sistemas Informáticos{' '}
        <span className="ml-2 text-sm bg-[#be0f2e] text-white rounded-full px-3 py-0.5">62</span>
      </h2>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#be0f2e] text-white">
            <tr>
              <th className="px-4 py-2 text-left">Nombre</th>
              <th className="px-4 py-2 text-left">Categoría</th>
              <th className="px-4 py-2 text-left">Email</th>
              <th className="px-4 py-2 text-left">Despacho</th>
            </tr>
          </thead>
          <tbody>
            {profes.map((p, i) => (
              <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-2 font-medium text-gray-800">{p.n}</td>
                <td className="px-4 py-2 text-gray-600">{p.cat}</td>
                <td className="px-4 py-2 text-[#be0f2e]">{p.email}</td>
                <td className="px-4 py-2 text-gray-700">{p.desp}</td>
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="font-display text-2xl">
          Conversaciones <span className="ml-2 text-sm bg-[#be0f2e] text-white rounded-full px-3 py-0.5">72 sesiones</span>
        </h2>
        <button className="px-4 py-2 bg-[#be0f2e] text-white rounded text-sm font-semibold">
          <i className="fa-solid fa-download mr-2" /> Exportar esta página
        </button>
      </div>
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[#be0f2e] text-white">
            <tr>
              <th className="px-3 py-2 w-8"><i className="fa-solid fa-check" /></th>
              <th className="px-3 py-2 text-left">Sesión</th>
              <th className="px-3 py-2 text-left">Mensajes</th>
              <th className="px-3 py-2 text-left">Primer mensaje</th>
              <th className="px-3 py-2 text-left">Último mensaje</th>
              <th className="px-3 py-2 text-left">Inicio</th>
              <th className="px-3 py-2 text-left">Duración</th>
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
                <td className="px-3 py-2">
                  <input type="checkbox" defaultChecked={s.revisada} readOnly />
                </td>
                <td className="px-3 py-2 font-mono text-gray-700">{s.id}</td>
                <td className="px-3 py-2 font-bold text-center">{s.n}</td>
                <td className="px-3 py-2 text-gray-700">{s.primero}</td>
                <td className={`px-3 py-2 ${s.revisada ? 'text-gray-400 line-through' : 'text-gray-800'}`}>{s.ultimo}</td>
                <td className="px-3 py-2 text-gray-600">{s.inicio}</td>
                <td className="px-3 py-2 text-gray-600">{s.dur}</td>
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
      <h2 className="font-display text-3xl mb-8">Estadísticas generales</h2>
      <div className="grid grid-cols-5 gap-5">
        {stats.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
            className="bg-white rounded-lg shadow p-6 text-center border border-gray-100"
          >
            <div className="text-4xl font-display font-bold text-[#be0f2e]">{s.v}</div>
            <div className="text-xs text-gray-500 mt-2 flex items-center justify-center gap-1.5">
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
