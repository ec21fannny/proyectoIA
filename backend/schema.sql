-- Esquema de la base de datos de ClariCopilot (SQLite).
-- Se ejecuta automáticamente al iniciar la aplicación si las tablas no existen.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL,
    email         TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    creado_en     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Cada vez que un usuario organiza unas instrucciones se guarda un análisis.
CREATE TABLE IF NOT EXISTS analisis (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    instrucciones TEXT    NOT NULL,
    objetivo      TEXT    NOT NULL,
    metodo        TEXT    NOT NULL CHECK (metodo IN ('reglas', 'ia')),
    creado_en     TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS requisitos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    analisis_id INTEGER NOT NULL REFERENCES analisis(id) ON DELETE CASCADE,
    descripcion TEXT    NOT NULL,
    orden       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tareas (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    analisis_id INTEGER NOT NULL REFERENCES analisis(id) ON DELETE CASCADE,
    descripcion TEXT    NOT NULL,
    orden       INTEGER NOT NULL,
    completada  INTEGER NOT NULL DEFAULT 0 CHECK (completada IN (0, 1))
);

CREATE TABLE IF NOT EXISTS advertencias (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    analisis_id INTEGER NOT NULL REFERENCES analisis(id) ON DELETE CASCADE,
    descripcion TEXT    NOT NULL,
    orden       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analisis_usuario ON analisis(usuario_id, creado_en);
CREATE INDEX IF NOT EXISTS idx_tareas_analisis  ON tareas(analisis_id);
