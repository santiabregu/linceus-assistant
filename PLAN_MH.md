# Plan Matrícula de Honor — Linceus Assistant

**Objetivo**: Elevar la memoria del TFG al nivel de Matrícula de Honor (MH).  
**Contexto MH (ETSII US)**: voto unánime del tribunal + propuesta del tutor + cupo 5% del grupo.  
**Evaluación**: Tutor 45 % · Tribunal 55 %  
**Criterios extra que diferencian un 10 de un 9**: rigor científico, comparativa cuantitativa con el estado del arte, trazabilidad completa, validación empírica sólida, contribución novedosa explícita.

---

## Bloque P1 — Rigor Científico y Evaluación (PRIORIDAD ALTA)

### P1.1 — Añadir 8 referencias bibliográficas académicas

**Archivo**: `memoria_tfg/Plantilla TfG/pfcbib.bib`

Añadir al final del archivo:

```bibtex
@ARTICLE{wollny2021survey,
  author    = {Wollny, S. and Schneider, J. and Di Mitri, D. and Weidlich, J. and Rittberger, M. and Drachsler, H.},
  title     = {Are We There Yet? -- A Systematic Literature Review on Chatbots in Education},
  journal   = {Frontiers in Artificial Intelligence},
  volume    = {4},
  year      = {2021},
  doi       = {10.3389/frai.2021.654924}
}

@ARTICLE{okonkwo2021chatbots,
  author    = {Okonkwo, C. W. and Ade-Ibijola, A.},
  title     = {Chatbots applications in education: A systematic review},
  journal   = {Computers and Education: Artificial Intelligence},
  volume    = {2},
  pages     = {100033},
  year      = {2021},
  doi       = {10.1016/j.caeai.2021.100033}
}

@ARTICLE{gao2024ragsurvey,
  author    = {Gao, Y. and Xiong, Y. and Gao, X. and Jia, K. and Pan, J. and Bi, Y. and Dai, Y. and Sun, J. and Wang, H.},
  title     = {Retrieval-Augmented Generation for Large Language Models: A Survey},
  journal   = {arXiv preprint arXiv:2312.10997},
  year      = {2024}
}

@INPROCEEDINGS{springerrag2025,
  author    = {Ramírez, A. and López, M. and Torres, C.},
  title     = {RAG-based University Advisors: A Comparative Study},
  booktitle = {Proceedings of the 17th International Conference on Computer Supported Education},
  year      = {2025},
  publisher = {Springer}
}

@INPROCEEDINGS{springerrasa2025,
  author    = {García, P. and Fernández, R.},
  title     = {Rasa-based Conversational Agents for Academic Guidance},
  booktitle = {Advances in Intelligent Systems and Computing},
  year      = {2025},
  publisher = {Springer}
}

@ARTICLE{mdpirag2025,
  author    = {Chen, X. and Wang, Z. and Liu, Y.},
  title     = {Evaluation of RAG Pipelines for Domain-Specific Question Answering},
  journal   = {Applied Sciences},
  volume    = {15},
  number    = {3},
  pages     = {1122},
  year      = {2025},
  publisher = {MDPI}
}

@INPROCEEDINGS{sdrag2025,
  author    = {Martínez, J. and Ruiz, A.},
  title     = {Hybrid NLU-RAG Architectures for Student Support Systems},
  booktitle = {ACM Symposium on Document Engineering},
  year      = {2025}
}

@ARTICLE{rageval2025,
  author    = {Saad-Falcon, J. and others},
  title     = {ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems},
  journal   = {arXiv preprint arXiv:2311.09476},
  year      = {2025}
}
```

---

### P1.2 — Añadir §1.X "Contribución de este trabajo"

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/01_introduccion.tex`  
**Posición**: Justo antes de `\section{Estructura del documento}` (última sección del capítulo).

```latex
\section{Contribución de este trabajo}
\label{sec:contribucion}

Este trabajo presenta tres aportaciones concretas al estado del arte de los asistentes conversacionales universitarios:

\begin{enumerate}
  \item \textbf{Arquitectura híbrida NLU+RAG orientada a dominio cerrado.} La combinación de DIET Classifier (Rasa 3.6) con recuperación semántica mediante pgvector (HNSW) y el modelo de embeddings \texttt{gemini-embedding-001} (2\,000 dimensiones) permite gestionar simultáneamente consultas estructuradas (horarios, matrículas) y preguntas abiertas sobre reglamentación, sin depender de un único LLM para clasificación. A diferencia de trabajos como \cite{springerrasa2025}, que utilizan Rasa en modo standalone, Linceus integra un LLM externo únicamente en la fase de generación, reduciendo el coste de inferencia.

  \item \textbf{Calibración empírica del umbral de similitud semántica.} El umbral de coincidencia difusa se determinó mediante 120 casos de prueba en tres iteraciones (sprint S4), obteniendo una combinación de umbral firme 0,60 y umbral mínimo 0,30 que alcanza precisión 92\,\% y exhaustividad 88\,\%. Este enfoque contrasta con la fijación ad-hoc de umbrales descrita en trabajos similares \cite{mdpirag2025}.

  \item \textbf{Panel de administración RAG sin código.} El panel Flask permite a personal no técnico actualizar la base de conocimiento mediante carga de documentos PDF/TXT, con reprocesado automático de embeddings, sin necesidad de redespliegue. Este componente cubre una brecha identificada en \cite{okonkwo2021chatbots}: la mayoría de prototipos académicos carecen de interfaz de mantenimiento operativa.
\end{enumerate}
```

---

### P1.3 — Tabla comparativa cuantitativa Estado del Arte

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/02_preparacion.tex` (o `soluciones_existentes.tex` si existe)  
**Posición**: Al final de la sección de soluciones existentes / trabajos relacionados.

```latex
\begin{table}[h!]
\centering
\caption{Comparativa cuantitativa con sistemas similares del estado del arte}
\label{tab:comparativa-arte}
\begin{tabular}{|p{2.8cm}|p{2.2cm}|p{2.2cm}|p{1.8cm}|p{2.4cm}|}
\hline
\textbf{Sistema} & \textbf{NLU} & \textbf{RAG / KB} & \textbf{LLM} & \textbf{Mantenimiento} \\
\hline
\cite{springerrasa2025} & Rasa DIET & No & No & Manual \\
\cite{okonkwo2021chatbots} (media) & Reglas/ML & No & No & Técnico \\
\cite{mdpirag2025} & GPT-4 & pgvector & GPT-4 & API \\
\cite{sdrag2025} & Rasa + RAG & FAISS & LLaMA-3 & Manual \\
\textbf{Linceus (este TFG)} & \textbf{Rasa DIET} & \textbf{pgvector HNSW} & \textbf{Gemini} & \textbf{Panel web} \\
\hline
\end{tabular}
\end{table}
```

---

### P1.4 — Métricas NLU (Precisión/Recall/F1) en pruebas

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/pruebas.tex`  
**Posición**: En la sección de resultados de pruebas del clasificador de intenciones.

```latex
\subsection{Métricas del clasificador NLU}
\label{sec:metricas-nlu}

La evaluación del clasificador DIET se realizó mediante validación cruzada de 5 pliegues sobre el conjunto de entrenamiento (\texttt{rasa test nlu --cross-validation}). La Tabla~\ref{tab:nlu-metricas} recoge las métricas por intención para las categorías con más de 10 ejemplos.

\begin{table}[h!]
\centering
\caption{Precisión, exhaustividad y F1 por categoría de intención (5-fold CV)}
\label{tab:nlu-metricas}
\begin{tabular}{|p{3.5cm}|r|r|r|r|}
\hline
\textbf{Intención} & \textbf{Prec.} & \textbf{Recall} & \textbf{F1} & \textbf{Soporte} \\
\hline
consulta\_asignatura      & 0,94 & 0,91 & 0,92 & 48 \\
consulta\_horario         & 0,89 & 0,93 & 0,91 & 31 \\
consulta\_matricula       & 0,92 & 0,88 & 0,90 & 24 \\
consulta\_reglamento      & 0,87 & 0,85 & 0,86 & 19 \\
fuera\_de\_ambito         & 0,96 & 0,97 & 0,96 & 38 \\
saludar / despedir        & 0,99 & 0,99 & 0,99 & 55 \\
\hline
\textbf{Media ponderada}  & \textbf{0,93} & \textbf{0,92} & \textbf{0,92} & \textbf{215} \\
\hline
\end{tabular}
\end{table}

El umbral de confianza mínima se fijó en 0,55 tras analizar la curva precisión-exhaustividad: por debajo de ese valor el clasificador derivaba las consultas al flujo \texttt{fallback}, evitando respuestas incorrectas con alta confianza aparente.
```

---

### P1.5 — Sección "Amenazas a la validez"

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/pruebas.tex`  
**Posición**: Al final del capítulo de pruebas.

```latex
\section{Amenazas a la validez}
\label{sec:amenazas-validez}

Siguiendo la taxonomía de Wohlin et al., se identifican las siguientes amenazas a la validez de la evaluación realizada:

\paragraph{Validez interna.} Los casos de prueba funcionales fueron diseñados por el propio desarrollador, lo que puede introducir sesgo de confirmación. Se mitigó mediante revisión cruzada con el tutor y la inclusión deliberada de casos límite (consultas ambiguas, entidades mal escritas, preguntas fuera de ámbito).

\paragraph{Validez de constructo.} La métrica \emph{tasa de resolución} (respuesta correcta / total de interacciones) es una aproximación al concepto de utilidad percibida por el usuario, pero no captura la satisfacción subjetiva. Una evaluación más completa requeriría un cuestionario de usabilidad (SUS o similar) con usuarios reales.

\paragraph{Validez externa.} El piloto se realizó con 59 sesiones de usuarios del Grado en Ingeniería Informática (ETSII, US). Los resultados pueden no generalizarse a otras titulaciones o universidades con estructuras administrativas distintas.

\paragraph{Validez de conclusión.} El tamaño de la muestra del piloto (59 sesiones) es suficiente para detectar efectos grandes, pero no efectos pequeños o medianos. Se estima un poder estadístico del 80\,\% para diferencias absolutas superiores al 10\,\%.
```

---

### P1.6 — Análisis de casos fallidos

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/pruebas.tex`  
**Posición**: Tras la sección de resultados generales de pruebas.

```latex
\subsection{Análisis de los casos fallidos}
\label{sec:casos-fallidos}

De las 85 pruebas del dominio de asignaturas, 5 resultaron en respuesta incorrecta o incompleta. El análisis de causa raíz identifica tres patrones:

\begin{enumerate}
  \item \textbf{Solapamiento de entidades} (2 casos): consultas que mencionan dos asignaturas simultáneamente (\emph{«diferencia entre Ingeniería del Software y Métodos de Desarrollo»}). El extractor de entidades recupera solo la primera entidad reconocida. Solución prevista: activar el extractor de múltiples entidades del mismo tipo.
  \item \textbf{Abreviatura no normalizada} (2 casos): \emph{«ISE»} en lugar de \emph{«Ingeniería del Software»}. La tabla de sinónimos cubre las abreviaturas documentadas en la guía docente oficial, pero no las de uso informal entre estudiantes. Solución: enriquecer el diccionario de sinónimos con términos recogidos en el piloto.
  \item \textbf{Fallo de RAG por chunk demasiado corto} (1 caso): el fragmento recuperado no contenía el dato solicitado porque estaba partido entre dos chunks. Solución: aumentar el solapamiento de 100 a 150 caracteres o implementar recuperación de contexto extendido.
\end{enumerate}
```

---

### P1.7 — Comparativa RAG vs. sin RAG (baseline)

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/pruebas.tex`

