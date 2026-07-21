/* --- util: debounce (opcional, evita demasiadas peticiones mientras el usuario escribe) --- */
function debounce(fn, delay=250) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), delay);
  };
}

/* --- render helpers --- */
function hideList() {
  const lista = document.getElementById('lista-sugerencias');
  if (!lista) return;
  lista.classList.add('hidden');
  lista.innerHTML = '';
}

function showNoResults() {
  const lista = document.getElementById('lista-sugerencias');
  if (!lista) return;
  lista.innerHTML = '<li class="p-2 text-gray-500">No hay resultados</li>';
  lista.classList.remove('hidden');
}

function renderResults(pacientes) {
  const lista = document.getElementById('lista-sugerencias');
  if (!lista) return;

  if (!Array.isArray(pacientes) || pacientes.length === 0) {
    showNoResults();
    return;
  }

  lista.innerHTML = pacientes.map(p => {
    const id   = p.id ?? p.paciente_id ?? ''; // por si tu backend usa otra key
    const nom  = p.nombre_completo ?? `${p.nombres ?? ''} ${p.apellidos ?? ''}`.trim();
    const safeNom = String(nom).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    return `
      <li class="p-2 cursor-pointer hover:bg-gray-200"
          onclick="seleccionarPaciente('${safeNom}', '${id}')">
        ${safeNom}${p.telefono ? ` (${p.telefono})` : ''}
      </li>
    `;
  }).join('');
  lista.classList.remove('hidden');
}

/* --- llamada primaria: POST /api/patients/search { q } --- */
async function searchPrimary(query) {
  const res = await fetch('/api/patients/search', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ q: query })
  });
  if (!res.ok) throw new Error('primary_not_ok');
  const data = await res.json();
  // esperamos { results: [...] }
  return Array.isArray(data.results) ? data.results : [];
}

