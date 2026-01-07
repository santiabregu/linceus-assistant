1) Se creó el diccionario general que se va a usar durante el proyecto.
2) Se definió el scope para asignaturas (Ing. Software - ETSII).
3) Se definió el esquema de la base de datos para todo el proyecto (esquema inicial).
4) Se insertaron los datos iniciales (documento tfg_chatbot_resumen_datos.md).
5) Se ha definido la lógica de versionado.
6) Se decidió separar los datos de entrenamiento NLU según épicas.
7) Se opta por un diseño basado en una intención general de consulta combinada con entidades que especifican el atributo solicitado, lo que permite una mayor escalabilidad, reutilización del modelo conversacional y adaptación al lenguaje natural del usuario, evitando la proliferación innecesaria de intenciones.
8) Se adopta `rapidfuzz` para fuzzy matching en lugar de `difflib`, ya que ofrece mejor precisión en detección de typos (ej.: "obligatioria" → "obligatoria") y es 10-100x más rápido. Se aplica tanto a atributos de asignaturas como a búsqueda por nombre.
9) Se ha creado una versión inicial del frontend. 
