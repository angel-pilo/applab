document.addEventListener("DOMContentLoaded", () => {
  const rows = [...document.querySelectorAll(".study-row")];
  const selectedContainer = document.getElementById("selected-studies");
  const emptyState = document.getElementById("selected-empty");
  const count = document.getElementById("selected-count");
  const total = document.getElementById("studies-total");
  const hidden = document.getElementById("selected-studies-json");
  const status = document.getElementById("study-save-status");
  const alert = document.getElementById("studies-alert");
  const form = document.getElementById("studies-form");
  const selected = new Map();
  let saveTimer;

  try {
    const initial = JSON.parse(document.getElementById("initial-selected-studies")?.textContent || "[]");
    initial.forEach((item) => {
      selected.set(String(item.prueba_id), {
        prueba_id: Number(item.prueba_id),
        prueba: item.prueba,
        tipo_prueba: item.tipo_prueba || "",
        cantidad: Number(item.cantidad) || 1,
        precio_unitario: Number(item.precio_unitario ?? (Number(item.precio) / (Number(item.cantidad) || 1))) || 0,
      });
    });
  } catch (error) {
    console.error("No se pudo recuperar la selección:", error);
  }

  function serialize() {
    return [...selected.values()].map((item) => ({
      ...item,
      precio: Number((item.precio_unitario * item.cantidad).toFixed(2)),
    }));
  }

  async function persist() {
    status.textContent = "Guardando selección...";
    try {
      const response = await fetch("/api/orden/estudios", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ estudios: serialize() }),
      });
      if (!response.ok) throw new Error("save_failed");
      const data = await response.json();
      status.textContent = `${data.cantidad} estudio${data.cantidad === 1 ? "" : "s"} guardado${data.cantidad === 1 ? "" : "s"}.`;
    } catch (error) {
      console.error(error);
      status.textContent = "No se pudo guardar. Se intentará al continuar.";
    }
  }

  function scheduleSave() {
    clearTimeout(saveTimer);
    status.textContent = "Cambios pendientes...";
    saveTimer = window.setTimeout(persist, 350);
  }

  function render() {
    const items = serialize();
    selectedContainer.replaceChildren();
    items.forEach((item) => {
      const article = document.createElement("article");
      article.className = "p-4";

      const top = document.createElement("div");
      top.className = "flex items-start justify-between gap-3";
      const copy = document.createElement("div");
      copy.className = "min-w-0";
      const name = document.createElement("strong");
      name.className = "block truncate text-sm text-gray-900";
      name.textContent = item.prueba;
      const type = document.createElement("small");
      type.className = "mt-0.5 block text-xs text-gray-500";
      type.textContent = item.tipo_prueba || "Estudio clínico";
      copy.append(name, type);
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "text-gray-400 hover:text-red-600";
      remove.setAttribute("aria-label", `Quitar ${item.prueba}`);
      remove.innerHTML = '<i class="fas fa-times"></i>';
      remove.addEventListener("click", () => toggleStudy(String(item.prueba_id), false));
      top.append(copy, remove);

      const bottom = document.createElement("div");
      bottom.className = "mt-3 flex items-center justify-between gap-3";
      const quantityLabel = document.createElement("label");
      quantityLabel.className = "flex items-center gap-2 text-xs text-gray-500";
      quantityLabel.append("Cantidad");
      const quantity = document.createElement("input");
      quantity.type = "number";
      quantity.min = "1";
      quantity.max = "99";
      quantity.value = String(item.cantidad);
      quantity.className = "h-8 w-16 rounded-lg border border-gray-200 px-2 text-center text-sm text-gray-900";
      quantity.addEventListener("change", () => {
        selected.get(String(item.prueba_id)).cantidad = Math.max(1, Math.min(Number(quantity.value) || 1, 99));
        render();
        scheduleSave();
      });
      quantityLabel.appendChild(quantity);
      const subtotal = document.createElement("strong");
      subtotal.className = "text-sm text-gray-900";
      subtotal.textContent = `$${(item.precio_unitario * item.cantidad).toFixed(2)}`;
      bottom.append(quantityLabel, subtotal);
      article.append(top, bottom);
      selectedContainer.appendChild(article);
    });

    const sum = items.reduce((value, item) => value + Number(item.precio), 0);
    count.textContent = String(items.length);
    total.textContent = `$${sum.toFixed(2)}`;
    hidden.value = JSON.stringify(items);
    emptyState.classList.toggle("hidden", items.length > 0);
    selectedContainer.classList.toggle("hidden", items.length === 0);
    alert.classList.add("hidden");
    rows.forEach((row) => {
      const checked = selected.has(row.dataset.id);
      row.querySelector(".study-checkbox").checked = checked;
      row.classList.toggle("bg-cyan-50", checked);
    });
  }

  function toggleStudy(id, checked) {
    const row = rows.find((candidate) => candidate.dataset.id === id);
    if (!row) return;
    if (checked) {
      selected.set(id, {
        prueba_id: Number(id),
        prueba: row.dataset.name,
        tipo_prueba: row.dataset.type || "",
        cantidad: selected.get(id)?.cantidad || 1,
        precio_unitario: Number(row.dataset.price) || 0,
      });
    } else {
      selected.delete(id);
    }
    render();
    scheduleSave();
  }

  rows.forEach((row) => {
    const checkbox = row.querySelector(".study-checkbox");
    checkbox.addEventListener("change", () => toggleStudy(row.dataset.id, checkbox.checked));
    row.addEventListener("click", (event) => {
      if (event.target.closest("input, button, a")) return;
      toggleStudy(row.dataset.id, !selected.has(row.dataset.id));
    });
  });

  document.getElementById("study-search")?.addEventListener("input", (event) => {
    const query = event.target.value.toLowerCase().trim();
    let visible = 0;
    rows.forEach((row) => {
      const matches = !query || row.dataset.search.includes(query);
      row.classList.toggle("hidden", !matches);
      if (matches) visible += 1;
    });
    document.getElementById("study-no-results")?.classList.toggle("hidden", visible > 0);
  });

  form.addEventListener("submit", (event) => {
    if (!selected.size) {
      event.preventDefault();
      alert.classList.remove("hidden");
      alert.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    hidden.value = JSON.stringify(serialize());
  });

  render();
  if (selected.size) status.textContent = `${selected.size} estudio${selected.size === 1 ? "" : "s"} recuperado${selected.size === 1 ? "" : "s"}.`;
});
