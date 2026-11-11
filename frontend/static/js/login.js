const loginTab = document.getElementById("loginTab");
const registerTab = document.getElementById("registerTab");
const form = document.getElementById("authForm");
const nameField = document.getElementById("nameField");
const passwordInput = document.getElementById("password");
const passwordHint = document.getElementById("passwordHint");
const authError = document.getElementById("authError");
const submitButton = document.getElementById("submitButton");

let mode = "login";

function setMode(newMode) {
    mode = newMode;
    const isRegister = mode === "register";

    loginTab.classList.toggle("active", !isRegister);
    registerTab.classList.toggle("active", isRegister);
    loginTab.setAttribute("aria-selected", String(!isRegister));
    registerTab.setAttribute("aria-selected", String(isRegister));

    nameField.hidden = !isRegister;
    passwordHint.hidden = !isRegister;
    passwordInput.autocomplete = isRegister ? "new-password" : "current-password";
    submitButton.textContent = isRegister ? "Crear cuenta →" : "Entrar →";
    authError.hidden = true;
}

loginTab.addEventListener("click", () => setMode("login"));
registerTab.addEventListener("click", () => setMode("register"));

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    authError.hidden = true;

    const payload = {
        email: form.email.value.trim(),
        password: form.password.value
    };
    if (mode === "register") {
        payload.nombre = form.nombre.value.trim();
    }

    submitButton.disabled = true;
    try {
        const response = await fetch(`/api/auth/${mode}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || "No se pudo completar la solicitud.");
        }
        window.location.href = "/";
    } catch (error) {
        authError.textContent = error.message === "Failed to fetch"
            ? "No se pudo conectar con el servidor."
            : error.message;
        authError.hidden = false;
    } finally {
        submitButton.disabled = false;
    }
});
