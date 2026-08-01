function debounce(fn, delay = 250) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn(...args), delay);
  };
}

function hidePatientResults() {
  const list = document.getElementById("lista-sugerencias");
  if (!list) return;
  list.classList.add("hidden");
  list.replaceChildren();
}

function renderPatientResults(patients) {
  const list = document.getElementById("lista-sugerencias");
  if (!list) return;
  list.replaceChildren();

  if (!Array.isArray(patients) || !patients.length) {
    const empty = document.createElement("li");
    empty.className = "px-3 py-3 text-sm text-gray-500";
    empty.textContent = "No se encontraron pacientes.";
    list.appendChild(empty);
    list.classList.remove("hidden");
    return;
  }

  patients.forEach((patient) => {
    const id = patient.id ?? patient.paciente_id ?? "";
    const name = patient.nombre_completo
      ?? `${patient.nombres ?? ""} ${patient.apellidos ?? ""}`.trim();
    const item = document.createElement("li");
    item.className = "cursor-pointer rounded-lg px-3 py-2.5 transition hover:bg-cyan-50";
    item.setAttribute("role", "option");

    const title = document.createElement("strong");
    title.className = "block text-sm font-semibold text-gray-900";
    title.textContent = name;
    item.appendChild(title);

    if (patient.telefono) {
      const phone = document.createElement("small");
      phone.className = "mt-0.5 block text-xs text-gray-500";
      phone.textContent = patient.telefono;
      item.appendChild(phone);
    }
    item.addEventListener("click", () => seleccionarPaciente(name, id, patient));
    list.appendChild(item);
  });
  list.classList.remove("hidden");
}

async function searchPatientsPrimary(query) {
  const response = await fetch("/api/patients/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ q: query }),
  });
  if (!response.ok) throw new Error("primary_search_failed");
  const data = await response.json();
  return Array.isArray(data.results) ? data.results : [];
}

async function searchPatientsFallback(query) {
  const response = await fetch(`/api/buscar_pacientes?q=${encodeURIComponent(query)}`);
  if (!response.ok) throw new Error("fallback_search_failed");
  const data = await response.json();
  return Array.isArray(data) ? data : [];
}

const buscarPacientes = debounce(async (query) => {
  const hidden = document.getElementById("patient_id");
  if (hidden) hidden.value = "";
  if (!query || query.trim().length < 1) {
    hidePatientResults();
    return;
  }

  try {
    let results;
    try {
      results = await searchPatientsPrimary(query.trim());
    } catch {
      results = await searchPatientsFallback(query.trim());
    }
    renderPatientResults(results);
  } catch (error) {
    console.error("Error al buscar pacientes:", error);
    hidePatientResults();
  }
}, 250);

function seleccionarPaciente(name, id, patient = {}) {
  const input = document.getElementById("nombre");
  const hidden = document.getElementById("patient_id");
  if (input) input.value = name;
  if (hidden) hidden.value = id;
  showPatientVerification({
    ...patient,
    nombre_completo: name,
  });
  clearFieldError("nombre");
  hidePatientResults();
}

function showPatientVerification(patient) {
  const card = document.getElementById("patient-verification");
  if (!card) return;
  const values = {
    "patient-verification-name": patient.nombre_completo || "Paciente",
    "patient-verification-phone": patient.telefono || "No registrado",
    "patient-verification-email": patient.correo || "No registrado",
    "patient-verification-birth": patient.fecha_nacimiento || "No registrada",
    "patient-verification-sex": (
      { M: "Masculino", F: "Femenino", O: "Otro" }[patient.sexo]
      || patient.sexo
      || "No registrado"
    ),
    "patient-verification-address": patient.direccion || "No registrada",
  };
  Object.entries(values).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
  const editLink = document.getElementById("edit-selected-patient");
  if (editLink && patient.id) {
    editLink.dataset.entityModalUrl = `/admin/edit_patient/${encodeURIComponent(patient.id)}?embed=1`;
  }
  card.classList.remove("hidden");
}

function clearSelectedPatient() {
  const name = document.getElementById("nombre");
  const hidden = document.getElementById("patient_id");
  const card = document.getElementById("patient-verification");
  if (name) name.value = "";
  if (hidden) hidden.value = "";
  card?.classList.add("hidden");
  const editLink = document.getElementById("edit-selected-patient");
  if (editLink) delete editLink.dataset.entityModalUrl;
  name?.focus();
}

async function refreshSelectedPatient() {
  const patientId = document.getElementById("patient_id")?.value;
  if (!patientId) return;
  try {
    const response = await fetch(`/api/paciente/${encodeURIComponent(patientId)}/resumen`);
    if (!response.ok) return;
    const patient = await response.json();
    const name = document.getElementById("nombre");
    if (name) name.value = patient.nombre_completo || name.value;
    showPatientVerification(patient);
  } catch (error) {
    console.error("No se pudo actualizar la ficha del paciente:", error);
  }
}

