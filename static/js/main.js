/******************************
 * Sidebar: estado + animación
 ******************************/
const SIDEBAR_KEY = "applab.sidebar.collapsed";

function isMobile() {
  return window.matchMedia("(max-width: 767px)").matches; // md breakpoint
}

function applySidebarState(collapsed) {
  const aside = document.getElementById("sidebar");
  const main = document.getElementById("main-content");
  const backdrop = document.getElementById("sidebar-backdrop"); // opcional si lo tienes
  if (!aside) return;

  // Asegurar clases de transición suaves
  aside.classList.add("transition-all", "duration-300", "ease-in-out");

  if (isMobile()) {
    // En móvil la sidebar funciona como drawer
    if (collapsed) {
      aside.classList.add("-translate-x-full");
      if (backdrop) backdrop.classList.add("hidden");
    } else {
      aside.classList.remove("-translate-x-full");
      if (backdrop) backdrop.classList.remove("hidden");
    }
    // En móvil no mostramos textos forzadamente; depende del ancho del drawer
    document.querySelectorAll(".sidebar-text").forEach(el => el.classList.remove("hidden"));
  } else {
    // Desktop: usamos data attribute para que el CSS cambie el ancho (w-64 / w-16)
    aside.dataset.collapsed = "false";

    // Mostrar/ocultar textos al colapsar (solo desktop)
    document.querySelectorAll(".sidebar-text").forEach(el => {
      el.classList.remove("hidden");
    });

    // Si aún dependes de margen en el contenido, ajusta aquí (fallback)
    if (main) {
      // Usa 250px expandido / 64px colapsado como en tu código previo
      main.style.marginLeft =  "64px";
    }
  }

  try { localStorage.setItem(SIDEBAR_KEY); } catch {}

  retunr;
}

// API pública para botón
function toggleSidebar(forceState) {
  const aside = document.getElementById("sidebar");
  if (!aside) return;

  // En desktop ya no hacemos nada: sidebar estática
  if (!isMobile()) return;

  const isHiddenMobile = aside.classList.contains("-translate-x-full");
  const current = isHiddenMobile;
  const next = (typeof forceState === "boolean") ? forceState : !current;

  applySidebarState(next);
}

// Inicializar estado en carga
window.addEventListener("DOMContentLoaded", () => {
  const aside = document.getElementById("sidebar");
  if (aside) {
    // Preparar animación
    aside.classList.add("transition-all", "duration-300", "ease-in-out");

    // Estado inicial (persistente en desktop; oculto por defecto en móvil)
    let collapsed = false;
    try { collapsed = localStorage.getItem(SIDEBAR_KEY) === "1"; } catch {}
    if (isMobile()) {
      collapsed = true;
      aside.classList.add("transition-transform", "duration-300", "ease-in-out");
      aside.classList.add("-translate-x-full"); // oculto
    }
    applySidebarState(collapsed);

    // Reaplicar al cambiar de tamaño
    window.addEventListener("resize", () => {
      let collapsed = false;
      try { collapsed = localStorage.getItem(SIDEBAR_KEY) === "1"; } catch {}
      if (isMobile()) {
        applySidebarState(true); // drawer oculto por defecto en móvil
      } else {
        applySidebarState(collapsed);
      }
    });
  }

  // Tooltip al hover cuando la sidebar está colapsada en desktop
  setupCollapsedTooltips();
});

// --- Sidebar: siempre colapsada ---
// Si en algún lugar llaman toggleSidebar, lo anulamos.
window.toggleSidebar = function () {
  // no-op: la sidebar permanece colapsada
};

