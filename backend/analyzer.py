"""Análisis de instrucciones académicas.

Dos motores con la misma salida:
  * analyze_with_rules: reglas de texto (siempre disponible, sin costo).
  * analyze_with_ai:    modelo de lenguaje de Anthropic (Claude), si hay API key.

analyze() usa la IA cuando está configurada y, si falla, vuelve a las reglas.
"""

import logging
import os
import re

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

DAYS = r"lunes|martes|miércoles|miercoles|jueves|viernes|sábado|sabado|domingo"
MONTHS = (
    r"enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|octubre|noviembre|diciembre"
)

SECTIONS = [
    "portada", "introducción", "introduccion", "objetivos", "metodología",
    "metodologia", "conclusiones", "bibliografía", "bibliografia", "referencias",
]

POSSIBLE_TASKS = [
    ("Identificar el objetivo de la actividad.",
     ["objetivo", "propósito", "proposito"]),
    ("Preparar las secciones o apartados solicitados.",
     ["portada", "introducción", "introduccion", "metodología", "metodologia", "conclusiones"]),
    ("Reunir las referencias o fuentes necesarias.",
     ["referencias", "bibliografía", "bibliografia", "fuentes"]),
    ("Preparar el documento o producto solicitado.",
     ["reporte", "documento", "proyecto", "investigación", "investigacion",
      "presentación", "presentacion"]),
    ("Confirmar la fecha y el formato de entrega.",
     ["entregar", "entrega", "viernes", "lunes", "formato"]),
    ("Revisar la ortografía y los requisitos antes de entregar.",
     ["revisar", "ortografía", "ortografia", "completas"]),
]

VAGUE_DATES = [
    "próximo viernes", "proximo viernes", "la próxima semana", "la proxima semana",
    "lo antes posible", "cuando se pueda", "a la brevedad",
]


# --------------------------------------------------------------------------
# Motor 1: reglas
# --------------------------------------------------------------------------

def identify_objective(text):
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]
    action = re.compile(
        r"\b(elaborar|realizar|desarrollar|crear|investigar|diseñar|construir|"
        r"presentar|entregar|analizar)\b",
        re.IGNORECASE,
    )
    for sentence in sentences:
        if action.search(sentence):
            return sentence
    return sentences[0] if sentences else "No se pudo identificar un objetivo."


def identify_requirements(text):
    requirements = []
    lower = text.lower()

    if re.search(r"\bpdf\b", text, re.IGNORECASE):
        requirements.append("Formato PDF mencionado.")
    if re.search(r"\bapa\b", text, re.IGNORECASE):
        requirements.append("Formato APA mencionado.")

    refs = re.search(
        r"\b(?:mínimo|minimo|al menos)\s+\d+\s+(?:referencias|fuentes)\b",
        text, re.IGNORECASE,
    )
    if refs:
        requirements.append(f"Cantidad de referencias: {refs.group(0)}.")

    # Día de la semana con fecha opcional ("viernes 30 de octubre"), sin el resto
    # de la oración ("... en PDF").
    date = re.search(
        rf"\b(?:{DAYS})\b(?:\s+\d{{1,2}}(?:\s+de\s+(?:{MONTHS}))?)?",
        text, re.IGNORECASE,
    )
    if date:
        requirements.append(
            f"Posible fecha de entrega: {date.group(0).strip()}. Confirma la fecha exacta."
        )

    found = list(dict.fromkeys(s for s in SECTIONS if s in lower))
    if found:
        requirements.append("Apartados mencionados: " + ", ".join(found) + ".")

    if not requirements:
        requirements.append(
            "No se detectaron requisitos mediante las reglas actuales. "
            "Revisa las instrucciones manualmente."
        )
    return requirements


def generate_tasks(text):
    lower = text.lower()
    tasks = [label for label, keywords in POSSIBLE_TASKS
             if any(k in lower for k in keywords)]
    tasks.append("Comparar el resultado final con las instrucciones originales.")
    return list(dict.fromkeys(tasks))


