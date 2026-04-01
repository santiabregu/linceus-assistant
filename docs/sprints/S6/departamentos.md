# Departamentos seleccionados

Fuente: https://www.informatica.us.es/index.php/departamentos/listado

| Siglas | Nombre | Web |
|--------|--------|-----|
| DTE | Tecnología Electrónica | https://www.dte.us.es |
| LSI | Lenguajes y Sistemas Informáticos | https://departamento.us.es/lsi/ |
| MA1 | Matemática Aplicada I | https://departamento.us.es/matapli1/ |
| CCIA | Ciencias de la Comput. e Int. Artificial | https://www.cs.us.es |

Son las mas relevantes y las que tienen sus propios enlaces (mas dificiles de encontrar para el alumno).

Nota: el dominio original de MA1 (http://ma1.us.es) esta caido; la web real es https://departamento.us.es/matapli1/.

---

## Analisis de informacion disponible por departamento

### DTE (~58 profesores)
- **Scrapeabilidad**: Media. Web en Plone CMS. Email ofuscado (imagen en vez de @).
- **Pagina principal de personal**: https://www.dte.us.es/dte_users_group
- **Campos disponibles**: nombre, categoria, email (ofuscado), telefono, despacho, tutorias.
- **Perfiles individuales**: ~50% tienen perfil propio (URLs inconsistentes: `/Members/{user}` o `/personal/{apellido}/`). Algunos requieren autenticacion.
- **Campos extra en perfiles**: asignaturas (a veces), areas de investigacion (raro).
- **No disponible**: foto, ORCID, Google Scholar, web personal como campo estructurado.

### LSI (~90 profesores)
- **Scrapeabilidad**: Alta. WordPress + Elementor, HTML estandar.
- **Listado**: https://departamento.us.es/lsi/profesorado/
- **Perfiles individuales**: https://departamento.us.es/lsi/profesor/{apellido1-apellido2-nombre}/ (todos tienen)
- **Campos disponibles**: nombre, categoria, email, telefono, despacho, foto, asignaturas, grupo de investigacion, URL PRISMA.
- **Campos opcionales**: web personal.
- **No disponible**: ORCID, Google Scholar, publicaciones.

### MA1 (~70 profesores)
- **Scrapeabilidad**: Baja. Web propia caida, datos dispersos en fuentes externas.
- **Fuentes alternativas**:
  - SISIUS: https://investigacion.us.es/sisius/sis_dep.php?id_dpto=92 (listado completo con IDs)
  - Directorio US: https://www.us.es/trabaja-en-la-us/directorio/{nombre-slug}
- **Campos en directorio US**: nombre, email, telefono, categoria, departamento, centro, grupo investigacion, enlace PRISMA.
- **Campos en SISIUS**: ORCID, Scopus, WoS, web personal, publicaciones.
- **No disponible**: foto, despacho (no fiable).

### CCIA (~34 profesores)
- **Scrapeabilidad**: Alta. HTML estatico, dataset pequeno.
- **Directorio**: https://www.cs.us.es/departamento/directorio
- **Perfiles individuales**: https://www.cs.us.es/perfiles/{apellido-nombre}
- **Tutorias (pagina unica)**: https://www.cs.us.es/docencia/horarios-de-tutorias
- **Campos disponibles**: nombre, categoria, email, telefono, despacho, tutorias, asignaturas, ORCID, Google Scholar, DBLP.
- **Campos opcionales**: web personal, grupo de investigacion, Scopus, ResearcherID.

---

## Campos recomendados para la DB

El schema actual de `profesores` tiene: nombre, apellidos, nombre_normalizado, email, telefono, despacho, edificio, planta, web_personal, orcid, activo, departamento_id.

**Campos a añadir**:
- `categoria_academica VARCHAR` — disponible en todos los deptos, util para el usuario.
- `enlace_perfil VARCHAR` — URL del perfil del profesor en la web del departamento (o en us.es si no tiene).

**Vectorizacion**: no necesaria. La info de profesores es estructurada y se presta a text-to-SQL, no a RAG.
