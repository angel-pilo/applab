(() => {
  let navigationLock = false;

  function elements() {
    return {
      overlay: document.getElementById("app-loading-overlay"),
      title: document.getElementById("app-loading-title"),
      message: document.getElementById("app-loading-message")
    };
  }

  function show(options = {}) {
    const {overlay, title, message} = elements();
    if (!overlay) return;
    if (options.title && title) title.textContent = options.title;
    if (Object.prototype.hasOwnProperty.call(options, "message") && message) {
      message.textContent = options.message;
      message.hidden = !options.message;
    }
    if (options.lock) navigationLock = true;
    overlay.classList.add("is-visible");
    overlay.setAttribute("aria-hidden", "false");
  }

  function hide(force = false) {
    if (navigationLock && !force) return;
    const {overlay} = elements();
    overlay?.classList.remove("is-visible");
    overlay?.setAttribute("aria-hidden", "true");
  }

  window.AppLoading = {show, hide};

  window.addEventListener("pageshow", () => {
    navigationLock = false;
    hide(true);
  });
})();

document.addEventListener("DOMContentLoaded", () => {
  window.AppLoading?.hide(true);

  document.addEventListener("click", event => {
    const backControl = event.target.closest("a, button");
    const backLabel = (backControl?.getAttribute("aria-label") || "").trim().toLocaleLowerCase("es");
    const isBackControl = Boolean(
      backControl && (
        backLabel.startsWith("volver")
        || backLabel.startsWith("regresar")
        || backControl.dataset.loadingBack !== undefined
        || (backControl.getAttribute("onclick") || "").includes("history.back")
      )
    );
    if (isBackControl && !event.defaultPrevented && event.button === 0) {
      window.AppLoading?.show({
        title: "Volviendo a la página anterior",
        message: "",
        lock: true
      });
      return;
    }

    const link = event.target.closest("a[href]");
    if (
      !link || event.defaultPrevented || event.button !== 0
      || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey
      || link.target === "_blank" || link.hasAttribute("download")
      || link.dataset.noLoader !== undefined
    ) return;
    const target = new URL(link.href, window.location.href);
    if (
      target.origin !== window.location.origin
      || target.href === window.location.href
      || target.hash && target.pathname === window.location.pathname
    ) return;
    const label = (
      link.dataset.loadingLabel
      || link.querySelector("strong")?.textContent
      || link.getAttribute("aria-label")
      || [...link.querySelectorAll("span")]
        .map(span => span.textContent.trim())
        .find(text => text)
      || link.textContent
      || "módulo"
    ).trim().replace(/\s+/g, " ");
    const isLogout = target.pathname.endsWith("/logout");
    window.AppLoading?.show({
      title: isLogout ? "Cerrando sesión" : `Abriendo ${label}`,
      message: isLogout
        ? "Estamos protegiendo y cerrando tu sesión."
        : "",
      lock: true
    });
  });

  document.addEventListener("submit", event => {
    setTimeout(() => {
      if (event.defaultPrevented) return;
      const form = event.target;
      const isLogin = new URL(form.action, window.location.href).pathname.endsWith("/login");
      window.AppLoading?.show({
        title: isLogin ? "Iniciando sesión" : "Guardando información",
        message: isLogin
          ? "Validando tus credenciales y preparando tu panel."
          : "Completando la operación solicitada.",
        lock: true
      });
    }, 0);
  });

  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  const openButton = document.getElementById("sidebar-open");
  const closeButton = document.getElementById("sidebar-close");
  const desktopQuery = window.matchMedia("(min-width: 1024px)");

  function setSidebar(open) {
    if (!sidebar) return;
    const mobileOpen = open && !desktopQuery.matches;
    sidebar.classList.toggle("is-open", mobileOpen);
    sidebar.setAttribute("aria-hidden", String(!desktopQuery.matches && !mobileOpen));
    backdrop?.classList.toggle("is-visible", mobileOpen);
    backdrop?.setAttribute("aria-hidden", String(!mobileOpen));
    openButton?.setAttribute("aria-expanded", String(mobileOpen));
    document.body.classList.toggle("app-menu-open", mobileOpen);
    if (mobileOpen) closeButton?.focus();
  }

  window.toggleSidebar = (forceClose = false) => {
    const shouldOpen = forceClose === true ? false : !sidebar?.classList.contains("is-open");
    setSidebar(shouldOpen);
  };

  openButton?.addEventListener("click", () => setSidebar(true));
  closeButton?.addEventListener("click", () => setSidebar(false));
  backdrop?.addEventListener("click", () => setSidebar(false));
  sidebar?.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => {
      if (!desktopQuery.matches) setSidebar(false);
    });
  });
  desktopQuery.addEventListener("change", () => setSidebar(false));

  const notifButton = document.getElementById("navNotifBtn");
  const notifPanel = document.getElementById("navNotifPanel");
  const profileButton = document.getElementById("navProfileBtn");
  const profilePanel = document.getElementById("navProfilePanel");
  const dropdowns = [
    { button: notifButton, panel: notifPanel },
    { button: profileButton, panel: profilePanel },
  ];

  function closeDropdown({ button, panel }) {
    if (!panel) return;
    panel.hidden = true;
    button?.setAttribute("aria-expanded", "false");
  }

  function toggleDropdown(target) {
    const wasOpen = target.panel && !target.panel.hidden;
    dropdowns.forEach(closeDropdown);
    if (!wasOpen && target.panel) {
      target.panel.hidden = false;
      target.button?.setAttribute("aria-expanded", "true");
    }
  }

  dropdowns.forEach(dropdown => {
    dropdown.button?.addEventListener("click", event => {
      event.stopPropagation();
      toggleDropdown(dropdown);
    });
  });

  document.addEventListener("click", event => {
    dropdowns.forEach(dropdown => {
      if (!dropdown.panel?.contains(event.target) && !dropdown.button?.contains(event.target)) {
        closeDropdown(dropdown);
      }
    });
  });

  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    if (sidebar?.classList.contains("is-open")) {
      setSidebar(false);
      openButton?.focus();
    }
    dropdowns.forEach(closeDropdown);
  });

  const notifDot = document.getElementById("navNotifDot");
  const notifCount = document.getElementById("navNotifCount");
  const notifList = document.getElementById("navNotifList");
  const notifFooter = document.getElementById("navNotifFooter");
  const notifReadAll = document.getElementById("navNotifReadAll");
  let todayNotifications = [];
  let notificationsInitialized = false;
  let notificationSoundUnlocked = false;

  document.addEventListener("pointerdown", () => {
    notificationSoundUnlocked = true;
  }, {once: true});

  function playResultReadySound() {
    if (!notificationSoundUnlocked) return;
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const context = new AudioContext();
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(740, context.currentTime);
      gain.gain.setValueAtTime(0.0001, context.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.12, context.currentTime + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.35);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start();
      oscillator.stop(context.currentTime + 0.36);
      oscillator.addEventListener("ended", () => context.close());
    } catch (_) {}
  }

  function updateNotificationCounter() {
    const unread = todayNotifications.filter(item => !item.read).length;
    if (notifDot) {
      notifDot.textContent = unread > 99 ? "99+" : String(unread);
      notifDot.hidden = unread === 0;
    }
    if (notifCount) notifCount.textContent = String(unread);
    if (notifFooter) notifFooter.hidden = unread === 0;
  }

  function createNotificationItem(notification) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `app-notification-item${notification.read ? " is-read" : ""}`;
    button.dataset.notificationKey = notification.key;

    const icon = document.createElement("span");
    icon.className = `app-notification-icon ${notification.type === "expiry" ? "is-amber" : "is-cyan"}`;
    const iconGlyph = document.createElement("i");
    iconGlyph.className = `fas ${
      notification.type === "expiry" ? "fa-calendar-times"
      : notification.type === "result_ready" ? "fa-file-medical-alt"
      : "fa-vial"
    }`;
    icon.appendChild(iconGlyph);

    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = notification.title;
    const detail = document.createElement("small");
    detail.textContent = notification.detail;
    copy.append(title, detail);

    const state = document.createElement("i");
    state.className = `fas ${notification.read ? "fa-check" : "fa-circle"} app-notification-read-state`;
    state.setAttribute("aria-label", notification.read ? "Leída" : "Marcar como leída");
    button.append(icon, copy, state);
    button.addEventListener("click", async () => {
      await markNotificationsRead([notification.key]);
      if (notification.url) window.location.href = notification.url;
    });
    return button;
  }

  function renderNotifications() {
    if (!notifList) return;
    notifList.replaceChildren();
    if (!todayNotifications.length) {
      const empty = document.createElement("div");
      empty.className = "app-notification-empty";
      const icon = document.createElement("i");
      icon.className = "fas fa-check-circle";
      const text = document.createElement("span");
      text.textContent = notifList.dataset.emptyMessage || "No tienes notificaciones para hoy.";
      empty.append(icon, text);
      notifList.appendChild(empty);
    } else {
      todayNotifications.forEach(item => notifList.appendChild(createNotificationItem(item)));
    }
    updateNotificationCounter();
  }

  async function loadNotifications() {
    if (!notifList) return;
    try {
      const response = await fetch("/api/notifications/today", {
        headers: {"Accept": "application/json"},
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      const incoming = data.notifications || [];
      if (notificationsInitialized) {
        const previousKeys = new Set(todayNotifications.map(item => item.key));
        if (incoming.some(item => item.type === "result_ready" && !item.read && !previousKeys.has(item.key))) {
          playResultReadySound();
        }
      }
      todayNotifications = incoming;
      notificationsInitialized = true;
      notifList.dataset.emptyMessage = data.empty_message || "No tienes notificaciones para hoy.";
      const subtitle = document.getElementById("navNotifSubtitle");
      if (subtitle && data.subtitle) subtitle.textContent = data.subtitle;
      renderNotifications();
    } catch {
      notifList.innerHTML = '<div class="app-notification-empty"><i class="fas fa-exclamation-circle"></i><span>No se pudieron cargar las alertas.</span></div>';
    }
  }

  async function markNotificationsRead(keys, markAll = false) {
    if (!keys.length && !markAll) return;
    try {
      const response = await fetch("/api/notifications/read", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(markAll ? {all: true} : {keys}),
      });
      if (!response.ok) throw new Error();
      const selected = new Set(keys);
      todayNotifications.forEach(item => {
        if (markAll || selected.has(item.key)) item.read = true;
      });
      renderNotifications();
    } catch {
      // Conserva el estado visible para que el usuario pueda reintentarlo.
    }
  }

  notifReadAll?.addEventListener("click", () => markNotificationsRead([], true));
  loadNotifications();
  window.setInterval(loadNotifications, 30000);

  setSidebar(false);
});
