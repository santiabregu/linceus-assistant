-- =========================================
-- 1) Titulaciones: GII-IC y GII-TI
-- =========================================
INSERT INTO titulaciones (
  id, centro_id, codigo, codigo_oficial, nombre, nombre_corto,
  tipo, plan_estudios_anio, creditos_totales, duracion_anios, requisito_idioma, activa
)
VALUES
  (
    'c0000000-0000-0000-0000-000000000002',
    'b0000000-0000-0000-0000-000000000001',
    'GII-IC',
    'GII-IC-2010',
    'Grado en Ingeniería Informática - Ingeniería de Computadores',
    'Ing. Computadores',
    'GRADO',
    2010,
    240,
    4,
    'B1',
    true
  ),
  (
    'c0000000-0000-0000-0000-000000000003',
    'b0000000-0000-0000-0000-000000000001',
    'GII-TI',
    'GII-TI-2010',
    'Grado en Ingeniería Informática - Tecnologías Informáticas',
    'Tecnologías Informáticas',
    'GRADO',
    2010,
    240,
    4,
    'B1',
    true
  )
ON CONFLICT (codigo) DO NOTHING;

-- =========================================
-- 2) Asignaturas IC (obligatorias + optativas)
-- =========================================
INSERT INTO asignaturas (
  id, titulacion_id, departamento_id, codigo, nombre, curso, creditos, duracion,
  tipologia, es_formacion_basica, es_optativa, nombre_normalizado, palabras_clave, activa
)
SELECT
  gen_random_uuid(),
  (SELECT id FROM titulaciones WHERE codigo = 'GII-IC' LIMIT 1),
  NULL,
  v.codigo,
  v.nombre,
  v.curso,
  v.creditos,
  v.duracion,
  v.tipologia,
  v.es_formacion_basica,
  v.es_optativa,
  v.nombre_normalizado,
  NULL::text[],
  true
