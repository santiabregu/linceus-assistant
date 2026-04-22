"""
Punto de entrada del servidor de administración de LinceUS.
"""

from flask import Flask
from flask_cors import CORS

from admin.routes import (
    centros, titulaciones, asignaturas,
    sevius, planes_docentes, profesores,
    horarios, conversaciones, stats,
)

app = Flask(__name__)
CORS(app)

PREFIX = "/api/admin"

for bp in [
    centros.bp,
    titulaciones.bp,
    asignaturas.bp,
    sevius.bp,
    planes_docentes.bp,
    profesores.bp,
    horarios.bp,
    conversaciones.bp,
    stats.bp,
]:
    app.register_blueprint(bp, url_prefix=PREFIX)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
