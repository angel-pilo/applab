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
