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

  if (!query || query.trim().length < 2) {
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