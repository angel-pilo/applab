(() => {
  "use strict";

  const selector = 'input[type="date"]:not([data-native-date]):not([data-date-ready])';

  function addCalendarActions(instance) {
    const calendar = instance.calendarContainer;
    if (!calendar || calendar.querySelector(".app-date-actions")) return;

    const actions = document.createElement("div");
    actions.className = "app-date-actions";

    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "app-date-action is-muted";
    clear.textContent = "Limpiar";
    clear.addEventListener("click", () => {
      instance.clear();
      instance.close();
    });

    const today = document.createElement("button");
    today.type = "button";
    today.className = "app-date-action is-primary";
    today.textContent = "Hoy";
    today.addEventListener("click", () => {
      const current = new Date();
      if (instance.config.minDate && current < instance.config.minDate) return;
      if (instance.config.maxDate && current > instance.config.maxDate) return;
      instance.setDate(current, true);
      instance.close();
    });

    actions.append(clear, today);
    calendar.appendChild(actions);
  }

  function connectAccessibleInput(original, instance) {
    const display = instance.altInput;
    if (!display) return;

    display.classList.add("app-date-display");
    display.placeholder = original.dataset.datePlaceholder || "dd/mm/aaaa";
    display.autocomplete = "off";
    display.inputMode = "numeric";

    if (original.id) {
      display.id = `${original.id}__display`;
      document.querySelectorAll(`label[for="${CSS.escape(original.id)}"]`).forEach(label => {
        label.htmlFor = display.id;
      });
    }
    if (original.getAttribute("aria-describedby")) {
      display.setAttribute("aria-describedby", original.getAttribute("aria-describedby"));
    }
    if (original.required) {
      display.required = true;
      original.required = false;
      original.dataset.dateRequired = "true";
    }
  }

  function initializeDateInput(input) {
    if (!window.flatpickr || input.dataset.dateReady === "true") return;
    input.dataset.dateReady = "true";

    const instance = window.flatpickr(input, {
      locale: window.flatpickr.l10ns?.es || "es",
      dateFormat: "Y-m-d",
      altInput: true,
      altFormat: "d/m/Y",
      allowInput: true,
      disableMobile: false,
      monthSelectorType: "static",
      prevArrow: '<span aria-hidden="true">&#8592;</span>',
      nextArrow: '<span aria-hidden="true">&#8594;</span>',
      onReady: [(_dates, _value, picker) => {
        connectAccessibleInput(input, picker);
        addCalendarActions(picker);
      }],
      onChange: [() => {
        input.dispatchEvent(new Event("input", { bubbles: true }));
      }]
    });

    input._appDatePicker = instance;
  }

  function initializeDates(root = document) {
    if (!window.flatpickr) return;
    if (root.matches?.(selector)) initializeDateInput(root);
    root.querySelectorAll?.(selector).forEach(initializeDateInput);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initializeDates();
    const observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => mutation.addedNodes.forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE) initializeDates(node);
      }));
    });
    observer.observe(document.body, { childList: true, subtree: true });
  });

  window.AppDatePicker = { refresh: initializeDates };
})();
