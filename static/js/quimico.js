document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("analysis-modal");
  const body = document.getElementById("analysis-modal-body");
  const title = document.getElementById("analysis-modal-title");
  const search = document.getElementById("result-order-search");
  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);

  async function openAnalysis(orderId) {
    title.textContent = `Estudios de la orden #${String(orderId).padStart(4, "0")}`;
    body.innerHTML = '<div class="py-10 text-center text-sm text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>Cargando estudios...</div>';
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
    try {
      const response = await fetch(`/api/analisis/${orderId}`, {headers: {"Accept": "application/json"}});
      const studies = await response.json();
      if (!response.ok) throw new Error(studies.error || "No se pudieron consultar los estudios.");
      if (!studies.length) {
        body.innerHTML = '<div class="rounded-xl border border-gray-200 bg-white p-5 text-center text-sm text-gray-500">Esta orden no tiene estudios registrados.</div>';
        return;
      }
      body.innerHTML = studies.map(study => {
        const elements = study.elementos || [];
        const reagents = study.reactivos || [];
        return `
          <article class="mb-3 rounded-xl border border-gray-200 bg-white p-4 last:mb-0">
            <div class="flex items-center gap-3">
              <span class="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-cyan-50 text-cyan-700"><i class="fas fa-flask"></i></span>
              <span class="min-w-0">
                <strong class="block text-sm text-gray-900">${escapeHtml(study.nombre || study.nombre_prueba || "Estudio")}</strong>
                <small class="text-gray-500">${escapeHtml(study.tipo || study.tipo_prueba || "Sin clasificación")}</small>
              </span>
            </div>
            <div class="mt-3 border-t border-gray-100 pt-3">
              <p class="text-[11px] font-bold uppercase tracking-wide text-gray-400">Elementos a reportar</p>
              <p class="mt-1 text-xs leading-5 text-gray-700">${elements.length ? elements.map(item => escapeHtml(item.nombre)).join(" · ") : "Sin elementos configurados"}</p>
              <p class="mt-3 text-[11px] font-bold uppercase tracking-wide text-gray-400">Reactivos por ejecución</p>
              <p class="mt-1 text-xs leading-5 text-gray-700">${reagents.length ? reagents.map(item => `${escapeHtml(item.nombre)} (${escapeHtml(item.cantidad)})`).join(" · ") : "Sin reactivos asociados"}</p>
            </div>
          </article>
        `;
      }).join("");
    } catch (error) {
      body.innerHTML = `<div class="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">${escapeHtml(error.message)}</div>`;
    }
  }

  function closeAnalysis() {
    modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }
  document.querySelectorAll("[data-analysis-order]").forEach(button =>
    button.addEventListener("click", () => openAnalysis(button.dataset.analysisOrder))
  );
  document.querySelectorAll("[data-close-analysis]").forEach(button =>
    button.addEventListener("click", closeAnalysis)
  );
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !modal.classList.contains("hidden")) closeAnalysis();
  });

  const feedback = document.getElementById("result-feedback-modal");
  function showFeedback(ok, message) {
    const icon = document.getElementById("result-feedback-icon");
    document.getElementById("result-feedback-title").textContent = ok
      ? "Orden finalizada"
      : "No se pudo finalizar";
    document.getElementById("result-feedback-message").textContent = message;
    icon.className = `mx-auto grid h-12 w-12 place-items-center rounded-2xl ${
      ok ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
    }`;
    icon.innerHTML = ok
      ? '<i class="fas fa-check-double"></i>'
      : '<i class="fas fa-exclamation-triangle"></i>';
    feedback.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
  }
  function closeFeedback() {
    feedback.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
  }
  document.querySelectorAll("[data-close-feedback]").forEach(button =>
    button.addEventListener("click", closeFeedback)
  );

  document.querySelectorAll("[data-finalize-order]").forEach(button =>
    button.addEventListener("click", async () => {
      const orderId = Number(button.dataset.finalizeOrder);
      const row = button.closest(".result-order-row");
      const original = button.innerHTML;
      button.disabled = true;
      button.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Finalizando...';
      try {
        const response = await fetch("/finalizar_resultados", {
          method: "POST",
          headers: {"Content-Type": "application/json", "Accept": "application/json"},
          body: JSON.stringify({orden_id: orderId})
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || "No se pudo finalizar la orden.");
        row.remove();
        const count = document.getElementById("chemical-order-count");
        count.textContent = String(Math.max(Number(count.textContent) - 1, 0));
        if (!document.querySelector(".result-order-row")) {
          document.getElementById("result-order-list").innerHTML = `
            <div class="px-5 py-16 text-center">
              <span class="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><i class="fas fa-check-double"></i></span>
              <h3 class="mt-4 font-bold text-gray-900">Sin órdenes por analizar</h3>
              <p class="mt-1 text-sm text-gray-500">Todas las órdenes terminadas fueron enviadas a mostrador.</p>
            </div>`;
        }
        showFeedback(true, `La orden #${String(orderId).padStart(4, "0")} fue finalizada y enviada correctamente a mostrador.`);
      } catch (error) {
        button.disabled = false;
        button.innerHTML = original;
        showFeedback(false, error.message);
      }
    })
  );

  search?.addEventListener("input", () => {
    const term = search.value.trim().toLocaleLowerCase("es");
    let visible = 0;
    document.querySelectorAll(".result-order-row").forEach(row => {
      const show = !term || row.dataset.search.includes(term);
      row.classList.toggle("hidden", !show);
      if (show) visible += 1;
    });
    document.getElementById("result-search-empty")?.classList.toggle("hidden", visible !== 0);
  });
});
