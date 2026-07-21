document.addEventListener('DOMContentLoaded', () => {
    const search = document.querySelector('[data-admin-catalog-search]');
    const table = document.querySelector('[data-admin-catalog-table]');
    if (!search || !table) return;

    const rows = [...table.querySelectorAll('tbody tr')].filter(row => row.querySelector('td'));
    const emptyMessage = document.getElementById('not-found-message');

    const normalize = value => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
    const apply = () => {
        const query = normalize(search.value.trim());
        const status = document.querySelector('input[name="filter-status"]:checked')?.value || 'all';
        let visible = 0;
        rows.forEach(row => {
            const text = normalize(row.textContent);
            const inactive = text.includes('inactivo');
            const matchesStatus = status === 'all' || (status === 'activo' && !inactive) || (status === 'inactivo' && inactive);
            const show = text.includes(query) && matchesStatus;
            row.style.display = show ? '' : 'none';
            if (show) visible += 1;
        });
        emptyMessage?.classList.toggle('hidden', visible > 0 || rows.length === 0);
    };

    search.addEventListener('input', apply);
    document.getElementById('apply-filters')?.addEventListener('click', () => {
        apply();
        document.getElementById('filter-menu')?.classList.add('hidden');
    });
});

function openAdminDetailDrawer() {
    document.querySelector('.admin-surface')?.classList.add('admin-detail-open');
}

function closeAdminDetailDrawer() {
    document.getElementById('employee-details')?.classList.add('hidden');
    document.querySelector('.admin-surface')?.classList.remove('admin-detail-open');
}

document.addEventListener('DOMContentLoaded', () => {
    const details = document.getElementById('employee-details');
    const drawer = details?.closest('section');
    if (!details || !drawer) return;

    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'admin-detail-close';
    closeButton.setAttribute('aria-label', 'Cerrar detalles');
    closeButton.innerHTML = '<i class="fas fa-times" aria-hidden="true"></i>';
    closeButton.addEventListener('click', closeAdminDetailDrawer);
    drawer.firstElementChild?.prepend(closeButton);

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && !details.classList.contains('hidden')) {
            closeAdminDetailDrawer();
        }
    });
});