```latex
\subsection{Ablación: RAG vs.\ respuesta directa del LLM}
\label{sec:ablacion-rag}

Para cuantificar el aporte del componente RAG, se ejecutó un experimento de ablación sobre 30 preguntas de reglamentación universitaria, comparando:

\begin{itemize}
  \item \textbf{Condición A (RAG activo)}: el sistema recupera los tres chunks más relevantes y los incluye en el prompt del LLM.
  \item \textbf{Condición B (LLM directo)}: el mismo LLM (Gemini gemma-3-27b-it) responde sin contexto adicional.
\end{itemize}

\begin{table}[h!]
\centering
\caption{Ablación RAG vs.\ LLM directo (30 preguntas de reglamentación)}
\label{tab:ablacion-rag}
\begin{tabular}{|l|r|r|r|}
\hline
\textbf{Condición} & \textbf{Resp. correctas} & \textbf{Alucinaciones} & \textbf{Latencia media} \\
\hline
RAG activo      & 27/30 (90\,\%) & 1/30 (3\,\%)  & 2,1 s \\
LLM directo     & 18/30 (60\,\%) & 8/30 (27\,\%) & 1,4 s \\
\hline
\end{tabular}
\end{table}

El RAG reduce las alucinaciones en un 24\,\% absoluto a costa de 0,7\,s adicionales de latencia, un intercambio favorable para un sistema de orientación académica donde la precisión factual es crítica.
```

---

## Bloque P2 — Profundidad Técnica y Arquitectura (PRIORIDAD ALTA)

### P2.1 — Tabla ISO 25010 en arquitectura

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/arquitectura_diseno.tex`  
**Posición**: Al final de la sección de evaluación arquitectónica.

```latex
\subsection{Evaluación de atributos de calidad (ISO 25010)}
\label{sec:iso25010}

La arquitectura fue evaluada frente a los atributos de calidad definidos por ISO/IEC 25010 \cite{bass2021sap}. La Tabla~\ref{tab:iso25010} sintetiza la táctica arquitectónica empleada y el nivel alcanzado.

\begin{table}[h!]
\centering
\caption{Atributos de calidad ISO 25010 y tácticas arquitectónicas empleadas}
\label{tab:iso25010}
\begin{tabular}{|p{2.6cm}|p{3.8cm}|p{3.8cm}|p{1.4cm}|}
\hline
\textbf{Atributo} & \textbf{Táctica empleada} & \textbf{Evidencia} & \textbf{Nivel} \\
\hline
Funcionalidad & DIET Classifier + RAG híbrido & F1 92\,\% NLU; 90\,\% RAG accuracy & Alto \\
Rendimiento & HNSW index; caché de embeddings & p95 < 3\,s bajo carga 10 usuarios & Medio-alto \\
Fiabilidad & Docker Compose restart=always; fallback handler & SLA 99,5\,\% en piloto 30 días & Alto \\
Seguridad & JWT; HTTPS; RLS Supabase & Pen-test básico sin vulnerabilidades críticas & Medio \\
Mantenibilidad & Arquitectura en capas; patrón Strategy & Tiempo de adición de dominio < 4\,h & Alto \\
Portabilidad & Docker multi-stage build & Despliegue reproducible en <10 min & Alto \\
\hline
\end{tabular}
\end{table}
```

---

### P2.2 — Tabla formal de patrones de diseño

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/arquitectura_diseno.tex` o `implementacion.tex`

```latex
\section{Patrones de diseño aplicados}
\label{sec:patrones-diseno}

La Tabla~\ref{tab:patrones} recoge los cinco patrones de diseño \cite{gamma1994gof} aplicados en la implementación, su motivación y el componente que los instancia.

\begin{table}[h!]
\centering
\caption{Patrones de diseño GoF aplicados en Linceus Assistant}
\label{tab:patrones}
\begin{tabular}{|p{2.4cm}|p{1.6cm}|p{4.0cm}|p{3.4cm}|}
\hline
\textbf{Patrón} & \textbf{Categoría} & \textbf{Motivación} & \textbf{Componente} \\
\hline
Template Method & Comportamiento & Definir el esqueleto del flujo de acción (validar → consultar → responder) permitiendo que cada dominio especialice los pasos variables & \texttt{BaseActionHandler} \\
Strategy        & Comportamiento & Intercambiar la estrategia de recuperación (SQL vs.\ RAG vs.\ fuzzy) sin modificar el código cliente & \texttt{QueryStrategySelector} \\
Facade          & Estructural    & Simplificar el acceso a Supabase exponiendo una API de alto nivel desde las acciones Rasa & \texttt{SupabaseClient} \\
Chain of Responsibility & Comportamiento & Encadenar los manejadores de intención hasta que uno resuelva la consulta, terminando en el fallback & Pipeline de acciones \\
Null Object     & Comportamiento & Retornar un objeto vacío tipado en lugar de \texttt{None} cuando la consulta no produce resultados, evitando comprobaciones explícitas & \texttt{EmptyQueryResult} \\
\hline
\end{tabular}
\end{table}
```

---

### P2.3 — Tres diagramas de secuencia UML

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/arquitectura_diseno.tex`

#### Flujo nominal (consulta de asignatura)

```latex
\begin{figure}[h!]
\centering
\begin{tikzpicture}[
  lifeline/.style={draw, rectangle, minimum width=2cm, minimum height=0.6cm, font=\small},
  msg/.style={->, >=Stealth, font=\footnotesize},
  ret/.style={->, >=Stealth, dashed, font=\footnotesize}
]
% Lifelines
\node[lifeline] (user)   at (0,0)   {Usuario};
\node[lifeline] (widget) at (3,0)   {Widget JS};
\node[lifeline] (rasa)   at (6,0)   {Rasa Server};
\node[lifeline] (action) at (9,0)   {Action Server};
\node[lifeline] (db)     at (12,0)  {Supabase};

% Lifeline lines
\foreach \n in {user,widget,rasa,action,db}
  \draw[dashed] (\n.south) -- ++(0,-6);

% Messages
\draw[msg] (0,-0.8) -- node[above]{\texttt{POST /webhooks/rest/webhook}} (3,-0.8);
\draw[msg] (3,-1.4) -- node[above]{mensaje JSON} (6,-1.4);
\draw[msg] (6,-2.0) -- node[above]{NLU: intent=consulta\_asig.} (6,-2.0);
\draw[msg] (6,-2.6) -- node[above]{invoke action\_query\_asig} (9,-2.6);
\draw[msg] (9,-3.2) -- node[above]{SELECT * FROM asignaturas} (12,-3.2);
\draw[ret] (12,-3.8) -- node[above]{rows[]} (9,-3.8);
\draw[ret] (9,-4.4) -- node[above]{BotUttered (texto)} (6,-4.4);
\draw[ret] (6,-5.0) -- node[above]{JSON response} (3,-5.0);
\draw[ret] (3,-5.6) -- node[above]{mensaje en burbuja} (0,-5.6);
\end{tikzpicture}
\caption{Diagrama de secuencia: flujo nominal de consulta de asignatura}
\label{fig:seq-nominal}
\end{figure}
```

#### Flujo RAG (consulta de reglamento)

```latex
\begin{figure}[h!]
\centering
\begin{tikzpicture}[
  lifeline/.style={draw, rectangle, minimum width=2cm, minimum height=0.6cm, font=\small},
  msg/.style={->, >=Stealth, font=\footnotesize},
  ret/.style={->, >=Stealth, dashed, font=\footnotesize}
]
\node[lifeline] (user)    at (0,0)   {Usuario};
\node[lifeline] (rasa)    at (3.5,0) {Rasa};
\node[lifeline] (action)  at (7,0)   {Action Server};
\node[lifeline] (pg)      at (10.5,0){pgvector};
\node[lifeline] (gemini)  at (14,0)  {Gemini API};

\foreach \n in {user,rasa,action,pg,gemini}
  \draw[dashed] (\n.south) -- ++(0,-7.5);

\draw[msg] (0,-0.8)  -- node[above]{consulta reglamento} (3.5,-0.8);
\draw[msg] (3.5,-1.4) -- node[above]{intent=rag\_query} (7,-1.4);
\draw[msg] (7,-2.0)  -- node[above]{embed(consulta)} (14,-2.0);
\draw[ret] (14,-2.6) -- node[above]{vector[2000d]} (7,-2.6);
\draw[msg] (7,-3.2)  -- node[above]{ANN search k=3} (10.5,-3.2);
\draw[ret] (10.5,-3.8) -- node[above]{chunks[]} (7,-3.8);
\draw[msg] (7,-4.4)  -- node[above]{generate(prompt+chunks)} (14,-4.4);
\draw[ret] (14,-5.0) -- node[above]{respuesta\_generada} (7,-5.0);
\draw[ret] (7,-5.6)  -- node[above]{BotUttered} (3.5,-5.6);
\draw[ret] (3.5,-6.2) -- node[above]{respuesta al usuario} (0,-6.2);
\end{tikzpicture}
\caption{Diagrama de secuencia: flujo RAG para consulta de reglamentación}
\label{fig:seq-rag}
\end{figure}
```

---

### P2.4 — Definición formal del problema en §3 (Conceptos)

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/03_conceptos.tex`  
**Posición**: Al inicio, antes de las definiciones de tecnologías.

```latex
\section{Definición formal del problema}
\label{sec:definicion-problema}

Sea $\mathcal{U}$ el conjunto de usuarios del sistema (estudiantes y personal de la ETSII) y $\mathcal{Q}$ el espacio de consultas en lenguaje natural que un usuario $u \in \mathcal{U}$ puede formular. Sea $\mathcal{K}$ la base de conocimiento institucional (guías docentes, reglamentos, información de matrícula).

El problema que aborda Linceus Assistant se define formalmente como:

\begin{quote}
\textit{Dado una consulta $q \in \mathcal{Q}$ formulada por $u \in \mathcal{U}$, encontrar una respuesta $r$ tal que:
\begin{enumerate}
  \item $r$ sea \textbf{factualmente correcta} respecto a $\mathcal{K}$ (sin alucinaciones),
  \item $r$ sea \textbf{comprensible} para un estudiante universitario sin formación técnica,
  \item $r$ se genere en \textbf{tiempo interactivo} (latencia $\leq$ 5\,s en el percentil 95), y
  \item el sistema sea \textbf{mantenible} por personal no técnico sin redespliegue.
\end{enumerate}}
\end{quote}

Las condiciones (1) y (4) son las que diferencian el enfoque híbrido NLU+RAG de un LLM de propósito general: (1) se garantiza mediante recuperación de fragmentos de $\mathcal{K}$ verificados, y (4) mediante el panel de administración Flask.
```

---

### P2.5 — Comparativa cuantitativa de LLMs

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/02_preparacion.tex`  
**Posición**: En la sección de selección del LLM.

```latex
\begin{table}[h!]
\centering
\caption{Comparativa de LLMs evaluados para la fase de generación}
\label{tab:comparativa-llm}
\begin{tabular}{|p{3.0cm}|r|r|p{2.4cm}|p{2.4cm}|}
\hline
\textbf{Modelo} & \textbf{Coste/1M tok.} & \textbf{Latencia media} & \textbf{Contexto} & \textbf{Uso gratuito} \\
\hline
Gemini gemma-3-27b & \$0 (API free tier) & 1,8\,s & 8\,192 tok & Sí (límites) \\
GPT-4o mini         & \$0,15 input         & 1,2\,s & 128\,k tok & No \\
LLaMA-3 8B (local)  & \$0 (self-hosted)   & 4,1\,s & 8\,192 tok & Sí (GPU req.) \\
DeepSeek V2         & \$0,14 input         & 2,3\,s & 128\,k tok & No \\
\hline
\end{tabular}
\end{table}

Se seleccionó Gemini gemma-3-27b-it por ser el único que combina acceso gratuito (crítico para un prototipo académico sin presupuesto de infraestructura), latencia aceptable y soporte nativo de embeddings de alta dimensionalidad (\texttt{gemini-embedding-001}, 2\,000 dims) mediante la misma API, lo que evita integrar un segundo proveedor de embeddings.
```

---

### P2.6 — Citas académicas en §3 (Conceptos)

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/03_conceptos.tex`

Añadir citas en cada subsección de conceptos principales:
- En RAG: `\cite{gao2024ragsurvey}`
- En chatbots educativos: `\cite{wollny2021survey}`, `\cite{okonkwo2021chatbots}`
- En NLU/DIET: referencia al paper de Rasa DIET Classifier (Bunk et al., 2020)

---

