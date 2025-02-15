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