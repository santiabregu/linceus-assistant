import React from 'react';

// Réplica fiel de pagina-principal.html / pagina-principal.css.
// Colores: --us-red #be0f2e, --us-red-dark #790624, --us-teal #059f94,
//          --us-gray-bg #f3f3f3, --us-text #3f3f3f, --us-footer-bg #3d3d3d,
//          --us-subfooter-bg #1e1e1e.

const RED = '#be0f2e';
const RED_DARK = '#790624';
const TEAL = '#059f94';
const TEXT = '#3f3f3f';
const MUTED = '#777';
const GRAY_BG = '#f3f3f3';
const FOOTER_BG = '#3d3d3d';
const SUBFOOTER_BG = '#1e1e1e';

function TopBar() {
  return (
    <div style={{ background: RED }}>
      <div className="mx-auto flex justify-end" style={{ maxWidth: 1200, padding: '0 20px' }}>
        <ul className="flex" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          <li>
            <a className="block text-white" style={{ padding: '10px 16px', fontSize: 13, fontWeight: 400 }}>
              Iniciar sesión
            </a>
          </li>
          <li>
            <a className="block text-white" style={{ padding: '10px 16px', fontSize: 13, fontWeight: 400 }}>
              Universidad Digital <i className="fa-solid fa-chevron-down" style={{ fontSize: 10, marginLeft: 4 }} />
            </a>
          </li>
        </ul>
      </div>
    </div>
  );
}