def detect_ambiguities(text):
    warnings = []
    lower = text.lower()

    if any(phrase in lower for phrase in VAGUE_DATES):
        warnings.append(
            "Confirma la fecha exacta de entrega; se detectó una expresión "
            "de tiempo poco precisa."
        )

    has_date = (
        re.search(rf"\b({DAYS})\b", text, re.IGNORECASE)
        or re.search(rf"\b\d{{1,2}}\s+de\s+({MONTHS})\b", text, re.IGNORECASE)
        or re.search(r"\b\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?\b", text)
    )
    if not has_date:
        warnings.append(
            "No se detectó una fecha clara de entrega. "
            "Comprueba si tu profesor indicó un plazo."
        )

    if not re.search(
        r"rúbrica|rubrica|criterios de evaluación|criterios de evaluacion|"
        r"porcentaje|puntuación|puntuacion",
        text, re.IGNORECASE,
    ):
        warnings.append(
            "No se detectaron criterios de evaluación explícitos. "
            "Revisa si existe una rúbrica o una lista de requisitos."
        )

    if not warnings:
        warnings.append(
            "No se detectaron ambigüedades con las reglas actuales. "
            "Esto no garantiza que las instrucciones estén completas."
        )
    return warnings


def analyze_with_rules(text):
    return {
        "objetivo": identify_objective(text),
        "requisitos": identify_requirements(text),
        "tareas": generate_tasks(text),
        "advertencias": detect_ambiguities(text),
        "metodo": "reglas",
    }


# --------------------------------------------------------------------------
# Motor 2: inteligencia artificial (Claude, de Anthropic)
# --------------------------------------------------------------------------

DEFAULT_MODEL = "claude-opus-5-5"

SYSTEM_PROMPT = """Eres ClariCopilot, un asistente que ayuda a estudiantes \
universitarios a entender las instrucciones de una actividad académica.

A partir del texto que pega el estudiante, devuelve:
- objetivo: una sola oración clara con lo que se debe entregar o lograr.
- requisitos: requisitos concretos mencionados (formato, extensión, apartados, \
número de referencias, estilo de citas, fecha, medio de entrega). Solo lo que \
aparece en el texto; no inventes requisitos.
- tareas: pasos accionables y ordenados para completar la actividad, de 4 a 10, \
cada uno empezando con un verbo en infinitivo.
- advertencias: ambigüedades o datos faltantes que el estudiante debería \
confirmar con su profesor (fecha imprecisa, sin rúbrica, extensión no \
indicada, etc.). Lista vacía si no hay.

Escribe todo en español, con frases breves."""


class AIAnalysis(BaseModel):
    objetivo: str = Field(description="Objetivo de la actividad en una oración")
    requisitos: list[str]
    tareas: list[str]
    advertencias: list[str]


def ai_enabled():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def analyze_with_ai(text):
    import anthropic  # importado aquí para que las reglas funcionen sin el paquete

    client = anthropic.Anthropic(timeout=60.0)
    response = client.beta.messages.parse(
        model=os.environ.get("CLARICOPILOT_MODEL", DEFAULT_MODEL),
        max_tokens=16000,
        # Tarea de extracción sencilla: esfuerzo bajo = más rápido y barato.
        output_config={"effort": "low"},
        # Si el modelo rechaza la petición, el servidor reintenta con otro modelo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
        output_format=AIAnalysis,
    )

    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"El modelo no devolvió un análisis ({response.stop_reason}).")

    result = response.parsed_output.model_dump()
    if not result["tareas"]:
        raise RuntimeError("El modelo devolvió un análisis sin tareas.")
    result["metodo"] = "ia"
    return result


def analyze(text):
    """Analiza con IA si está configurada; si no, o si falla, con reglas."""
    if ai_enabled():
        try:
            return analyze_with_ai(text)
        except Exception:  # noqa: BLE001 - cualquier falla de la IA usa las reglas
            log.exception("Falló el análisis con IA; se usan las reglas.")
            result = analyze_with_rules(text)
            result["advertencias"].append(
                "El servicio de IA no respondió; este resultado se generó con reglas."
            )
            return result
    return analyze_with_rules(text)
