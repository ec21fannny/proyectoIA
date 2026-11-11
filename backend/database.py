"""Acceso a la base de datos SQLite de ClariCopilot."""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_db():
    """Devuelve la conexión de la petición actual (una por petición)."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(database_path):
    """Crea las tablas si todavía no existen."""
    with sqlite3.connect(database_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


# ---------- Usuarios ----------

def create_user(nombre, email, password_hash):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO usuarios (nombre, email, password_hash) VALUES (?, ?, ?)",
        (nombre, email, password_hash),
    )
    db.commit()
    return cursor.lastrowid


def find_user_by_email(email):
    return get_db().execute(
        "SELECT * FROM usuarios WHERE email = ?", (email,)
    ).fetchone()


def find_user_by_id(user_id):
    return get_db().execute(
        "SELECT id, nombre, email, creado_en FROM usuarios WHERE id = ?",
        (user_id,),
    ).fetchone()


# ---------- Análisis ----------

def save_analysis(user_id, instructions, result):
    """Guarda un análisis completo (objetivo, requisitos, tareas y advertencias)."""
    db = get_db()
    cursor = db.execute(
        "INSERT INTO analisis (usuario_id, instrucciones, objetivo, metodo) "
        "VALUES (?, ?, ?, ?)",
        (user_id, instructions, result["objetivo"], result["metodo"]),
    )
    analysis_id = cursor.lastrowid

    for table, key in (
        ("requisitos", "requisitos"),
        ("tareas", "tareas"),
        ("advertencias", "advertencias"),
    ):
        db.executemany(
            f"INSERT INTO {table} (analisis_id, descripcion, orden) VALUES (?, ?, ?)",
            [(analysis_id, text, i) for i, text in enumerate(result[key])],
        )

    db.commit()
    return analysis_id


def list_analyses(user_id):
    rows = get_db().execute(
        """
        SELECT a.id, a.objetivo, a.metodo, a.creado_en,
               COUNT(t.id)                AS total_tareas,
               COALESCE(SUM(t.completada), 0) AS tareas_completadas
        FROM analisis a
        LEFT JOIN tareas t ON t.analisis_id = a.id
        WHERE a.usuario_id = ?
        GROUP BY a.id
        ORDER BY a.creado_en DESC, a.id DESC
        """,
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_analysis(user_id, analysis_id):
    """Devuelve un análisis del usuario o None si no existe o es de otro usuario."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM analisis WHERE id = ? AND usuario_id = ?",
        (analysis_id, user_id),
    ).fetchone()
    if row is None:
        return None

    def texts(table):
        return [
            r["descripcion"]
            for r in db.execute(
                f"SELECT descripcion FROM {table} WHERE analisis_id = ? ORDER BY orden",
                (analysis_id,),
            )
        ]

    tasks = db.execute(
        "SELECT id, descripcion, completada FROM tareas "
        "WHERE analisis_id = ? ORDER BY orden",
        (analysis_id,),
    ).fetchall()

    return {
        "id": row["id"],
        "instrucciones": row["instrucciones"],
        "objetivo": row["objetivo"],
        "metodo": row["metodo"],
        "creado_en": row["creado_en"],
        "requisitos": texts("requisitos"),
        "advertencias": texts("advertencias"),
        "tareas": [
            {"id": t["id"], "descripcion": t["descripcion"], "completada": bool(t["completada"])}
            for t in tasks
        ],
    }


def delete_analysis(user_id, analysis_id):
    db = get_db()
    cursor = db.execute(
        "DELETE FROM analisis WHERE id = ? AND usuario_id = ?",
        (analysis_id, user_id),
    )
    db.commit()
    return cursor.rowcount > 0


def set_task_completed(user_id, task_id, completed):
    """Marca una tarea; solo si pertenece a un análisis del usuario."""
    db = get_db()
    cursor = db.execute(
        """
        UPDATE tareas SET completada = ?
        WHERE id = ?
          AND analisis_id IN (SELECT id FROM analisis WHERE usuario_id = ?)
        """,
        (1 if completed else 0, task_id, user_id),
    )
    db.commit()
    return cursor.rowcount > 0
