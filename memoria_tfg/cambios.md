en la estructura de la base de datos \9 no se si hace falta añadir FKs):
1) a centros le faltan los campos 
created_at
updated_at
codigo_sevius
codigo_us
2) a departamentos le falta
created_at
updated_at
centro_id (FK)
codigo_us
3) a tiutlaciones le faltan
updated_at
created_at
4) a asignatura les faltan:
created_at
updated_at
5) a profesores le falta:
created_at
updated_at
categoria_academica
enlace_perfil
centro_id (FK)
6) a horarios les faltan:
created_at
updated_at
cuatrimestre
7) a planes docentes le falta:
created_at
8) a chunks planes docentes le falta
created_at
y esta mal escrita Secci´on del documento (e.g.,
.Evaluaci´on”)
Teniendo en cuenta todo esto , revisa 10.5– Relaciones entre entidades