/* --- fallback: GET /api/buscar_pacientes?q=... (tu endpoint anterior) --- */
async function searchFallback(query) {
  const res = await fetch(`/api/buscar_pacientes?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('fallback_not_ok');
  const data = await res.json();
  // tu endpoint antiguo devolvía directamente array
  return Array.isArray(data) ? data : [];
}

/* --- función principal que mantiene tu mismo nombre --- */
const buscarPacientes = debounce(async function(query) {
  const lista = document.getElementById('lista-sugerencias');
  if (!lista) return;

  if (!query || query.trim().length < 1) {
    hideList();
    // Si el usuario vuelve a escribir, limpiamos el hidden para forzar selección válida
    const hidden = document.getElementById('patient_id');
    if (hidden) hidden.value = '';
    return;
  }

  try {
    let resultados = [];
    try {
      resultados = await searchPrimary(query);
    } catch (e) {
      // si falla el primario, intentamos con tu endpoint anterior
      resultados = await searchFallback(query);
    }
    renderResults(resultados);
  } catch (e) {
    console.error('Error buscando pacientes', e);
    hideList();
  }
}, 250);

/* --- mantener tu misma firma --- */
function seleccionarPaciente(nombre, id) {
  const input = document.getElementById('nombre');
  if (input) input.value = nombre;

  // Hidden consistente con orden.html actualizado
  let inputId = document.getElementById('patient_id');
  if (!inputId) {
    inputId = document.createElement('input');
    inputId.type = 'hidden';
    inputId.name = 'patient_id';
    inputId.id = 'patient_id';
    // insertamos después del input de nombre
    if (input && input.parentNode) input.parentNode.appendChild(inputId);
  }
  inputId.value = id;

  hideList();
}

/* --- UX: ocultar la lista si se da clic fuera --- */
document.addEventListener('click', (ev) => {
  const lista = document.getElementById('lista-sugerencias');
  const input = document.getElementById('nombre');
  if (!lista || !input) return;
  if (!lista.contains(ev.target) && ev.target !== input) {
    hideList();
  }
});

//* ===== Orden: validación + toast centrado (sin resaltar inputs) ===== */

/* --- Toast centrado y pequeño (sin barra) --- */
function ensureToastRoot() {
  let root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    root.className = "fixed inset-x-0 top-6 z-50 flex justify-center items-start pointer-events-none";
    document.body.appendChild(root);
  }
  return root;
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/**
 * Muestra un toast Tailwind centrado.
 * Acepta string o array de strings.
 * @param {string|string[]} messages
 * @param {{type?: 'error'|'success', timeout?: number}} opts
 */
function showToast(messages, opts = {}) {
  const { type = "error", timeout = 4000 } = opts;
  const msgs = Array.isArray(messages) ? messages : [messages];

  const root = ensureToastRoot();
  const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;

  const style = type === "error"
    ? { bg: "bg-red-50", ring: "ring-red-200", text: "text-red-800", icon: "text-red-600", title: "Error" }
    : { bg: "bg-green-50", ring: "ring-green-200", text: "text-green-800", icon: "text-green-600", title: "Listo" };

  const html = `
  <div id="${id}" role="alert" aria-live="assertive"
       class="self-start pointer-events-auto transform transition-all duration-200 opacity-0 scale-95
              shadow-lg ring-1 ${style.ring} ${style.bg}
              rounded-[1rem] px-3 py-3 max-w-sm w-[20rem] max-h-[15vh] overflow-hidden">
    <div class="flex items-start">
      <i class="fas fa-exclamation-circle ${style.icon} mt-0.5 mr-2"></i>
      <div class="flex-1 ${style.text}">
        <p class="font-semibold">${style.title}</p>
        <ul class="mt-1 text-sm leading-4">
          ${msgs.map(m => `<li>${escapeHtml(m)}</li>`).join("")}
        </ul>
      </div>
      <button type="button" aria-label="Cerrar"
              class="ml-2 text-gray-500 hover:text-gray-700"
              onclick="document.getElementById('${id}')?.remove()">
        &times;
      </button>
    </div>
  </div>`;

  root.insertAdjacentHTML("beforeend", html);

  // Animación de entrada
  requestAnimationFrame(() => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("opacity-0", "scale-95");
  });

  // Auto-cerrar
  setTimeout(() => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.add("opacity-0", "scale-95");
    setTimeout(() => el.remove(), 150);
  }, timeout);
}

/* --- Limpia cualquier clase roja residual en inputs (por si quedó de código previo) --- */
function clearErrorStyling() {
  ["nombre", "hospital", "cuarto", "doctor"].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.classList.remove("ring-2","ring-red-500","border-red-500","border-red-600","focus:border-red-600");
  });
}

/* --- Intercepción del submit de la Orden (sin resaltar inputs) --- */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form");
  if (!form) return;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    clearErrorStyling();

    const nombre = (document.getElementById("nombre")?.value || "").trim();
    const patient_id = (document.getElementById("patient_id")?.value || "").trim();
    const hospital = document.getElementById("hospital")?.value || "";
    const cuarto = (document.getElementById("cuarto")?.value || "").trim();
    const doctor = document.getElementById("doctor")?.value || "";

    const errs = [];
    if (!nombre || !patient_id) errs.push("Selecciona un paciente desde la lista de sugerencias.");
    if (!hospital) errs.push("Selecciona un hospital.");
    if (!cuarto) errs.push("Ingresa el número/nombre de cuarto.");
    if (!doctor) errs.push("Selecciona un doctor.");
    if (cuarto && !/^[A-Za-z0-9\-# ]{1,15}$/.test(cuarto)) {
      errs.push("El campo 'Cuarto' solo permite letras, números, espacio, -, # (máx. 15).");
    }

    if (errs.length) {
      showToast(errs, { type: "error" });
      return;
    }

    // Validación contra BD (no cambiamos de página si algo está mal)
    try {
      const resp = await fetch("/api/validar_orden", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre, patient_id, hospital, cuarto, doctor }),
      });
      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        const mensajes = data?.errors?.length ? data.errors : ["No se pudo validar la orden."];
        showToast(mensajes, { type: "error" });
        return;
      }

      // OK: enviar realmente para pasar a la siguiente vista
      form.submit();
    } catch (e) {
      console.error(e);
      showToast("No se pudo validar en el servidor. Intenta de nuevo.", { type: "error" });
    }
  });

  // Si el usuario vuelve a teclear el nombre, invalidamos la selección previa
  const nombreInput = document.getElementById("nombre");
  if (nombreInput) {
    nombreInput.addEventListener("input", () => {
      const hidden = document.getElementById("patient_id");
      if (hidden) hidden.value = ""; // obliga a seleccionar de nuevo
    });
  }
});