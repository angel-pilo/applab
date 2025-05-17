async function buscarPacientes(query) {
  const lista = document.getElementById('lista-sugerencias');
  if (!query) {
    lista.innerHTML = '';
    lista.classList.add('hidden');
    return;
  }

  try {
    const res = await fetch(`/api/buscar_pacientes?q=${encodeURIComponent(query)}`);
    const pacientes = await res.json();

    if (pacientes.length === 0) {
      lista.innerHTML = '<li class="p-2 text-gray-500">No hay resultados</li>';
      
      lista.classList.remove('hidden');
      return;
    }

    lista.innerHTML = pacientes.map(p => `
      <li
        class="p-2 cursor-pointer hover:bg-gray-200"
        onclick="seleccionarPaciente('${p.nombre_completo}', ${p.id})"
      >${p.nombre_completo}</li>
    `).join('');
    lista.classList.remove('hidden');
  } catch (e) {
    console.error('Error buscando pacientes', e);
  }
}

function seleccionarPaciente(nombre, id) {
  const input = document.getElementById('nombre');
  input.value = nombre;

  // Puedes almacenar el ID en un input hidden si necesitas enviar al backend
  let inputId = document.getElementById('paciente_id');
  if (!inputId) {
    inputId = document.createElement('input');
    inputId.type = 'hidden';
    inputId.name = 'paciente_id';
    inputId.id = 'paciente_id';
    input.parentNode.appendChild(inputId);
  }
  inputId.value = id;

  // Ocultar la lista de sugerencias
  document.getElementById('lista-sugerencias').classList.add('hidden');
}