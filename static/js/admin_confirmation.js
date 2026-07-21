let adminConfirmationEndpoint = null;

function openAdminConfirmation({ endpoint, entity, action }) {
    const modal = document.getElementById('admin-confirm-modal');
    const submit = document.getElementById('admin-confirm-submit');
    const isDelete = action === 'eliminar';

    adminConfirmationEndpoint = endpoint;
    document.getElementById('admin-confirm-title').textContent = isDelete ? 'Confirmar eliminación' : 'Confirmar activación';
    document.getElementById('admin-confirm-text').textContent = `¿Deseas ${action} ${entity}?`;
    document.getElementById('admin-confirm-message').textContent = '';
    document.getElementById('admin-confirm-password').value = '';
    submit.textContent = isDelete ? 'Eliminar' : 'Activar';
    submit.className = `rounded-xl px-4 py-2 text-sm font-semibold text-white ${isDelete ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'}`;
    modal.classList.remove('hidden');
    document.getElementById('admin-confirm-password').focus();
}

function closeAdminConfirmation() {
    document.getElementById('admin-confirm-modal')?.classList.add('hidden');
    adminConfirmationEndpoint = null;
}

async function submitAdminConfirmation() {
    const password = document.getElementById('admin-confirm-password').value.trim();
    const message = document.getElementById('admin-confirm-message');
    if (!password) {
        message.className = 'mt-3 text-center text-sm text-red-600';
        message.textContent = 'La contraseña es requerida.';
        return;
    }

    try {
        const response = await fetch(adminConfirmationEndpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({password}),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'No se pudo completar la acción.');
        message.className = 'mt-3 text-center text-sm text-emerald-600';
        message.textContent = data.message || 'Acción completada.';
        setTimeout(() => window.location.reload(), 700);
    } catch (error) {
        message.className = 'mt-3 text-center text-sm text-red-600';
        message.textContent = error.message;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('admin-confirm-submit')?.addEventListener('click', submitAdminConfirmation);
    document.getElementById('admin-confirm-modal')?.addEventListener('click', event => {
        if (event.target.id === 'admin-confirm-modal') closeAdminConfirmation();
    });
});
