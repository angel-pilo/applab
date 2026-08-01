document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("sample-modal");
  const body = document.getElementById("sample-modal-body");
  const progress = document.getElementById("sample-modal-progress");
  const status = document.getElementById("sample-save-status");
  const finalizeButton = document.getElementById("finalize-samples");
  const search = document.getElementById("buscar-muestra");
  let currentOrderId = null;
  let samples = [];

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);

  const sampleLabel = (type) => ({
    sangre: "Sangre", orina: "Orina", heces: "Heces",
    exudado: "Exudado", saliva: "Saliva", otro: "Otra muestra"
  })[type] || type.charAt(0).toUpperCase() + type.slice(1);

  const sampleIcon = (type) => ({
    sangre: "fa-tint", orina: "fa-flask", heces: "fa-vial",
    exudado: "fa-microscope", saliva: "fa-prescription-bottle", otro: "fa-box"
  })[type] || "fa-vial";

  function setStatus(message, error = false) {
    status.textContent = message;
    status.className = `text-xs ${error ? "text-red-600" : "text-gray-500"}`;
  }

  function updateProgress() {
    const complete = samples.filter(item => item.recolectada).length;
    const total = samples.length;
    progress.textContent = `${complete} de ${total} muestras recolectadas`;
    finalizeButton.disabled = !total || complete !== total;
    finalizeButton.classList.toggle("opacity-50", finalizeButton.disabled);
    const row = document.querySelector(`[data-order-id="${currentOrderId}"]`);
    if (row) {
      row.querySelector(".order-progress-label").textContent = `${complete}/${total}`;
      row.querySelector(".order-progress-bar").style.width = `${total ? complete * 100 / total : 0}%`;
    }
  }

  function renderSamples() {
    if (!samples.length) {
      body.innerHTML = '<div class="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">Esta orden no tiene requisitos configurados. Revisa la migración de muestras.</div>';
      updateProgress();
      return;
    }
    body.innerHTML = samples.map(item => {
      const studies = (item.estudios || []).map(study =>
        `<span class="rounded-full bg-gray-100 px-2 py-1 text-xs text-gray-600">${escapeHtml(study)}</span>`
      ).join("");
      return `
        <article class="rounded-2xl border ${item.recolectada ? "border-emerald-200 bg-emerald-50/50" : "border-gray-200 bg-white"} p-4" data-sample="${escapeHtml(item.tipo_muestra)}">
          <div class="flex items-start gap-3">
            <span class="grid h-10 w-10 shrink-0 place-items-center rounded-xl ${item.recolectada ? "bg-emerald-100 text-emerald-700" : "bg-amber-50 text-amber-700"}">
              <i class="fas ${sampleIcon(item.tipo_muestra)}"></i>
            </span>
            <div class="min-w-0 flex-1">
              <div class="flex items-center justify-between gap-3">
                <div><h3 class="font-bold text-gray-900">${escapeHtml(sampleLabel(item.tipo_muestra))}</h3><p class="text-xs text-gray-500">${item.recolectada ? "Muestra confirmada" : "Pendiente de recolección"}</p></div>
                <label class="relative inline-flex cursor-pointer items-center">
                  <input type="checkbox" class="sample-check peer sr-only" ${item.recolectada ? "checked" : ""}>
                  <span class="h-6 w-11 rounded-full bg-gray-200 transition peer-checked:bg-emerald-600 after:absolute after:left-1 after:top-1 after:h-4 after:w-4 after:rounded-full after:bg-white after:transition peer-checked:after:translate-x-5"></span>
                </label>
              </div>
              <div class="mt-3 flex flex-wrap gap-1.5">${studies || '<span class="text-xs text-gray-400">Sin estudios vinculados</span>'}</div>
              <label class="mt-3 block text-xs font-semibold text-gray-600">Observaciones
                <input type="text" class="sample-notes mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-normal outline-none focus:border-cyan-500" maxlength="250" value="${escapeHtml(item.observaciones || "")}" placeholder="Ej. volumen insuficiente, paciente pendiente...">
              </label>
            </div>
          </div>
        </article>`;
    }).join("");

    body.querySelectorAll("[data-sample]").forEach(card => {
      const type = card.dataset.sample;
      const checkbox = card.querySelector(".sample-check");
      const notes = card.querySelector(".sample-notes");
      checkbox.addEventListener("change", () => saveSample(type, checkbox.checked, notes.value));
      notes.addEventListener("change", () => saveSample(type, checkbox.checked, notes.value));
    });
    updateProgress();
  }

  async function loadSamples(orderId) {
    currentOrderId = orderId;
    body.innerHTML = '<div class="py-12 text-center text-sm text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>Cargando requisitos...</div>';
    progress.textContent = "Consultando la orden...";
    modal.classList.remove("hidden");
    document.body.classList.add("overflow-hidden");
    try {
      const response = await fetch(`/api/muestra/${orderId}/requisitos`, {headers: {"Accept": "application/json"}});
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error);
      samples = data.muestras || [];
      renderSamples();
      setStatus("Los cambios se guardan automáticamente.");
    } catch (error) {
      samples = [];
      body.innerHTML = `<div class="rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">${escapeHtml(error.message || "No se pudieron cargar las muestras.")}</div>`;
      updateProgress();
    }
  }

  async function saveSample(type, collected, notes) {
    setStatus("Guardando...");
    try {
      const response = await fetch(`/api/muestra/${currentOrderId}/requisitos`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({tipo_muestra: type, recolectada: collected, observaciones: notes})
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error);
      samples = data.muestras || [];
      renderSamples();
      setStatus("Cambios guardados correctamente.");
    } catch (error) {
      setStatus(error.message || "No se pudo guardar el cambio.", true);
      await loadSamples(currentOrderId);
    }
  }

  async function finalizeOrder() {
    if (finalizeButton.disabled || !currentOrderId) return;
    finalizeButton.disabled = true;
    setStatus("Enviando orden a Químico...");
    try {
      const response = await fetch(`/api/muestra/finalizar/${currentOrderId}`, {
        method: "POST", headers: {"Content-Type": "application/json"}
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error);
      document.querySelector(`[data-order-id="${currentOrderId}"]`)?.remove();
      closeModal();
      const count = document.querySelectorAll(".orden-muestra-row").length;
      document.getElementById("ordenes-pendientes-count").textContent = count;
      if (!count) window.location.reload();
    } catch (error) {
      setStatus(error.message || "No se pudo finalizar la orden.", true);
      updateProgress();
    }
  }

  function closeModal() {
    modal.classList.add("hidden");
    document.body.classList.remove("overflow-hidden");
    currentOrderId = null;
    samples = [];
  }

  document.querySelectorAll("[data-open-samples]").forEach(button =>
    button.addEventListener("click", () => loadSamples(button.dataset.openSamples))
  );
  document.querySelectorAll("[data-close-samples]").forEach(button => button.addEventListener("click", closeModal));
  finalizeButton.addEventListener("click", finalizeOrder);
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !modal.classList.contains("hidden")) closeModal(); });
  search?.addEventListener("input", () => {
    const term = search.value.trim().toLocaleLowerCase("es");
    let visible = 0;
    document.querySelectorAll(".orden-muestra-row").forEach(row => {
      const show = !term || row.dataset.search.includes(term);
      row.classList.toggle("hidden", !show);
      if (show) visible += 1;
    });
    document.getElementById("muestras-search-empty")?.classList.toggle("hidden", visible !== 0);
  });
});
