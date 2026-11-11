"""Servidor Flask de ClariCopilot."""

import os
import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import (Flask, jsonify, redirect, request, send_from_directory,
                   session)
from werkzeug.security import check_password_hash, generate_password_hash

from backend import analyzer
from backend import database as db

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
MAX_INSTRUCTIONS = 10_000
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def error(message, status):
    return jsonify({"status": "error", "message": message}), status


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return error("Inicia sesión para continuar.", 401)
        return view(*args, **kwargs)
    return wrapper


def create_app(config=None):
    # CSS y JS se sirven desde frontend/static en la ruta /static/...
    app = Flask(
        __name__,
        static_folder=str(FRONTEND_DIR / "static"),
        static_url_path="/static",
    )
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-cambia-esta-clave"),
        DATABASE=os.environ.get("DATABASE", str(BASE_DIR / "claricopilot.db")),
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if config:
        app.config.update(config)

    db.init_db(app.config["DATABASE"])
    app.teardown_appcontext(db.close_db)

    # ---------- Páginas ----------

    @app.get("/")
    def home():
        if "user_id" not in session:
            return redirect("/login")
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/login")
    def login_page():
        if "user_id" in session:
            return redirect("/")
        return send_from_directory(FRONTEND_DIR, "login.html")

    # ---------- Estado del servidor ----------

    @app.get("/api/health")
    def health():
        try:
            db.get_db().execute("SELECT 1")
            database_ok = True
        except sqlite3.Error:
            database_ok = False
        return jsonify({
            "status": "ok" if database_ok else "error",
            "message": "El servidor de ClariCopilot funciona.",
            "database": "ok" if database_ok else "error",
            "ai_enabled": analyzer.ai_enabled(),
        }), 200 if database_ok else 503

    # ---------- Autenticación ----------

    @app.post("/api/auth/register")
    def register():
        data = request.get_json(silent=True) or {}
        nombre = str(data.get("nombre", "")).strip()
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        if not nombre or not email or not password:
            return error("Completa nombre, correo y contraseña.", 400)
        if not EMAIL_RE.match(email):
            return error("El correo no tiene un formato válido.", 400)
        if len(password) < 8:
            return error("La contraseña debe tener al menos 8 caracteres.", 400)
        if db.find_user_by_email(email):
            return error("Ya existe una cuenta con ese correo.", 409)

        user_id = db.create_user(nombre, email, generate_password_hash(password))
        session.clear()
        session["user_id"] = user_id
        return jsonify({"status": "ok", "user": dict(db.find_user_by_id(user_id))}), 201

    @app.post("/api/auth/login")
    def login():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email", "")).strip().lower()
        password = str(data.get("password", ""))

        user = db.find_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            return error("Correo o contraseña incorrectos.", 401)

        session.clear()
        session["user_id"] = user["id"]
        return jsonify({"status": "ok", "user": dict(db.find_user_by_id(user["id"]))})

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"status": "ok"})

    @app.get("/api/auth/me")
    @login_required
    def me():
        user = db.find_user_by_id(session["user_id"])
        if user is None:
            session.clear()
            return error("La sesión ya no es válida.", 401)
        return jsonify({"status": "ok", "user": dict(user)})

    # ---------- Análisis ----------

    @app.post("/api/analyze")
    @login_required
    def analyze():
        data = request.get_json(silent=True) or {}
        instructions = str(data.get("instructions", "")).strip()

        if not instructions:
            return error("Escribe unas instrucciones para analizar.", 400)
        if len(instructions) > MAX_INSTRUCTIONS:
            return error(
                f"Las instrucciones superan el límite de {MAX_INSTRUCTIONS} caracteres.",
                413,
            )

        result = analyzer.analyze(instructions)
        analysis_id = db.save_analysis(session["user_id"], instructions, result)
        return jsonify({
            "status": "ok",
            "analysis": db.get_analysis(session["user_id"], analysis_id),
        }), 201

    @app.get("/api/analyses")
    @login_required
    def analyses():
        return jsonify({"status": "ok", "analyses": db.list_analyses(session["user_id"])})

    @app.get("/api/analyses/<int:analysis_id>")
    @login_required
    def analysis_detail(analysis_id):
        analysis = db.get_analysis(session["user_id"], analysis_id)
        if analysis is None:
            return error("Análisis no encontrado.", 404)
        return jsonify({"status": "ok", "analysis": analysis})

    @app.delete("/api/analyses/<int:analysis_id>")
    @login_required
    def analysis_delete(analysis_id):
        if not db.delete_analysis(session["user_id"], analysis_id):
            return error("Análisis no encontrado.", 404)
        return jsonify({"status": "ok"})

    @app.patch("/api/tasks/<int:task_id>")
    @login_required
    def task_update(task_id):
        data = request.get_json(silent=True) or {}
        if not isinstance(data.get("completada"), bool):
            return error("Indica 'completada' como true o false.", 400)
        if not db.set_task_completed(session["user_id"], task_id, data["completada"]):
            return error("Tarea no encontrada.", 404)
        return jsonify({"status": "ok"})

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
