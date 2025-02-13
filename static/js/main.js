function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('sidebar-expanded');
    sidebar.classList.toggle('sidebar-collapsed');
}

function toggleNotifications() {
    const notificationPopup = document.getElementById('notificationPopup');
    notificationPopup.classList.toggle('active');
}

function toggleProfile() {
    const profilePopup = document.getElementById('profilePopup');
    profilePopup.classList.toggle('active');
}
