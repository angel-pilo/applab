document.addEventListener("DOMContentLoaded", () => {
  const checkboxes = [...document.querySelectorAll(".label-checkbox")];
  const selectAll = document.getElementById("select-all-labels");
  const search = document.getElementById("label-search");
  const format = document.getElementById("label-format");
  const copies = document.getElementById("label-copies");
  const showQr = document.getElementById("label-show-qr");
  const printButton = document.getElementById("print-labels");
  const count = document.getElementById("label-selection-count");
  const sheet = document.getElementById("label-print-sheet");

  const escapeHtml = value => String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);

  function selectedLabels() {
    return checkboxes.filter(input => input.checked && !input.closest(".label-row").classList.contains("hidden"));
  }

  function updateSelection() {
    const selected = selectedLabels().length;
    count.textContent = `${selected} muestra${selected === 1 ? "" : "s"} seleccionada${selected === 1 ? "" : "s"}`;
    printButton.disabled = selected === 0;
    printButton.classList.toggle("opacity-50", selected === 0);
  }

  function syncAdminDefaults() {
    const formatField = document.getElementById("admin-label-format");
    const copiesField = document.getElementById("admin-label-copies");
    const qrField = document.getElementById("admin-label-qr");
    if (formatField) formatField.value = format.value;
    if (copiesField) copiesField.value = copies.value;
    if (qrField) qrField.value = showQr.checked ? "on" : "";
  }

  function buildLabel(input, width, height) {
    const compact = width <= 50 || height <= 30;
    const label = document.createElement("article");
    label.className = "sample-label";
    label.style.cssText = `width:${width}mm;height:${height}mm;padding:${compact ? 2 : 3}mm;display:grid;grid-template-columns:1fr ${showQr.checked ? (compact ? 18 : 24) : 0}mm;gap:2mm;align-items:center;`;
    label.innerHTML = `
      <div style="min-width:0;line-height:1.15">
        <div style="font-size:${compact ? 7 : 9}pt;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${escapeHtml(input.dataset.patient)}</div>
        <div style="font-size:${compact ? 11 : 15}pt;font-weight:800;margin-top:1.3mm">ORD #${String(input.dataset.orderId).padStart(4, "0")}</div>
        <div style="font-size:${compact ? 8 : 10}pt;font-weight:700;text-transform:uppercase;margin-top:1mm">${escapeHtml(input.dataset.sample)}</div>
        <div style="font-size:${compact ? 6 : 7}pt;margin-top:1mm">${escapeHtml(input.dataset.created)} · M-${input.value}</div>
      </div>
      ${showQr.checked ? '<div class="label-qr" style="display:grid;place-items:center"></div>' : ""}
    `;
    if (showQr.checked && window.QRCode) {
      new QRCode(label.querySelector(".label-qr"), {
        text: input.dataset.scanUrl,
        width: compact ? 62 : 84,
        height: compact ? 62 : 84,
        correctLevel: QRCode.CorrectLevel.M
      });
    }
    return label;
  }

  async function printLabels() {
    const selected = selectedLabels();
    const copyCount = Math.max(1, Math.min(10, Number(copies.value) || 1));
    const [width, height] = format.value.split("x").map(Number);
    sheet.replaceChildren();
    selected.forEach(input => {
      for (let copy = 0; copy < copyCount; copy += 1) {
        sheet.appendChild(buildLabel(input, width, height));
      }
    });
    try {
      await fetch("/api/etiquetas/impresion", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({muestra_ids: selected.map(item => Number(item.value)), copias: copyCount})
      });
    } catch (_) {}
    window.setTimeout(() => window.print(), 180);
  }

  checkboxes.forEach(input => input.addEventListener("change", updateSelection));
  selectAll?.addEventListener("change", () => {
    checkboxes.forEach(input => {
      if (!input.closest(".label-row").classList.contains("hidden")) input.checked = selectAll.checked;
    });
    updateSelection();
  });
  search?.addEventListener("input", () => {
    const term = search.value.trim().toLocaleLowerCase("es");
    document.querySelectorAll(".label-row").forEach(row => {
      row.classList.toggle("hidden", Boolean(term) && !row.dataset.search.includes(term));
    });
    if (selectAll) selectAll.checked = false;
    updateSelection();
  });
  [format, copies, showQr].forEach(input => input?.addEventListener("change", syncAdminDefaults));
  printButton?.addEventListener("click", printLabels);
  syncAdminDefaults();
  updateSelection();
});
