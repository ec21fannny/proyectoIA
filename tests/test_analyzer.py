"""Pruebas del motor de reglas y del respaldo cuando falla la IA."""

from backend import analyzer

EJEMPLO = """Elaborar un reporte de investigación sobre una problemática tecnológica.
El documento debe incluir portada, introducción, metodología, conclusiones
y mínimo 5 referencias en formato APA.
Entregar el viernes 30 de octubre en PDF.
Revisar ortografía."""


def test_objetivo_usa_la_oracion_con_verbo_de_accion():
    assert analyzer.identify_objective(EJEMPLO).startswith("Elaborar un reporte")


def test_objetivo_sin_verbo_usa_la_primera_oracion():
    assert analyzer.identify_objective("Tema libre. Algo más.") == "Tema libre"


def test_requisitos_detectados():
    req = " ".join(analyzer.identify_requirements(EJEMPLO))
    assert "PDF" in req
    assert "APA" in req
    assert "mínimo 5 referencias" in req
    assert "Posible fecha de entrega: viernes 30 de octubre." in req  # sin "en PDF"
    assert "portada" in req and "metodología" in req


def test_sin_requisitos_da_mensaje_de_revision():
    req = analyzer.identify_requirements("hola")
    assert len(req) == 1 and "No se detectaron requisitos" in req[0]


def test_tareas_sin_duplicados_y_con_revision_final():
    tareas = analyzer.generate_tasks(EJEMPLO)
    assert len(tareas) == len(set(tareas))
    assert tareas[-1].startswith("Comparar el resultado final")
    assert "Reunir las referencias o fuentes necesarias." in tareas


def test_advertencia_fecha_imprecisa_y_sin_rubrica():
    adv = " ".join(analyzer.detect_ambiguities("Entregar la próxima semana un ensayo."))
    assert "fecha exacta" in adv
    assert "No se detectó una fecha clara" in adv
    assert "criterios de evaluación" in adv


def test_fecha_numerica_cuenta_como_fecha():
    adv = " ".join(analyzer.detect_ambiguities("Entregar el 15/11 según la rúbrica."))
    assert "No se detectó una fecha clara" not in adv
    assert "criterios de evaluación" not in adv


def test_sin_api_key_usa_reglas(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert analyzer.analyze(EJEMPLO)["metodo"] == "reglas"


def test_con_api_key_usa_ia(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")
    falso = {"objetivo": "X", "requisitos": [], "tareas": ["Hacer X"],
             "advertencias": [], "metodo": "ia"}
    monkeypatch.setattr(analyzer, "analyze_with_ai", lambda text: falso)
    assert analyzer.analyze(EJEMPLO)["metodo"] == "ia"


def test_si_la_ia_falla_se_usan_reglas(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "clave-de-prueba")

    def falla(_text):
        raise ConnectionError("sin red")

    monkeypatch.setattr(analyzer, "analyze_with_ai", falla)
    resultado = analyzer.analyze(EJEMPLO)
    assert resultado["metodo"] == "reglas"
    assert "IA no respondió" in resultado["advertencias"][-1]


class _ClienteFalso:
    """Imita anthropic.Anthropic para probar analyze_with_ai sin red."""

    def __init__(self, respuesta):
        self.llamadas = []
        cliente = self

        class _Messages:
            def parse(self, **kwargs):
                cliente.llamadas.append(kwargs)
                return respuesta

        class _Beta:
            messages = _Messages()

        self.beta = _Beta()


def test_analyze_with_ai_convierte_la_respuesta(monkeypatch):
    import anthropic
    from types import SimpleNamespace

    salida = analyzer.AIAnalysis(objetivo="Escribir un ensayo", requisitos=["PDF"],
                                 tareas=["Investigar", "Redactar"], advertencias=[])
    falso = _ClienteFalso(SimpleNamespace(stop_reason="end_turn", parsed_output=salida))
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: falso)

    resultado = analyzer.analyze_with_ai("Escribir un ensayo en PDF")
    assert resultado == {"objetivo": "Escribir un ensayo", "requisitos": ["PDF"],
                         "tareas": ["Investigar", "Redactar"], "advertencias": [],
                         "metodo": "ia"}
    llamada = falso.llamadas[0]
    assert llamada["output_format"] is analyzer.AIAnalysis
    assert llamada["messages"][0]["content"] == "Escribir un ensayo en PDF"


def test_analyze_with_ai_rechazo_lanza_error(monkeypatch):
    import anthropic
    import pytest
    from types import SimpleNamespace

    falso = _ClienteFalso(SimpleNamespace(stop_reason="refusal", parsed_output=None))
    monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: falso)
    with pytest.raises(RuntimeError):
        analyzer.analyze_with_ai("texto")