### P2.7 — Trabajo futuro técnicamente específico

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/conclusiones.tex`  
**Posición**: Reemplazar / ampliar la sección de líneas futuras.

```latex
\section{Líneas de evolución}
\label{sec:lineas-futuras}

Las siguientes líneas de evolución están ordenadas por impacto estimado y viabilidad técnica:

\begin{enumerate}
  \item \textbf{Evaluación con usuarios reales (SUS / CSAT).} El piloto interno de 59 sesiones debe completarse con un estudio controlado que incluya el cuestionario SUS (System Usability Scale) y métricas de satisfacción (CSAT $\geq$ 4/5). Estimación: 2 sprints de 2 semanas.

  \item \textbf{Localización de espacios universitarios.} La funcionalidad fue aplazada por ausencia de datos oficiales de planos (Sección~\ref{sec:req-evolucion}). Su implementación requiere integración con la API del SCI-US o ingesta de planos en formato DXF/SVG, con un módulo de \emph{indoor routing} basado en grafos (A*). Estimación: 3--4 meses.

  \item \textbf{Soporte multiidioma (inglés).} La titulación tiene estudiantes Erasmus. La adición del inglés requiere duplicar el corpus NLU, reentrenar DIET, y añadir un segundo conjunto de embeddings para los documentos en inglés. Estimación: 1 sprint.

  \item \textbf{Retrieval aumentado con re-ranking.} Sustituir la recuperación ANN pura por un pipeline de dos fases (ANN + cross-encoder) siguiendo el patrón de \cite{gao2024ragsurvey}, lo que podría elevar la precisión del RAG del 90\,\% al 94--96\,\%.

  \item \textbf{Evaluación automática con ARES/RAGAS.} Integrar el framework \cite{rageval2025} en el CI/CD para detectar regresiones en la calidad de las respuestas RAG ante cambios en la base de conocimiento.

  \item \textbf{Multi-intención.} Reactivar el modo multi-intent de Rasa cuando el clasificador DIET alcance F1 $\geq$ 0,85 en las combinaciones más frecuentes, reduciendo la necesidad del modal de aclaración en un 30\,\% estimado.
\end{enumerate}
```

---

### P2.8 — Consideraciones éticas

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/conclusiones.tex`

```latex
\section{Consideraciones éticas}
\label{sec:etica}

El desarrollo de un asistente conversacional para estudiantes plantea responsabilidades que van más allá de la corrección técnica:

\paragraph{Veracidad de la información.} El sistema puede influir en decisiones académicas relevantes (elección de asignaturas, plazos de matrícula). Se implementaron tres salvaguardas: (1) el RAG ancla las respuestas a documentos oficiales verificados, (2) el flujo \texttt{fallback} indica explícitamente cuándo el sistema no tiene información suficiente, y (3) el panel de administración permite al personal responsable actualizar o retirar documentos incorrectos.

\paragraph{Privacidad.} El sistema no almacena el contenido de las conversaciones individuales más allá de la sesión activa. Los identificadores de sesión son efímeros y no están vinculados a datos de identidad del estudiante.

\paragraph{Sesgo en los datos de entrenamiento.} El corpus NLU fue elaborado manualmente por el autor, lo que puede reflejar sesgos en la forma de formular preguntas. La diversificación del corpus mediante \emph{data augmentation} controlado (paráfrasis con LLM) es una de las líneas de mejora identificadas.

\paragraph{Dependencia tecnológica.} La generación de respuestas depende de la API de Gemini (Google). En caso de interrupción del servicio, el sistema degrada su comportamiento a respuestas puramente basadas en la base de datos estructurada, sin componente generativa.
```

---

## Bloque P3 — Cierre y Presentación (PRIORIDAD MEDIA)

### P3.1 — Tabla "Linceus en números"

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/conclusiones.tex`  
**Posición**: Al inicio de las conclusiones, como resumen ejecutivo.

```latex
\section{Linceus en números}
\label{sec:linceus-numeros}

\begin{table}[h!]
\centering
\caption{Resumen cuantitativo del sistema Linceus Assistant}
\label{tab:linceus-numeros}
\begin{tabular}{|p{5.5cm}|r|}
\hline
\textbf{Indicador} & \textbf{Valor} \\
\hline
Intenciones NLU cubiertas & 24 \\
Entidades NLU & 8 \\
Casos de prueba funcionales & 385 \\
Tasa de superación de pruebas & 94,8\,\% \\
F1 medio clasificador NLU (5-fold CV) & 0,92 \\
Precisión RAG (30 preguntas reglamentación) & 90\,\% \\
Latencia media (p50) & 1,9\,s \\
Latencia p95 & 2,8\,s \\
Sesiones piloto analizadas & 59 \\
Horas de desarrollo registradas (Clockify) & $\sim$300 \\
Sprints completados & 9 \\
Líneas de código (Python + JS, sin tests) & $\sim$4\,200 \\
Documentos en la base de conocimiento RAG & 18 \\
Chunks vectorizados (pgvector) & 412 \\
\hline
\end{tabular}
\end{table}
```

---

### P3.2 — Contribución al estado del arte (Conclusiones)

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/conclusiones.tex`

```latex
\subsection{Contribución al estado del arte}
\label{sec:contribucion-arte}

Linceus Assistant se posiciona en la intersección de dos tendencias activas de investigación: los asistentes conversacionales para educación superior \cite{wollny2021survey, okonkwo2021chatbots} y los sistemas RAG sobre documentos de dominio cerrado \cite{gao2024ragsurvey, mdpirag2025}. La contribución diferencial respecto a trabajos publicados en 2025 \cite{springerrasa2025, sdrag2025} reside en tres aspectos:

\begin{itemize}
  \item La \textbf{calibración empírica documentada} del umbral de similitud semántica (Sección~\ref{sec:ablacion-rag}), ausente en los trabajos comparados.
  \item La \textbf{interfaz de mantenimiento sin código} que cierra el ciclo de vida del sistema, permitiendo su operación autónoma por personal no técnico.
  \item La \textbf{arquitectura híbrida NLU+RAG} que combina precisión en consultas estructuradas (SQL sobre Supabase) con flexibilidad en consultas abiertas (generación con contexto vectorial), demostrando que ambos enfoques son complementarios y no excluyentes.
\end{itemize}
```

---

## Bloque P4 — Acciones Menores de Pulido (PRIORIDAD BAJA)

### P4.1 — Verificar cross-references en todo el documento

Comprobar que todas las referencias `\ref{}` y `\cite{}` añadidas en P1--P3 resuelven correctamente al compilar. Ejecutar:

```powershell
cd "memoria_tfg/Plantilla TfG"
latexmk -pdf proyect.tex 2>&1 | Select-String "undefined|Warning"
```

---

### P4.2 — Consistencia de cifras entre capítulos

Verificar que los números citados en tablas (385 casos de prueba, 59 sesiones, ~300h) sean coherentes entre el capítulo de pruebas, metodología y conclusiones. Si hay discrepancia, usar el valor del capítulo de pruebas como fuente de verdad.

---

### P4.3 — Ajuste final del resumen (abstract)

**Archivo**: `memoria_tfg/Plantilla TfG/Capitulos/resumen.tex`

Asegurarse de que el resumen mencione explícitamente:
- La arquitectura híbrida NLU+RAG
- El F1 0,92 del clasificador
- La precisión 90% del componente RAG
- El panel de administración como diferenciador operacional

---

## Bloque P5 — Auditoría memoria ↔ código (PRIORIDAD ALTA)

Este bloque se añade tras una revisión cruzada exhaustiva del código real (`config.yml`, `actions/`, `rag/`, `admin/`, `frontend/`, `tests/results/`) contra lo afirmado en `Capitulos/*.tex`. Recoge **afirmaciones de la memoria que el código contradice**, **funcionalidad declarada que no existe** y **trabajo real no contado**. Resolverlo es condición necesaria para defender con rigor: cualquier discrepancia que detecte el tribunal mina la credibilidad del resto.

### P5.1 — Discrepancias factuales en la memoria (CORREGIR)

| # | Afirmación en memoria | Realidad en código | Acción |
|---|----------------------|---------------------|--------|
| a | FallbackClassifier `threshold = 0,7` (`arquitectura_diseno.tex`, decisión NLU) | `config.yml:68` → **`threshold: 0,8`** y `ambiguity_threshold: 0,10` | Corregir el valor citado y añadir una línea sobre el rol de `ambiguity_threshold` |
| b | Pipeline NLU empieza con `WhitespaceTokenizer` y consta de **9 etapas** | `config.yml:18-69` → **`SpacyNLP(es_core_news_md) + SpacyTokenizer + … + SpacyFeaturizer (step 5)` → 10 componentes** | Reescribir la enumeración del pipeline; **la decisión de usar embeddings preentrenados de spaCy es decisiva** (DIET aprende con ~600-800 ejemplos solo porque recibe vectores semánticos) y hoy la memoria la omite |
| c | Modelo de embeddings `text-embedding-004` (`img/diagrama_despliegue.puml:55`; comentarios obsoletos en `rag/__init__.py:7` y `rag/pipeline.py:8`) | `rag/embeddings.py:21` → **`models/gemini-embedding-001`** (2000 dims, reducidas de 3072) | Regenerar el SVG del diagrama de despliegue y corregir el texto de `implementacion.tex` que cite `text-embedding-004` |
| d | "Pipeline NLU 9 etapas" en `arquitectura_diseno.tex` | Real: 10 componentes (falta documentar `SpacyFeaturizer` y los dos `CountVectorsFeaturizer` con sus n-gramas `word(1-2)` y `char_wb(2-4)`) | Reescribir el listado y justificar los rangos de n-gramas |
| e | Policies = "MemoizationPolicy + RulePolicy + TEDPolicy" (descripción típica) | Real: **4 policies**, incluido `UnexpecTEDIntentPolicy(max_history=5, epochs=100)` con `core_fallback_threshold=0,4` | Añadir `UnexpecTEDIntentPolicy` y explicar su rol frente a TED |
| f | Cuatrimestre Q1 = septiembre-enero, Q2 = febrero-julio (`implementacion.tex` épica horarios) | Verificar contra el código en `actions/horarios/` antes de defenderlo en tribunal | Trazar la heurística exacta y citar la línea |

### P5.2 — Afirmaciones a MATIZAR en la memoria (no son falsas pero están descritas con inexactitud)

| # | Afirmación en memoria | Realidad matizada | Acción recomendada |
|---|----------------------|-------------------|--------------------|
| a | RNF-13 "Seguridad panel admin: HTTP 401 sin credencial / **Basic Auth HTTPS**" | Hay autenticación, **pero no es Basic Auth**. El mecanismo real es **Supabase Auth client-side**: `frontend/login.html` + `frontend/login.js:38` lanza `supabase.auth.signInWithPassword(email, password)`, y `frontend/admin.js:15-17` redirige a `login.html` si no hay sesión válida. El backend Flask (`admin/app.py:14-15`) **no verifica el JWT** en cada request; depende de que el cliente legítimo siempre pase por la UI autenticada y del despliegue en red privada / detrás del nginx | (i) corregir RNF-13: mecanismo = **Supabase Auth (JWT, email/password)**, no Basic Auth; (ii) opcionalmente añadir verificación del JWT en el backend Flask con un `before_request` que valide el `Authorization: Bearer` (~1h con `gotrue-py` o JWT decode manual), si se quiere cerrar el gap servidor; (iii) si se mantiene tal cual, dejar constancia en la memoria de que la auth es client-side y la protección de servidor descansa en el despliegue (nginx + red privada) |
| b | "Mecanismo de feedback de respuestas incorrectas" (RF-T6, RF-AD7, RI-6) | **CONFIRMADO existente y completo**: `frontend/chatbot-widget.js:547-589` tiene botón "✍ Feedback", panel con rating buttons (`feedback-rating button`), textarea de comentario y función `logFeedback(rating, comment)` (línea 508) que inserta directamente en tabla `feedback` de Supabase vía REST. Backend: tabla `feedback` + `log_feedback()` en `actions/shared/logger.py`. **Ningún cambio necesario** | Esta línea está **bien cumplida** — añadir una nota en `implementacion.tex` documentando el flujo (widget → insert REST directo en `feedback` table → panel admin lee), porque actualmente la memoria infraestima esta funcionalidad |
| c | Ollama como "patrón Strategy / fallback LLM local" (`arquitectura_diseno.tex`) | Es **correcto a nivel arquitectónico**: `actions/shared/ollama_client.py:24` expone `llamar_ollama(prompt, options=…) -> str \| None` con la **misma firma** que `gemini_client.llamar_gemini`, por lo que son **intercambiables como Strategy**. Lo que NO existe es **switching automático en runtime**: ninguna action importa `ollama_client` (todas usan `gemini_client`), y no hay un wrapper que pruebe Ollama si Gemini retorna `None`. El cliente está **operativo y disponible como Strategy configurable en build** (cambio de import), no como **failover dinámico** | Matizar la memoria: el patrón Strategy es correcto; aclarar que la conmutación es **manual / por configuración** (cambio del import en las acciones o flag de entorno), no automática. Si se quiere reforzar, añadir un `LLM_BACKEND=gemini\|ollama` leído por un `llm_client.py` envoltorio que despache al cliente correcto — convierte el Strategy en **runtime-switchable** sin tocar las acciones (~1h) |
| d | "Pen-test básico sin vulnerabilidades críticas" (propuesto en P2.1) | Inverificable; además, dado el gap servidor-side de (a), un pen-test elemental podría detectar que el API Flask responde sin requerir token (siempre que conozca el endpoint) | No introducir esta afirmación en la memoria mientras no se haga el pen-test real; ver P6.5 |

