const instructionsInput = document.getElementById("instructions");
const analyzeButton = document.getElementById("analyzeButton");
const exampleButton = document.getElementById("exampleButton");
const clearButton = document.getElementById("clearButton");
const logoutButton = document.getElementById("logoutButton");

const emptyState = document.getElementById("emptyState");
const results = document.getElementById("results");
const objectiveOutput = document.getElementById("objective");
const requirementsOutput = document.getElementById("requirements");
const warningsOutput = document.getElementById("warnings");
const taskList = document.getElementById("taskList");
const methodBadge = document.getElementById("methodBadge");
const resultDate = document.getElementById("resultDate");
const statusMessage = document.getElementById("statusMessage");

const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const progressPercent = document.getElementById("progressPercent");

const historyList = document.getElementById("historyList");
const historyEmpty = document.getElementById("historyEmpty");

const ANALYZE_LABEL = "Organizar instrucciones →";

// Instrucción de ejemplo para probar el prototipo.
const exampleInstructions = `
Elaborar un reporte de investigación sobre una problemática tecnológica.

El documento debe incluir portada, introducción, planteamiento
del problema, objetivo general, tres objetivos específicos,
metodología, conclusiones y mínimo 5 referencias en formato APA.

Entregar el viernes 30 de octubre en PDF.
Revisar ortografía y comprobar que todas las secciones estén completas.
`;

// ---------- Comunicación con el servidor ----------

async function api(path, options = {}) {
    const response = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options
    });

    if (response.status === 401) {
        window.location.href = "/login";
        throw new Error("Sesión expirada.");
    }

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || "Error del servidor.");
    }
    return data;
}

function showStatus(message) {
    statusMessage.textContent = message;
    statusMessage.hidden = !message;
}

// ---------- Inicio ----------

async function init() {
    try {
        const [{ user }, health] = await Promise.all([
            api("/api/auth/me"),
            api("/api/health")
        ]);

        document.getElementById("userName").textContent = user.nombre;
        document.getElementById("userEmail").textContent = user.email;
        document.getElementById("userInitial").textContent =
            user.nombre.charAt(0).toUpperCase();
        document.getElementById("engineBadge").textContent =
            health.ai_enabled ? "Motor: IA" : "Motor: reglas";

        await loadHistory();
    } catch (error) {
        showStatus("No se pudo conectar con el servidor: " + error.message);
    }
}

// ---------- Botones ----------

exampleButton.addEventListener("click", () => {
    instructionsInput.value = exampleInstructions.trim();
});

clearButton.addEventListener("click", () => {
    instructionsInput.value = "";
    emptyState.hidden = false;
    results.hidden = true;
    taskList.replaceChildren();
    showStatus("");
    updateProgress();
});

logoutButton.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST" });
    window.location.href = "/login";
});

analyzeButton.addEventListener("click", async () => {
    const text = instructionsInput.value.trim();

    if (!text) {
        alert("Primero escribe o pega las instrucciones de tu actividad.");
        instructionsInput.focus();
        return;
    }

    analyzeButton.disabled = true;
    analyzeButton.textContent = "Analizando...";
    showStatus("");

    try {
        const data = await api("/api/analyze", {
            method: "POST",
            body: JSON.stringify({ instructions: text })
        });
        showAnalysis(data.analysis);
        await loadHistory();
    } catch (error) {
        showStatus("No se pudo analizar: " + error.message);
    } finally {
        analyzeButton.disabled = false;
        analyzeButton.textContent = ANALYZE_LABEL;
    }
});

// ---------- Mostrar resultados ----------

function fillList(element, items) {
    element.replaceChildren(
        ...items.map(text => {
            const item = document.createElement("li");
            item.textContent = text;
            return item;
        })
    );
}

function showAnalysis(analysis) {
    objectiveOutput.textContent = analysis.objetivo;
    fillList(requirementsOutput, analysis.requisitos);
    fillList(
        warningsOutput,
        analysis.advertencias.length
            ? analysis.advertencias
            : ["No hay puntos pendientes por confirmar."]
    );
    showTasks(analysis.tareas);

    methodBadge.textContent =
        analysis.metodo === "ia" ? "Analizado con IA" : "Analizado con reglas";
    methodBadge.dataset.method = analysis.metodo;
    resultDate.textContent = "Guardado el " + analysis.creado_en;

    emptyState.hidden = true;
    results.hidden = false;
    updateProgress();
}

function showTasks(tasks) {
    taskList.replaceChildren();

    tasks.forEach(task => {
        const label = document.createElement("label");
        label.className = "task-item";
        label.classList.toggle("completed", task.completada);

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = task.completada;

        const text = document.createElement("span");
        text.textContent = task.descripcion;

        checkbox.addEventListener("change", async () => {
            label.classList.toggle("completed", checkbox.checked);
            updateProgress();

            try {
                await api("/api/tasks/" + task.id, {
                    method: "PATCH",
                    body: JSON.stringify({ completada: checkbox.checked })
                });
                await loadHistory();
            } catch (error) {
                // Revertir si no se pudo guardar.
                checkbox.checked = !checkbox.checked;
                label.classList.toggle("completed", checkbox.checked);
                updateProgress();
                showStatus("No se pudo guardar la tarea: " + error.message);
            }
        });

        label.append(checkbox, text);
        taskList.appendChild(label);
    });
}

function updateProgress() {
    const checkboxes = [...taskList.querySelectorAll('input[type="checkbox"]')];
    const completed = checkboxes.filter(checkbox => checkbox.checked).length;
    const total = checkboxes.length;
    const percentage = total > 0 ? Math.round((completed / total) * 100) : 0;

    progressBar.style.width = percentage + "%";
    progressText.textContent = completed + " de " + total + " tareas completadas";
    progressPercent.textContent = percentage + "%";
}

// ---------- Historial ----------

async function loadHistory() {
    const { analyses } = await api("/api/analyses");

    historyEmpty.hidden = analyses.length > 0;
    historyList.replaceChildren(...analyses.map(historyItem));
}

function historyItem(analysis) {
    const item = document.createElement("li");
    item.className = "history-item";

    const open = document.createElement("button");
    open.type = "button";
    open.className = "history-open";

    const title = document.createElement("strong");
    title.textContent = analysis.objetivo;

    const meta = document.createElement("span");
    meta.textContent =
        analysis.creado_en + " · " +
        (analysis.metodo === "ia" ? "IA" : "reglas") + " · " +
        analysis.tareas_completadas + "/" + analysis.total_tareas + " tareas";

    open.append(title, meta);
    open.addEventListener("click", async () => {
        try {
            const data = await api("/api/analyses/" + analysis.id);
            instructionsInput.value = data.analysis.instrucciones;
            showAnalysis(data.analysis);
            document.getElementById("resultado").scrollIntoView();
        } catch (error) {
            showStatus("No se pudo abrir el análisis: " + error.message);
        }
    });

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "history-delete";
    remove.textContent = "Eliminar";
    remove.setAttribute("aria-label", "Eliminar análisis: " + analysis.objetivo);
    remove.addEventListener("click", async () => {
        if (!confirm("¿Eliminar este análisis del historial?")) {
            return;
        }
        try {
            await api("/api/analyses/" + analysis.id, { method: "DELETE" });
            await loadHistory();
        } catch (error) {
            showStatus("No se pudo eliminar: " + error.message);
        }
    });

    item.append(open, remove);
    return item;
}

init();
