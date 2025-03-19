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
function selectEmployee(employeeId, name, lastname, role, emergencyContact, allergies, joiningDate) {
    // Selecciona el input de tipo radio
    document.getElementById('employee-' + employeeId).checked = true;
    // Muestra los detalles
    showDetails({ name: name, lastname: lastname, role: role, emergencyContact: emergencyContact, allergies: allergies, joiningDate: joiningDate });
}


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
    console.log("Empleado a eliminar:", employeeId);
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-employee-id').value = employeeId;
}

function deleteEmployee() {
    const employeeId = document.getElementById('delete-employee-id').value;
    const password = document.getElementById('password').value.trim();
    const modalMessage = document.getElementById('modal-message'); // Obtener el contenedor de mensajes

    // Limpiar mensajes anteriores
    modalMessage.innerHTML = '';

    // Validar que la contraseña no esté vacía
    if (!password) {
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">La contraseña es requerida.</p>';
        return;
    }

    // Enviar la solicitud al servidor
    fetch(`/admin/delete_employee/${employeeId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `password=${encodeURIComponent(password)}`
    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(({ status, body }) => {
        if (status === 200) {
            modalMessage.innerHTML = '<p class="text-green-600 text-sm">Empleado desactivado correctamente.</p>';
            setTimeout(() => {
                closeModal(); // Cerrar modal después de 2 segundos
                location.reload(); // Refrescar la página
            }, 2000);
        } else {
            // Mostrar el mensaje de error sin fondo
            modalMessage.innerHTML = `<p class="text-red-600 text-sm">${body.message}</p>`;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">Hubo un error al comunicarse con el servidor.</p>';
    });
}

function confirmActivate(employeeId) {
    console.log("Empleado a activar:", employeeId);
    const modal = document.getElementById('activation-modal');

    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('activate-employee-id').value = employeeId;
    } else {
        console.error("No se encontró el modal de activación");
    }
}

function activateEmployee() {
    const employeeId = document.getElementById('activate-employee-id').value;
    const password = document.getElementById('activate-password').value.trim();
    const modalMessage = document.getElementById('activation-modal-message');

    modalMessage.innerHTML = '';

    if (!password) {
        modalMessage.innerHTML = '<p class="text-red-600 text-sm">La contraseña es requerida.</p>';
        return;
    }

    fetch(`/admin/activate_employee/${employeeId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `password=${encodeURIComponent(password)}`
    })
    .then(response => response.json().then(data => ({ status: response.status, body: data })))
    .then(({ status, body }) => {
        if (status === 200) {
            modalMessage.innerHTML = '<p class="text-green-600 text-sm">Empleado activado correctamente.</p>';
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


//buscar empleado
function normalizeText(text) {
    return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function searchEmployee() {
    const searchValue = normalizeText(document.getElementById('search-input').value);
    const searchWords = searchValue.split(" "); // Divide la búsqueda en palabras clave
    const rows = document.querySelectorAll('tbody tr');
    let found = false;

    rows.forEach(row => {
        const name = normalizeText(row.querySelector('td:nth-child(2)').innerText);
        const lastName = normalizeText(row.querySelector('td:nth-child(3)').innerText);
        const fullNameWords = `${name} ${lastName}`.split(" "); // Divide el nombre y apellido en palabras

        // Verifica si todas las palabras de la búsqueda coinciden con el inicio de alguna palabra en el nombre completo
        const matches = searchWords.every(word => 
            fullNameWords.some(fullWord => fullWord.startsWith(word))
        );

        if (matches) {
            row.style.display = '';
            found = true;
        } else {
            row.style.display = 'none';
        }
    });

    document.getElementById('not-found-message').classList.toggle('hidden', found);
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

        function validateForm() {
            const requiredFields = document.querySelectorAll('[required]');
            let valid = true;

            requiredFields.forEach(field => {
                if (!field.value) {
                    field.classList.add('border-red-500');
                    valid = false;
                } else {
                    field.classList.remove('border-red-500');
                }
            });

            if (!valid) {
                alert('Por favor, complete todos los campos obligatorios.');
            }

            return valid;
        }

        function updateUsername() {
            const firstName = document.getElementById('nombres').value;
            const lastName = document.getElementById('apellidos').value;
            const birthdate = document.getElementById('fecha_nacimiento').value;
        
            const firstInitial = firstName ? firstName.charAt(0).toLowerCase() : '';
            const firstLastName = lastName ? lastName.split(' ')[0].toLowerCase() : '';
            const birthYear = birthdate ? new Date(birthdate).getFullYear().toString().slice(-2) : '';
        
            document.getElementById('username').value = `${firstInitial}${firstLastName}${birthYear}`;
        }
        
        function openDatePicker() {
            document.getElementById('fecha_nacimiento').showPicker();
        }
        


//add_employee
        function validateForm() {
            const requiredFields = document.querySelectorAll('[required]');
            let valid = true;

            requiredFields.forEach(field => {
                if (!field.value) {
                    field.classList.add('border-red-500');
                    valid = false;
                } else {
                    field.classList.remove('border-red-500');
                }
            });

            if (!valid) {
                alert('Por favor, complete todos los campos obligatorios.');
            }

            return valid;
        }


// Manejo del evento de click en el enlace "Explorar"
function triggerFileInput(event) {
    event.preventDefault();  // Evita que se agregue # a la URL
    document.getElementById('file-input').click();  // Abre el explorador de archivos
}

// Función para manejar la selección del archivo
function handleFileSelect(event) {
    const fileInput = event.target;
    const file = fileInput.files[0];

    if (file) {
        const fileName = file.name;
        const fileReader = new FileReader();

        fileReader.onload = function() {
            const imageUrl = fileReader.result;
            // Muestra la imagen seleccionada y el botón de eliminar con el icono SVG
            document.getElementById('file-drop-zone').innerHTML = `
                <div class="relative">
                    <img src="${imageUrl}" alt="Foto de perfil" class="w-24 h-24 object-cover rounded-full mx-auto mb-4">
                    <button class="absolute top-0 right-0 bg-white p-1 rounded-full" onclick="removeImage()">
                        <img src="{{ url_for('static', filename='icons/eliminar.svg') }}" alt="Eliminar imagen" class="w-5 h-5">
                    </button>
                    <p class="text-gray-600 mt-2">Imagen seleccionada: ${fileName}</p>
                </div>
            `;
        };

        fileReader.readAsDataURL(file);
    }
}

// Función para manejar la eliminación de la imagen
function removeImage() {
    const dropZone = document.getElementById('file-drop-zone');
    // Restaura la zona de arrastre a su estado inicial
    dropZone.innerHTML = `
        <i class="fas fa-cloud-upload-alt text-4xl text-gray-400"></i>
        <p class="mt-2 text-gray-600">Arrastrar y soltar archivos o <a href="#" class="text-blue-500" onclick="triggerFileInput(event)">Explorar</a></p>
        <p class="text-gray-400">Formatos admitidos: JPEG, PNG, GIF, WEBP</p>
        <input type="file" id="file-input" class="hidden" accept="image/jpeg, image/png, image/gif, image/webp, image/svg+xml, image/vnd.adobe.illustrator" onchange="handleFileSelect(event)">
    `;
}

document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('file-drop-zone');

    // Evitar el comportamiento predeterminado en dragenter y dragover
    dropZone.addEventListener('dragenter', function(event) {
        event.preventDefault();  // Es necesario para permitir el drop
        dropZone.classList.add('dragging');  // Activar feedback visual
    });

    dropZone.addEventListener('dragover', function(event) {
        event.preventDefault();
        dropZone.classList.add('dragging');  // Mantener el feedback visual
    });

    // Eliminar feedback visual cuando el archivo deja la zona
    dropZone.addEventListener('dragleave', function(event) {
        event.preventDefault();
            dropZone.classList.remove('dragging');  // Restaurar estilos
        });

    // Manejar la caída del archivo en la zona
    dropZone.addEventListener('drop', function(event) {
        event.preventDefault();
        dropZone.classList.remove('dragging');  // Restaurar estilos

        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];  // Tomar el primer archivo

            // Verificar que el archivo sea de tipo imagen
            if (file.type.startsWith('image/')) {
                const fileReader = new FileReader();
                fileReader.onload = function() {
                    const imageUrl = fileReader.result;
                    // Mostrar la imagen cargada en el área y el botón de eliminar con el icono SVG
                    dropZone.innerHTML = `  
                        <div class="relative">
                            <img src="${imageUrl}" alt="Imagen seleccionada" class="w-24 h-24 object-cover rounded-full mx-auto mb-4">
                            <button class="absolute top-0 right-0 bg-white p-1 rounded-full" onclick="removeImage()">
                                <img src="{{ url_for('static', filename='icons/eliminar.svg') }}" class="icon-small">
                            </button>
                            <p class="text-gray-600 mt-2">Imagen seleccionada: ${file.name}</p>
                        </div>
                    `;
                };

                fileReader.readAsDataURL(file);  // Leer el archivo como URL para mostrar la imagen
            } else {
                dropZone.innerHTML = `
                    <p class="text-red-500">Por favor, selecciona una imagen.</p>
                `;
            }
        }
    });
});

function getSelectedEmployeeType() {
    const selectedEmployee = document.querySelector('input[name="employee_type"]:checked');
    if (selectedEmployee) {
        console.log(`Empleado seleccionado: ${selectedEmployee.value}`);
    } else {
        console.log('No se ha seleccionado un empleado');
    }
}

function getSelectedGender() {
    const selectedGender = document.querySelector('input[name="gender"]:checked');
    if (selectedGender) {
        console.log(`Sexo seleccionado: ${selectedGender.value}`);
    } else {
        console.log('No se ha seleccionado un sexo');
    }
}

// Ejemplo de cómo usarlas
document.getElementById('yourButtonId').addEventListener('click', function() {
    getSelectedEmployeeType();
    getSelectedGender();
});


    // Obtener todos los inputs de tipo radio para 'employee_type'
    const employeeTypeRadios = document.querySelectorAll('input[name="employee_type"]');

    // Agregar un evento de cambio para cada radio button
    employeeTypeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            // Obtener el 'role_id' desde el atributo 'data-role-id' del radio seleccionado
            const roleId = this.getAttribute('data-role-id');
            // Actualizar el campo oculto con el 'role_id'
            document.getElementById('role_id').value = roleId;
        });
    });