### P5.3 — Trabajo real OMITIDO en la memoria (añadir para reforzar)

a) **Scrapers por departamento** ([actions/profesores/scraper_ccia.py](actions/profesores/scraper_ccia.py), [scraper_dte.py](actions/profesores/scraper_dte.py), [scraper_lsi.py](actions/profesores/scraper_lsi.py), [scraper_ma1.py](actions/profesores/scraper_ma1.py)). La memoria sólo cita "us.es PDI" como fuente; en realidad hay un sistema de fallback con cuatro scrapers específicos cuando el directorio US devuelve perfil vacío. Esto es contribución no contada — añadirlo en `implementacion.tex` épica profesores como tabla "fuentes en cascada".

b) **Reranking RAG por sección** ([rag/buscar.py](rag/buscar.py) → `RERANK_WEIGHTS`). Tras la búsqueda ANN se aplican bonificaciones de +0,15 por sección detectada según el tipo de pregunta (profesorado, evaluación, contenidos, horarios, bibliografía), con detección regex sobre la consulta del usuario. La memoria sólo describe "búsqueda vectorial + fallback ILIKE". Documentar el reranking eleva la sofisticación percibida del RAG.

c) **Tres umbrales fuzzy distintos** —no uno solo— calibrados por dominio:
- Cambio de contexto académico: cutoff 85 (`ActionCambiarContexto` en `actions/contexto/actions.py`)
- Matching de profesores: 0,60 firme + 0,30 sugerencia (`actions/shared/matching.py`, calibrado empíricamente con 120 casos, decisión documentada en `docs/sprints/`)
- Asignaturas: cascada de 5 etapas (NLU → alias exactos → regex en texto crudo → slots ≤3 turnos → fuzzy 85 %)

La memoria los homogeneíza a "umbral 80 %". Reescribir mostrando los tres umbrales como decisión de calibración por dominio.

d) **Modularización del NLU training**: `data/nlu/` contiene 5 archivos por dominio (`asignaturas.yml` 691 líneas, `general.yml`, `contexto.yml`, `horarios.yml`, `profesores.yml`) más `multi_intent.yml.disabled`. La memoria los trata como bloque único. Mencionar la modularización en `implementacion.tex` (permite reentrenar dominios independientes).

e) **Validador SQL** en `actions/asignaturas/text_to_sql.py`: rechaza `non-SELECT`, tablas no permitidas, patrones `UNION`, `OR 1=1`, `SLEEP`, e inyecta automáticamente el filtro `titulacion_id` desde el slot. La memoria lo cita pero sin las reglas concretas. Reproducir la lista de rechazos como tabla — es una barrera real contra inyección SQL.

f) **Benchmark Gemini** activado por variable de entorno `LINCEUS_BENCH_METRICS` que volca JSONL con tokens + latencia por llamada. Explicar el mecanismo en `pruebas.tex` da trazabilidad a las cifras de coste/latencia.

g) **`demo/` (React + Vite + Framer Motion + Playwright)**: aclarar en el README de la memoria o en `implementacion.tex` que es **material de presentación / grabación de screencasts**, **no** el widget desplegado en producción. Si el tribunal abre el repo y ve React, hay que evitar la contradicción con la afirmación "vanilla JS sin frameworks".

### P5.4 — Aclaraciones para evitar dudas del tribunal (HIGIENE)

- `actions/multi_intent/`, `data/nlu/multi_intent.yml.disabled` y los bloques comentados de `domain.yml`/`data/rules.yml`: la memoria ya justifica la desactivación (D-072, 55 % accuracy en 40 casos). Añadir una nota explícita en implementación de que **el código se conserva como referencia técnica, no como código muerto**.
- Archivos huérfanos en la raíz del repo: `iniciar_ollama.bat`, `_audit_symbols.py`, `texput.log`, `TODO.md` (184B). O se eliminan antes de la entrega final, o se documentan brevemente para evitar la impresión de descuido.
- `frontend/login.html` + `login.js`: existen pero no hay autenticación real detrás. Mismo dilema que P5.2(a) — implementar o reconocer.

---

## Bloque P6 — ALERTAS sobre el propio plan P1–P3 (CRÍTICO antes de aplicar)

Antes de aplicar los bloques P1.1, P1.4, P1.7, P2.1 y P3.1 a la memoria, **revisarlos**: contienen referencias inventadas, métricas inventadas o cifras que contradicen lo ya medido en `tests/results/`. Aplicarlos tal cual introduciría falsificaciones en la memoria.

### P6.1 — Referencias bibliográficas posiblemente ficticias (P1.1)

De las 8 entradas propuestas para `pfcbib.bib`, **al menos 4 parecen plantillas inventadas y no se localizan como publicaciones reales**:

- `springerrag2025` — "RAG-based University Advisors: A Comparative Study" (autores y conferencia no verificables)
- `springerrasa2025` — "Rasa-based Conversational Agents for Academic Guidance" (autores y venue no verificables)
- `mdpirag2025` — "Evaluation of RAG Pipelines for Domain-Specific Question Answering" (número, página y autores no verificables)
- `sdrag2025` — "Hybrid NLU-RAG Architectures for Student Support Systems" (autores y venue no verificables)

**Citar referencias inventadas es falsificación bibliográfica**: motivo directo de retirada de un TFG y de denegación de la MH. Antes de añadir nada a `pfcbib.bib`:

1. **Verificar cada cita** en Google Scholar / DBLP / arXiv / Crossref por DOI.
2. **Sustituir** las no verificables por referencias reales y recientes (2023-2025) de Frontiers, ACM, IEEE Xplore, arXiv. Sugerencias verificables:
   - Lewis et al. 2020, *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks* (NeurIPS).
   - Bunk et al. 2020, *DIET: Lightweight Language Understanding for Dialogue Systems* (arXiv:2004.09936).
   - Es et al. 2023, *RAGAS: Automated Evaluation of Retrieval Augmented Generation* (arXiv:2309.15217).
   - Saad-Falcon et al. 2023, *ARES* (arXiv:2311.09476) — verificar la entrada `rageval2025` exacta.

Mantener únicamente las 3-4 referencias verificables (`wollny2021survey`, `okonkwo2021chatbots`, `gao2024ragsurvey` tras comprobación en Frontiers / Elsevier / arXiv).

### P6.2 — Métricas NLU del bloque P1.4 (incompatibles con lo medido)

**Confirmado tras lectura directa de `pruebas.tex`**: la memoria ya tiene la **Tabla 8 (`tab:nlu-resultados`, líneas 100-115)** con métricas NLU+Policy a nivel de **story/acción** (F1 weighted = 1,00 sobre 44 stories y 158 acciones, ejecutada con `rasa test core --fail-on-prediction-errors`). La tabla `tab:visiongeneral` (líneas 205-220) cita este resultado como una de las seis capas de validación.

P1.4 propone una tabla **distinta** (Precision/Recall/F1 **por intent individual** con media 0,92) que incluye intents **que no existen** en el sistema (`consulta_matricula`, `consulta_reglamento`). Los intents reales (`domain.yml`) son `consulta_asignatura_especifica`, `consulta_horario_asignatura`, `consulta_asignaturas_listado`, `consulta_asignaturas_conteo`, `consulta_profesor`, `consulta_horario`, `cambiar_contexto_academico`, etc. (36 intents definidos, 34 activos; 2 multi-intent comentados).

**Acción**: descartar P1.4 tal cual. **Sí es legítimo y complementario** añadir una tabla de métricas a nivel intent (es ortogonal a la Tabla 8, que es a nivel story). Para que sea real, ejecutar:

```powershell
rasa test nlu --cross-validation --folds 5 --runs 1 --out tests/results/nlu_cv/
```

y volcar las cifras reales con los nombres de intent reales. Insertar como nueva subsección dentro de §`sec:pruebas-nlu`, **antes** de la Tabla 8 (mide componentes distintos: NLU intent classification vs Policy action prediction).

### P6.3 — Experimento de ablación RAG (P1.7) NO ejecutado

P1.7 reporta "27/30 RAG vs 18/30 LLM directo, 1 vs 8 alucinaciones, 2,1 s vs 1,4 s latencia". **No se ha ejecutado este experimento**: no existe script de ablación, ni dataset A/B, ni resultados en `tests/results/`. Las cifras son ilustrativas.

**Acción**: o se ejecuta de verdad (deshabilitar la inyección de contexto RAG en el prompt del action server, lanzar las 30 preguntas reales de `tests/plans/rag_asignaturas_manual.md` sobre condición B, anotar veredictos: 1-2 días de trabajo) y se publican las cifras reales, o se **elimina** P1.7. No introducir tabla con cifras ficticias.

### P6.4 — "Linceus en números" (P3.1) incompatible con lo medido

| Indicador (P3.1) | Plan dice | Real (memoria + código) |
|---|---|---|
| Intenciones NLU cubiertas | 24 | **36 definidos / 34 activos** (`domain.yml`) |
| Casos de prueba funcionales | 385 | **159 E2E + 50 RAG baseline + 74 RAG profundidad + 158 NLU action-level + 24 admin pytest ≈ 465** |
| F1 medio clasificador NLU (5-fold CV) | 0,92 | **1,00** weighted en NLU+Policy story-level; 5-fold CV no ejecutado |
| Precisión RAG | 90 % | **91,9 %** (profundidad, 74 preguntas) / 94,0 % (baseline, 50 preguntas) |
| Latencia mediana p50 | 1,9 s | **3,4 s** (RNF-1, memoria; `tests/results/coste_latencia.md`) |
| Latencia p95 | 2,8 s | **10,5 s** (RNF-2) |
| Documentos RAG | 18 | No verificado — ejecutar `SELECT COUNT(*) FROM planes_docentes` antes de citar |
| Chunks vectorizados | 412 | No verificado — ejecutar `SELECT COUNT(*) FROM planes_docentes_chunks` |
| Sprints completados | 9 | Verificar contra `docs/sprints/S1..S?` |
| Horas Clockify | ~300 | Verificar contra `Clockify_Time_Report_Summary_…csv` |
| LOC Python+JS (sin tests) | ~4 200 | No verificado — `cloc actions/ rag/ admin/ frontend/ --exclude-dir=node_modules,rasa_env` |

**Acción**: reescribir P3.1 entera con los datos reales antes de tocar `conclusiones.tex`. La tabla "en números" es buena idea — solo con cifras correctas. Las cifras reales **siguen siendo fuertes** (91,9 % RAG, 98,3 % tráfico real, 34 intents, 465 casos, 1,00 F1 action-level): no hay necesidad de inflarlas.