// --- Tooltip al hover para elementos con data-tooltip ---
(function () {
  let tipEl = null;

  function showTip(target) {
    const text = target.getAttribute('data-tooltip');
    if (!text) return;
    if (!tipEl) {
      tipEl = document.createElement('div');
      tipEl.className = 'applab-tooltip';
      document.body.appendChild(tipEl);
    }
    tipEl.textContent = text;
    const rect = target.getBoundingClientRect();
    const top = rect.top + window.scrollY + rect.height / 2;
    const left = rect.right + window.scrollX + 8; // a la derecha del icono
    tipEl.style.top = `${top}px`;
    tipEl.style.left = `${left}px`;
    tipEl.style.display = 'block';
  }

  function hideTip() {
    if (tipEl) tipEl.style.display = 'none';
  }

  document.addEventListener('mouseover', (e) => {
    const t = e.target.closest('[data-tooltip]');
    if (t) showTip(t);
  });
  document.addEventListener('mouseout', (e) => {
    const t = e.target.closest('[data-tooltip]');
    if (t) hideTip();
  });
})();

// Tooltip para data-tooltip (sidebar colapsada)
(function () {
  let tipEl = null;

  function showTip(target) {
    const text = target.getAttribute('data-tooltip');
    if (!text) return;
    if (!tipEl) {
      tipEl = document.createElement('div');
      tipEl.className = 'applab-tooltip';
      document.body.appendChild(tipEl);
    }
    tipEl.textContent = text;
    const rect = target.getBoundingClientRect();
    const top = rect.top + window.scrollY + rect.height / 2;
    const left = rect.right + window.scrollX + 8;
    tipEl.style.top = `${top}px`;
    tipEl.style.left = `${left}px`;
    tipEl.style.display = 'block';
  }

  function hideTip() {
    if (tipEl) tipEl.style.display = 'none';
  }

  document.addEventListener('mouseover', (e) => {
    const t = e.target.closest('[data-tooltip]');
    if (t) showTip(t);
  });
  document.addEventListener('mouseout', (e) => {
    const t = e.target.closest('[data-tooltip]');
    if (t) hideTip();
  });
})();

// Sidebar: deslizar SOLO en móvil (md < 768px)
(function () {
  const sidebar  = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;

  function openMobile() {
    sidebar.classList.remove('-translate-x-full');
    sidebar.classList.add('translate-x-0');
    backdrop.classList.remove('hidden');
  }
  function closeMobile() {
    sidebar.classList.add('-translate-x-full');
    sidebar.classList.remove('translate-x-0');
    backdrop.classList.add('hidden');
  }

  window.toggleSidebar = function (forceClose = false) {
    if (isDesktop()) return; // en desktop no deslizamos (siempre colapsada)
    const isOpen = sidebar.classList.contains('translate-x-0');
    if (forceClose === true) return closeMobile();
    if (isOpen) closeMobile(); else openMobile();
  };

  // Al cambiar tamaño: si pasas a desktop, cierra el drawer y oculta backdrop
  window.addEventListener('resize', () => {
    if (isDesktop()) {
      closeMobile();
    }
  });
})();

(function () {
  let tipEl = null;
  function showTip(t) {
    const text = t.getAttribute('data-tooltip'); if (!text) return;
    if (!tipEl) { tipEl = document.createElement('div'); tipEl.className = 'applab-tooltip'; document.body.appendChild(tipEl); }
    tipEl.textContent = text;
    const r = t.getBoundingClientRect();
    tipEl.style.top  = (r.top + window.scrollY + r.height/2) + 'px';
    tipEl.style.left = (r.right + window.scrollX + 8) + 'px';
    tipEl.style.display = 'block';
  }
  function hideTip(){ if (tipEl) tipEl.style.display = 'none'; }
  document.addEventListener('mouseover', e => { const t = e.target.closest('[data-tooltip]'); if (t) showTip(t); });
  document.addEventListener('mouseout',  e => { const t = e.target.closest('[data-tooltip]'); if (t) hideTip(); });
})();

