let adminConfirmationEndpoint = null;
let adminConfirmationLastFocus = null;

function openAdminConfirmation({ endpoint, entity, action }) {
    const modal = document.getElementById('admin-confirm-modal');
    const submit = document.getElementById('admin-confirm-submit');
    const icon = document.getElementById('admin-confirm-icon');
    const isDelete = action === 'eliminar';
    if (!modal || !submit || !icon) return;

    adminConfirmationLastFocus = document.activeElement;
    adminConfirmationEndpoint = endpoint;
    document.getElementById('admin-confirm-title').textContent =
        isDelete ? 'Confirmar eliminación' : 'Confirmar activación';
    document.getElementById('admin-confirm-text').textContent =
        `¿Deseas ${action} ${entity}?`;
    document.getElementById('admin-confirm-message').textContent = '';
    document.getElementById('admin-confirm-message').className = 'admin-confirm-message';
    document.getElementById('admin-confirm-password').value = '';
    submit.textContent = isDelete ? 'Eliminar registro' : 'Activar registro';
    submit.className = `admin-confirm-submit ${isDelete ? 'is-delete' : 'is-activate'}`;
    icon.className = `admin-confirm-icon ${isDelete ? 'is-delete' : 'is-activate'}`;
    icon.innerHTML = `<i class="fas ${isDelete ? 'fa-trash-alt' : 'fa-check'}" aria-hidden="true"></i>`;

    modal.classList.remove('hidden');
    document.body.classList.add('admin-confirm-open');
    document.getElementById('admin-confirm-password').focus();
}

function closeAdminConfirmation() {
    document.getElementById('admin-confirm-modal')?.classList.add('hidden');
    document.body.classList.remove('admin-confirm-open');
    adminConfirmationEndpoint = null;
    adminConfirmationLastFocus?.focus();
}

async function submitAdminConfirmation() {
    const passwordInput = document.getElementById('admin-confirm-password');
    const password = passwordInput.value.trim();
    const message = document.getElementById('admin-confirm-message');
    const submit = document.getElementById('admin-confirm-submit');

    if (!password) {
        message.className = 'admin-confirm-message is-error';
        message.textContent = 'Ingresa tu contraseña para continuar.';
        passwordInput.focus();
        return;
    }

    submit.disabled = true;
    submit.textContent = 'Procesando...';

    try {
        const response = await fetch(adminConfirmationEndpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({password}),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.message || 'No se pudo completar la acción.');
        message.className = 'admin-confirm-message is-success';
        message.textContent = data.message || 'Acción completada correctamente.';
        setTimeout(() => window.location.reload(), 700);
    } catch (error) {
        message.className = 'admin-confirm-message is-error';
        message.textContent = error.message;
        submit.disabled = false;
        submit.textContent = submit.classList.contains('is-delete') ? 'Eliminar registro' : 'Activar registro';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('admin-confirm-submit')?.addEventListener('click', submitAdminConfirmation);
    document.querySelectorAll('[data-admin-confirm-close]').forEach(button => {
        button.addEventListener('click', closeAdminConfirmation);
    });
    document.getElementById('admin-confirm-password')?.addEventListener('keydown', event => {
        if (event.key === 'Enter') submitAdminConfirmation();
    });
    document.addEventListener('keydown', event => {
        const modal = document.getElementById('admin-confirm-modal');
        if (event.key === 'Escape' && modal && !modal.classList.contains('hidden')) {
            closeAdminConfirmation();
        }
    });
});
