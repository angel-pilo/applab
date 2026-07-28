document.addEventListener("DOMContentLoaded", () => {
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

  setSidebar(false);
});
