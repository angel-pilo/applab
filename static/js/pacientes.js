// Mostrar modal de eliminación
function confirmDeletePatient(patientId) {
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-patient-id').value = patientId;
}

function deletePatient() {
    const patientId = document.getElementById('delete-patient-id').value;
    const password = document.getElementById('password').value.trim();
    const message = document.getElementById('modal-message');
    message.innerHTML = '';

    if (!password) {
        message.innerHTML = '<p class="text-red-500">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/delete_patient/${patientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `password=${encodeURIComponent(password)}`
    })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                message.innerHTML = '<p class="text-green-500">Paciente desactivado correctamente.</p>';
                setTimeout(() => window.location.reload(), 1500);
            } else {
                message.innerHTML = `<p class="text-red-500">${body.message}</p>`;
            }
        })
        .catch(() => {
            message.innerHTML = '<p class="text-red-500">Error de red.</p>';
        });
}

function confirmActivatePatient(patientId) {
    document.getElementById('activation-modal').classList.remove('hidden');
    document.getElementById('activate-patient-id').value = patientId;
}

function activatePatient() {
    const patientId = document.getElementById('activate-patient-id').value;
    const password = document.getElementById('activate-password').value.trim();
    const message = document.getElementById('activation-modal-message');
    message.innerHTML = '';

    if (!password) {
        message.innerHTML = '<p class="text-red-500">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/activate_patient/${patientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `password=${encodeURIComponent(password)}`
    })
        .then(res => res.json().then(data => ({ status: res.status, body: data })))
        .then(({ status, body }) => {
            if (status === 200) {
                message.innerHTML = '<p class="text-green-500">Paciente activado correctamente.</p>';
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
    const searchInput = document.getElementById("search-patient");
    const rows = document.querySelectorAll("tbody tr");
    const notFoundMessage = document.getElementById("not-found-message");

    searchInput.addEventListener("input", () => {
        const value = searchInput.value.trim().toLowerCase();
        let found = false;

        rows.forEach(row => {
            const name = row.querySelector("td:nth-child(2)").textContent.toLowerCase();
            const match = name.includes(value);
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
