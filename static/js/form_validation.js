(function () {
  const INTERACTIVE_SELECTOR = "input, select, textarea";

  function validationMessage(field) {
    const label = field.closest(".admin-field, .auth-field, fieldset")
      ?.querySelector("label, legend")?.textContent?.replace("*", "").trim();
    const name = label ? `“${label}”` : "este campo";
    const validity = field.validity;

    if (validity.valueMissing) return `Completa ${name}.`;
    if (validity.typeMismatch && field.type === "email") return `Escribe un correo válido en ${name}.`;
    if (validity.patternMismatch) return `Revisa el formato solicitado en ${name}.`;
    if (validity.tooShort) return `${name} necesita al menos ${field.minLength} caracteres.`;
    if (validity.tooLong) return `${name} permite máximo ${field.maxLength} caracteres.`;
    if (validity.rangeUnderflow) return `${name} debe ser igual o mayor a ${field.min}.`;
    if (validity.rangeOverflow) return `${name} debe ser igual o menor a ${field.max}.`;
    if (validity.stepMismatch) return `Escribe un valor válido en ${name}.`;
    if (validity.badInput) return `Escribe un valor válido en ${name}.`;
    return field.validationMessage || `Revisa ${name}.`;
  }

  function fieldContainer(field) {
    if (field.type === "radio" || field.type === "checkbox") {
      return field.closest("fieldset") || field.closest(".admin-field") || field.parentElement;
    }
    return field.closest(".admin-field, .auth-field") || field.parentElement;
  }

  function feedbackFor(field, create = false) {
    const container = fieldContainer(field);
    if (!container) return null;
    let feedback = container.querySelector(":scope > .app-field-feedback");
    if (!feedback && create) {
      feedback = document.createElement("p");
      feedback.className = "app-field-feedback";
      feedback.setAttribute("role", "alert");
      container.appendChild(feedback);
    }
    return feedback;
  }

  function markInvalid(field) {
    const container = fieldContainer(field);
    field.classList.add("app-field-invalid");
    field.setAttribute("aria-invalid", "true");
    container?.classList.add("app-field-has-error");
    const feedback = feedbackFor(field, true);
    if (feedback) {
      feedback.textContent = validationMessage(field);
      if (!feedback.id) {
        feedback.id = `field-error-${field.id || field.name || Math.random().toString(16).slice(2)}`;
      }
      field.setAttribute("aria-describedby", feedback.id);
    }
  }

  function clearInvalid(field) {
    const container = fieldContainer(field);
    field.classList.remove("app-field-invalid");
    field.removeAttribute("aria-invalid");
    container?.classList.remove("app-field-has-error");
    const feedback = feedbackFor(field);
    feedback?.remove();
    if ((field.getAttribute("aria-describedby") || "").startsWith("field-error-")) {
      field.removeAttribute("aria-describedby");
    }
  }

  function controlsFor(form) {
    return Array.from(form.querySelectorAll(INTERACTIVE_SELECTOR)).filter(field => (
      !field.disabled
      && field.type !== "hidden"
      && field.type !== "submit"
      && field.type !== "button"
    ));
  }

  function validateForm(form) {
    const controls = controlsFor(form);
    const invalid = controls.filter(field => !field.checkValidity());
    controls.forEach(field => field.checkValidity() ? clearInvalid(field) : markInvalid(field));

    if (!invalid.length) return true;
    const first = invalid[0];
    const target = fieldContainer(first) || first;
    target.scrollIntoView({behavior: "smooth", block: "center"});
    window.setTimeout(() => {
      first.focus({preventScroll: true});
      first.reportValidity?.();
    }, 280);
    return false;
  }

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form").forEach(form => {
      if (form.dataset.smartValidation === "off") return;

      form.addEventListener("submit", event => {
        if (!validateForm(form)) {
          event.preventDefault();
        }
      });

      controlsFor(form).forEach(field => {
        const refresh = () => {
          if (field.checkValidity()) {
            clearInvalid(field);
            if (field.type === "radio" && field.name) {
              form.querySelectorAll(`input[type="radio"][name="${CSS.escape(field.name)}"]`)
                .forEach(clearInvalid);
            }
          } else if (field.classList.contains("app-field-invalid")) {
            markInvalid(field);
          }
        };
        field.addEventListener("input", refresh);
        field.addEventListener("change", refresh);
        field.addEventListener("blur", () => {
          if (field.value || field.classList.contains("app-field-invalid")) refresh();
        });
        field.addEventListener("invalid", event => {
          event.preventDefault();
          markInvalid(field);
        });
      });
    });
  });
})();
