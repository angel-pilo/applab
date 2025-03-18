function confirmDelete(hospitalId) {
    console.log("Hospital a eliminar:", hospitalId);
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-hospital-id').value = hospitalId;
}

function deleteHospital() {
    const hospitalId = document.getElementById('delete-hospital-id').value;
    const password = document.getElementById('password').value.trim();
    const modalMessage = document.getElementById('modal-message');

    modalMessage.innerHTML = '';

    if (!password) {
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/delete_hospital/${hospitalId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `password=${encodeURIComponent(password)}`
    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(({ status, body }) => {
        if (status === 200) {
            modalMessage.innerHTML = '<p class="text-green-600 text-sm">Hospital desactivado correctamente.</p>';
            setTimeout(() => {
                closeModal();
                location.reload();
            }, 2000);
        } else {
            modalMessage.innerHTML = `<p class="text-red-600 text-sm">${body.message}</p>`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">Hubo un error al comunicarse con el servidor.</p>';
    });
}

function confirmActivate(hospitalId) {
    console.log("Hospital a activar:", hospitalId);
    const modal = document.getElementById('activation-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('activate-hospital-id').value = hospitalId;
    } else {
        console.error("No se encontró el modal de activación");
    }
}

function activateHospital() {
    const hospitalId = document.getElementById('activate-hospital-id').value;
    const password = document.getElementById('activate-password').value.trim();
    const modalMessage = document.getElementById('activation-modal-message');

    modalMessage.innerHTML = '';

    if (!password) {
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/activate_hospital/${hospitalId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `password=${encodeURIComponent(password)}`
    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(({ status, body }) => {
        if (status === 200) {
            modalMessage.innerHTML = '<p class="text-green-600 text-sm">Hospital activado correctamente.</p>';
            setTimeout(() => {
                closeModal();
                location.reload();
            }, 2000);
        } else {
            modalMessage.innerHTML = `<p class="text-red-600 text-sm">${body.message}</p>`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">Hubo un error al comunicarse con el servidor.</p>';
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