FROM (
  VALUES
    -- 1º Formación básica
    ('2040001','Fundamentos de Programación',1,12,'A','FORMACION_BASICA',true,false,'fundamentos de programacion'),
    ('2040006','Administración de Empresas',1,6,'C1','FORMACION_BASICA',true,false,'administracion de empresas'),
    ('2040002','Álgebra Lineal y Numérica',1,6,'C1','FORMACION_BASICA',true,false,'algebra lineal y numerica'),
    ('2040003','Circuitos Electrónicos Digitales',1,6,'C1','FORMACION_BASICA',true,false,'circuitos electronicos digitales'),
    ('2040005','Introducción a la Matemática Discreta',1,6,'C1','FORMACION_BASICA',true,false,'introduccion a la matematica discreta'),
    ('2040007','Cálculo Infinitesimal y Numérico',1,6,'C2','FORMACION_BASICA',true,false,'calculo infinitesimal y numerico'),
    ('2040008','Estadística',1,6,'C2','FORMACION_BASICA',true,false,'estadistica'),
    ('2040009','Estructura de Computadores',1,6,'C2','FORMACION_BASICA',true,false,'estructura de computadores'),
    ('2040004','Fundamentos Físicos de la Informática',1,6,'C2','FORMACION_BASICA',true,false,'fundamentos fisicos de la informatica'),

    -- 2º Obligatorias
    ('2040010','Análisis y Diseño de Datos y Algoritmos',2,12,'A','OBLIGATORIA',false,false,'analisis y diseno de datos y algoritmos'),
    ('2040012','Diseño de Sistemas Digitales',2,6,'C1','OBLIGATORIA',false,false,'diseno de sistemas digitales'),
    ('2040047','Introducción a la Ingeniería del Software y los Sistemas de Información I',2,6,'C1','OBLIGATORIA',false,false,'introduccion a la ingenieria del software y los sistemas de informacion i'),
    ('2040013','Sistemas Operativos',2,6,'C1','OBLIGATORIA',false,false,'sistemas operativos'),
    ('2040014','Tecnología de Computadores',2,6,'C1','OBLIGATORIA',false,false,'tecnologia de computadores'),
    ('2040015','Arquitectura de Computadores',2,6,'C2','OBLIGATORIA',false,false,'arquitectura de computadores'),
    ('2040048','Introducción a la Ingeniería del Software y los Sistemas de Información II',2,6,'C2','OBLIGATORIA',false,false,'introduccion a la ingenieria del software y los sistemas de informacion ii'),
    ('2040016','Matemática Discreta',2,6,'C2','OBLIGATORIA',false,false,'matematica discreta'),
    ('2040017','Redes de Computadores',2,6,'C2','OBLIGATORIA',false,false,'redes de computadores'),

    -- 3º Obligatorias
    ('2040049','Arquitectura y Tecnologías de Redes I',3,6,'C1','OBLIGATORIA',false,false,'arquitectura y tecnologias de redes i'),
    ('2040019','Inteligencia Artificial',3,6,'C1','OBLIGATORIA',false,false,'inteligencia artificial'),
    ('2040021','Sistemas Paralelos y Distribuidos',3,6,'C1','OBLIGATORIA',false,false,'sistemas paralelos y distribuidos'),
    ('2040026','Software de Sistemas',3,6,'C1','OBLIGATORIA',false,false,'software de sistemas'),
    ('2040022','Teoría de Grafos',3,6,'C1','OBLIGATORIA',false,false,'teoria de grafos'),
    ('2040050','Arquitectura y Tecnologías de Redes II',3,6,'C2','OBLIGATORIA',false,false,'arquitectura y tecnologias de redes ii'),
    ('2040023','Desarrollo de Aplicaciones Distribuidas',3,6,'C2','OBLIGATORIA',false,false,'desarrollo de aplicaciones distribuidas'),
    ('2040024','Geometría Computacional',3,6,'C2','OBLIGATORIA',false,false,'geometria computacional'),
    ('2040020','Periféricos e Interfaces',3,6,'C2','OBLIGATORIA',false,false,'perifericos e interfaces'),
    ('2040025','Sistemas Empotrados y de Tiempo Real I',3,6,'C2','OBLIGATORIA',false,false,'sistemas empotrados y de tiempo real i'),

    -- 4º Obligatorias
    ('2040032','Laboratorio de Desarrollo de Hardware',4,6,'C1','OBLIGATORIA',false,false,'laboratorio de desarrollo de hardware'),
    ('2040033','Planificación y Gestión de Proyectos Informáticos',4,6,'C1','OBLIGATORIA',false,false,'planificacion y gestion de proyectos informaticos'),
    ('2040036','Sistemas Empotrados y de Tiempo Real II',4,6,'C1','OBLIGATORIA',false,false,'sistemas empotrados y de tiempo real ii'),
    ('2040046','Trabajo Fin de Grado',4,12,'C2','TFG',false,false,'trabajo fin de grado'),

    -- 4º Optativas
    ('2040027','Prácticas Externas',4,6,'A','OPTATIVA',false,true,'practicas externas'),
    ('2040028','Criptografía',4,6,'C1','OPTATIVA',false,true,'criptografia'),
    ('2040030','Fiabilidad y Tolerancia a Fallos',4,6,'C1','OPTATIVA',false,true,'fiabilidad y tolerancia a fallos'),
    ('2040031','Gestión de la Producción',4,6,'C1','OPTATIVA',false,true,'gestion de la produccion'),
    ('2040034','Procesamiento Digital de Señales',4,6,'C1','OPTATIVA',false,true,'procesamiento digital de senales'),
    ('2040035','Seguridad en Sistemas Informáticos y en Internet',4,6,'C1','OPTATIVA',false,true,'seguridad en sistemas informaticos y en internet'),
    ('2040037','Tecnología, Informática y Sociedad',4,6,'C1','OPTATIVA',false,true,'tecnologia informatica y sociedad'),
    ('2040038','Acceso Inteligente a la Información',4,6,'C2','OPTATIVA',false,true,'acceso inteligente a la informacion'),
    ('2040039','Aplicaciones de Soft Computing',4,6,'C2','OPTATIVA',false,true,'aplicaciones de soft computing'),
    ('2040029','Estadística Computacional',4,6,'C2','OPTATIVA',false,true,'estadistica computacional'),
    ('2040040','Integración de Sistemas Físicos e Informáticos',4,6,'C2','OPTATIVA',false,true,'integracion de sistemas fisicos e informaticos'),
    ('2040041','Plataformas Hardware de Aplicación Específica',4,6,'C2','OPTATIVA',false,true,'plataformas hardware de aplicacion especifica'),
    ('2040042','Procesamiento de Imágenes Digitales',4,6,'C2','OPTATIVA',false,true,'procesamiento de imagenes digitales'),
    ('2040043','Robótica y Automatización',4,6,'C2','OPTATIVA',false,true,'robotica y automatizacion'),
    ('2040044','Sistemas de Adquisición y Control',4,6,'C2','OPTATIVA',false,true,'sistemas de adquisicion y control'),
    ('2040045','Teledetección',4,6,'C2','OPTATIVA',false,true,'teledeteccion')
) AS v(codigo, nombre, curso, creditos, duracion, tipologia, es_formacion_basica, es_optativa, nombre_normalizado)
ON CONFLICT (codigo) DO NOTHING;