function openEntityModal(url) {
  const modal = document.getElementById("entity-form-modal");
  const frame = document.getElementById("entity-form-frame");
  if (!modal || !frame || !url) return;
  if (modal.parentElement !== document.body) document.body.appendChild(modal);
  Object.assign(modal.style, {
    position: "fixed",
    inset: "0",
    width: "100vw",
    height: "100dvh",
    margin: "0",
    zIndex: "9999",
  });
  frame.src = url;
  modal.classList.remove("hidden");
  document.body.classList.add("overflow-hidden");
}

function closeEntityModal() {
  const modal = document.getElementById("entity-form-modal");
  const frame = document.getElementById("entity-form-frame");
  modal?.classList.add("hidden");
  if (frame) frame.src = "about:blank";
  document.body.classList.remove("overflow-hidden");
}

async function refreshOrderCatalogs(entity, selectedId) {
  try {
    const response = await fetch("/api/orden/catalogos");
    if (!response.ok) return;
    const data = await response.json();
    [
      ["hospital", "Selecciona una procedencia", "Sin hospital · Paciente particular", data.hospitales || []],
      ["doctor", "Selecciona una opción", "Sin médico solicitante", data.doctores || []],
    ].forEach(([id, placeholder, noneLabel, items]) => {
      const select = document.getElementById(id);
      if (!select) return;
      const previous = select.value;
      select.replaceChildren(new Option(placeholder, ""), new Option(noneLabel, "none"));
      items.forEach((item) => select.appendChild(new Option(item.nombre, String(item.id))));
      const desired = entity === id ? String(selectedId) : previous;
      if ([...select.options].some((option) => option.value === desired)) select.value = desired;
    });
    updateHospitalRequirements();
  } catch (error) {
    console.error("No se pudieron actualizar hospitales y médicos:", error);
  }
}

function updateHospitalRequirements() {
  const hospital = document.getElementById("hospital");
  const room = document.getElementById("cuarto");
  const required = document.getElementById("room-required");
  const isPrivate = hospital?.value === "none";
  if (!room) return;
  room.required = !isPrivate;
  room.disabled = isPrivate;
  room.placeholder = isPrivate ? "No aplica para paciente particular" : "Ej. 204, Urgencias o UCI";
  if (isPrivate) {
    room.value = "";
    clearFieldError("cuarto");
    required?.classList.add("hidden");
  } else {
    required?.classList.remove("hidden");
  }
}

function ensureToastRoot() {
  let root = document.getElementById("toast-root");
  if (!root) {
    root = document.createElement("div");
    root.id = "toast-root";
    root.className = "pointer-events-none fixed inset-x-0 top-6 z-50 flex justify-center";
    document.body.appendChild(root);
  }
  return root;
}

function showOrderToast(messages) {
  const root = ensureToastRoot();
  const values = Array.isArray(messages) ? messages : [messages];
  const toast = document.createElement("div");
  toast.className = "pointer-events-auto mx-4 flex max-w-md items-start gap-3 rounded-xl border border-red-200 bg-white px-4 py-3 text-sm text-red-800 shadow-xl";

  const icon = document.createElement("i");
  icon.className = "fas fa-exclamation-circle mt-0.5 text-red-600";
  toast.appendChild(icon);

  const content = document.createElement("div");
  content.className = "flex-1";
  const title = document.createElement("strong");
  title.className = "block text-gray-900";
  title.textContent = "Revisa la información";
  content.appendChild(title);
  values.forEach((message) => {
    const line = document.createElement("p");
    line.className = "mt-1";
    line.textContent = message;
    content.appendChild(line);
  });
  toast.appendChild(content);
  root.replaceChildren(toast);
  window.setTimeout(() => toast.remove(), 4500);
}

function showEntitySuccess(message) {
  const root = ensureToastRoot();
  const toast = document.createElement("div");
  toast.className = "pointer-events-auto mx-4 flex max-w-md items-center gap-3 rounded-xl border border-emerald-200 bg-white px-4 py-3 text-sm text-emerald-800 shadow-xl";
  const icon = document.createElement("span");
  icon.className = "grid h-8 w-8 shrink-0 place-items-center rounded-full bg-emerald-50";
  icon.innerHTML = '<i class="fas fa-check"></i>';
  const text = document.createElement("strong");
  text.textContent = message;
  toast.append(icon, text);
  root.replaceChildren(toast);
  window.setTimeout(() => toast.remove(), 3500);
}

function clearFieldError(id) {
  const field = document.getElementById(id);
  const message = document.getElementById(`${id}-error`);
  if (field) {
    field.classList.remove("!border-red-500", "!bg-red-50", "!ring-2", "!ring-red-100");
    field.removeAttribute("aria-invalid");
  }
  if (message) {
    message.textContent = "";
    message.classList.add("hidden");
  }
}

