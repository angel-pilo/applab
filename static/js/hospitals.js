function confirmDelete(hospitalId) {
    console.log("Hospital a eliminar:", hospitalId);
    const modal = document.getElementById('delete-modal');

    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('delete-hospital-id').value = hospitalId;
    } else {
        console.error("No se encontró el modal de eliminación");
    }
}

function deleteHospital() {
    const hospitalId = document.getElementById('delete-hospital-id').value;
    const password = document.getElementById('password').value.trim();
    const modalMessage = document.getElementById('modal-message');

    // Limpiar mensajes anteriores
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
                closeModal(); // Cerrar modal
                console.log("Recargando página después de eliminar...");
                window.location.href = window.location.href; // Recargar la página
            }, 2000);
        } else {
            modalMessage.innerHTML = `<p class="text-red-600 text-sm">${body.message}</p>`;
            console.error("Error del servidor al eliminar:", body.message);
        }
    })
    .catch(error => {
        console.error('Error en fetch:', error);
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
                console.log("Recargando página después de activar...");
                location.reload(); // Recargar la página después de activar
            }, 1500);
        } else {
            console.error("Error del servidor al activar:", body.message);
            modalMessage.innerHTML = `<p class="text-red-600 text-sm">${body.message}</p>`;
        }
    })
    .catch(error => {
        console.error('Error en fetch:', error);
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">Hubo un error al comunicarse con el servidor.</p>';
    });
}



function closeModal() {
    const deleteModal = document.getElementById('delete-modal');
    const activationModal = document.getElementById('activation-modal');
    const passwordField = document.getElementById('password');
    const activatePasswordField = document.getElementById('activate-password');
    const modalMessage = document.getElementById('modal-message');
    const activationMessage = document.getElementById('activation-modal-message');

    if (deleteModal) {
        deleteModal.classList.add('hidden');
    }
    
    if (activationModal) {
        activationModal.classList.add('hidden');
    }

    if (passwordField) {
        passwordField.value = '';
    }

    if (activatePasswordField) {
        activatePasswordField.value = '';
    }

    if (modalMessage) {
        modalMessage.innerHTML = '';
    }

    if (activationMessage) {
        activationMessage.innerHTML = '';
    }
}

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