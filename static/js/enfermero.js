function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarTexts = document.querySelectorAll('.sidebar-text');

    sidebar.classList.toggle('sidebar-expanded');
    sidebar.classList.toggle('sidebar-collapsed');

    sidebarTexts.forEach(text => {
        text.classList.toggle('hidden');
    });
}


function toggleNotifications() {
    const notificationPopup = document.getElementById('notificationPopup');
    notificationPopup.classList.toggle('active');
}

function closeNotifications() {
    const notificationPopup = document.getElementById('notificationPopup');
    notificationPopup.classList.remove('active');
}

function toggleProfile() {
    const profilePopup = document.getElementById('profilePopup');
    profilePopup.classList.toggle('active');
}

function closeProfile() {
    const profilePopup = document.getElementById('profilePopup');
    profilePopup.classList.remove('active');
}

// Close the notification and profile popups if clicked outside
window.onclick = function(event) {
    if (!event.target.matches('.fa-bell') && !event.target.closest('#notificationPopup')) {
        const notificationPopup = document.getElementById('notificationPopup');
        if (notificationPopup.classList.contains('active')) {
            notificationPopup.classList.remove('active');
        }
    }
    if (!event.target.closest('.flex.items-center.space-x-2') && !event.target.closest('#profilePopup')) {
        const profilePopup = document.getElementById('profilePopup');
        if (profilePopup.classList.contains('active')) {
            profilePopup.classList.remove('active');
        }
    }
};

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("modal-analisis");
  const analisisBody = document.getElementById("analisis-body");

  let currentOrdenId = null;
  let currentFinalizarBtn = null;

  /**
   * Abre el modal y consulta las pruebas asociadas a la orden.
   * @param {number} ordenId - ID real de la orden (tabla ordenes.id)
   */
  async function abrirModal(ordenId) {
    currentOrdenId = ordenId;

    // Ubicar el botón "Finalizar" de esta orden y dejarlo deshabilitado por defecto
    currentFinalizarBtn = document.querySelector(
      `.finalizar-btn[data-orden-id="${ordenId}"]`
    );
    if (currentFinalizarBtn) {
      currentFinalizarBtn.disabled = true;
      currentFinalizarBtn.classList.add("opacity-50", "cursor-not-allowed");
    }

    // Mensaje de carga
    analisisBody.innerHTML = `
      <tr>
        <td colspan="3" class="text-center text-gray-500 py-2">
          Cargando análisis...
        </td>
      </tr>
    `;

    try {
      const response = await fetch(`/api/analisis/${ordenId}`);
      if (!response.ok) {
        throw new Error("Respuesta no válida del servidor");
      }

      const pruebas = await response.json();

      if (!pruebas || pruebas.length === 0) {
        analisisBody.innerHTML = `
          <tr>
            <td colspan="3" class="text-center text-gray-500 py-2">
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
              <td class="py-2 text-center">
                <input type="checkbox" class="form-checkbox rounded text-blue-500 chk-analisis">
              </td>
              <td class="py-2">${nombre}</td>
              <td class="py-2">${tipo}</td>
            </tr>
          `;
        });
      }

      modal.classList.remove("hidden");
    } catch (error) {
      console.error(error);
      analisisBody.innerHTML = `
        <tr>
          <td colspan="3" class="text-center text-red-500 py-2">
            Ocurrió un error al cargar los análisis.
          </td>
        </tr>
      `;
      modal.classList.remove("hidden");
    }
  }

  /**
   * Solo habilita "Finalizar" si TODOS los checkbox están seleccionados
   * y el usuario da clic en "Guardar selección".
   */
  function guardarSeleccion() {
    if (!currentFinalizarBtn || !currentOrdenId) return;

    const checkboxes = analisisBody.querySelectorAll(".chk-analisis");

    // Si no hay análisis, no se puede finalizar
    if (checkboxes.length === 0) {
      return;
    }

    const todosMarcados = Array.from(checkboxes).every((chk) => chk.checked);

    if (todosMarcados) {
      currentFinalizarBtn.disabled = false;
      currentFinalizarBtn.classList.remove("opacity-50", "cursor-not-allowed");
    } else {
      currentFinalizarBtn.disabled = true;
      currentFinalizarBtn.classList.add("opacity-50", "cursor-not-allowed");
    }
  }

  /**
   * Llama al backend para cambiar el flujo de la orden a 'en_quimico'.
   * Solo debe ejecutarse cuando el botón "Finalizar" ya está habilitado.
   */
  async function finalizarOrden(ordenId) {
    const btn = document.querySelector(
      `.finalizar-btn[data-orden-id="${ordenId}"]`
    );
    if (!btn || btn.disabled) {
      return; // No debería pasar, pero por si acaso
    }

    // Deshabilitar mientras se procesa
    btn.disabled = true;
    btn.classList.add("opacity-50", "cursor-not-allowed");

    try {
      const resp = await fetch(`/api/muestra/finalizar/${ordenId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!resp.ok) {
        throw new Error("Error al actualizar flujo");
      }

      // Visualmente puedes marcarlo como enviado
      btn.textContent = "Enviado a químico";

      // Opcional: cambiar el punto rojo a verde en la fila
      const fila = btn.closest("tr");
      const dot = fila?.querySelector("span.h-3.w-3");
      if (dot) {
        dot.classList.remove("bg-red-600");
        dot.classList.add("bg-green-600");
      }

    } catch (error) {
      console.error(error);
      // Si falla, volvemos a habilitar el botón para reintentar
      btn.disabled = false;
      btn.classList.remove("opacity-50", "cursor-not-allowed");
      alert("Ocurrió un error al finalizar la muestra. Intenta de nuevo.");
    }
  }

  function cerrarModal() {
    const checkboxes = analisisBody.querySelectorAll(".chk-analisis");
    checkboxes.forEach((chk) => {
      chk.checked = false;
    });

    modal.classList.add("hidden");
  }

  // Exponer funciones globales para los onclick del HTML
  window.abrirModal = abrirModal;
  window.cerrarModal = cerrarModal;
  window.guardarSeleccion = guardarSeleccion;
  window.finalizarOrden = finalizarOrden;
});