document.addEventListener("DOMContentLoaded", () => {
  function confirmClinicalAction({
    eyebrow = "Confirmar operación",
    title,
    message,
    confirmText = "Continuar",
    icon = "fa-check"
  }) {
    let modal = document.getElementById("clinical-confirm-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "clinical-confirm-modal";
      modal.className = "app-flash-modal hidden";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.innerHTML = `
        <button type="button" class="app-flash-backdrop" data-clinical-cancel aria-label="Cancelar"></button>
        <div class="app-flash-dialog" role="document">
          <header class="app-flash-header">
            <span class="app-flash-icon is-info" aria-hidden="true">
              <i id="clinical-confirm-icon" class="fas fa-check"></i>
            </span>
            <div>
              <p id="clinical-confirm-eyebrow"></p>
              <h2 id="clinical-confirm-title"></h2>
            </div>
            <button type="button" class="app-flash-close" data-clinical-cancel aria-label="Cerrar">
              <i class="fas fa-times" aria-hidden="true"></i>
            </button>
          </header>
          <div class="app-flash-body">
            <p id="clinical-confirm-message"></p>
          </div>
          <footer class="app-flash-actions app-confirm-actions">
            <button type="button" class="app-confirm-secondary" data-clinical-cancel>Cancelar</button>
            <button type="button" class="app-flash-primary" id="clinical-confirm-submit"></button>
          </footer>
        </div>`;
      document.body.appendChild(modal);
    }

    modal.querySelector("#clinical-confirm-eyebrow").textContent = eyebrow;
    modal.querySelector("#clinical-confirm-title").textContent = title;
    modal.querySelector("#clinical-confirm-message").textContent = message;
    modal.querySelector("#clinical-confirm-icon").className = `fas ${icon}`;
    const submit = modal.querySelector("#clinical-confirm-submit");
    submit.textContent = confirmText;
    modal.classList.remove("hidden");
    document.body.classList.add("app-flash-open");

    return new Promise(resolve => {
      let settled = false;
      const finish = result => {
        if (settled) return;
        settled = true;
        modal.classList.add("hidden");
        document.body.classList.remove("app-flash-open");
        submit.removeEventListener("click", accept);
        modal.querySelectorAll("[data-clinical-cancel]").forEach(element => {
          element.removeEventListener("click", cancel);
        });
        document.removeEventListener("keydown", onKeydown);
        resolve(result);
      };
      const accept = () => finish(true);
      const cancel = () => finish(false);
      const onKeydown = event => {
        if (event.key === "Escape") cancel();
      };
      submit.addEventListener("click", accept);
      modal.querySelectorAll("[data-clinical-cancel]").forEach(element => {
        element.addEventListener("click", cancel);
      });
      document.addEventListener("keydown", onKeydown);
      submit.focus();
    });
  }

  const stateStyles = {
    normal: ["Normal", "bg-emerald-50 text-emerald-700"],
    alto: ["Alto", "bg-red-50 text-red-700"],
    bajo: ["Bajo", "bg-amber-50 text-amber-700"],
    fuera: ["Fuera de rango", "bg-red-50 text-red-700"],
    sin_referencia: ["Sin referencia", "bg-gray-100 text-gray-600"],
    invalido: ["Valor inválido", "bg-red-50 text-red-700"]
  };

  function evaluate(value, reference) {
    const raw = String(value ?? "").trim();
    if (!raw) return null;
    if (reference.normal !== null && reference.normal !== undefined) {
      return raw.toLowerCase() === String(reference.normal).toLowerCase() ? "normal" : "fuera";
    }
    const number = Number(raw.replace(",", "."));
    if (!Number.isFinite(number)) return "invalido";
    if (reference.min !== null && reference.min !== undefined && number < Number(reference.min)) return "bajo";
    if (reference.max !== null && reference.max !== undefined && number > Number(reference.max)) return "alto";
    return reference.min !== null || reference.max !== null ? "normal" : "sin_referencia";
  }

  function updateField(field) {
    const input = field.querySelector(".result-input");
    const badge = field.querySelector(".result-state");
    const reference = JSON.parse(field.querySelector(".result-reference").textContent);
    const state = evaluate(input.value, reference);
    badge.className = "result-state rounded-full px-2.5 py-1 text-[11px] font-semibold";
    if (!state) {
      badge.textContent = "Sin capturar";
      badge.classList.add("bg-gray-100", "text-gray-500");
      field.classList.remove("border-red-300", "border-emerald-300");
      return;
    }
    const [label, classes] = stateStyles[state];
    badge.textContent = label;
    classes.split(" ").forEach(item => badge.classList.add(item));
    field.classList.toggle("border-red-300", ["alto", "bajo", "fuera", "invalido"].includes(state));
    field.classList.toggle("border-emerald-300", state === "normal");
  }

  document.querySelectorAll(".result-field").forEach(field => {
    field.querySelector(".result-input").addEventListener("input", () => updateField(field));
    const verified = field.querySelector(".result-verified");
    verified.addEventListener("change", () => {
      const label = field.querySelector(".verification-label");
      label.textContent = verified.checked ? "Sí" : "No";
      label.className = `verification-label font-semibold ${verified.checked ? "text-emerald-700" : "text-gray-500"}`;
    });
    updateField(field);
  });

  function collectedValues(card, includeEmpty = false) {
    return Object.fromEntries(
      [...card.querySelectorAll(".result-field")]
        .map(field => [
          field.dataset.element,
          field.querySelector(".result-input").value.trim()
        ])
        .filter(([, value]) => includeEmpty || value)
    );
  }

  function collectedVerifications(card) {
    return Object.fromEntries(
      [...card.querySelectorAll(".result-field")].map(field => [
        field.dataset.element,
        field.querySelector(".result-verified").checked
      ])
    );
  }

  document.querySelectorAll(".save-draft").forEach(button => button.addEventListener("click", async () => {
    const card = button.closest(".result-study");
    const values = collectedValues(card);
    const message = card.querySelector(".result-message");
    if (!Object.keys(values).length) {
      message.className = "result-message mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-800";
      message.textContent = "Captura al menos un resultado para guardar el avance.";
      return;
    }
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Guardando...';
    try {
      const response = await fetch("/api/resultados/borrador", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({
          orden_id: Number(card.dataset.order),
          detalle_id: Number(card.dataset.detail),
          valores: values,
          verificaciones: collectedVerifications(card)
        })
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo guardar el avance.");
      message.className = "result-message mt-4 rounded-xl bg-blue-50 p-3 text-sm text-blue-700";
      message.textContent = "Avance guardado. Todavía no se descontaron reactivos.";
      setTimeout(() => window.location.reload(), 650);
    } catch (error) {
      message.className = "result-message mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700";
      message.textContent = error.message;
      button.disabled = false;
      button.innerHTML = '<i class="fas fa-bookmark mr-2"></i>Guardar avance';
    }
  }));

  document.querySelectorAll(".save-result").forEach(button => button.addEventListener("click", async () => {
    const card = button.closest(".result-study");
    const otherStudies = [...document.querySelectorAll(".result-study")].filter(item => item !== card);
    const willFinalizeOrder = otherStudies.every(item => item.dataset.completed === "true");
    const fields = [...card.querySelectorAll(".result-field")];
    const empty = fields.find(field => !field.querySelector(".result-input").value.trim());
    if (empty) {
      empty.querySelector(".result-input").focus();
      empty.classList.add("border-red-300");
      return;
    }
    if (willFinalizeOrder) {
      const accepted = await confirmClinicalAction({
        eyebrow: "Último estudio pendiente",
        title: "Completar y enviar resultados",
        message: card.dataset.verification
          ? "Se guardará esta verificación, se registrará nuevamente el consumo de reactivos y la orden completa se enviará a mostrador."
          : "Todos los estudios están capturados. Al continuar, este resultado se completará y la orden se enviará a mostrador.",
        confirmText: "Completar y enviar",
        icon: "fa-paper-plane"
      });
      if (!accepted) return;
    } else if (card.dataset.verification) {
      const accepted = await confirmClinicalAction({
        eyebrow: "Verificación analítica",
        title: "Guardar resultado verificado",
        message: "Se guardará la verificación y los reactivos asociados se descontarán nuevamente una sola vez.",
        confirmText: "Guardar verificación",
        icon: "fa-check-double"
      });
      if (!accepted) return;
    }
    const values = collectedValues(card, true);
    const message = card.querySelector(".result-message");
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Guardando...';
    try {
      const response = await fetch("/api/resultados/ejecutar", {
        method: "POST",
        headers: {"Content-Type": "application/json", "Accept": "application/json"},
        body: JSON.stringify({
          orden_id: Number(card.dataset.order),
          detalle_id: Number(card.dataset.detail),
          valores: values,
          verificaciones: collectedVerifications(card),
          verificacion_de_id: card.dataset.verification ? Number(card.dataset.verification) : null,
          clave_idempotencia: crypto.randomUUID()
        })
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo guardar.");
      message.className = "result-message mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700";
      if (willFinalizeOrder) {
        message.textContent = "Estudio completado. Enviando resultados a mostrador...";
        const finishResponse = await fetch("/finalizar_resultados", {
          method: "POST",
          headers: {"Content-Type": "application/json", "Accept": "application/json"},
          body: JSON.stringify({orden_id: Number(card.dataset.order)})
        });
        const finishData = await finishResponse.json();
        if (!finishResponse.ok || !finishData.ok) {
          throw new Error(finishData.error || "El estudio se guardó, pero no se pudo enviar la orden.");
        }
        message.textContent = "Resultado finalizado y enviado correctamente a mostrador.";
        setTimeout(() => { window.location.href = "/resultados"; }, 1100);
      } else {
        message.textContent = "Estudio completado y consumo de reactivos registrado.";
        setTimeout(() => window.location.reload(), 700);
      }
    } catch (error) {
      message.className = "result-message mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-700";
      message.textContent = error.message;
      button.disabled = false;
      button.innerHTML = card.dataset.verification
        ? '<i class="fas fa-check-double mr-2"></i>Guardar verificación'
        : '<i class="fas fa-check mr-2"></i>Completar estudio';
    }
  }));

});