(function () {
  const sidebar  = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');

  const isDesktop = () => window.matchMedia('(min-width: 768px)').matches;

  function openMobile() {
    sidebar.classList.remove('-translate-x-full');
    sidebar.classList.add('translate-x-0');
    sidebar.setAttribute('data-open', 'true');   // ⬅️ marca abierto
    backdrop.classList.remove('hidden');
  }
  function closeMobile() {
    sidebar.classList.add('-translate-x-full');
    sidebar.classList.remove('translate-x-0');
    sidebar.removeAttribute('data-open');        // ⬅️ marca cerrado
    backdrop.classList.add('hidden');
  }

  window.toggleSidebar = function (forceClose = false) {
    if (isDesktop()) return; // en desktop, la sidebar queda fija y colapsada
    const isOpen = sidebar.classList.contains('translate-x-0');
    if (forceClose === true) return closeMobile();
    if (isOpen) closeMobile(); else openMobile();
  };

  // Al pasar a desktop, garantizamos estado cerrado en móvil
  window.addEventListener('resize', () => {
    if (isDesktop()) closeMobile();
  });
})();



/******************************
 * Notificaciones y Perfil
 ******************************/
function toggleNotifications() {
  const el = document.getElementById('notificationPopup');
  if (el) el.classList.toggle('active');
}
function closeNotifications() {
  const el = document.getElementById('notificationPopup');
  if (el) el.classList.remove('active');
}
function toggleProfile() {
  const el = document.getElementById('profilePopup');
  if (el) el.classList.toggle('active');
}
function closeProfile() {
  const el = document.getElementById('profilePopup');
  if (el) el.classList.remove('active');
}

// Cerrar popups al dar click fuera
window.addEventListener("click", (event) => {
  // Notificaciones
  if (!event.target.matches('.fa-bell') && !event.target.closest('#notificationPopup')) {
    const el = document.getElementById('notificationPopup');
    if (el && el.classList.contains('active')) el.classList.remove('active');
  }
  // Perfil: usa tu wrapper de avatar (ajusta selector si cambia)
  if (!event.target.closest('.flex.items-center.space-x-2') && !event.target.closest('#profilePopup')) {
    const el = document.getElementById('profilePopup');
    if (el && el.classList.contains('active')) el.classList.remove('active');
  }
});

// Exponer funciones globales si las llamas desde HTML
window.toggleSidebar = toggleSidebar;
window.toggleNotifications = toggleNotifications;
window.closeNotifications = closeNotifications;
window.toggleProfile = toggleProfile;
window.closeProfile = closeProfile;

// --- Navbar: dropdowns de Notificaciones y Perfil ---
(function () {
  const notifBtn   = document.getElementById('navNotifBtn');
  const notifPanel = document.getElementById('navNotifPanel');
  const profBtn    = document.getElementById('navProfileBtn');
  const profPanel  = document.getElementById('navProfilePanel');

  function closePanel(panel, btn) {
    if (!panel) return;
    panel.classList.add('hidden');
    panel.classList.remove('open');
    if (btn) btn.setAttribute('aria-expanded', 'false');
  }
  function openPanel(panel, btn) {
    if (!panel) return;
    panel.classList.remove('hidden');
    // forzar reflow para animación
    void panel.offsetWidth;
    panel.classList.add('open');
    if (btn) btn.setAttribute('aria-expanded', 'true');
  }
  function toggle(panel, btn) {
    const open = panel && !panel.classList.contains('hidden');
    // cierra ambos antes de abrir el solicitado
    closePanel(notifPanel, notifBtn);
    closePanel(profPanel,  profBtn);
    if (!open) openPanel(panel, btn);
  }

  notifBtn?.addEventListener('click', (e) => { e.stopPropagation(); toggle(notifPanel, notifBtn); });
  profBtn ?.addEventListener('click', (e) => { e.stopPropagation(); toggle(profPanel,  profBtn ); });

  // Cerrar al hacer click fuera
  document.addEventListener('click', (e) => {
    const inNotif = notifPanel?.contains(e.target) || notifBtn?.contains(e.target);
    const inProf  = profPanel ?.contains(e.target) || profBtn ?.contains(e.target);
    if (!inNotif && !inProf) {
      closePanel(notifPanel, notifBtn);
      closePanel(profPanel,  profBtn);
    }
  });

  // Cerrar con ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closePanel(notifPanel, notifBtn);
      closePanel(profPanel,  profBtn);
    }
  });
})();