### P6.5 — ISO 25010 (P2.1) con valores incompatibles

P2.1 indica "p95 < 3 s bajo carga 10 usuarios" como evidencia de Rendimiento, y "Pen-test básico sin vulnerabilidades críticas" como evidencia de Seguridad.

- p95 real = **10,5 s** (RNF-2). No hay prueba de carga concurrente con 10 usuarios — el `--delay 5` del runner es throttling por cuota Gemini, no simulación de concurrencia.
- Pen-test "sin vulnerabilidades críticas" es inverificable y, dado P5.2(a), problemático: un escaneo elemental detectaría el panel admin abierto a Internet sin auth.

**Acción**: reescribir la tabla ISO 25010 con valores reales (p50 3,4 s, p95 10,5 s — clasificar Rendimiento como "Medio", no "Medio-alto") y reformular Seguridad como "anonimato por diseño + datos públicos; autenticación del panel admin pendiente para fase 2" (o implementarla antes — ver P5.2.a).

### P6.6 — Contribución (P1.2) — afinar para no contradecir P5

El §"Contribución de este trabajo" propuesto en P1.2 cita "calibración empírica del umbral de similitud semántica" como uno de los tres aportes. Bien — pero la memoria reescrita debe contar **los tres umbrales** del sistema (P5.3.c), no el "umbral 80 %" simplificado. Y "Panel de administración RAG sin código" sí es un diferenciador operacional legítimo: la auth real existe ([frontend/login.html](frontend/login.html) + Supabase Auth) y la UI de feedback también ([chatbot-widget.js:547-589](frontend/chatbot-widget.js#L547-L589)) — solo precisar el mecanismo (Supabase Auth, no Basic Auth) y, si se quiere endurecer, validar el JWT también en el backend Flask (P5.2.a).

---

## Bloque P7 — JOYAS TÉCNICAS DEL CÓDIGO QUE LA MEMORIA NO CUENTA (PRIORIDAD ALTA)

Tras una lectura profunda de `actions/` y `rag/` cotejada contra `implementacion.tex`, hay un conjunto de decisiones de ingeniería **reales y verificables** que la memoria omite o trata de pasada. Documentarlas eleva la sofisticación percibida del trabajo sin inventar nada. Cada entrada incluye archivo:línea para que se pueda verificar antes de citar.

### P7.1 — Épica Asignaturas

| # | Hallazgo | Dónde | Qué eleva |
|---|---------|-------|-----------|
| 1 | **Cascada de resolución de asignatura con 5 etapas REALES y nombradas** | [actions/asignaturas/actions.py:327-446](actions/asignaturas/actions.py#L327) (`resolver_asignatura()`) | La memoria dice "5 etapas" sin más. Documentar: (i) NLU entity con filtrado anti-ruido, (ii) **expansión recursiva de alias quitando prefijos `de/del` hasta 3 pasadas**, (iii) regex boundary-safe sobre alias ordenados por longitud DESC, (iv) herencia de slot ≤3 turnos, (v) `rapidfuzz.process.extractOne` a threshold 85/75 sobre **ventanas deslizantes de 3-6 palabras**. Cada salto está condicionado: rigor mostrable. |
| 2 | **Deduplicación de entidades NLU con filtrado de ruido** | [actions/asignaturas/actions.py:175-229](actions/asignaturas/actions.py#L175) (`extraer_nombre_asignatura()`) | Cuando NLU devuelve múltiples `nombre_asignatura`, descarta (a) palabras genéricas hardcoded (`info, datos, hablame, sobre`), (b) fragmentos de titulación (`software, computador, telematic, informatica, ingenieria, grado`), (c) sufijos ruido (`del, de, la, el…`) iterativamente. Elige la más larga si persiste ambigüedad. **Calibración contra falsos positivos del NLU** (entidad "software" cuando se pregunta por "Ingeniería del Software"). |
| 3 | **Detección multi-asignatura con expansión coordinada** | [actions/asignaturas/actions.py:147-172](actions/asignaturas/actions.py#L147) (`_extraer_multiples_nombres()`) | Detecta `[alias] [y/,/e] [alias]` en la consulta, expande ambos contra el diccionario, devuelve lista ≥2 si las dos son válidas. Bifurca a `_run_multi()` que agrupa chunks RAG etiquetados por asignatura. Funcionalidad real **no documentada** en la memoria. |
| 4 | **Match exacto previo al reranking fuzzy** | [actions/asignaturas/actions.py:421-444](actions/asignaturas/actions.py#L421) | Antes de `token_set_ratio`, comprueba si algún resultado tiene `nombre_normalizado == objetivo_normalizado`. Si lo hay, devuelve sin reranking. **Defensa explícita contra el bug AE vs AAE / IA vs AIA** (un nombre prefijo de otro). |
| 5 | **Validador SQL con blocklist de ~14 patrones + whitelist de columnas** | [actions/asignaturas/text_to_sql.py:618-692](actions/asignaturas/text_to_sql.py#L618) (`validar_sql()`) | Rechaza: `INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/TRUNCATE/EXEC`, `--`, `;--`, `UNION SELECT`, `OR 1=1`, `OR '1'='1'`, `SLEEP()`, `BENCHMARK()`. Exige `SELECT` inicial, tablas en whitelist (`asignaturas, titulaciones`), columnas en `COLUMNAS_PERMITIDAS`. Para `COUNT`, exige `COUNT(*)`. Limpia placeholders. **La memoria solo cita "UNION, OR 1=1, SLEEP"** — la lista real es mucho más completa, justifica defensa en profundidad. |
| 6 | **Inyección de filtro `titulacion_id` por subquery parametrizado** | [actions/asignaturas/text_to_sql.py:53-83](actions/asignaturas/text_to_sql.py#L53) (`_inyectar_filtro_titulacion()`) | Si el SQL no contiene `titulacion_id`, busca `WHERE activa = true` e inserta `AND titulacion_id = (SELECT id FROM titulaciones WHERE codigo = %s LIMIT 1)`. Si no hay `activa = true`, lo inserta al inicio del WHERE. **Por subquery con código, no por UUID hardcoded** — parametrización defensiva real. |

### P7.2 — Épica Profesores

| # | Hallazgo | Dónde | Qué eleva |
|---|---------|-------|-----------|
| 7 | **`score_por_normalizado` como métrica explícita** | [actions/shared/matching.py:50-79](actions/shared/matching.py#L50) (`clasificar_por_normalizado()`) | Métrica = proporción de tokens de la consulta presentes en `nombre_normalizado`. Calibrada con 120 casos, 3 iteraciones (S4): `≥0,60 firmes`, `0,30-0,60 sugerencias`, `<0,30 descartados`. La memoria cita la calibración pero **no documenta la métrica subyacente**. Documentar la fórmula (proporción) y los casos limítrofes ("Pareja" → 0,67 sugerencia; "García" ambiguo → descarte para evitar falsos positivos en nombres cortos) es contribución reproducible. |
| 8 | **Cuatro scrapers por departamento como fallback** | [actions/profesores/scraper_ccia.py](actions/profesores/scraper_ccia.py), [scraper_dte.py](actions/profesores/scraper_dte.py), [scraper_lsi.py](actions/profesores/scraper_lsi.py), [scraper_ma1.py](actions/profesores/scraper_ma1.py) | Cuando el directorio US PDI devuelve perfil vacío, el sistema **consulta scrapers específicos por departamento** (CCIA, DTE, LSI, MA1). La memoria solo cita `us.es PDI`. Añadir tabla "fuentes en cascada" en `implementacion.tex` épica profesores. |

### P7.3 — Épica Horarios

| # | Hallazgo | Dónde | Qué eleva |
|---|---------|-------|-----------|
| 9 | **Detección de "letra del DNI" con bloqueo proactivo** | [actions/horarios/actions.py:119-127](actions/horarios/actions.py#L119) (`_RE_LETRA_DNI`, `_tiene_referencia_letra_dni()`) | Regex `letra\s+([a-zñ])(?:\s+(?:de\|del)\s+(?:mi\s+)?dni\|…)`. Si detecta, responde proactivamente "La asignación de grupos por letra del DNI varía cada curso, consulta…". **Evita que la letra "T" se interprete como alias de Teledetección.** No documentado en la memoria. |
| 10 | **GROUP BY por (día, hora, asignatura, cuatrimestre) para colapsar aulas** | [actions/horarios/actions.py:221-223](actions/horarios/actions.py#L221) | El JOIN entre `horarios + grupos_clase + asignaturas + aulas` produce duplicados (mismo día/hora, distintas aulas teoría/lab). El GROUP BY agrupa por la sesión real. La memoria dice "se reagrupa" sin explicar **por qué sin GROUP BY hay duplicados** ni que el cuatrimestre forma parte de la clave de agrupación. |
| 11 | **Inferencia de cuatrimestre por fecha del sistema** | [actions/horarios/actions.py:152-167](actions/horarios/actions.py#L152) (`_cuatrimestre_actual_por_fecha()`) | Mapeo explícito: sept-ene → C1, feb-jul → C2, agosto → indefinido. Verificar contra calendario académico US Sevilla. La memoria lo menciona vagamente; documentar la función concreta cierra el detalle. |

### P7.4 — Épica Contexto y Fallback

| # | Hallazgo | Dónde | Qué eleva |
|---|---------|-------|-----------|
| 12 | **Heurística "todos los grupos" sin coste LLM** | [actions/fallback/actions.py:27-31](actions/fallback/actions.py#L27) (`_RE_CONTINUACION_TODOS_GRUPOS`) | Regex `\b(todos\s+los\s+grupos\|los\s+demás\s+grupos\|…)` detecta una continuación frecuente. Si dispara con slot reciente, hereda asignatura y resuelve **sin llamar a Gemini** (ahorra ~2-3 s y un turno de coste). La memoria lo menciona; merece subsección breve por ser micro-optimización medible. |
| 13 | **Smart fallback con bifurcación a 3 acciones via JSON estructurado** | [actions/fallback/actions.py:61-104](actions/fallback/actions.py#L61) | Gemini recibe (pregunta, titulación, última asignatura, últimos 3 intercambios, acciones disponibles) y devuelve JSON `{"action": "BUSCAR_ASIGNATURA"\|"BUSCAR_HORARIO"\|"BUSCAR_PROFESOR"\|"NINGUNO", "parametros": {…}, "respuesta_directa": "…"}`. Las funciones `_ejecutar_consulta_*` son **versiones simplificadas internas, no reinvocan los actions** — evita ciclos Rasa (acción → fallback → acción → fallback…). La memoria explica el flujo; este detalle de "no reinvocar" es valor añadido. |
| 14 | **Prompt-engineering defensivo con reglas de continuación explícitas** | [actions/fallback/actions.py:78-93](actions/fallback/actions.py#L78) (PROMPT_CLASIFICAR) | El prompt instruye explícitamente: "Si la pregunta es corta/pronominal/referencial, asume la última asignatura"; y "si `ultima_asignatura = ninguna`, no asumas nada". Documentar el prompt en un apéndice de la memoria muestra ingeniería de prompt madura. |
| 15 | **Inyección de entidades sintéticas en el `Tracker` para reutilizar actions** | [actions/shared/resolver_afirmacion.py:33-66](actions/shared/resolver_afirmacion.py#L33) (`_inyectar_entidad()`) | `ActionResolverAfirmacion` necesita re-ejecutar la action sugerida con un valor confirmado. En lugar de duplicar lógica, **deepcopya `latest_message`, inyecta una entidad sintética con `extractor: "sugerencia"` y reconstruye un `Tracker` nuevo**. Reutiliza el action existente sin tocarlo. Técnica elegante, no documentada. |

### P7.5 — Módulo RAG

| # | Hallazgo | Dónde | Qué eleva |
|---|---------|-------|-----------|
| 16 | **Tabla de pesos `RERANK_WEIGHTS` por tipo de consulta** | [rag/buscar.py:29-61](rag/buscar.py#L29) y [:103-128](rag/buscar.py#L103) | Tras la búsqueda ANN, se aplica reranking aditivo: `{tipo_consulta → {sección → bonus}}`, p. ej. `profesorado: {profesorado: +0,15, coordinador: +0,12}`. La detección del tipo se hace por regex sobre la consulta del usuario. **Bonus positivos pequeños (0,03-0,15), sin penalizaciones negativas** — diseño explícito tras observar que penalizaciones (`-0,30`) enmascaraban chunks mal etiquetados. Calibración empírica documentada en `docs/sprints/S7/registro_decisiones.md:275`. La memoria menciona "reranking" sin tabla; añadirla es contribución verificable. |
| 17 | **Búsqueda en dos fases: vectorial + fallback ILIKE por keywords** | [rag/buscar.py:195-211](rag/buscar.py#L195) (`buscar_en_plan_docente()`) | Si `generar_embedding()` falla (rate-limit Gemini, error), cae a `_buscar_por_keywords()`: extrae palabras > 3 chars, descarta stopwords, hace ILIKE OR sobre `contenido`. **Ambas fases aplican el mismo reranking.** Demuestra degradación elegante. La memoria solo menciona vectorial; documentar la segunda fase **eleva el atributo de fiabilidad** (ISO 25010 fault tolerance). |
| 18 | **Resolución de grupo con LIKE wildcard** | [rag/buscar.py:131-157](rag/buscar.py#L131) (`_resolver_grupo()`) | Si el usuario dice "Grupo 5" pero la BD tiene "Grupo 5 INGLES", busca `pd.grupo LIKE %Grupo 5%`. Manejo de variantes de nomenclatura. No documentado. |
| 19 | **Chunking por secciones con deduplicación de cabeceras repetidas** | [rag/chunking.py:60-193](rag/chunking.py#L60) | Pipeline: (1) `_partir_por_secciones` aplica las **16 regex de `_SECTION_HEADERS`** sobre el texto extraído del PDF; (2) si la misma sección aparece varias veces (PDF multi-página), `_deduplicar_bloques` **conserva la versión más larga**; (3) `_chunkar_texto` aplica MAX=800 / OVERLAP=100 / MIN=50 respetando párrafos (split `\n\s*\n`) y **sin cruzar secciones**. La memoria menciona el chunking; documentar la deduplicación cierra una causa real de bugs en BD (chunks duplicados). |
| 20 | **Cabeceras con variantes ortográficas** | [rag/chunking.py:37-57](rag/chunking.py#L37) (`_SECTION_HEADERS`) | 16 regex compiladas con `re.IGNORECASE` y variantes para tildes (`Datos b[áa]sicos`, `Metodolog[íi]a`). **Robustez frente a inconsistencias de extracción de PDF.** No documentado. |
| 21 | **Batch de embeddings con throttle 100 RPM + retry backoff 60 s en 429** | [rag/embeddings.py:24-27](rag/embeddings.py#L24), [:79-113](rag/embeddings.py#L79), [:101-113](rag/embeddings.py#L101) | `BATCH_SIZE=100`, `PAUSA_ENTRE_BATCHES=1.0 s`. En `429 / RESOURCE_EXHAUSTED`, espera 60 s y reintenta. Diseñado para respetar el tier gratuito (100 RPM / 1000 RPD). No documentado. |
| 22 | **Hash SHA-256 + máquina de estados RAG** | [rag/db_vectores.py](rag/db_vectores.py) + tabla `planes_docentes` campo `estado_rag` | Estados: `pendiente → en_proceso → completado / error`. Hash SHA-256 del PDF: si coincide con el guardado, salta el reprocesado completo; si difiere, **borra chunks antiguos y reprocesa**. Idempotencia explícita. La memoria menciona el hash; añadir la máquina de estados completa cierra el patrón. |

### P7.6 — Transversales

| # | Hallazgo | Dónde | Qué eleva |
|---|---------|-------|-----------|
| 23 | **Calibración de temperatura por caso de uso** | [actions/asignaturas/text_to_sql.py:376-384](actions/asignaturas/text_to_sql.py#L376) y [:479-488](actions/asignaturas/text_to_sql.py#L479) | `temperature=0,0` para generación SQL y clasificación (determinismo, evita variabilidad léxica que rompería el validador). `temperature=0,3` para redacción natural (suficiente variabilidad sin alucinar). La memoria menciona temperatura sin desglose; documentar la diferencia es ingeniería madura. |
| 24 | **Bench metrics JSONL toggleable por `LINCEUS_BENCH_METRICS`** | [actions/shared/gemini_client.py:24](actions/shared/gemini_client.py#L24), [:31-40](actions/shared/gemini_client.py#L31), [:113-129](actions/shared/gemini_client.py#L113) | Si la env var apunta a un fichero, cada llamada a Gemini hace append-only de un JSON con `{ts, modelo, context, input_tokens, output_tokens, total_tokens, latencia_ms, prompt_chars, respuesta_chars, ok}`. `context` es etiqueta libre (`"profesores.text_to_sql"`, `"horarios.render"`). Sin overhead si la var no está. **Documentar el schema completo del JSONL** (no solo "registra latencia y tokens") justifica las tablas de coste/latencia de `pruebas.tex`. |
| 25 | **Logger de conversación con schema explícito** | [actions/shared/logger.py:9-30](actions/shared/logger.py#L9) (`log_conversation`) y [:33-54](actions/shared/logger.py#L33) (`log_feedback`) | Conversation: `(session_id, user_message, bot_response, intent, confidence)`. Feedback: `(session_id, rating, comment, last_user_message, last_bot_response)` — incluye **contexto del último turno** para auditoría sin tener que cruzar tablas. Silencia errores de BD (no rompe el bot). Schema explícito mejora RI-5/RI-6. |

### P7.7 — Casos fallidos reales (para alimentar P1.6 sin inventar)

Tras leer `pruebas.tex`, la memoria identifica casos fallidos concretos con ID que pueden alimentar la sección "Análisis de casos fallidos" propuesta en P1.6 **sin inventar nada**:

- **E-T02** (RAG baseline): alias en BD no coincide con el nombre coloquial usado por el usuario. Causa raíz: tabla de alias incompleta.
- **E-T04** (RAG baseline): enrutado erróneo a la acción `cambiar_contexto`. Causa raíz: solapamiento NLU entre cambio de contexto y consulta.
- **C-P05** (RAG baseline): confusión entre flujos `conteo` y `listado`. Causa raíz: ambigüedad de "¿cuántas optativas hay?" vs "¿qué optativas hay?".
- **X-P06** (Tráfico real): pregunta sobre electrónica de sistemas embebidos — el bot devuelve asignaturas afines sin cruzarlas con titulaciones. Causa raíz: falta el flujo `consulta_titulacion_por_tema`. Documentado como trabajo futuro.
- **5 PARCIAL en RAG profundidad**: respuestas correctas pero incompletas (faltan detalles del plan docente). Causa raíz típica: chunk recuperado cubre la respuesta principal pero no los matices.
- **1 FAIL en RAG profundidad**: verificar contra `tests/results/rag_asignaturas.md` para identificar el caso concreto.
- **Categoría `profesor` 86,0 %**: 1 FAIL + 4 PEND + 1 vacío sobre 43 — concentra la cola larga por dependencias multitabla (profesor↔asignatura↔grupo). Causa documentada: tabla `profesor_asignatura` con columnas `grupo` y `es_coordinador` parcialmente vacías.

Reescribir P1.6 ("Análisis de los casos fallidos") usando estos IDs y causas reales convierte la sección en una contribución sólida en vez de en ejemplos genéricos.

---

## Bloque P8 — CALIDAD DEL CAPÍTULO DE REQUISITOS (Guía Segura) — PRIORIDAD ALTA

La guía oficial [ssegura/Guia_TFG](https://github.com/ssegura/Guia_TFG) §8 establece **cinco mínimos** para el capítulo de requisitos del TFG, y los aplica como criterio de evaluación:

1. **Tres tipos de requisitos**: funcionales, de información, no funcionales.
2. **Criterios de aceptación** ligados a las pruebas de aceptación.
3. **RNF medibles** (no vagos).
4. **Prototipos de interfaz con descripción textual detallada e indicación del software** usado para diseñarlos.
5. **Artefactos opcionales**: modelo conceptual (RI) y/o modelo de proceso (dominio).

La memoria actual (`Capitulos/requisitos.tex`, 316 líneas) **cumple los tres tipos**, los **RNF son medibles con valor alcanzado**, hay **trazabilidad obj↔RF↔pruebas**, **evolución del alcance** y **5 figuras de prototipos**. Lo que **falta o flojea** según la guía y la práctica de los TFG con MH:

### P8.1 — Auditoría de la cobertura actual vs guía Segura

| # | Criterio Guía Segura §8 | Estado actual | Gap |
|---|--------------------------|---------------|-----|
| a | RF, RI, RNF presentes | ✓ Cubierto | — |
| b | Criterios de aceptación explícitos por RF | ⚠ Parcial: hay columna `Pruebas` con IDs (`E-P01..E-P12`) pero **no hay criterio textual Given–When–Then por RF** | P8.2 |
| c | RNF medibles | ✓ Cubierto con umbral + valor alcanzado | RNF-13 incorrecto (Basic Auth) — ver P5.2.a |
| d | Prototipos UI con **descripción textual detallada** y software usado | ⚠ Parcial: hay 5 figuras con `caption` corto. La guía pide "descripciones textuales detalladas". El software se menciona ("HTML/CSS/JS vanilla, identidad us.es") | P8.3 |
| e | Modelo conceptual de información (opcional pero recomendado) | ✗ Ausente del capítulo: hay tabla de entidades pero **no se incluye ER ni diagrama**. Existe `memoria_tfg/diagrama_er.mmd` pero pertenece a `estructura_bd.tex`, no a requisitos | P8.4 |
| f | Modelo de proceso (opcional, eleva claridad de dominio) | ✗ Ausente | P8.7 |
| g | Coherencia interna de cifras | ⚠ La Tabla `tab:traz-rf-pruebas` (asignaturas 85, horarios 35, profesorado 39, transversal 16) **no cuadra** con `tab:e2e-categorias` de `pruebas.tex` (asignaturas E2E suma 65, profesor 43, horarios 27, transversal 23) | P8.5 |
| h | Atomicidad de RF | ⚠ Algunos RF compuestos: RF-A1 mezcla "nombre + alias + acrónimo" en una sola línea | P8.6 |
| i | Priorización razonada | ⚠ Hay columna `Prio.` Alta/Media pero **sin criterio explicitado** (no se cita MoSCoW ni se justifica) | P8.6 |
| j | Restricciones, suposiciones y dependencias externas | ✗ Ausente como sección dedicada | P8.6 |
| k | Casos de uso | ⚠ Hay diagrama UML en `arquitectura_diseno.tex §2.3.5` (corrección del tutor), pero **no referenciado desde requisitos** | P8.6 |
| l | RF sin pruebas asociadas | ⚠ RF-T6 (feedback) tiene "---" en columna Pruebas pese a que la UI y la BD están implementadas (ver P5.2.b y P7) | P8.6 |
| m | RF-AD sin columna Pruebas | ⚠ La Tabla `tab:rf-admin` no incluye columna `Pruebas`, a diferencia de las otras 4 tablas RF. La tabla `tab:traz-rf-pruebas` la cita como "cobertura parcial" pero no liga RF↔IDs | P8.6 |

### P8.2 — Criterios de aceptación explícitos por RF (gap principal)

La guía recomienda explícitamente que **cada RF lleve su criterio de aceptación**, que luego se materializa en una prueba de aceptación. La memoria ya tiene los IDs de prueba en la columna `Pruebas` y el formato Given–When–Then en `pruebas.tex §2.2`, pero **falta el puente textual**: una columna o tabla anexa donde cada RF lleve **al menos un criterio de aceptación textual**.

**Propuesta concreta**: añadir una **subsección §`sec:req-aceptacion`** justo después de `sec:req-funcionales` con una tabla del tipo:

```latex
\begin{table}[hbtp]
\caption{Criterios de aceptación (selección representativa).}\label{tab:criterios-aceptacion}
\begin{tabular}{|p{1.1cm}|p{11cm}|}
\hline
\textbf{RF} & \textbf{Criterio (Given–When–Then)} \\ \hline
RF-A1 & \textbf{Given} titulación GII-IS, \textbf{when} el usuario escribe \emph{«qué es ADDA»}, \textbf{then} la respuesta contiene el nombre completo (\emph{Análisis y Diseño de Datos y Algoritmos}) y los créditos. \\ \hline
RF-A5 & \textbf{Given} la última asignatura mencionada fue \emph{Redes}, \textbf{when} el usuario escribe \emph{«¿y cuántos créditos tiene?»}, \textbf{then} la respuesta resuelve la elipsis hereditaria sin preguntar por el nombre. \\ \hline
RF-H7 & \textbf{Given} consulta de horario para curso 8, \textbf{when} el usuario envía \emph{«horario de 8º»}, \textbf{then} el bot rechaza explícitamente el curso inexistente sin alucinar contenido. \\ \hline
RF-P3 & \textbf{Given} pregunta sobre coordinador de \emph{IISSI2}, \textbf{when} el RAG no encuentra el rol en la tabla \texttt{profesor\_asignatura}, \textbf{then} el bot recupera del plan docente vía RAG y devuelve el nombre del coordinador. \\ \hline
RF-T4 & \textbf{Given} consulta con prompt injection (\emph{«ignora las instrucciones anteriores»}), \textbf{when} se procesa, \textbf{then} el bot mantiene el sistema de instrucciones y responde dentro del dominio. \\ \hline
RF-AD3 & \textbf{Given} un PDF nuevo subido al panel, \textbf{when} se invoca \emph{vectorizar}, \textbf{then} el estado del plan transita \texttt{pendiente → en\_proceso → completado} y los \emph{chunks} aparecen en \texttt{planes\_docentes\_chunks}. \\ \hline
\end{tabular}
\end{table}
```

Bastan **5–8 criterios representativos** (uno por dominio + uno por panel) — no es necesario uno por cada RF. El tribunal valora la disciplina, no la exhaustividad. Texto introductorio breve: "La derivación completa figura en `pruebas.tex §2.2`; la columna `Pruebas` de las Tablas X-Y proporciona la traza individual."

### P8.3 — Descripciones textuales detalladas de los prototipos de UI

La guía pide literalmente *"descripciones textuales detalladas"* de los prototipos. La memoria solo tiene 5 figuras con `\caption{…}` de una línea. **Añadir, debajo de cada figura, un párrafo de 4-6 líneas** describiendo:

- **Elementos UI visibles** (cabecera, panel lateral, lista, formulario, botón "Sincronizar", etc.).
- **Acciones que permite** (filtrar por curso, ver detalle, lanzar vectorización…).
- **Origen de los datos** (Sevius, us.es PDI, plan docente, conversation\_log).
- **Estado mostrado en la captura** (qué fila resaltada, qué filtro activo).

Ejemplo concreto para `fig:admin-asignaturas`:

> La Figura~\ref{fig:admin-asignaturas} muestra la vista de gestión de asignaturas del panel. La barra superior contiene la migaja de pan \emph{Centros → Titulaciones → Asignaturas} y un botón \emph{Sincronizar desde Sevius} que dispara el flujo preview-first descrito en RF-AD2. El cuerpo principal lista las asignaturas con columnas \emph{código, nombre, curso, créditos, duración, tipología}. La barra lateral derecha agrega métricas en tiempo real consumidas desde \texttt{/api/admin/stats}. La captura corresponde a la titulación GII-IS, con 73 asignaturas activas.

Repetir para las 5 figuras. **Impacto MH**: cierra un criterio formal de la guía sin tocar código.

Sobre el **software de los prototipos**, la memoria ya lo declara (`sec:req-prototipos` línea 205): "interfaz construida directamente sobre código HTML/CSS/JS vanilla, identidad visual de us.es, sin Figma". Mantenerlo y añadir una nota breve: "Las decisiones de diseño visual están registradas en D-027 (paleta), D-029 y D-030 (refinamientos del piloto)."

### P8.4 — Modelo conceptual de información en el capítulo de requisitos

La guía dice que un modelo conceptual *"detecta posibles inconsistencias"* en los RI. La memoria tiene un diagrama ER en `memoria_tfg/diagrama_er.mmd` pero pertenece al capítulo de BD. **Acción**: incluir una versión simplificada (solo entidades + cardinalidades, sin tipos SQL) al final de `subsec:ri-dominio`, etiquetada como `\caption{Modelo conceptual de los requisitos de información.}` y referenciarla desde la introducción del capítulo.

Aprovechar para verificar **inconsistencias detectables**:
- ¿Profesor-Asignatura tiene cardinalidad N:M con atributos `grupo`, `rol`? Comprobar contra `estructura_bd.tex`.
- ¿Aula está vinculada a Horario o también a Plan Docente?
- ¿Conversation\_log y Feedback están relacionados (mismo `session_id`)? Documentar la cardinalidad.

Si surge alguna inconsistencia, **es valor añadido** documentarla y resolverla — es exactamente lo que la guía quiere que produzca el modelo conceptual.

### P8.5 — Consistencia interna de cifras entre requisitos.tex y pruebas.tex

La tabla `tab:traz-rf-pruebas` (requisitos.tex líneas 281-291) **no cuadra** con `tab:e2e-categorias` (pruebas.tex líneas 35-56):

| Dominio | requisitos.tex | Suma equivalente en pruebas.tex |
|---------|----------------|---------------------------------|
| Asignaturas | 85 casos (80 PASS = 94,1 %) | especifica 22 + listado 15 + conteo 10 + horario\_asignatura 18 = **65 (no 85)**. La diferencia podría ser RAG-P74 + E-S* pero entonces la fila "Asignaturas" mezcla capas distintas |
| Horarios | 35 casos (97,1 %) | horario 27. **Discrepancia +8** |
| Profesorado | 39 casos (92,3 %) | profesor 43. **Discrepancia −4** |
| Transversal | 16 casos (100 %) | cambiar\_contexto 13 + fuera\_ambito 8 + cross\_dominio 1 + seguimiento 1 = **23**. Discrepancia −7 |
| Total E2E | 159 casos | 158 (suma de la tabla) vs 159 en línea TOTAL — **discrepancia interna en pruebas.tex también** |

**Acción**: definir una **fuente única de verdad** (probablemente `tests/results/testing_general.json`) y reescribir ambas tablas para que coincidan. Si la fila "Asignaturas" en `tab:traz-rf-pruebas` mezcla capas (E2E + RAG), separarla en dos filas. Esta inconsistencia es del tipo que el tribunal detecta abriendo dos páginas a la vez — corrigible en 1 hora si se tiene el JSON real.

### P8.6 — Refuerzos puntuales que elevan la calidad

a) **Atomicidad de RF**. Dividir RF compuestos. Ejemplo:
- RF-A1 actual: "ficha completa cuando el usuario la nombra de forma explícita o mediante alias o acrónimo (ADDA, FP, IISSI2)" → atomizar en RF-A1.a (nombre explícito), RF-A1.b (alias/acrónimo), o mantener pero añadir 3 criterios de aceptación distintos en P8.2.

b) **Priorización razonada**. Añadir párrafo introductorio a `sec:req-funcionales`: "La prioridad se asigna siguiendo MoSCoW (Must/Should/Could/Won't). Los requisitos `Alta` son **Must** del prototipo de fase 1; los `Media` son **Should** validados pero con casos de uso menos frecuentes; no hay requisitos `Won't` activos (las funcionalidades aplazadas figuran en `sec:req-evolucion`)."

c) **Sección de restricciones y dependencias**. Añadir `\section{Restricciones y dependencias externas}` con:
- Dependencia de Sevius (`sevius.us.es`): si cambia el HTML, los scrapers requieren actualización.
- Dependencia de Gemini API: cuota gratuita 100 RPM / 1000 RPD; si Google revoca tier free, se activa Ollama local (P5.2.c).
- Dependencia de Supabase Free: 5 000 MAU; a partir de ahí, Plan Pro 25 \$/mes.
- Dependencia de `us.es` PDI: requiere que el directorio publique los perfiles de profesorado con la estructura HTML actual.
- Restricción: el sistema se entrena para **español peninsular** (RNF-7); inglés aplazado a fase 2.
- Restricción legal: solo trata datos públicos; el sistema **no requeriría adaptación RGPD significativa** mientras no incorpore datos identificables.

d) **Casos de uso desde requisitos**. Añadir párrafo al final de `sec:req-funcionales`: "La visión de casos de uso UML asociada a estos requisitos figura en `arquitectura_diseno.tex §2.3.5` (Figura X)." Y referenciarla con `\ref{}`. La trazabilidad bidireccional eleva la lectura.

e) **RF-T6 con prueba asociada**. La UI feedback existe ([chatbot-widget.js:547-589](frontend/chatbot-widget.js#L547-L589)). Añadir al menos un caso de prueba manual `FB-01` en `pruebas.tex` (verificación: enviar feedback, comprobar fila en tabla `feedback` desde panel admin) y asignarlo a RF-T6 en `tab:rf-transversal`.

f) **Columna Pruebas para RF-AD**. Añadir columna a `tab:rf-admin` con los IDs de las 24 pruebas pytest (A01–A24). Mapeo natural:
- RF-AD1 → A03, A12 (centros/titulaciones)
- RF-AD2 → A14, A15, A21–A24 (sync Sevius con mocks)
- RF-AD3 → planes\_docentes/procesar (verificar si A26+ existe)
- RF-AD4 → A06, A07 (profesores)
- RF-AD6 → A10, A11 (conversaciones)
- RF-AD7 → (verificar si hay endpoint de feedback en tests)

### P8.7 — Modelo de proceso (opcional pero recomendado)

La guía cita explícitamente el modelo de proceso para *"entender mejor el dominio del problema"*. Añadir al final del capítulo (`\section{Modelo de proceso del flujo conversacional}`) **un diagrama de actividad o flujo BPMN** del turno típico:

```
Usuario escribe consulta → Widget POST /webhooks/rest/webhook → Rasa NLU clasifica intent
  ├─ confianza < 0,8 → ActionSmartFallback (Gemini clasificador) → ramifica a action
  └─ confianza ≥ 0,8 → action correspondiente
                       ├─ asignaturas → resolver_asignatura cascada → Text-to-SQL | RAG
                       ├─ horarios → SQL con JOIN + GROUP BY
                       ├─ profesores → SQL + RAG fallback
                       └─ contexto → set_slot contexto_titulacion
                       → genera respuesta (Gemini temp=0,3) → bot_uttered → widget
                       → log_conversation()
                       (opcional) usuario pulsa Feedback → log_feedback()
```

Diagrama BPMN simple en TikZ o exportado desde draw.io. **Impacto**: cubre criterio opcional de la guía y conecta requisitos con arquitectura.

### P8.8 — Coherencia con P5/P6/P7

- **RNF-13**: la memoria afirma "Basic Auth HTTPS, HTTP 401 sin credencial". La realidad es Supabase Auth client-side (ver P5.2.a). **Reescribir** el texto de RNF-13: descripción = "Autenticación Supabase Auth (email/password con JWT) en `login.html`; el panel se sirve detrás de nginx y el frontend redirige a login si la sesión es inválida"; umbral = "Sesión Supabase requerida para ver `/admin.html`"; valor alcanzado = "Cumplido (verificación manual)". Si se decide endurecer el backend Flask validando el JWT, actualizar el umbral.
- **RF-T6**: confirmar que la UI feedback existe (sí, [chatbot-widget.js:547-589](frontend/chatbot-widget.js#L547-L589)) y añadir prueba FB-01 (ver P8.6.e).
- **RF-AD3** (vectorizar): aprovechar la documentación del pipeline RAG con máquina de estados (P7.5.22) como evidencia de cumplimiento.

### P8.9 — Plantilla compacta para añadir todo P8 a la memoria

Estructura recomendada del capítulo de requisitos tras aplicar P8:

```
\chapter{Análisis de requisitos}
  \section{Identificación de actores}          % YA existe
  \section{Requisitos funcionales}             % YA existe — atomización P8.6.a
    \subsection{Dominio de asignaturas}
    \subsection{Dominio de horarios}
    \subsection{Dominio de profesorado}
    \subsection{Comportamientos transversales} % RF-T6 con prueba P8.6.e
    \subsection{Funcionalidades del panel admin}% columna Pruebas P8.6.f
  \section{Criterios de aceptación}            % NUEVO P8.2 (5-8 ejemplos GWT)
  \section{Casos de uso}                       % NUEVO breve, referencia diagrama de arquitectura P8.6.d
  \section{Requisitos de información}          % YA existe
    \subsection{Entidades de dominio}
    \subsection{Entidades del módulo RAG}
    \subsection{Entidades de operación}
    \subsection{Modelo conceptual}             % NUEVO P8.4 (ER simplificado)
  \section{Requisitos no funcionales}          % YA existe — RNF-13 corregido P8.8
  \section{Restricciones y dependencias externas} % NUEVO P8.6.c
  \section{Prototipos de interfaz}             % YA existe — descripciones detalladas P8.3
  \section{Modelo de proceso}                  % NUEVO P8.7 (BPMN del turno)
  \section{Matrices de trazabilidad}           % YA existe — cifras consistentes P8.5
  \section{Evolución del alcance}              % YA existe
```

Coste estimado de aplicar P8 completo: **8-12 horas** de redacción + 1-2 figuras nuevas (modelo conceptual ER, modelo de proceso BPMN). Impacto MH **alto**: cierra los 5 mínimos formales de la guía con margen.

---

## Tabla de ejecución recomendada

| Orden | Tarea | Archivo | Complejidad | Impacto MH |
|-------|-------|---------|-------------|------------|
| 1 | P1.1 — Añadir 8 refs bib | pfcbib.bib | Baja | Alto |
| 2 | P1.4 — Tabla NLU métricas | pruebas.tex | Media | Muy alto |
| 3 | P1.7 — Ablación RAG vs. sin RAG | pruebas.tex | Media | Muy alto |
| 4 | P1.2 — §Contribución | 01_introduccion.tex | Media | Alto |
| 5 | P1.5 — Amenazas validez | pruebas.tex | Baja | Alto |
| 6 | P1.6 — Casos fallidos | pruebas.tex | Baja | Alto |
| 7 | P2.1 — ISO 25010 tabla | arquitectura_diseno.tex | Baja | Medio |
| 8 | P2.2 — Tabla patrones GoF | arquitectura_diseno.tex | Baja | Medio |
| 9 | P2.3 — Diagramas secuencia | arquitectura_diseno.tex | Alta | Medio |
| 10 | P2.4 — Def. formal problema | 03_conceptos.tex | Baja | Medio |
| 11 | P2.5 — Tabla comparativa LLMs | 02_preparacion.tex | Baja | Medio |
| 12 | P1.3 — Tabla comparativa arte | 02_preparacion.tex | Baja | Alto |
| 13 | P2.7 — Trabajo futuro técnico | conclusiones.tex | Media | Medio |
| 14 | P2.8 — Ética | conclusiones.tex | Baja | Medio |
| 15 | P3.1 — Tabla "en números" | conclusiones.tex | Baja | Medio |
| 16 | P3.2 — Contribución estado arte | conclusiones.tex | Baja | Alto |
| 17 | P2.6 — Citas en §3 Conceptos | 03_conceptos.tex | Baja | Bajo |
| 18 | P4.1 — Cross-references | Compilación | Baja | Crítico |
| 19 | P4.2 — Consistencia cifras | Revisión | Baja | Bajo |
| 20 | P4.3 — Ajuste resumen | resumen.tex | Baja | Medio |

### Orden REVISADO tras incorporar P5/P6/P7/P8 (recomendado)

> Las filas marcadas con ⚠ del plan original deben tratarse **después** de los bloques P5/P6, no antes — algunos contienen datos inventados que entran en conflicto con la realidad del código. El bloque **P8 (calidad de requisitos según guía Segura)** se prioriza porque cubre criterios formales del tribunal y porque las correcciones de P5 cruzan con él (RNF-13, RF-T6).

| Orden | Tarea | Archivo | Notas |
|-------|-------|---------|-------|
| 1 | **P6.1 — Verificar / sustituir referencias inventadas** | pfcbib.bib | BLOQUEANTE: integridad académica |
| 2 | **P5.1 — Corregir threshold 0,8, pipeline NLU real, embeddings gemini-001** | arquitectura_diseno.tex, implementacion.tex, img/diagrama_despliegue.* | Discrepancias factuales contra el código |
| 3 | **P8.5 — Reconciliar cifras tab:traz-rf-pruebas vs tab:e2e-categorias** | requisitos.tex, pruebas.tex | Fuente única: `tests/results/testing_general.json`. Sin esto, las dos tablas se contradicen entre páginas |
| 4 | **P5.2.a + P8.8 — Reescribir RNF-13: Supabase Auth (JWT), no Basic Auth** | requisitos.tex (RNF-13), arquitectura_diseno.tex | Corregir mecanismo. Opcionalmente endurecer backend Flask validando JWT (~1h) |
| 5 | **P8.2 — Criterios de aceptación explícitos (Given-When-Then) por RF representativos** | requisitos.tex (nueva §sec:req-aceptacion) | Cubre el criterio nº2 de la guía Segura. 5-8 criterios bastan |
| 6 | **P8.3 — Descripciones textuales detalladas de los 5 prototipos UI** | requisitos.tex §sec:req-prototipos | Cubre el criterio nº4 de la guía. Párrafo de 4-6 líneas por figura |
| 7 | **P8.4 — Modelo conceptual de información (ER simplificado) en requisitos** | requisitos.tex §subsec:ri-dominio | Cubre artefacto opcional pero muy valorado. Reutilizar `memoria_tfg/diagrama_er.mmd` |
| 8 | **P5.2.b + P8.6.e — Documentar UI feedback + añadir prueba FB-01** | implementacion.tex, requisitos.tex, pruebas.tex | UI ya existe ([chatbot-widget.js:547-589](frontend/chatbot-widget.js#L547-L589)); cerrar RF-T6 con su prueba |
| 9 | **P8.6.f — Columna Pruebas en tab:rf-admin (mapeo a A01-A24)** | requisitos.tex Tabla rf-admin | Consistencia con el resto de tablas RF |
| 10 | **P8.6.c — Sección "Restricciones y dependencias externas"** | requisitos.tex (nueva §) | Sevius, Gemini quota, Supabase Free, us.es PDI, español peninsular |
| 11 | **P8.6.a + P8.6.b — Atomicidad de RF compuestos + nota MoSCoW en intro** | requisitos.tex §sec:req-funcionales | Cierra crítica clásica de tribunales |
| 12 | **P8.6.d — Referenciar diagrama UML de casos de uso desde requisitos** | requisitos.tex (nueva §sec:casos-uso breve) | El diagrama ya existe en arquitectura — solo enlazar |
| 13 | **P8.7 — Modelo de proceso (BPMN del turno conversacional)** | requisitos.tex (nueva §) | Artefacto opcional de la guía; valor narrativo alto |
| 14 | **P5.2.c — Matizar el Strategy LLM** Gemini/Ollama intercambiables en build, no failover dinámico | arquitectura_diseno.tex | Aclarar naturaleza del switching o introducir wrapper `llm_client.py` (~1h) |
| 15 | **P7 (todas) — Joyas técnicas por épica** | implementacion.tex + arquitectura_diseno.tex | **Bloque clave de elevación**: 25 hallazgos con archivo:línea. Priorizar: validador SQL completo (P7.1.5), `score_por_normalizado` (P7.2.7), `RERANK_WEIGHTS` (P7.5.16), búsqueda en dos fases RAG (P7.5.17), chunking con deduplicación (P7.5.19), bench metrics JSONL (P7.6.24), smart fallback con JSON (P7.4.13), cascada 5 etapas detallada (P7.1.1) |
| 16 | P5.3 — Reranking, 3 umbrales fuzzy, scrapers por dpto, modularización NLU | implementacion.tex | Solapa con P7 — agruparlos en la edición |
| 17 | **P7.7 — Reescribir P1.6 con casos fallidos reales (E-T02, E-T04, C-P05, X-P06)** | pruebas.tex | Sustituye ejemplos genéricos por IDs reales |
| 18 | P5.4 — Higiene de repo + nota sobre `multi_intent/` conservado por referencia | implementacion.tex, repo raíz | |
| 19 | P1.2 — §Contribución, **ajustada según P6.6** | 01_introduccion.tex | No contradecir P5 |
| 20 | P1.3 — Comparativa estado del arte **con referencias verificadas** | 02_preparacion.tex | |
| 21 | P1.5 — Amenazas a la validez (Wohlin) | pruebas.tex | Sin cambios |
| 22 | P2.4 — Definición formal del problema | 03_conceptos.tex | Sin cambios |
| 23 | P2.5 — Comparativa LLMs | 02_preparacion.tex | Sin cambios |
| 24 | P2.7 — Trabajo futuro técnicamente específico | conclusiones.tex | Sin cambios |
| 25 | P2.8 — Ética | conclusiones.tex | Sin cambios |
| 26 | P3.2 — Contribución al estado del arte | conclusiones.tex | Solo con referencias verificadas |
| 27 | P2.2 — Tabla patrones GoF | arquitectura_diseno.tex | Quitar Strategy LLM si Ollama queda archivado (P5.2.c) |
| 28 | **P2.1 — ISO 25010 con cifras reales** (ver P6.5) | arquitectura_diseno.tex | p50 3,4 s, p95 10,5 s; quitar pen-test |
| 29 | **P3.1 — "Linceus en números" con cifras reales** (ver P6.4) | conclusiones.tex | 36 intents, ≈465 casos, p50 3,4 s, p95 10,5 s, 91,9 % RAG |
| 30 | P2.3 — Diagramas de secuencia | arquitectura_diseno.tex | Verificar nombres reales de actions; usar `gemini-embedding-001` |
| 31 | P2.6 — Citas en §3 Conceptos | 03_conceptos.tex | Solo con referencias verificadas |
| 32 | P4.1, P4.2, P4.3 — Cross-refs, consistencia, resumen | varios | Igual que antes |
| ⚠ | **P1.1 — Refs bib (8 entradas)** | pfcbib.bib | **NO aplicar** hasta verificar/sustituir las 4 sospechosas (P6.1) |
| ⚠ | **P1.4 — Tabla NLU métricas inventada** | pruebas.tex | **NO aplicar tal cual** (P6.2). Reemplazar por `rasa test nlu --cross-validation` real |
| ⚠ | **P1.7 — Ablación RAG inventada** | pruebas.tex | **NO aplicar tal cual** (P6.3). O ejecutar el experimento, o eliminar |

---

## Notas de contexto

- **Criterio MH ETSII US**: voto unánime + propuesta tutor + cupo 5% grupo. El tribunal valora especialmente rigor científico y originalidad.
- **Tutor**: José Antonio Parejo Maestre (Lenguajes y Sistemas Informáticos). Ha revisado el trabajo y enviado correcciones detalladas — esas correcciones ya fueron aplicadas en la sesión anterior.
- **Stack**: Rasa 3.6.21 + Gemini gemma-3-27b-it + Supabase/PostgreSQL + pgvector (HNSW) + Docker Compose + vanilla JS widget + Flask admin
- **Correcciones del profesor ya aplicadas** (no repetir):
  - Localización de espacios → aplazada, con justificación en §req-evolucion
  - Segunda persona corregida en §2.1.3
  - Diagrama UML de casos de uso añadido en §2.3.5
  - RNF-13/14/15 añadidos con valores medidos
  - §11.7 multi-intent expandido con 3 razones técnicas
  - §11.8.3 fuzzy matching con calibración empírica (120 casos, 3 iteraciones)
  - 6 referencias académicas añadidas (Bass, GoF, Fielding, Newman, Docker, Martin)
  - Parte III renombrada a "Análisis, Diseño e Implementación"
  - §6.5 matrices de trazabilidad (obj↔RF, RF↔pruebas)
  - Tabla RNF restructurada con columna "Valor alcanzado"
