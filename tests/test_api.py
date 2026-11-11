"""Pruebas de la API: autenticación, análisis, historial y tareas."""

from conftest import register

INSTRUCCIONES = "Elaborar un ensayo. Entregar el viernes en PDF con mínimo 3 referencias."


# ---------- Servidor ----------

def test_health(client):
    data = client.get("/api/health").get_json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["ai_enabled"] is False


def test_inicio_sin_sesion_redirige_a_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_archivos_estaticos(client):
    assert client.get("/login").status_code == 200
    assert client.get("/static/css/styles.css").status_code == 200
    assert client.get("/static/js/script.js").status_code == 200
    assert client.get("/static/js/login.js").status_code == 200
    assert client.get("/app.py").status_code == 404  # no expone el código
    assert client.get("/static/../app.py").status_code == 404
    assert client.get("/backend/database.py").status_code == 404


# ---------- Autenticación ----------

def test_registro_inicia_sesion(client):
    response = register(client)
    assert response.status_code == 201
    assert response.get_json()["user"]["email"] == "ana@example.com"
    assert "password_hash" not in response.get_json()["user"]
    assert client.get("/api/auth/me").status_code == 200


def test_registro_validaciones(client):
    assert register(client, email="no-es-correo").status_code == 400
    assert register(client, password="corta").status_code == 400
    assert register(client, nombre="").status_code == 400


def test_registro_correo_duplicado(client):
    register(client)
    assert register(client, email="ANA@example.com").status_code == 409


def test_login_y_logout(client):
    register(client)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401

    bad = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "mala1234"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "secreta123"})
    assert ok.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_rutas_protegidas_sin_sesion(client):
    assert client.post("/api/analyze", json={"instructions": "x"}).status_code == 401
    assert client.get("/api/analyses").status_code == 401
    assert client.patch("/api/tasks/1", json={"completada": True}).status_code == 401


# ---------- Análisis ----------

def test_analisis_vacio(logged_client):
    assert logged_client.post("/api/analyze", json={"instructions": "   "}).status_code == 400
    assert logged_client.post("/api/analyze", data="no json").status_code == 400


def test_analisis_demasiado_largo(logged_client):
    response = logged_client.post("/api/analyze", json={"instructions": "a" * 10_001})
    assert response.status_code == 413


def test_analisis_se_guarda_y_aparece_en_historial(logged_client):
    response = logged_client.post("/api/analyze", json={"instructions": INSTRUCCIONES})
    assert response.status_code == 201
    analysis = response.get_json()["analysis"]

    assert analysis["metodo"] == "reglas"
    assert analysis["objetivo"] == "Elaborar un ensayo"
    assert any("PDF" in r for r in analysis["requisitos"])
    assert all(t["completada"] is False for t in analysis["tareas"])

    history = logged_client.get("/api/analyses").get_json()["analyses"]
    assert len(history) == 1
    assert history[0]["id"] == analysis["id"]
    assert history[0]["total_tareas"] == len(analysis["tareas"])

    detail = logged_client.get(f"/api/analyses/{analysis['id']}").get_json()["analysis"]
    assert detail["instrucciones"] == INSTRUCCIONES


def test_marcar_tarea(logged_client):
    analysis = logged_client.post("/api/analyze", json={"instructions": INSTRUCCIONES}).get_json()["analysis"]
    task_id = analysis["tareas"][0]["id"]

    assert logged_client.patch(f"/api/tasks/{task_id}", json={"completada": True}).status_code == 200
    assert logged_client.patch(f"/api/tasks/{task_id}", json={"completada": "si"}).status_code == 400

    history = logged_client.get("/api/analyses").get_json()["analyses"]
    assert history[0]["tareas_completadas"] == 1


def test_eliminar_analisis(logged_client):
    analysis_id = logged_client.post("/api/analyze", json={"instructions": INSTRUCCIONES}).get_json()["analysis"]["id"]
    assert logged_client.delete(f"/api/analyses/{analysis_id}").status_code == 200
    assert logged_client.get(f"/api/analyses/{analysis_id}").status_code == 404
    assert logged_client.get("/api/analyses").get_json()["analyses"] == []


def test_un_usuario_no_ve_datos_de_otro(app):
    ana = app.test_client()
    register(ana)
    analysis = ana.post("/api/analyze", json={"instructions": INSTRUCCIONES}).get_json()["analysis"]

    beto = app.test_client()
    register(beto, email="beto@example.com", nombre="Beto")
    assert beto.get("/api/analyses").get_json()["analyses"] == []
    assert beto.get(f"/api/analyses/{analysis['id']}").status_code == 404
    assert beto.delete(f"/api/analyses/{analysis['id']}").status_code == 404
    task_id = analysis["tareas"][0]["id"]
    assert beto.patch(f"/api/tasks/{task_id}", json={"completada": True}).status_code == 404