-- =========================================
-- 3) Asignaturas TI (obligatorias + optativas)
-- =========================================
INSERT INTO asignaturas (
  id, titulacion_id, departamento_id, codigo, nombre, curso, creditos, duracion,
  tipologia, es_formacion_basica, es_optativa, nombre_normalizado, palabras_clave, activa
)
SELECT
  gen_random_uuid(),
  (SELECT id FROM titulaciones WHERE codigo = 'GII-TI' LIMIT 1),
  NULL,
  v.codigo,
  v.nombre,
  v.curso,
  v.creditos,
  v.duracion,
  v.tipologia,
  v.es_formacion_basica,
  v.es_optativa,
  v.nombre_normalizado,
  NULL::text[],
  true
FROM (
  VALUES
    -- 1º Formación básica
    ('2060001','Fundamentos de Programación',1,12,'A','FORMACION_BASICA',true,false,'fundamentos de programacion'),
    ('2060003','Cálculo Infinitesimal y Numérico',1,6,'C1','FORMACION_BASICA',true,false,'calculo infinitesimal y numerico'),
    ('2060004','Circuitos Electrónicos Digitales',1,6,'C1','FORMACION_BASICA',true,false,'circuitos electronicos digitales'),
    ('2060009','Fundamentos Físicos de la Informática',1,6,'C1','FORMACION_BASICA',true,false,'fundamentos fisicos de la informatica'),
    ('2060005','Introducción a la Matemática Discreta',1,6,'C1','FORMACION_BASICA',true,false,'introduccion a la matematica discreta'),
    ('2060002','Administración de Empresas',1,6,'C2','FORMACION_BASICA',true,false,'administracion de empresas'),
    ('2060006','Álgebra Lineal y Numérica',1,6,'C2','FORMACION_BASICA',true,false,'algebra lineal y numerica'),
    ('2060007','Estadística',1,6,'C2','FORMACION_BASICA',true,false,'estadistica'),
    ('2060008','Estructura de Computadores',1,6,'C2','FORMACION_BASICA',true,false,'estructura de computadores'),

    -- 2º Obligatorias
    ('2060010','Análisis y Diseño de Datos y Algoritmos',2,12,'A','OBLIGATORIA',false,false,'analisis y diseno de datos y algoritmos'),
    ('2060054','Introducción a la Ingeniería del Software y los Sistemas de Información I',2,6,'C1','OBLIGATORIA',false,false,'introduccion a la ingenieria del software y los sistemas de informacion i'),
    ('2060013','Matemática Discreta',2,6,'C1','OBLIGATORIA',false,false,'matematica discreta'),
    ('2060014','Redes de Computadores',2,6,'C1','OBLIGATORIA',false,false,'redes de computadores'),
    ('2060015','Arquitectura de Computadores',2,6,'C2','OBLIGATORIA',false,false,'arquitectura de computadores'),
    ('2060055','Introducción a la Ingeniería del Software y los Sistemas de Información II',2,6,'C2','OBLIGATORIA',false,false,'introduccion a la ingenieria del software y los sistemas de informacion ii'),
    ('2060017','Sistemas Operativos',2,6,'C2','OBLIGATORIA',false,false,'sistemas operativos'),

    -- 2º Optativas (menciones)
    ('2060012','Lógica Informática',2,6,'C1','OPTATIVA',false,true,'logica informatica'),
    ('2060016','Arquitectura de Redes',2,6,'C2','OPTATIVA',false,true,'arquitectura de redes'),

    -- 3º Obligatoria
    ('2060021','Inteligencia Artificial',3,6,'C1','OBLIGATORIA',false,false,'inteligencia artificial'),

    -- 3º Optativas
    ('2060018','Configuración, Implementación y Mantenimiento de Sistemas Informáticos',3,6,'C1','OPTATIVA',false,true,'configuracion implementacion y mantenimiento de sistemas informaticos'),
    ('2060019','Gestión de Sistemas de Información',3,6,'C1','OPTATIVA',false,true,'gestion de sistemas de informacion'),
    ('2060020','Gestión y Estrategia Empresarial',3,6,'C1','OPTATIVA',false,true,'gestion y estrategia empresarial'),
    ('2060022','Procesadores de Lenguajes',3,6,'C1','OPTATIVA',false,true,'procesadores de lenguajes'),
    ('2060023','Programación Declarativa',3,6,'C1','OPTATIVA',false,true,'programacion declarativa'),
    ('2060024','Tecnologías Avanzadas de la Información',3,6,'C1','OPTATIVA',false,true,'tecnologias avanzadas de la informacion'),
    ('2060025','Ampliación de Inteligencia Artificial',3,6,'C2','OPTATIVA',false,true,'ampliacion de inteligencia artificial'),
    ('2060026','Arquitectura de Sistemas Distribuidos',3,6,'C2','OPTATIVA',false,true,'arquitectura de sistemas distribuidos'),
    ('2060027','Matemática Aplicada a Sistemas de Información',3,6,'C2','OPTATIVA',false,true,'matematica aplicada a sistemas de informacion'),
    ('2060028','Sistemas de Información Empresariales',3,6,'C2','OPTATIVA',false,true,'sistemas de informacion empresariales'),
    ('2060029','Sistemas Inteligentes',3,6,'C2','OPTATIVA',false,true,'sistemas inteligentes'),
    ('2060030','Sistemas Orientados a Servicios',3,6,'C2','OPTATIVA',false,true,'sistemas orientados a servicios'),

    -- 4º Obligatorias
    ('2060040','Planificación y Gestión de Proyectos Informáticos',4,6,'C1','OBLIGATORIA',false,false,'planificacion y gestion de proyectos informaticos'),
    ('2060053','Trabajo Fin de Grado',4,12,'C2','TFG',false,false,'trabajo fin de grado'),

    -- 4º Optativas
    ('2060033','Administración de Sistemas de Información',4,6,'C1','OPTATIVA',false,true,'administracion de sistemas de informacion'),
    ('2060034','Gestión de Procesos y Servicios',4,6,'C1','OPTATIVA',false,true,'gestion de procesos y servicios'),
    ('2060035','Infraestructura de Sistemas de Información',4,6,'C1','OPTATIVA',false,true,'infraestructura de sistemas de informacion'),
    ('2060037','Interacción Persona-ordenador',4,6,'C1','OPTATIVA',false,true,'interaccion persona ordenador'),
    ('2060038','Matemática Aplicada a Tecnologías de la Información',4,6,'C1','OPTATIVA',false,true,'matematica aplicada a tecnologias de la informacion'),
    ('2060039','Matemáticas para la Computación',4,6,'C1','OPTATIVA',false,true,'matematicas para la computacion'),
    ('2060045','Computación Móvil',4,6,'C2','OPTATIVA',false,true,'computacion movil'),
    ('2060049','Inteligencia Empresarial',4,6,'C2','OPTATIVA',false,true,'inteligencia empresarial'),
    ('2060050','Modelado y Análisis de Requisitos en Sistemas de Información',4,6,'C2','OPTATIVA',false,true,'modelado y analisis de requisitos en sistemas de informacion'),
    ('2060051','Modelos de Computación y Complejidad',4,6,'C2','OPTATIVA',false,true,'modelos de computacion y complejidad'),

    -- Optativas comunes
    ('2060031','Prácticas Externas',4,6,'A','OPTATIVA',false,true,'practicas externas'),
    ('2060036','Integración de Sistemas Físicos e Informáticos',4,6,'C1','OPTATIVA',false,true,'integracion de sistemas fisicos e informaticos'),
    ('2060041','Procesamiento de Imágenes Digitales',4,6,'C1','OPTATIVA',false,true,'procesamiento de imagenes digitales'),
    ('2060042','Seguridad en Sistemas Informáticos y en Internet',4,6,'C1','OPTATIVA',false,true,'seguridad en sistemas informaticos y en internet'),
    ('2060043','Teledetección',4,6,'C1','OPTATIVA',false,true,'teledeteccion'),
    ('2060032','Acceso Inteligente a la Información',4,6,'C2','OPTATIVA',false,true,'acceso inteligente a la informacion'),
    ('2060044','Aplicaciones de Soft Computing',4,6,'C2','OPTATIVA',false,true,'aplicaciones de soft computing'),
    ('2060046','Criptografía',4,6,'C2','OPTATIVA',false,true,'criptografia'),
    ('2060047','Estadística Computacional',4,6,'C2','OPTATIVA',false,true,'estadistica computacional'),
    ('2060048','Gestión de la Producción',4,6,'C2','OPTATIVA',false,true,'gestion de la produccion'),
    ('2060052','Tecnología, Informática y Sociedad',4,6,'C2','OPTATIVA',false,true,'tecnologia informatica y sociedad')
) AS v(codigo, nombre, curso, creditos, duracion, tipologia, es_formacion_basica, es_optativa, nombre_normalizado)
ON CONFLICT (codigo) DO NOTHING;
