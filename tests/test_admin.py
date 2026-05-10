"""
Suite de pruebas del panel de administración de Linceus Assistant.

Organización:
  - Bloque GET:  endpoints de lectura contra BD de producción (sin efectos).
  - Bloque 400:  validación de parámetros obligatorios (no llega a BD).
  - Bloque mock: lógica de sync_asignaturas con Sevius mockeado.

Ejecución:
  cd <raíz del proyecto>
  pip install pytest
  pytest tests/test_admin.py -v
"""

import json
import pytest
from unittest.mock import patch

from admin.app import app as flask_app


# ─────────────────────────────────────────────────────────────────────────────
# Fixture: cliente de test de Flask
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


PREFIX = "/api/admin"


# ─────────────────────────────────────────────────────────────────────────────
# GET — lectura (contra BD real, solo lectura)
# ─────────────────────────────────────────────────────────────────────────────

class TestGetEndpoints:

    def test_health(self, client):
        """El servidor responde y la BD es accesible."""
        r = client.get(f"{PREFIX}/health")
        assert r.status_code == 200
        assert r.get_json()["status"] == "ok"

    def test_stats_contiene_claves(self, client):
        """GET /stats devuelve un objeto con todas las claves esperadas."""
        r = client.get(f"{PREFIX}/stats")
        assert r.status_code == 200
        data = r.get_json()
        for clave in ["centros", "titulaciones", "asignaturas", "profesores",
                      "grupos", "horarios", "planes_docentes", "chunks",
                      "conversaciones", "feedback"]:
            assert clave in data, f"Falta clave '{clave}' en /stats"

    def test_stats_valores_positivos(self, client):
        """Los conteos de /stats son enteros >= 0."""
        data = client.get(f"{PREFIX}/stats").get_json()
        for clave, valor in data.items():
            assert isinstance(valor, int) and valor >= 0, \
                f"{clave} tiene valor inválido: {valor}"

    def test_centros_lista(self, client):
        """GET /centros devuelve una lista no vacía con los campos requeridos."""
        r = client.get(f"{PREFIX}/centros")
        assert r.status_code == 200
        centros = r.get_json()
        assert isinstance(centros, list) and len(centros) > 0
        for c in centros:
            for campo in ["id", "codigo", "nombre", "num_titulaciones"]:
                assert campo in c

    def test_asignaturas_sin_filtro(self, client):
        """GET /asignaturas sin filtro devuelve todas las asignaturas activas."""
        r = client.get(f"{PREFIX}/asignaturas")
        assert r.status_code == 200
        asigs = r.get_json()
        assert isinstance(asigs, list) and len(asigs) > 0

    def test_asignaturas_con_titulacion(self, client):
        """GET /asignaturas?titulacion_id=<id> filtra correctamente."""
        # Obtener un titulacion_id real desde la BD
        centros = client.get(f"{PREFIX}/centros").get_json()
        assert centros, "No hay centros en BD"
        centro_id = centros[0]["id"]

        r = client.get(f"{PREFIX}/titulaciones?centro_id={centro_id}")
        assert r.status_code == 200
        tits = r.get_json()
        assert tits, "No hay titulaciones para el centro"

        tit_id = tits[0]["id"]
        r2 = client.get(f"{PREFIX}/asignaturas?titulacion_id={tit_id}")
        assert r2.status_code == 200
        asigs = r2.get_json()
        assert isinstance(asigs, list)
        for a in asigs:
            assert a["titulacion_nombre"] is not None

    def test_profesores_lista(self, client):
        """GET /profesores devuelve una lista con los campos de contacto."""
        r = client.get(f"{PREFIX}/profesores")
        assert r.status_code == 200
        profs = r.get_json()
        assert isinstance(profs, list) and len(profs) > 0
        for p in profs:
            for campo in ["id", "nombre", "apellidos", "email"]:
                assert campo in p

    def test_profesor_detalle(self, client):
        """GET /profesores/<id> devuelve el perfil completo de un profesor."""
        profs = client.get(f"{PREFIX}/profesores").get_json()
        assert profs
        pid = profs[0]["id"]
        r = client.get(f"{PREFIX}/profesores/{pid}")
        assert r.status_code == 200
        p = r.get_json()
        assert p["id"] == pid
        assert "email" in p

    def test_profesor_inexistente_404(self, client):
        """GET /profesores/<uuid-falso> devuelve 404."""
        r = client.get(f"{PREFIX}/profesores/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_horarios_con_titulacion(self, client):
        """GET /horarios?titulacion_id=<id> devuelve franjas con los campos esperados."""
        centros = client.get(f"{PREFIX}/centros").get_json()
        centro_id = centros[0]["id"]
        tits = client.get(f"{PREFIX}/titulaciones?centro_id={centro_id}").get_json()
        tit_id = tits[0]["id"]

        r = client.get(f"{PREFIX}/horarios?titulacion_id={tit_id}")
        assert r.status_code == 200
        horarios = r.get_json()
        assert isinstance(horarios, list)
        if horarios:
            for campo in ["dia_semana", "hora_inicio", "hora_fin", "asignatura_nombre"]:
                assert campo in horarios[0]

    def test_conversaciones_estructura(self, client):
        """GET /conversaciones devuelve total y rows."""
        r = client.get(f"{PREFIX}/conversaciones")
        assert r.status_code == 200
        data = r.get_json()
        assert "total" in data and "rows" in data
        assert isinstance(data["total"], int) and data["total"] >= 0

    def test_sesiones_estructura(self, client):
        """GET /conversaciones/sesiones devuelve total y rows con session_id."""
        r = client.get(f"{PREFIX}/conversaciones/sesiones")
        assert r.status_code == 200
        data = r.get_json()
        assert "total" in data and "rows" in data
        if data["rows"]:
            assert "session_id" in data["rows"][0]
            assert "num_mensajes" in data["rows"][0]

    def test_extractores_horarios(self, client):
        """GET /horarios/extractores devuelve la lista de centros soportados."""
        r = client.get(f"{PREFIX}/horarios/extractores")
        assert r.status_code == 200
        extractores = r.get_json()
        assert isinstance(extractores, list) and len(extractores) > 0
        assert "centro_codigo" in extractores[0]


# ─────────────────────────────────────────────────────────────────────────────
# Validación de parámetros obligatorios — HTTP 400/404 (no toca BD)
# ─────────────────────────────────────────────────────────────────────────────

class TestValidacionParametros:

    def test_sync_asignaturas_sin_body_400(self, client):
        """POST /asignaturas/sync sin body devuelve 400."""
        r = client.post(f"{PREFIX}/asignaturas/sync",
                        data=json.dumps({}),
                        content_type="application/json")
        assert r.status_code == 400
        assert "error" in r.get_json()

    def test_sync_asignaturas_falta_titulacion_400(self, client):
        """POST /asignaturas/sync sin titulacion_id devuelve 400."""
        r = client.post(f"{PREFIX}/asignaturas/sync",
                        data=json.dumps({"codcentro": "3",
                                         "codigo_titulacion_sevius": "205"}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_sync_asignaturas_titulacion_inexistente_404(self, client):
        """POST /asignaturas/sync con titulacion_id falso devuelve 404."""
        r = client.post(f"{PREFIX}/asignaturas/sync",
                        data=json.dumps({
                            "titulacion_id": "00000000-0000-0000-0000-000000000000",
                            "codcentro": "3",
                            "codigo_titulacion_sevius": "205",
                        }),
                        content_type="application/json")
        assert r.status_code == 404

    def test_generar_horarios_sin_centro_400(self, client):
        """POST /horarios/generar sin centro_id devuelve 400."""
        r = client.post(f"{PREFIX}/horarios/generar",
                        data=json.dumps({}),
                        content_type="application/json")
        assert r.status_code == 400

    def test_generar_horarios_centro_inexistente_404(self, client):
        """POST /horarios/generar con centro_id falso devuelve 404."""
        r = client.post(f"{PREFIX}/horarios/generar",
                        data=json.dumps({
                            "centro_id": "00000000-0000-0000-0000-000000000000",
                        }),
                        content_type="application/json")
        assert r.status_code == 404

    def test_titulaciones_sin_centro_id(self, client):
        """GET /horarios/titulaciones sin centro_id devuelve 400."""
        r = client.get(f"{PREFIX}/horarios/titulaciones")
        assert r.status_code == 400

    def test_borrar_horarios_sin_centro_400(self, client):
        """DELETE /horarios sin centro_id devuelve 400."""
        r = client.delete(f"{PREFIX}/horarios")
        assert r.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Lógica de sync_asignaturas con Sevius mockeado
# ─────────────────────────────────────────────────────────────────────────────

class TestSyncAsignaturasMock:
    """
    Prueba la lógica de inserción de sync_asignaturas sin llamar a Sevius
    ni modificar la BD de producción.
    Estrategia: mock del scraper + mock de execute_returning para capturar
    la query generada sin ejecutarla.
    """

    def _titulacion_id_real(self, client):
        """Obtiene un titulacion_id real de la BD para los tests."""
        centros = client.get(f"{PREFIX}/centros").get_json()
        centro_id = centros[0]["id"]
        tits = client.get(f"{PREFIX}/titulaciones?centro_id={centro_id}").get_json()
        return tits[0]["id"]

    def test_sevius_sin_resultados_404(self, client):
        """Si Sevius no devuelve asignaturas, el endpoint responde 404."""
        tit_id = self._titulacion_id_real(client)
        with patch("admin.routes.asignaturas.sevius_asignaturas", return_value=[]):
            r = client.post(f"{PREFIX}/asignaturas/sync",
                            data=json.dumps({
                                "titulacion_id": tit_id,
                                "codcentro": "3",
                                "codigo_titulacion_sevius": "205",
                            }),
                            content_type="application/json")
        assert r.status_code == 404

    def test_sevius_error_502(self, client):
        """Si Sevius lanza excepción, el endpoint responde 502."""
        tit_id = self._titulacion_id_real(client)
        with patch("admin.routes.asignaturas.sevius_asignaturas",
                   side_effect=Exception("timeout")):
            r = client.post(f"{PREFIX}/asignaturas/sync",
                            data=json.dumps({
                                "titulacion_id": tit_id,
                                "codcentro": "3",
                                "codigo_titulacion_sevius": "205",
                            }),
                            content_type="application/json")
        assert r.status_code == 502
        assert "Sevius" in r.get_json()["error"]

    def test_asignaturas_ya_existentes_no_se_duplican(self, client):
        """
        Si todas las asignaturas que devuelve Sevius ya están en BD,
        la respuesta contiene 'creadas': [] y 'existentes' con todas ellas.
        """
        tit_id = self._titulacion_id_real(client)

        # Obtener asignaturas reales de esa titulación
        asigs_bd = client.get(
            f"{PREFIX}/asignaturas?titulacion_id={tit_id}"
        ).get_json()
        assert asigs_bd, "La titulación no tiene asignaturas en BD"

        # Simular que Sevius devuelve exactamente esas asignaturas
        sevius_fake = [{"codigo": a["codigo"], "nombre": a["nombre"]}
                       for a in asigs_bd[:3]]

        with patch("admin.routes.asignaturas.sevius_asignaturas",
                   return_value=sevius_fake):
            r = client.post(f"{PREFIX}/asignaturas/sync",
                            data=json.dumps({
                                "titulacion_id": tit_id,
                                "codcentro": "3",
                                "codigo_titulacion_sevius": "205",
                            }),
                            content_type="application/json")

        assert r.status_code == 200
        data = r.get_json()
        assert data["creadas"] == [], \
            "No debería crear asignaturas que ya existen"
        assert len(data["existentes"]) == len(sevius_fake), \
            "Todas las asignaturas deberían estar en 'existentes'"

    def test_asignatura_nueva_se_inserta(self, client):
        """
        Si Sevius devuelve una asignatura con código inexistente,
        execute_returning se llama con el INSERT correcto.
        Mock de execute_returning para no tocar BD.
        """
        tit_id = self._titulacion_id_real(client)
        asig_nueva = {"codigo": "TEST-9999", "nombre": "Asignatura de prueba"}

        with patch("admin.routes.asignaturas.sevius_asignaturas",
                   return_value=[asig_nueva]), \
             patch("admin.routes.asignaturas.execute_returning",
                   return_value={"id": "fake-uuid",
                                 "codigo": "TEST-9999",
                                 "nombre": "Asignatura de prueba"}) as mock_insert:

            r = client.post(f"{PREFIX}/asignaturas/sync",
                            data=json.dumps({
                                "titulacion_id": tit_id,
                                "codcentro": "3",
                                "codigo_titulacion_sevius": "205",
                            }),
                            content_type="application/json")

        assert r.status_code == 201
        data = r.get_json()
        assert len(data["creadas"]) == 1
        assert data["creadas"][0]["codigo"] == "TEST-9999"
        # Verificar que el INSERT se llamó con el titulacion_id correcto
        call_params = mock_insert.call_args[0][1]
        assert call_params[0] == tit_id
        assert call_params[1] == "TEST-9999"
