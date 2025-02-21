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






//COSAS QUE SIRVEN PARA EMPLEADOS

// admin.js

function showDetails(employee) {
    document.getElementById('employee-name').innerText = employee.name;
    document.getElementById('employee-lastname').innerText = employee.lastname;
    document.getElementById('employee-role').innerText = employee.role;
    document.getElementById('employee-emergency-contact').innerText = employee.emergencyContact;
    document.getElementById('employee-allergies').innerText = employee.allergies;
    document.getElementById('employee-joining-date').innerText = employee.joiningDate;
    document.getElementById('no-selection-message').classList.add('hidden');
    document.getElementById('employee-details').classList.remove('hidden');
}

function confirmDelete(employeeId) {
    document.querySelector(`input[value="${employeeId}"]`).checked = true;
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-employee-id').value = employeeId;
}

function closeModal() {
    document.getElementById('delete-modal').classList.add('hidden');
}

function searchEmployee() {
    const searchValue = document.getElementById('search-input').value.toLowerCase().trim();
    const rows = document.querySelectorAll('tbody tr');
    let found = false;

    rows.forEach(row => {
        const name = row.querySelector('td:nth-child(2)').innerText.toLowerCase().trim();
        const nameWords = name.split(' ');
        if (nameWords.some(word => word.startsWith(searchValue))) {
            row.style.display = '';
            found = true;
        } else {
            row.style.display = 'none';
        }
    });

    const notFoundMessage = document.getElementById('not-found-message');
    if (!found) {
        notFoundMessage.classList.remove('hidden');
    } else {
        notFoundMessage.classList.add('hidden');
    }
}

function toggleFilterMenu() {
    document.getElementById('filter-menu').classList.toggle('hidden');
}

function applyFilters() {
    const roleFilter = document.querySelector('input[name="filter-role"]:checked')?.value;
    const emergencyContactFilter = document.getElementById('filter-emergency-contact').checked;
    const allergiesFilter = document.getElementById('filter-allergies').checked;
    const rows = document.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const role = row.querySelector('td:nth-child(3)').innerText.toLowerCase();
        const emergencyContact = row.querySelector('td:nth-child(4)').innerText.toLowerCase();
        const allergies = row.querySelector('td:nth-child(5)').innerText.toLowerCase();

        let showRow = true;

        if (roleFilter && !role.includes(roleFilter)) {
            showRow = false;
        }
        if (emergencyContactFilter && !emergencyContact.includes('contacto de emergencia')) {
            showRow = false;
        }
        if (allergiesFilter && !allergies.includes('alergias')) {
            showRow = false;
        }

        row.style.display = showRow ? '' : 'none';
    });

    toggleFilterMenu(); // Close the filter menu after applying filters
}

window.onload = function() {
    document.getElementById('no-selection-message').classList.remove('hidden');
    document.getElementById('employee-details').classList.add('hidden');
    const radioButtons = document.querySelectorAll('input[name="employee"]');
    radioButtons.forEach(radio => radio.checked = false);
}