function setFieldError(id, text) {
  const field = document.getElementById(id);
  const message = document.getElementById(`${id}-error`);
  if (field) {
    field.classList.add("!border-red-500", "!bg-red-50", "!ring-2", "!ring-red-100");
    field.setAttribute("aria-invalid", "true");
  }
  if (message) {
    message.textContent = text;
    message.classList.remove("hidden");
  }
}

function validateOrderFields() {
  const name = (document.getElementById("nombre")?.value || "").trim();
  const patientId = (document.getElementById("patient_id")?.value || "").trim();
  const hospital = document.getElementById("hospital")?.value || "";
  const room = (document.getElementById("cuarto")?.value || "").trim();
  const doctor = document.getElementById("doctor")?.value || "";
  const errors = {};

  if (!name || !patientId) errors.nombre = "Selecciona un paciente desde la lista de resultados.";
  if (!hospital) errors.hospital = "Indica si existe un hospital de procedencia.";
  if (hospital !== "none" && !room) errors.cuarto = "Ingresa el cuarto o ubicación.";
  if (hospital !== "none" && room && !/^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9\-# ]{1,15}$/.test(room)) {
    errors.cuarto = "Usa letras, números, espacios, guiones o # (máximo 15).";
  }
  if (!doctor) errors.doctor = "Indica si existe un médico solicitante.";
  return { errors, name, patientId, hospital, room, doctor };
}

document.addEventListener("click", (event) => {
  const list = document.getElementById("lista-sugerencias");
  const input = document.getElementById("nombre");
  if (list && input && !list.contains(event.target) && event.target !== input) {
    hidePatientResults();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("order-form");
  if (!form) return;
  const entityModal = document.getElementById("entity-form-modal");
  if (entityModal && entityModal.parentElement !== document.body) {
    document.body.appendChild(entityModal);
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    ["nombre", "hospital", "cuarto", "doctor"].forEach(clearFieldError);
    const values = validateOrderFields();

    if (Object.keys(values.errors).length) {
      Object.entries(values.errors).forEach(([id, text]) => setFieldError(id, text));
      const first = document.getElementById(Object.keys(values.errors)[0]);
      first?.scrollIntoView({ behavior: "smooth", block: "center" });
      window.setTimeout(() => first?.focus({ preventScroll: true }), 350);
      showOrderToast(Object.values(values.errors));
      return;
    }

    try {
      const response = await fetch("/api/validar_orden", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre: values.name,
          patient_id: values.patientId,
          hospital: values.hospital,
          cuarto: values.room,
          doctor: values.doctor,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        showOrderToast(data?.errors?.length ? data.errors : "No se pudo validar la orden.");
        return;
      }
      form.submit();
    } catch (error) {
      console.error(error);
      showOrderToast("No se pudo validar con el servidor. Intenta nuevamente.");
    }
  });

  const nameInput = document.getElementById("nombre");
  nameInput?.addEventListener("input", () => {
    clearFieldError("nombre");
    document.getElementById("patient-verification")?.classList.add("hidden");
  });
  document.getElementById("change-patient")?.addEventListener("click", clearSelectedPatient);
  window.addEventListener("focus", refreshSelectedPatient);
  refreshSelectedPatient();
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-entity-modal-url]");
    if (trigger) openEntityModal(trigger.dataset.entityModalUrl);
    if (event.target.closest("[data-entity-modal-close]")) closeEntityModal();
  });
  window.addEventListener("message", async (event) => {
    if (event.origin !== window.location.origin) return;
    if (event.data?.type === "applab:close-entity-modal") {
      closeEntityModal();
      return;
    }
    if (event.data?.type !== "applab:entity-saved") return;
    const { entity, id } = event.data;
    closeEntityModal();
    const labels = {
      patient: "Paciente guardado correctamente.",
      hospital: "Hospital guardado correctamente.",
      doctor: "Médico guardado correctamente.",
    };
    showEntitySuccess(labels[entity] || "Información guardada correctamente.");
    if (entity === "patient" && id) {
      const response = await fetch(`/api/paciente/${encodeURIComponent(id)}/resumen`);
      if (response.ok) {
        const patient = await response.json();
        seleccionarPaciente(patient.nombre_completo, patient.id, patient);
      }
    } else if ((entity === "hospital" || entity === "doctor") && id) {
      await refreshOrderCatalogs(entity, id);
    }
  });
  document.getElementById("hospital")?.addEventListener("change", updateHospitalRequirements);
  updateHospitalRequirements();
  ["hospital", "cuarto", "doctor"].forEach((id) => {
    const field = document.getElementById(id);
    field?.addEventListener(field.tagName === "SELECT" ? "change" : "input", () => clearFieldError(id));
  });
});
