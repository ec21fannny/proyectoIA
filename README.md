# ClariCopilot

Asistente académico que ayuda a estudiantes a entender las instrucciones de una
actividad: identifica el objetivo, los requisitos, genera una lista de tareas y
señala los puntos ambiguos que conviene confirmar con el profesor.

Proyecto académico — Instituto Tecnológico de Tijuana, Ingeniería en Sistemas
Computacionales.

## Qué se puede hacer (versión 0.2)

- Crear una cuenta e iniciar sesión.
- Pegar las instrucciones de una actividad y obtener objetivo, requisitos,
  tareas y advertencias.
- Marcar tareas como completadas (el avance se guarda).
- Consultar, reabrir y eliminar análisis anteriores desde el historial.
- Análisis con inteligencia artificial (Claude, de Anthropic) si se configura
  una API key; sin ella, se usa el motor de reglas.

## Arquitectura

```
Navegador (HTML + CSS + JS)
        │  fetch JSON + cookie de sesión
        ▼
Flask (app.py) ── backend/analyzer.py ──► Motor de reglas (siempre)
        │                            └──► API de Claude (opcional)
        ▼
backend/database.py ──► SQLite (claricopilot.db)
```

## Estructura del proyecto

```
proyectoIA/
├── app.py                  Servidor Flask: rutas, sesión y validación de entradas
├── backend/
│   ├── analyzer.py         Motores de análisis (reglas e IA) con respaldo automático
│   ├── database.py         Consultas a SQLite
│   └── schema.sql          Tablas: usuarios, analisis, requisitos, tareas, advertencias
├── frontend/
│   ├── index.html          Pantalla principal (análisis, tareas, historial)
│   ├── login.html          Inicio de sesión y registro
│   └── static/
│       ├── css/styles.css
│       └── js/
│           ├── script.js   Lógica de la pantalla principal
│           └── login.js    Lógica del acceso
├── tests/                  Pruebas automáticas (pytest)
├── docs/evidencias/        Capturas de pantalla del Avance 2
├── requirements.txt
└── .env.example            Variables de entorno (clave de IA, modelo, SECRET_KEY)
```

`claricopilot.db` se crea al iniciar el servidor y no se sube al repositorio.

## Instalación

Requiere Python 3.10 o superior.

```bash
python -m venv .venv
```

```bash
.venv\Scripts\activate
```

(En macOS o Linux: `source .venv/bin/activate`.)

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python app.py
```

Abre http://127.0.0.1:5000, crea una cuenta y pulsa **Probar ejemplo**.
La base de datos `claricopilot.db` se crea sola la primera vez.

### Activar la inteligencia artificial (opcional)

Define la variable `ANTHROPIC_API_KEY` antes de iniciar el servidor
(ver `.env.example`). En PowerShell:

```powershell
$env:ANTHROPIC_API_KEY = "tu-clave"
python app.py
```

La insignia "Motor: IA" aparece en la parte superior. Si la API falla, el
análisis se hace con reglas y se avisa al usuario.

## Pruebas

```bash
python -m pytest -v
```

Las pruebas usan una base de datos temporal y nunca llaman a la API real.

## API

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado del servidor, de la BD y del motor de IA |
| POST | `/api/auth/register` | Crear cuenta `{nombre, email, password}` |
| POST | `/api/auth/login` | Iniciar sesión `{email, password}` |
| POST | `/api/auth/logout` | Cerrar sesión |
| GET | `/api/auth/me` | Usuario actual |
| POST | `/api/analyze` | Analizar y guardar `{instructions}` |
| GET | `/api/analyses` | Historial del usuario |
| GET | `/api/analyses/<id>` | Detalle de un análisis |
| DELETE | `/api/analyses/<id>` | Eliminar un análisis |
| PATCH | `/api/tasks/<id>` | Marcar tarea `{completada: true/false}` |

Todas las rutas excepto `health`, `register` y `login` requieren sesión.
