document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("admin-global-search");
  if (!modal) return;

  const input = document.getElementById("admin-global-search-input");
  const clearButton = document.getElementById("admin-global-search-clear");
  const summary = document.getElementById("admin-global-search-summary");
  const empty = document.getElementById("admin-global-search-empty");
  const items = [...modal.querySelectorAll("[data-admin-global-search-item]")];
  let activeIndex = -1;

  const normalize = value => (value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

  const visibleItems = () => items.filter(item => !item.classList.contains("hidden"));

  const setActive = index => {
    const visible = visibleItems();
    items.forEach(item => item.classList.remove("bg-cyan-50", "ring-1", "ring-inset", "ring-cyan-100"));
    if (!visible.length || index < 0) {
      activeIndex = -1;
      input.removeAttribute("aria-activedescendant");
      return;
    }
    activeIndex = (index + visible.length) % visible.length;
    const active = visible[activeIndex];
    if (!active.id) active.id = `admin-global-search-option-${items.indexOf(active)}`;
    active.classList.add("bg-cyan-50", "ring-1", "ring-inset", "ring-cyan-100");
    active.scrollIntoView({ block: "nearest" });
    input.setAttribute("aria-activedescendant", active.id);
  };

  const filter = () => {
    const terms = normalize(input.value).split(/\s+/).filter(Boolean);
    let matches = 0;
    items.forEach(item => {
      const visible = terms.every(term => normalize(item.dataset.search).includes(term));
      item.classList.toggle("hidden", !visible);
      if (visible) matches += 1;
    });
    empty.classList.toggle("hidden", matches !== 0);
    summary.textContent = input.value.trim()
      ? `${matches} ${matches === 1 ? "resultado" : "resultados"}`
      : `${matches} opciones disponibles`;
    clearButton.classList.toggle("hidden", !input.value);
    clearButton.classList.toggle("grid", Boolean(input.value));
    setActive(matches ? 0 : -1);
  };

  const open = () => {
    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");
    document.body.classList.add("overflow-hidden");
    window.requestAnimationFrame(() => {
      input.focus();
      input.select();
      filter();
    });
  };

  const close = () => {
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
    document.body.classList.remove("overflow-hidden");
    input.value = "";
    filter();
  };

  document.querySelectorAll("[data-admin-search-open]").forEach(button => button.addEventListener("click", open));
  modal.querySelectorAll("[data-admin-search-close]").forEach(button => button.addEventListener("click", close));
  clearButton.addEventListener("click", () => {
    input.value = "";
    input.focus();
    filter();
  });
  input.addEventListener("input", filter);
  input.addEventListener("keydown", event => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive(activeIndex + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive(activeIndex <= 0 ? visibleItems().length - 1 : activeIndex - 1);
    } else if (event.key === "Enter") {
      const active = visibleItems()[activeIndex];
      if (active) {
        event.preventDefault();
        active.click();
      }
    }
  });
  document.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      open();
    } else if (event.key === "Escape" && !modal.classList.contains("hidden")) {
      close();
    }
  });
});
