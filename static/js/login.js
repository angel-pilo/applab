document.addEventListener("DOMContentLoaded", function () {
    const passwordInput = document.getElementById("password");
    const passwordToggle = document.querySelector(".auth-password-toggle");
    const loginForm = document.querySelector(".auth-form");
    const loading = document.getElementById("auth-loading");

    loginForm?.addEventListener("submit", function (event) {
        setTimeout(function () {
            if (event.defaultPrevented) return;
            loading?.classList.add("is-visible");
            loading?.setAttribute("aria-hidden", "false");
        }, 0);
    });

    window.addEventListener("pageshow", function () {
        loading?.classList.remove("is-visible");
        loading?.setAttribute("aria-hidden", "true");
    });

    if (passwordInput && passwordToggle) {
        passwordToggle.addEventListener("click", function () {
            const showPassword = passwordInput.type === "password";
            passwordInput.type = showPassword ? "text" : "password";
            passwordToggle.textContent = showPassword ? "Ocultar" : "Mostrar";
            passwordToggle.setAttribute("aria-label", showPassword ? "Ocultar contraseña" : "Mostrar contraseña");
            passwordToggle.setAttribute("aria-pressed", String(showPassword));
            passwordInput.focus();
        });
    }

    setTimeout(function () {
        document.querySelectorAll(".auth-alert").forEach(function (flashMessage) {
            flashMessage.style.transition = "opacity 0.5s";
            flashMessage.style.opacity = "0";
            setTimeout(() => flashMessage.style.display = "none", 500);
        });
    }, 3500);
});
