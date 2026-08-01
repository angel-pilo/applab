// Esta función se ejecuta al hacer clic en un reactivo de la tabla
function selectReactivo(id, nombre, tipo, cantidad, precio) {
    // Actualiza el panel de detalles con los datos del reactivo seleccionado
    document.getElementById("reactivo-name").innerText = nombre;
    document.getElementById("reactivo-type").innerText = tipo;
    document.getElementById("reactivo-quantity").innerText = cantidad;
    document.getElementById("reactivo-price").innerText = precio;
    document.getElementById('no-selection-message').classList.add('hidden');
    document.getElementById('employee-details').classList.remove('hidden');
    openAdminDetailDrawer();

    // Realizar una solicitud al backend para obtener los detalles completos del reactivo
    fetch(`/admin/get_reactivo_details/${id}`)
        .then(response => response.json())
        .then(data => {
            // Asegúrate de que los datos existen antes de actualizarlos
            if (data) {
                document.getElementById("reactivo-supplier").innerText = data.proveedor_nombre || "N/A";
                renderReactivoLots(data.lotes || []);
            }
        })
        .catch(error => {
            console.error("Error al cargar los detalles del reactivo:", error);
        });
}

function renderReactivoLots(lotes) {
    const body = document.getElementById("reactivo-lots");
    const wrapper = document.getElementById("reactivo-lots-wrapper");
    const empty = document.getElementById("reactivo-no-lots");
    if (!body || !wrapper || !empty) return;

    body.replaceChildren();
    if (!lotes.length) {
        wrapper.classList.add("hidden");
        empty.classList.remove("hidden");
        return;
    }

    lotes.forEach((lote) => {
        const row = document.createElement("tr");
        [
            lote.numero_lote || `Lote #${lote.id}`,
            lote.fecha_entrada || "—",
            lote.fecha_vencimiento || "Sin vencimiento",
            lote.existencia_actual ?? 0,
        ].forEach((value) => {
            const cell = document.createElement("td");
            cell.textContent = value;
            row.appendChild(cell);
        });
        body.appendChild(row);
    });
    empty.classList.add("hidden");
    wrapper.classList.remove("hidden");
}

//para la barra de busqueda.
function normalizeText(text) {
    return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function searchInventory() {
    const searchValue = normalizeText(document.getElementById('search-input').value);
    const searchWords = searchValue.split(" "); // Palabras clave
    const rows = document.querySelectorAll('tbody tr');
    let found = false;

    rows.forEach(row => {
        // Extraemos texto de las columnas relevantes: Nombre y Tipo
        const nombre = normalizeText(row.querySelector('td:nth-child(2)').innerText);
        const tipo = normalizeText(row.querySelector('td:nth-child(3)').innerText);

        // Concatenamos para buscar entre ambos campos
        const combinedTextWords = `${nombre} ${tipo}`.split(" ");

        // Verificar que todas las palabras de búsqueda coincidan con inicio de alguna palabra
        const matches = searchWords.every(word =>
            combinedTextWords.some(fullWord => fullWord.startsWith(word))
        );

        if (matches) {
            row.style.display = '';
            found = true;
        } else {
            row.style.display = 'none';
        }

        document.getElementById('not-found-message').classList.toggle('hidden', found);
    });

}
