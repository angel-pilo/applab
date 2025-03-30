// Mostrar modal de eliminación
function confirmDeleteProveedor(proveedorId) {
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-proveedor-id').value = proveedorId;
}

function deleteProveedor() {
    const proveedorId = document.getElementById('delete-proveedor-id').value;
    const password = document.getElementById('password').value.trim();
    const message = document.getElementById('modal-message');
    message.innerHTML = '';

    if (!password) {
        message.innerHTML = '<p class="text-red-500">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/delete_proveedor/${proveedorId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `password=${encodeURIComponent(password)}`
    })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                message.innerHTML = '<p class="text-green-500">Proveedor desactivado correctamente.</p>';
                setTimeout(() => window.location.reload(), 1500);
            } else {
                message.innerHTML = `<p class="text-red-500">${body.message}</p>`;
            }
        })
        .catch(() => {
            message.innerHTML = '<p class="text-red-500">Error de red.</p>';
        });
}

function confirmActivateProveedor(proveedorId) {
    document.getElementById('activation-modal').classList.remove('hidden');
    document.getElementById('activate-proveedor-id').value = proveedorId;
}

function activateProveedor() {
    const proveedorId = document.getElementById('activate-proveedor-id').value;
    const password = document.getElementById('activate-password').value.trim();
    const message = document.getElementById('activation-modal-message');
    message.innerHTML = '';

    if (!password) {
        message.innerHTML = '<p class="text-red-500">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/activate_proveedor/${proveedorId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `password=${encodeURIComponent(password)}`
    })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                message.innerHTML = '<p class="text-green-500">Proveedor activado correctamente.</p>';
                setTimeout(() => window.location.reload(), 1500);
            } else {
                message.innerHTML = `<p class="text-red-500">${body.message}</p>`;
            }
        })
        .catch(() => {
            message.innerHTML = '<p class="text-red-500">Error de red.</p>';
        });
}

function closeModal() {
    document.getElementById('delete-modal').classList.add('hidden');
    document.getElementById('activation-modal').classList.add('hidden');
    document.getElementById('password').value = '';
    document.getElementById('activate-password').value = '';
    document.getElementById('modal-message').innerHTML = '';
    document.getElementById('activation-modal-message').innerHTML = '';
}

// Buscador y filtros

document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("search-proveedor");
    const rows = document.querySelectorAll("tbody tr");
    const notFoundMessage = document.getElementById("not-found-message");

    searchInput.addEventListener("input", () => {
        const value = searchInput.value.trim().toLowerCase();
        let found = false;

        rows.forEach(row => {
            const nombre = row.querySelector("td:nth-child(2)").textContent.toLowerCase();
            const match = nombre.includes(value);
            row.style.display = match ? "" : "none";
            if (match) found = true;
        });

        notFoundMessage.classList.toggle("hidden", found);
    });
});

function toggleFilterMenu() {
    document.getElementById("filter-menu").classList.toggle("hidden");
}

document.getElementById("apply-filters").addEventListener("click", () => {
    const selected = document.querySelector('input[name="filter-status"]:checked').value;
    const rows = document.querySelectorAll("tbody tr");
    const notFoundMessage = document.getElementById("not-found-message");
    let found = false;

    rows.forEach(row => {
        const estado = row.querySelector(".estado").textContent.trim().toLowerCase();
        const shouldShow = (selected === "all") || 
            (selected === "activo" && estado === "activo") || 
            (selected === "inactivo" && estado === "inactivo");

        row.style.display = shouldShow ? "" : "none";
        if (shouldShow) found = true;
    });

    notFoundMessage.classList.toggle("hidden", found);
    toggleFilterMenu();
});