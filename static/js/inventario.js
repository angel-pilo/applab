// Mostrar modal de eliminación
function confirmDeleteReactivo(reactivoId) {
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-reactivo-id').value = reactivoId;
}

// Eliminar reactivo
function deleteReactivo() {
    const reactivoId = document.getElementById('delete-reactivo-id').value;
    const password = document.getElementById('password').value.trim();
    const message = document.getElementById('modal-message');
    message.innerHTML = '';

    if (!password) {
        message.innerHTML = '<p class="text-red-500">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/delete_reactivo/${reactivoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `password=${encodeURIComponent(password)}`
    })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                message.innerHTML = '<p class="text-green-500">Reactivo desactivado correctamente.</p>';
                setTimeout(() => window.location.reload(), 1500);
            } else {
                message.innerHTML = `<p class="text-red-500">${body.message}</p>`;
            }
        })
        .catch(() => {
            message.innerHTML = '<p class="text-red-500">Error de red.</p>';
        });
}

// Mostrar modal de activación
function confirmActivateReactivo(reactivoId) {
    document.getElementById('activation-modal').classList.remove('hidden');
    document.getElementById('activate-reactivo-id').value = reactivoId;
}

// Activar reactivo
function activateReactivo() {
    const reactivoId = document.getElementById('activate-reactivo-id').value;
    const password = document.getElementById('activate-password').value.trim();
    const message = document.getElementById('activation-modal-message');
    message.innerHTML = '';

    if (!password) {
        message.innerHTML = '<p class="text-red-500">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/activate_reactivo/${reactivoId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `password=${encodeURIComponent(password)}`
    })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                message.innerHTML = '<p class="text-green-500">Reactivo activado correctamente.</p>';
                setTimeout(() => window.location.reload(), 1500);
            } else {
                message.innerHTML = `<p class="text-red-500">${body.message}</p>`;
            }
        })
        .catch(() => {
            message.innerHTML = '<p class="text-red-500">Error de red.</p>';
        });
}

// Cerrar modales
function closeModal() {
    document.getElementById('delete-modal').classList.add('hidden');
    document.getElementById('activation-modal').classList.add('hidden');
    document.getElementById('password').value = '';
    document.getElementById('activate-password').value = '';
    document.getElementById('modal-message').innerHTML = '';
    document.getElementById('activation-modal-message').innerHTML = '';
}

// Esta función se ejecuta al hacer clic en un reactivo de la tabla
function selectReactivo(id, nombre, tipo, cantidad, precio) {
    // Actualiza el panel de detalles con los datos del reactivo seleccionado
    document.getElementById("reactivo-name").innerText = nombre;
    document.getElementById("reactivo-type").innerText = tipo;
    document.getElementById("reactivo-quantity").innerText = cantidad;
    document.getElementById("reactivo-price").innerText = precio;

    // Realizar una solicitud al backend para obtener los detalles completos del reactivo
    fetch(`/admin/get_reactivo_details/${id}`)
        .then(response => response.json())
        .then(data => {
            // Asegúrate de que los datos existen antes de actualizarlos
            if (data) {
                document.getElementById("reactivo-entry-date").innerText = data.fecha_entrada || "N/A";
                document.getElementById("reactivo-expiry-date").innerText = data.fecha_vencimiento || "N/A";
                document.getElementById("reactivo-supplier").innerText = data.proveedor_nombre || "N/A";
            }
        })
        .catch(error => {
            console.error("Error al cargar los detalles del reactivo:", error);
        });
}