# Instrucciones para completar la memoria del TFG

## ✅ Capítulos añadidos

He creado tres nuevos capítulos siguiendo la estructura del TFG de referencia que sacó sobresaliente:

1. **`Capitulos/herramientas.tex`** - Herramientas utilizadas (similar al capítulo 2.1 del TFG de referencia)
2. **`Capitulos/marco_tecnologico.tex`** - Marco tecnológico completo
3. **`Capitulos/estructura_bd.tex`** - Estructura de la base de datos

Estos capítulos ya están incluidos en `proyect.tex` y se compilarán automáticamente.

## 📋 Elementos que debes añadir

### Imágenes necesarias

Los capítulos hacen referencia a las siguientes imágenes que debes crear y colocar en la carpeta `Plantilla TfG/img/`:

1. **`arquitectura.png/pdf`** - Diagrama de arquitectura del sistema (3 capas):
   - Capa de presentación (Frontend Node.js)
   - Capa de procesamiento conversacional (Rasa + Ollama)
   - Capa de datos (PostgreSQL/Supabase)

2. **`diagrama_er.png/pdf`** - Diagrama entidad-relación:
   - Puedes usar el contenido de `db_tables.md` para generarlo
   - Herramientas recomendadas: draw.io, dbdiagram.io, o Mermaid
   - El diagrama ya está en formato Mermaid en `db_tables.md`, solo necesitas exportarlo como imagen

### Cómo generar el diagrama ER desde Mermaid

1. Ve a https://mermaid.live/
2. Copia el contenido del archivo `db_tables.md`
3. Pégalo en el editor de Mermaid Live
4. Exporta como PNG o SVG
5. Guarda el archivo como `diagrama_er.png` en `Plantilla TfG/img/`

### Comandos LaTeX personalizados

Los capítulos usan comandos personalizados que probablemente estén definidos en `pclass.cls` o similar:

- `\figura{escala}{ruta}{caption}{label}{nota}` - Para insertar figuras
- `\cuadro{formato}{caption}{label}{contenido}` - Para insertar tablas

Si estos comandos no existen, puedes reemplazarlos por los comandos estándar de LaTeX:

```latex
% En lugar de \figura{0.8}{img/arquitectura}{...}{fig:arquitectura}{}
\begin{figure}[h]
\centering
\includegraphics[width=0.8\linewidth]{img/arquitectura}
\caption{Arquitectura general del sistema LinceUS Assistant}
\label{fig:arquitectura}
\end{figure}

% En lugar de \cuadro{|l|l|p{6cm}|}{...}{tab:universidades}{...}
\begin{table}[h]
\centering
\begin{tabular}{|l|l|p{6cm}|}
\hline
% contenido de la tabla
\end{tabular}
\caption{Estructura de la tabla UNIVERSIDADES}
\label{tab:universidades}
\end{table}
```

## 🔧 Ajustes recomendados

### Personalización del contenido

Los capítulos están completos pero puedes personalizarlos:

1. **Herramientas**: Añade otras herramientas que hayas usado (Postman, Docker, etc.)
2. **Marco tecnológico**: Ajusta versiones específicas si han cambiado
3. **Estructura BD**: Añade más detalles sobre consultas específicas que uses

### Verificar referencias cruzadas

Asegúrate de que las referencias a otros capítulos sean correctas:
- Los capítulos hacen referencia a "Capítulo \ref{cap1}" y similares
- Verifica que los labels coincidan con tus capítulos existentes

## 📚 Compilación

Para compilar el documento completo:

1. Abre `proyect.tex` en Overleaf o tu editor LaTeX local
2. Compila (pdflatex + bibtex)
3. Revisa que todas las referencias e imágenes se carguen correctamente

## 📖 Estructura seguida

He seguido fielmente la estructura del TFG de referencia (que sacó sobresaliente):

- **Capítulo de Herramientas**: Tabla resumen al final, descripción detallada de cada herramienta
- **Marco tecnológico**: Separado por capas (frontend, backend, BD, IA)
- **Estructura BD**: Tablas detalladas con cada campo y su tipo

## ⚠️ Notas importantes

1. **No he tocado los capítulos existentes** (capitulo1.tex, capitulo2.tex) como solicitaste
2. Los capítulos están listos para compilar, solo faltan las imágenes
3. La estructura sigue las normas de la ETSII para TFGs
4. Todos los nombres de tablas y tecnologías coinciden con tu proyecto real

## 🎯 Próximos pasos

1. Crear las dos imágenes mencionadas arriba
2. Compilar el documento
3. Revisar y personalizar el contenido según tus necesidades
4. Añadir referencias bibliográficas en `pfcbib.bib` si es necesario

¡Buena suerte con tu TFG! 🚀
