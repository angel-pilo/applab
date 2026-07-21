function verificarResultadosCompletos() {
  const filas = document.querySelectorAll('tbody tr');
  let todosCompletados = true;

  filas.forEach((row) => {
    const resultadoInput = row.querySelector('input[name="resultado"]');
    if (!resultadoInput || resultadoInput.value.trim() === '') {
      todosCompletados = false;
    }
  });

  const finalizarButton = document.querySelector('#finalizar-btn');
  finalizarButton.disabled = !todosCompletados;
}

// Llamar a la función cada vez que se ingrese un resultado
document.querySelectorAll('input[name="resultado"]').forEach(input => {
  input.addEventListener('input', verificarResultadosCompletos);
});

// Iniciar la verificación al cargar la página
document.addEventListener('DOMContentLoaded', verificarResultadosCompletos);

function verificarResultadosCompletos() {
  const filas = document.querySelectorAll('tbody tr');
  let todosCompletados = true;

  filas.forEach((row) => {
    const resultadoInput = row.querySelector('input[name="resultado"]');
    if (!resultadoInput || resultadoInput.value.trim() === '') {
      todosCompletados = false;
    }
  });

  const finalizarButton = document.querySelector('#finalizar-btn');
  finalizarButton.disabled = !todosCompletados;
}

// Llamar a la función cada vez que se ingrese un resultado
document.querySelectorAll('input[name="resultado"]').forEach(input => {
  input.addEventListener('input', verificarResultadosCompletos);
});

// Iniciar la verificación al cargar la página
document.addEventListener('DOMContentLoaded', verificarResultadosCompletos);


document.addEventListener('DOMContentLoaded', function () {
});


document.addEventListener("DOMContentLoaded", () => {
  // Referencias a modales y cuerpos de tablas
  const modalFaltantes = document.getElementById("modal-faltantes");
  const modalFaltantesBody = document.getElementById("modal-faltantes-body");

  const modalAnalisis = document.getElementById("modal-analisis");
  const analisisBody = document.getElementById("analisis-body");

  // Datos de faltantes desde el template (se asigna en window.faltantesData)
  const faltantesData = Array.isArray(window.faltantesData)
    ? window.faltantesData
    : [];

  function formatoFolio(id) {
    return String(id).padStart(5, "0");
  }

  // Modal 1: abre lista completa de faltantes
  function abrirModalFaltantes() {
    modalFaltantesBody.innerHTML = "";

    if (!faltantesData || faltantesData.length === 0) {
      modalFaltantesBody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center text-gray-500 py-2">
            No hay órdenes pendientes de muestra.
          </td>
        </tr>
      `;
      modalFaltantes.classList.remove("hidden");
      return;
    }

    faltantesData.forEach((orden) => {
      const folio = orden.id;
      const folioStr = formatoFolio(folio);
      const nombre = orden.nombre_paciente || "";
      const lugar = orden.cuarto || "";

      modalFaltantesBody.innerHTML += `
        <tr class="border-b hover:bg-gray-50">
          <td class="py-2 text-red-600 font-bold">#${folioStr}</td>
          <td class="py-2">${nombre}</td>
          <td class="py-2">${lugar}</td>
          <td class="py-2 text-center">
            <button
              type="button"
              class="btn-cancelar px-3 py-1 rounded-[1rem]"
              onclick="abrirModalAnalisis(${folio})"
            >
              Ver análisis
            </button>
          </td>
        </tr>
      `;
    });

    modalFaltantes.classList.remove("hidden");
  }

  function cerrarModalFaltantes() {
    modalFaltantes.classList.add("hidden");
  }

  // Modal 2: muestra los análisis de una orden en SOLO lectura (sin checkbox)
  async function abrirModalAnalisis(ordenId) {
    analisisBody.innerHTML = `
      <tr>
        <td colspan="2" class="text-center text-gray-500 py-2">
          Cargando análisis...
        </td>
      </tr>
    `;
    modalAnalisis.classList.remove("hidden");

    try {
      const resp = await fetch(`/api/analisis/${ordenId}`);
      if (!resp.ok) {
        throw new Error("Respuesta no válida del servidor");
      }

      const pruebas = await resp.json();

      if (!pruebas || pruebas.length === 0) {
        analisisBody.innerHTML = `
          <tr>
            <td colspan="2" class="text-center text-gray-500 py-2">
              Sin análisis registrados para esta orden.
            </td>
          </tr>
        `;
      } else {
        analisisBody.innerHTML = "";
        pruebas.forEach((p) => {
          const nombre = p.nombre || p.nombre_prueba || "";
          const tipo = p.tipo || p.tipo_prueba || "";

          analisisBody.innerHTML += `
            <tr class="border-b">
              <td class="py-2">${nombre}</td>
              <td class="py-2">${tipo}</td>
            </tr>
          `;
        });
      }
    } catch (error) {
      console.error(error);
      analisisBody.innerHTML = `
        <tr>
          <td colspan="2" class="text-center text-red-500 py-2">
            Ocurrió un error al cargar los análisis.
          </td>
        </tr>
      `;
    }
  }

  function cerrarModalAnalisis() {
    modalAnalisis.classList.add("hidden");
  }

  // Exponer funciones globales para los onclick del HTML
  window.abrirModalFaltantes = abrirModalFaltantes;
  window.cerrarModalFaltantes = cerrarModalFaltantes;
  window.abrirModalAnalisis = abrirModalAnalisis;
  window.cerrarModalAnalisis = cerrarModalAnalisis;
});

