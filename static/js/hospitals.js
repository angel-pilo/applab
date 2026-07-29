//para buscar
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-hospital");
    const rows = document.querySelectorAll("tbody tr");
    const notFoundMessage = document.getElementById("not-found-message");

    function normalizeText(text) {
        return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
    }

    searchInput.addEventListener("input", function () {
        const searchValue = normalizeText(searchInput.value);
        const searchWords = searchValue.split(" "); // Divide la búsqueda en palabras clave
        let found = false;

        rows.forEach(row => {
            const name = normalizeText(row.querySelector("td:nth-child(2)").textContent);
            const nameWords = name.split(" "); // Divide el nombre en palabras

            // Verifica si todas las palabras de la búsqueda coinciden con el inicio de alguna palabra en el nombre
            const matches = searchWords.every(word =>
                nameWords.some(fullWord => fullWord.startsWith(word))
            );

            if (matches) {
                row.style.display = "";
                found = true;
            } else {
                row.style.display = "none";
            }
        });

        notFoundMessage.classList.toggle("hidden", found);
    });
});


//filtrar hospitales
document.addEventListener("DOMContentLoaded", function () {
    const filterMenu = document.getElementById("filter-menu");
    const applyFilterButton = document.getElementById("apply-filters");
    const filterStatusOptions = document.querySelectorAll('input[name="filter-status"]');
    const filterStateOptions = document.getElementById("filter-state");
    const rows = Array.from(document.querySelectorAll("tbody tr"));
    const notFoundMessage = document.getElementById("not-found-message");

    // Función para mostrar/ocultar menú de filtros
    window.toggleFilterMenu = function () {
        filterMenu.classList.toggle("hidden");
    };

    // Aplicar filtros al hacer click en "Aplicar filtros"
    applyFilterButton.addEventListener("click", function () {
        applyFilters();
    });

    // Función para ordenar la tabla por ID
    function sortTable() {
        const tbody = document.querySelector("tbody");
        const sortedRows = [...tbody.rows].sort((a, b) => {
            const idA = parseInt(a.cells[0].textContent.trim());
            const idB = parseInt(b.cells[0].textContent.trim());
            return idA - idB; // Orden ascendente
        });

        tbody.innerHTML = ""; // Limpiar la tabla
        sortedRows.forEach(row => tbody.appendChild(row)); // Agregar filas ordenadas
    }

    function applyFilters() {
        const selectedStatus = document.querySelector('input[name="filter-status"]:checked')?.value;
        const selectedState = filterStateOptions.value.toLowerCase();
        let found = false;

        // Filtrar y ordenar por ID
        const filteredRows = rows.filter(row => {
            const status = row.querySelector("td:nth-child(6)").textContent.trim().toLowerCase();
            const state = row.querySelector("td:nth-child(5)").textContent.split(",").pop().trim().toLowerCase(); // Extraer solo el estado

            const statusMatch = selectedStatus === "all" || status === selectedStatus;
            const stateMatch = selectedState === "all" || state === selectedState;

            return statusMatch && stateMatch;
        });

        // Ordenar por ID antes de mostrar la tabla
        filteredRows.sort((a, b) => {
            const idA = parseInt(a.querySelector("td:nth-child(1)").textContent.trim());
            const idB = parseInt(b.querySelector("td:nth-child(1)").textContent.trim());
            return idA - idB; // Orden ascendente
        });

        // Vaciar la tabla y agregar las filas filtradas y ordenadas
        const tbody = document.querySelector("tbody");
        tbody.innerHTML = "";
        filteredRows.forEach(row => tbody.appendChild(row));

        found = filteredRows.length > 0;
        notFoundMessage.classList.toggle("hidden", found);

        filterMenu.classList.add("hidden"); // Ocultar menú después de aplicar filtro
    }

    // Llamar a la función para ordenar la tabla al cargar la página
    sortTable();
});