function MainHeader() {
  return (
    <header style={{ background: '#fff', borderBottom: '1px solid #e0e0e0' }}>
      <div
        className="mx-auto flex items-center justify-between"
        style={{ maxWidth: 1200, padding: '18px 20px' }}
      >
        {/* Izquierda: logo US + dropdown "Información para mí" */}
        <div className="flex items-center" style={{ gap: 30 }}>
          {/* Logo US: lo dibujamos en SVG porque no podemos cargar el png del frontend */}
          <UsLogo />
          <a
            style={{
              fontFamily: 'Raleway, sans-serif',
              fontSize: 14,
              fontWeight: 600,
              color: TEXT,
              textDecoration: 'none',
            }}
          >
            Información para mí{' '}
            <i className="fa-solid fa-chevron-down" style={{ fontSize: 10, marginLeft: 4 }} />
          </a>
        </div>

        {/* Derecha: search */}
        <form className="flex items-center" onSubmit={(e) => e.preventDefault()}>
          <input
            type="text"
            placeholder="Buscar..."
            style={{
              border: '2px solid #bcbaba',
              borderRadius: '24px 0 0 24px',
              padding: '10px 18px',
              fontSize: 14,
              outline: 'none',
              width: 240,
              fontFamily: 'Open Sans, sans-serif',
            }}
          />
          <button
            type="submit"
            style={{
              background: RED,
              border: 'none',
              borderRadius: '0 24px 24px 0',
              padding: '10px 16px',
              color: '#fff',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            <i className="fa-solid fa-magnifying-glass" />
          </button>
        </form>
      </div>
    </header>
  );
}

function MainNav() {
  const items = [
    'La US',
    'Estudiar',
    'Investigar',
    'Vivir la US',
    'Empresas',
    'Internacional',
    'Trabaja en la US',
  ];
  return (
    <nav style={{ background: '#fff', borderBottom: `3px solid ${RED}` }}>
      <div className="mx-auto" style={{ maxWidth: 1200, padding: '0 20px' }}>
        <ul className="flex" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
          {items.map((it) => (
            <li key={it}>
              <a
                style={{
                  display: 'block',
                  padding: '14px 18px',
                  fontFamily: 'Raleway, sans-serif',
                  fontSize: 14,
                  fontWeight: 600,
                  color: TEXT,
                  textDecoration: 'none',
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px',
                  borderBottom: '3px solid transparent',
                  marginBottom: -3,
                }}
              >
                {it}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </nav>
  );
}

function Card({ tag, title, body }) {
  return (
    <article
      style={{
        background: '#fff',
        padding: '40px 35px',
        borderRadius: 2,
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      }}
    >
      <span
        style={{
          display: 'inline-block',
          fontSize: 11,
          letterSpacing: 2,
          color: '#fff',
          background: TEAL,
          padding: '4px 10px',
          borderRadius: 2,
          marginBottom: 18,
          fontWeight: 600,
        }}
      >
        {tag}
      </span>
      <h2
        style={{
          fontFamily: 'Raleway, sans-serif',
          fontSize: 22,
          fontWeight: 400,
          marginBottom: 16,
          color: TEXT,
          lineHeight: 1.4,
        }}
      >
        {title}
      </h2>
      <p style={{ fontSize: 14, lineHeight: 1.8, color: MUTED, marginBottom: 24 }}>
        {body}
      </p>
      <a
        style={{
          fontSize: 13,
          letterSpacing: 1,
          fontWeight: 600,
          color: RED,
          textDecoration: 'none',
          borderBottom: `2px solid ${RED}`,
          paddingBottom: 4,
        }}
      >
        SABER MÁS <i className="fa-solid fa-arrow-right" style={{ marginLeft: 4, fontSize: 11 }} />
      </a>
    </article>
  );
}

function Comunicaciones() {
  return (
    <main className="mx-auto" style={{ maxWidth: 1200, padding: '60px 20px' }}>
      <h1
        style={{
          fontFamily: 'Raleway, sans-serif',
          fontSize: 36,
          fontWeight: 300,
          marginBottom: 50,
          textAlign: 'center',
          color: TEXT,
        }}
      >
        Comunicaciones oficiales
      </h1>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 30,
        }}
      >
        <Card
          tag="MOVILIDAD"
          title="Resolución provisional de la convocatoria general de movilidad..."
          body="La Universidad de Sevilla hace pública la resolución provisional de destinos de la convocatoria general de movilidad internacional para el curso..."
        />
        <Card
          tag="BECAS Y AYUDAS"
          title="Becas Santander Estudios Erasmus y no Erasmus"
          body="Se hacen públicas las convocatorias de Becas Santander Estudios ligadas a los destinos Erasmus y no Erasmus, correspondientes a la Convocatoria..."
        />
      </div>
    </main>
  );
}

function Footer() {
  return (
    <>
      <footer style={{ background: FOOTER_BG, color: '#e1e1e1', marginTop: 40 }}>
        <div
          className="mx-auto"
          style={{
            maxWidth: 1200,
            padding: '40px 20px',
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 30,
          }}
        >
          <div>
            <UsLogo white />
          </div>
          <div>
            <h4 style={{ fontFamily: 'Raleway', fontSize: 15, fontWeight: 600, marginBottom: 14, color: '#fff' }}>
              Contacto
            </h4>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc' }}>
              San Fernando, 4<br />
              41004 Sevilla
            </p>
            <p style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc' }}>Tel: 954 55 10 00</p>
          </div>
          <div>
            <h4 style={{ fontFamily: 'Raleway', fontSize: 15, fontWeight: 600, marginBottom: 14, color: '#fff' }}>
              Redes sociales
            </h4>
            <div className="flex" style={{ gap: 12 }}>
              {['fa-facebook-f', 'fa-instagram', 'fa-linkedin-in', 'fa-youtube'].map((ic) => (
                <a
                  key={ic}
                  className="flex items-center justify-center"
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    background: 'rgba(255,255,255,0.15)',
                    color: '#fff',
                    fontSize: 15,
                  }}
                >
                  <i className={`fa-brands ${ic}`} />
                </a>
              ))}
            </div>
          </div>
          <div>
            <h4 style={{ fontFamily: 'Raleway', fontSize: 15, fontWeight: 600, marginBottom: 14, color: '#fff' }}>
              Acceso rápido
            </h4>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              <li style={{ marginBottom: 6 }}>
                <a style={{ color: '#ccc', fontSize: 13, textDecoration: 'none' }}>Accesibilidad</a>
              </li>
              <li style={{ marginBottom: 6 }}>
                <a style={{ color: '#ccc', fontSize: 13, textDecoration: 'none' }}>Secretaría virtual</a>
              </li>
              <li style={{ marginBottom: 6 }}>
                <a style={{ color: '#ccc', fontSize: 13, textDecoration: 'none' }}>Enseñanza virtual</a>
              </li>
            </ul>
          </div>
        </div>
        <div style={{ background: SUBFOOTER_BG, textAlign: 'center', padding: '16px 20px' }}>
          <p style={{ fontSize: 12, color: '#999', margin: 0 }}>© Universidad de Sevilla</p>
        </div>
      </footer>
    </>
  );
}

// Logo US recreado en SVG (formato clásico: escudo a la izda + texto a la dcha).
function UsLogo({ white = false }) {
  const colorPrimary = white ? '#fff' : RED;
  return (
    <svg width="170" height="50" viewBox="0 0 170 50" style={{ display: 'block' }}>
      {/* Escudo: óvalo con corona estilizada */}
      <g transform="translate(0,0)">
        <ellipse cx="22" cy="25" rx="20" ry="22" fill={colorPrimary} />
        <text
          x="22"
          y="32"
          textAnchor="middle"
          fontFamily="Raleway, serif"
          fontSize="18"
          fontWeight="700"
          fill="#fff"
        >
          US
        </text>
        {/* Corona pequeña */}
        <path d="M10 8 L14 4 L18 8 L22 4 L26 8 L30 4 L34 8 L34 10 L10 10 Z" fill={colorPrimary} />
      </g>
      {/* Texto */}
      <text
        x="55"
        y="22"
        fontFamily="Raleway, serif"
        fontSize="13"
        fontWeight="700"
        fill={colorPrimary}
        letterSpacing="1.2"
      >
        UNIVERSIDAD
      </text>
      <text
        x="55"
        y="38"
        fontFamily="Raleway, serif"
        fontSize="13"
        fontWeight="700"
        fill={colorPrimary}
        letterSpacing="1.2"
      >
        DSEVILLA
      </text>
      <text
        x="55"
        y="48"
        fontFamily="Raleway, serif"
        fontSize="7"
        fill={colorPrimary}
        letterSpacing="1"
      >
        1505
      </text>
    </svg>
  );
}

export default function PaginaPrincipal() {
  return (
    <div
      className="w-full h-full overflow-hidden"
      style={{
        background: GRAY_BG,
        color: TEXT,
        fontFamily: 'Open Sans, sans-serif',
        fontWeight: 300,
        fontSize: 14,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <TopBar />
      <MainHeader />
      <MainNav />
      <div style={{ flex: 1 }}>
        <Comunicaciones />
      </div>
      <Footer />
    </div>
  );
}
