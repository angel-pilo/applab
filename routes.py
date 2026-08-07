import os
import bcrypt
import re
import uuid
import unicodedata
from io import BytesIO
from xml.sax.saxutils import escape
from urllib.parse import unquote, urlparse
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for, jsonify, send_file
from functools import wraps
from services import *
from datetime import datetime
import json
import logging
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.graphics.shapes import Drawing, Rect, Path
from supabase_client import supabase, supabase_storage, SUPABASE_AVATAR_BUCKET
from permissions import (
    endpoint_is_allowed,
    normalize_permissions,
    preferred_home,
)



app_routes = Blueprint('app_routes', __name__)
logger = logging.getLogger(__name__)

# Obtener la ruta del archivo JSON con estados
ruta_estados = os.path.join(os.path.dirname(__file__), 'static', 'JSON', 'estados.json')

# Cargar estados desde el JSON
with open(ruta_estados, 'r', encoding='utf-8') as file:
    estados_data = json.load(file)
    estados = estados_data["estados"]  # Extrae la lista de estados del JSON


# Mapeo de roles por ID
role_map = {
    1: "Admin",
    2: "Mostrador",
    3: "Enfermero",
    4: "Quimico",
    5: "Personalizado",
}

AVATAR_UPLOAD_FOLDER = os.path.join(
    os.path.dirname(__file__), "static", "uploads", "avatars"
)
AVATAR_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
AVATAR_MAX_BYTES = 3 * 1024 * 1024


def validate_employee_avatar(file):
    """Valida extensión, tamaño y firma básica de una foto de perfil."""
    if not file or not file.filename:
        return None, None

    extension = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if extension not in AVATAR_EXTENSIONS:
        return None, "La foto debe ser JPG, PNG, GIF o WEBP."

    content = file.read(AVATAR_MAX_BYTES + 1)
    file.seek(0)
    if len(content) > AVATAR_MAX_BYTES:
        return None, "La foto no puede superar 3 MB."

    signatures = {
        "jpg": content.startswith(b"\xff\xd8\xff"),
        "jpeg": content.startswith(b"\xff\xd8\xff"),
        "png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "gif": content.startswith((b"GIF87a", b"GIF89a")),
        "webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
    }
    if not signatures.get(extension):
        return None, "El contenido del archivo no corresponde a una imagen válida."

    return extension, None


def validate_brand_asset(file, asset_type):
    extension, error = validate_employee_avatar(file)
    if error or not extension:
        return extension, error
    if extension == "gif":
        return None, "Usa PNG, JPG o WEBP; los recursos de identidad no deben ser animados."
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    maximum = 1024 * 1024 if asset_type == "logo" else 512 * 1024
    if size > maximum:
        label = "1 MB" if asset_type == "logo" else "512 KB"
        return None, f"El archivo no puede superar {label}."
    return extension, None


def save_employee_avatar(file, extension):
    """Guarda una foto validada exclusivamente en Supabase Storage."""
    filename = f"employee-{uuid.uuid4().hex}.{extension}"
    if not SUPABASE_AVATAR_BUCKET:
        raise RuntimeError("Configura SUPABASE_AVATAR_BUCKET antes de subir imágenes.")
    file.seek(0)
    content = file.read()
    supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).upload(
        f"profiles/{filename}", content,
        {"content-type": file.mimetype or f"image/{extension}", "cache-control": "3600"},
    )
    return supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).get_public_url(
        f"profiles/{filename}"
    )


def save_brand_asset(file, extension, asset_type):
    """Guarda logos y favicons exclusivamente en Supabase Storage."""
    if not SUPABASE_AVATAR_BUCKET:
        raise RuntimeError("Configura SUPABASE_AVATAR_BUCKET antes de subir la identidad.")
    filename = f"{asset_type}-{uuid.uuid4().hex}.{extension}"
    path = f"branding/{filename}"
    file.seek(0)
    supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).upload(
        path, file.read(),
        {"content-type": file.mimetype or f"image/{extension}", "cache-control": "3600"},
    )
    return supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).get_public_url(path)


def delete_brand_asset(asset_url):
    """Elimina únicamente recursos administrados dentro de branding/."""
    if not asset_url or not SUPABASE_AVATAR_BUCKET:
        return
    marker = f"/storage/v1/object/public/{SUPABASE_AVATAR_BUCKET}/"
    parsed_path = unquote(urlparse(asset_url).path)
    if marker not in parsed_path:
        return
    storage_path = parsed_path.split(marker, 1)[1]
    if storage_path.startswith("branding/"):
        supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).remove([storage_path])


def save_employee_signature(file, extension):
    """Guarda la imagen de firma del responsable sin exponer archivos locales."""
    filename = f"signature-{uuid.uuid4().hex}.{extension}"
    if not SUPABASE_AVATAR_BUCKET:
        raise RuntimeError("Configura SUPABASE_AVATAR_BUCKET antes de subir imágenes.")
    file.seek(0)
    content = file.read()
    path = f"profiles/signatures/{filename}"
    supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).upload(
        path, content,
        {"content-type": file.mimetype or f"image/{extension}", "cache-control": "3600"},
    )
    return supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).get_public_url(path)


def delete_local_employee_avatar(avatar_url):
    """Elimina avatares administrados, tanto locales como de Supabase Storage."""
    if (
        avatar_url and SUPABASE_AVATAR_BUCKET
        and "/storage/v1/object/public/" in avatar_url
    ):
        marker = f"/storage/v1/object/public/{SUPABASE_AVATAR_BUCKET}/"
        parsed_path = unquote(urlparse(avatar_url).path)
        if marker in parsed_path:
            storage_path = parsed_path.split(marker, 1)[1]
            if storage_path.startswith("profiles/"):
                supabase_storage.storage.from_(SUPABASE_AVATAR_BUCKET).remove(
                    [storage_path]
                )
        return

    prefix = "/static/uploads/avatars/"
    if not avatar_url or not avatar_url.startswith(prefix):
        return

    filename = os.path.basename(avatar_url)
    target = os.path.abspath(os.path.join(AVATAR_UPLOAD_FOLDER, filename))
    folder = os.path.abspath(AVATAR_UPLOAD_FOLDER)
    if os.path.commonpath((target, folder)) == folder and os.path.isfile(target):
        os.remove(target)


def normalize_avatar_choice(value):
    """Acepta únicamente las opciones de avatar conocidas por la interfaz."""
    choice = (value or "initials").strip()
    if choice in {"initials", "upload", "current"}:
        return choice
    if choice.startswith("preset:"):
        try:
            preset_id = int(choice.split(":", 1)[1])
        except (TypeError, ValueError):
            return "initials"
        if 1 <= preset_id <= 12:
            return f"preset:{preset_id}"
    return "initials"


def attribute_audit_event(entity_type, entity_id, extra_changes=None):
    """Añade al evento automático la identidad del usuario autenticado."""
    return atribuir_ultimo_evento(
        entidad_tipo=entity_type,
        entidad_id=entity_id,
        actor_usuario_id=session.get("user_id"),
        actor_empleado_id=session.get("empleado_id"),
        actor_username=session.get("usuario"),
        actor_nombre=session.get("nombres"),
        cambios_extra=extra_changes,
    )

# Decorador para restringir acceso según rol
def require_role(roles):
    if isinstance(roles, str):
        roles = {role.strip() for role in roles.split(",")}
    else:
        roles = set(roles)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "usuario" not in session:
                return redirect(url_for("app_routes.login"))
            # El administrador puede operar cualquier área sin dejar de ser el
            # actor real que quedará registrado en la bitácora.
            if session.get("rol") == "Admin":
                return f(*args, **kwargs)
            if session.get("rol") in roles:
                return f(*args, **kwargs)
            if (
                session.get("rol") == "Personalizado"
                and endpoint_is_allowed(
                    request.endpoint, session.get("permisos", [])
                )
            ):
                return f(*args, **kwargs)
            abort(403)
        return wrapper
    return decorator


def current_home_endpoint():
    """Obtiene la página inicial según el rol o su mezcla de permisos."""
    if session.get("rol") == "Personalizado":
        return preferred_home(session.get("permisos", []))
    role = session.get("rol", "")
    if role == "Admin":
        role = session.get("area_activa", "Admin")
    if role in role_map.values() and role != "Personalizado":
        return f"app_routes.{role.lower()}_dashboard"
    return None


def current_workspace_role():
    """Área visible sin alterar el rol ni la identidad autenticada."""
    role = session.get("rol", "")
    if role != "Admin":
        return role
    workspace = session.get("area_activa", "Admin")
    return workspace if workspace in {"Admin", "Mostrador", "Enfermero", "Quimico"} else "Admin"


def current_user_can(permission):
    return (
        session.get("rol") == "Admin"
        or permission in set(session.get("permisos", []))
    )


def admin_override_from_request():
    """Obtiene y valida las credenciales usadas para una excepción puntual."""
    return verificar_autorizador_admin(
        request.form.get("admin_username"),
        request.form.get("admin_password"),
    )


def override_requester():
    return {
        "usuario_id": session.get("user_id"),
        "empleado_id": session.get("empleado_id"),
        "username": session.get("usuario"),
        "nombre": session.get("nombres"),
    }


def as_int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def validate_order_data(data):
    nombre = (data.get("nombre") or "").strip()
    patient_id = (data.get("patient_id") or "").strip()
    hospital_id = (data.get("hospital") or "").strip()
    cuarto = (data.get("cuarto") or "").strip()
    doctor_id = (data.get("doctor") or "").strip()
    errors = []

    if not nombre or not patient_id:
        errors.append("Selecciona un paciente desde la lista de sugerencias.")
    has_hospital = hospital_id not in {"", "none"}
    has_doctor = doctor_id not in {"", "none"}
    if not hospital_id:
        errors.append("Indica si la orden tiene hospital de procedencia.")
    if has_hospital and not cuarto:
        errors.append("Ingresa el cuarto o ubicación del hospital.")
    if not doctor_id:
        errors.append("Indica si la orden tiene médico solicitante.")
    if cuarto and not re.fullmatch(r"[A-Za-z0-9\-# ]{1,15}", cuarto):
        errors.append("El campo 'Cuarto' solo permite letras, números, espacio, -, # (máx. 15).")
    if patient_id and not existe_paciente_activo(as_int_or_none(patient_id)):
        errors.append("El paciente seleccionado no existe o está inactivo.")
    if has_hospital and not existe_hospital_activo(as_int_or_none(hospital_id)):
        errors.append("El hospital seleccionado no existe o está inactivo.")
    if has_doctor and not existe_doctor_activo(as_int_or_none(doctor_id)):
        errors.append("El doctor seleccionado no existe o está inactivo.")

    return errors


def normalize_order_studies(items):
    """Valida estudios contra el catálogo activo y recalcula precios."""
    if not isinstance(items, list):
        return []
    catalog = {
        str(test["id"]): test
        for test in obtener_pruebas()
        if test.get("activo", True) is True
    }
    normalized = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        test_id = str(item.get("prueba_id") or "")
        if test_id not in catalog or test_id in seen:
            continue
        try:
            quantity = max(1, min(int(item.get("cantidad") or 1), 99))
            unit_price = float(catalog[test_id].get("precio") or 0)
        except (TypeError, ValueError):
            continue
        test = catalog[test_id]
        normalized.append({
            "prueba_id": int(test["id"]),
            "prueba": test.get("nombre") or "Estudio",
            "tipo_prueba": test.get("tipo") or "",
            "cantidad": quantity,
            "precio_unitario": unit_price,
            "precio": round(unit_price * quantity, 2),
        })
        seen.add(test_id)
    return normalized


def validate_clinical_test_elements(elements):
    """Valida que cada elemento tenga completa su estructura de referencia."""
    if not isinstance(elements, list) or not elements:
        return ["Agrega al menos un elemento a la prueba."]

    errors = []
    for index, element in enumerate(elements, start=1):
        name = (element.get("nombre") or "").strip() if isinstance(element, dict) else ""
        kind = (element.get("tipo_separacion") or "").strip() if isinstance(element, dict) else ""
        structure = element.get("estructura") if isinstance(element, dict) else None
        label = name or f"Elemento {index}"

        if not name or not kind or not isinstance(structure, dict):
            errors.append(f"{label}: faltan sus datos principales.")
            continue

        ranges = []
        unit_required = kind != "positivo-negativo"
        if kind == "sexo":
            ranges = [structure.get("M"), structure.get("F")]
        elif kind in {"edades", "edad-sexo"}:
            ranges = structure.get("rangos") or []
        elif kind == "min-max":
            ranges = [structure]
        elif kind == "menor-que":
            if structure.get("max") is None:
                errors.append(f"{label}: completa el valor máximo permitido.")
            if not str(structure.get("unidad") or "").strip():
                errors.append(f"{label}: escribe la unidad de medida.")
            continue
        elif kind == "positivo-negativo":
            if structure.get("valor_normal") not in {"positivo", "negativo"}:
                errors.append(f"{label}: selecciona el resultado normal.")
            continue
        else:
            errors.append(f"{label}: el tipo de referencia no es válido.")
            continue

        if not ranges or any(not isinstance(item, dict) for item in ranges):
            errors.append(f"{label}: faltan los rangos de referencia.")
            continue

        for item in ranges:
            if item.get("min") is None or item.get("max") is None:
                errors.append(f"{label}: completa todos los valores mínimo y máximo.")
                break
            if item["min"] > item["max"]:
                errors.append(f"{label}: el mínimo no puede ser mayor que el máximo.")
                break

        unit = structure.get("unidad")
        if kind == "sexo" and ranges:
            unit = ranges[0].get("unidad")
        if unit_required and not str(unit or "").strip():
            errors.append(f"{label}: escribe la unidad de medida.")

    return errors


def _patient_age(patient):
    try:
        born = datetime.fromisoformat(str(patient.get("fecha_nacimiento"))[:10]).date()
        today = datetime.now().date()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except (TypeError, ValueError):
        return None


def _patient_sex_code(patient):
    value = str(patient.get("sexo") or "").strip().lower()
    if value in {"m", "masculino", "hombre"}:
        return "M"
    if value in {"f", "femenino", "mujer"}:
        return "F"
    return None


def resolve_clinical_reference(element, patient):
    """Resuelve el rango aplicable usando edad y sexo del paciente."""
    kind = element.get("tipo_separacion")
    structure = element.get("estructura") or {}
    reference = {
        "tipo": kind,
        "unidad": structure.get("unidad") or "",
        "min": None,
        "max": None,
        "normal": None,
        "descripcion": "Sin referencia aplicable",
    }
    sex = _patient_sex_code(patient)
    age = _patient_age(patient)
    selected = None
    if kind == "sexo" and sex:
        selected = structure.get(sex)
    elif kind in {"edades", "edad-sexo"}:
        for item in structure.get("rangos") or []:
            if kind == "edad-sexo" and sex and item.get("sexo") != sex:
                continue
            minimum_age = item.get("min_edad")
            maximum_age = item.get("max_edad")
            if age is not None and (minimum_age is None or age >= minimum_age) and (
                maximum_age is None or age <= maximum_age
            ):
                selected = item
                break
    elif kind == "min-max":
        selected = structure
    elif kind == "menor-que":
        reference.update({
            "max": structure.get("max"),
            "unidad": structure.get("unidad") or "",
            "descripcion": f"Menor que {structure.get('max')} {structure.get('unidad') or ''}".strip(),
        })
        return reference
    elif kind == "positivo-negativo":
        normal = str(structure.get("valor_normal") or "").lower()
        reference.update({
            "normal": normal,
            "opciones": structure.get("valores_permitidos") or ["positivo", "negativo"],
            "descripcion": f"Normal: {normal.title()}",
        })
        return reference
    if selected:
        reference.update({
            "min": selected.get("min"),
            "max": selected.get("max"),
            "unidad": selected.get("unidad") or structure.get("unidad") or "",
        })
        reference["descripcion"] = (
            f"{reference['min']} – {reference['max']} {reference['unidad']}".strip()
        )
    return reference


def evaluate_clinical_value(value, reference):
    raw = str(value or "").strip()
    result = {
        "valor": raw,
        "estado": "sin_referencia",
        "referencia": reference.get("descripcion"),
        "unidad": reference.get("unidad") or "",
    }
    if reference.get("normal") is not None:
        result["estado"] = (
            "normal" if raw.lower() == str(reference["normal"]).lower() else "fuera"
        )
        return result
    try:
        numeric = float(raw.replace(",", "."))
    except ValueError:
        result["estado"] = "invalido"
        return result
    minimum = reference.get("min")
    maximum = reference.get("max")
    if minimum is not None and numeric < float(minimum):
        result["estado"] = "bajo"
    elif maximum is not None and numeric > float(maximum):
        result["estado"] = "alto"
    elif minimum is not None or maximum is not None:
        result["estado"] = "normal"
    return result

# Ruta principal
@app_routes.route("/")
def home():
    if "usuario" in session:
        endpoint = current_home_endpoint()
        return redirect(url_for(endpoint or "app_routes.configuracion"))

    return redirect(url_for("app_routes.login"))

@app_routes.route("/proximamente")
@require_role(role_map.values())
def proximamente():
    feature = (request.args.get("feature") or "Esta función").strip()
    feature_details = {
        "Corte de caja": ("fa-cash-register", "Control y conciliación de movimientos del día."),
        "Control de calidad": ("fa-vials", "Seguimiento de controles, lotes y criterios de aceptación."),
        "Equipos": ("fa-tools", "Administración del estado y mantenimiento de equipos."),
        "Incidencias": ("fa-flag", "Registro y seguimiento de eventos del laboratorio."),
        "Registro de toma": ("fa-syringe", "Captura de hora, recipiente y condiciones de la muestra."),
        "Bioseguridad": ("fa-shield-virus", "Control de incidencias y protocolos de bioseguridad."),
        "Envío / Traslado": ("fa-truck", "Cadena de custodia y traslado de muestras."),
    }
    icon, description = feature_details.get(
        feature,
        ("fa-flask", "Esta herramienta formará parte de una próxima actualización."),
    )
    return render_template(
        "proximamente.html",
        feature=feature,
        icon=icon,
        description=description,
    )

# Ruta de Dashboard
@app_routes.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("app_routes.login"))
    
    rol = session.get("rol", "")
    if rol not in role_map.values():
        session.clear()
        return redirect(url_for("app_routes.login"))
    endpoint = current_home_endpoint()
    return redirect(url_for(endpoint or "app_routes.configuracion"))


@app_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = verificar_usuario(usuario, password)
        if not user:
            flash('Usuario o contraseña incorrectos.', 'error')
            return redirect(url_for('app_routes.login'))

        # Asignar rol
        rol_id = as_int_or_none(user.get('rol_id'))
        rol = role_map.get(rol_id)

        if not rol:
            flash('Error: Rol no reconocido.', 'error')
            return redirect(url_for('app_routes.login'))

        # Guardar sesión
        session["usuario"] = usuario
        session["rol"] = rol
        session["nombres"] = user.get("nombres")
        session["foto_perfil"] = user.get("foto_perfil")
        session["permisos"] = normalize_permissions(user.get("permisos"))
        session["area_activa"] = "Admin" if rol == "Admin" else rol

        session['user_id'] = user['id']  # Establecer user_id en la sesión correctamente
        session['empleado_id'] = user.get('empleado_id')

        endpoint = current_home_endpoint()
        return redirect(url_for(endpoint or "app_routes.configuracion"))

    return render_template('auth/login.html')


@app_routes.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('app_routes.home'))


@app_routes.route("/cambiar-area/<area>", methods=["POST"])
@require_role("Admin")
def cambiar_area(area):
    """Cambia el espacio de trabajo del administrador, no su identidad."""
    if session.get("rol") != "Admin":
        abort(403)
    areas = {
        "admin": ("Admin", "app_routes.admin_operational_dashboard"),
        "mostrador": ("Mostrador", "app_routes.mostrador_dashboard"),
        "enfermero": ("Enfermero", "app_routes.enfermero_dashboard"),
        "quimico": ("Quimico", "app_routes.quimico_dashboard"),
    }
    selection = areas.get((area or "").lower())
    if not selection:
        abort(404)
    workspace, endpoint = selection
    session["area_activa"] = workspace
    return redirect(url_for(endpoint))

@app_routes.route("/admin")
@require_role("Admin")
def admin_dashboard():
    if session.get("rol") != "Admin":
        return redirect(url_for("app_routes.admin_operational_dashboard"))
    session["area_activa"] = "Admin"
    return render_template("admin/area_selector.html")


@app_routes.route("/admin/panel")
@require_role("Admin")
def admin_operational_dashboard():
    dashboard = obtener_resumen_admin()
    return render_template(
        "admin/admin.html",
        dashboard_counts=dashboard["counts"],
        inventory_alerts=dashboard["inventory_alerts"],
    )


@app_routes.route("/api/notifications/today")
@require_role(role_map.values())
def notifications_today():
    rol = current_workspace_role()
    permisos = set(session.get("permisos", []))
    if rol == "Personalizado":
        notifications = []
        if "front.results.deliver" in permisos:
            notifications.extend(
                obtener_notificaciones_resultados(session.get("user_id"))
            )
        if permisos.intersection({
            "admin.inventory", "lab.inventory.entry", "lab.results.capture"
        }):
            notifications.extend(
                obtener_notificaciones_inventario(
                    session.get("user_id"), "Quimico"
                )
            )
    elif rol == "Mostrador":
        notifications = obtener_notificaciones_resultados(session.get("user_id"))
    else:
        notifications = obtener_notificaciones_inventario(session.get("user_id"), rol)
    return jsonify({
        "notifications": notifications,
        "unread": sum(not item.get("read") for item in notifications),
        "scope": (
            "combined" if rol == "Personalizado"
            else "inventory" if rol in {"Admin", "Quimico"}
            else "results" if rol == "Mostrador"
            else "personal"
        ),
        "subtitle": (
            "Avisos relacionados con tus permisos"
            if rol == "Personalizado"
            else "Alertas diarias de inventario"
            if rol in {"Admin", "Quimico"}
            else "Resultados listos para entregar"
            if rol == "Mostrador"
            else "Avisos relacionados con tus funciones"
        ),
        "empty_message": (
            "No tienes notificaciones para hoy."
            if rol == "Personalizado"
            else "No tienes alertas de inventario para hoy."
            if rol in {"Admin", "Quimico"}
            else "No hay resultados nuevos para entregar."
            if rol == "Mostrador"
            else "No tienes notificaciones para hoy."
        ),
    })


@app_routes.route("/api/notifications/read", methods=["POST"])
@require_role(role_map.values())
def notifications_read():
    payload = request.get_json(silent=True) or {}
    rol = current_workspace_role()
    permisos = set(session.get("permisos", []))
    current = []
    if rol in {"Mostrador", "Personalizado"} and (
        rol == "Mostrador" or "front.results.deliver" in permisos
    ):
        current.extend(obtener_notificaciones_resultados(session.get("user_id")))
    if rol != "Mostrador" and (
        rol != "Personalizado"
        or permisos.intersection({
            "admin.inventory", "lab.inventory.entry", "lab.results.capture"
        })
    ):
        current.extend(obtener_notificaciones_inventario(
            session.get("user_id"),
            "Quimico" if rol == "Personalizado" else rol,
        ))
    valid_keys = {item["key"] for item in current}
    requested = payload.get("keys") or []
    keys = valid_keys if payload.get("all") else valid_keys.intersection(requested)
    if not marcar_notificaciones_leidas(session.get("user_id"), keys):
        return jsonify({"message": "No se pudieron guardar las lecturas."}), 500
    return jsonify({"message": "Notificaciones marcadas como leídas."})

@app_routes.route("/backlog")
@require_role("Admin")
def backlog():
    return render_template("backlog.html")


@app_routes.route("/api/backlog/events")
@require_role("Admin")
def backlog_events():
    events = obtener_eventos_bitacora(limit=200)
    if events is None:
        return jsonify({
            "ok": False,
            "message": (
                "La bitácora todavía no está disponible. Ejecuta la migración "
                "20260728_realtime_audit_log.sql en Supabase."
            ),
            "events": [],
        }), 503

    search = (request.args.get("q") or "").strip().casefold()
    module = (request.args.get("module") or "").strip()
    severity = (request.args.get("severity") or "").strip()

    filtered = []
    for event in events:
        searchable = " ".join(
            str(event.get(field) or "")
            for field in (
                "titulo", "detalle", "modulo", "entidad_id",
                "actor_nombre", "actor_username"
            )
        ).casefold()
        if search and search not in searchable:
            continue
        if module and event.get("modulo") != module:
            continue
        if severity and event.get("severidad") != severity:
            continue
        filtered.append(event)

    modules = sorted({
        event.get("modulo") for event in events if event.get("modulo")
    })
    today = datetime.now().date().isoformat()
    stats = {
        "total": len(events),
        "today": sum(
            1 for event in events
            if str(event.get("creado_en") or "")[:10] == today
        ),
        "warnings": sum(
            1 for event in events
            if event.get("severidad") in {"warning", "danger"}
        ),
        "modules": len(modules),
    }

    return jsonify({
        "ok": True,
        "events": filtered[:100],
        "modules": modules,
        "stats": stats,
        "refreshed_at": datetime.now().isoformat(),
    })

@app_routes.route("/admin/employees", methods=["GET", "POST"])
@require_role("Admin")
def manage_employees():
    empleados = obtener_empleados()

    if request.method == "POST":
        flash("Empleado añadido correctamente", "success")
        return redirect(url_for("app_routes.manage_employees"))
    
    return render_template("admin/employees.html", empleados=empleados)

from flask import redirect, render_template, request, url_for
import bcrypt

@app_routes.route("/admin/add_employee", methods=["GET", "POST"])
@require_role("Admin")
def add_employee():
    if request.method == "POST":
        form_data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in request.form.to_dict().items()
        }
        selected_permissions = normalize_permissions(request.form.getlist("permisos"))
        form_data["permisos"] = selected_permissions
        form_data["rol_id"] = form_data.get("tipo_empleado", "")

        required_fields = [
            "sexo", "fecha_nacimiento", "nombres", "apellidos", "telefono", "correo",
            "username", "password", "calle", "numero_ext", "codigo_postal", "municipio",
            "estado", "curp_rfc", "turno", "contacto_emergencia", "tipo_empleado"
        ]

        if not all(form_data.get(field) for field in required_fields):
            flash("Completa todos los campos obligatorios antes de guardar.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )

        # Datos generales
        sexo = form_data['sexo']
        fecha_nacimiento = form_data['fecha_nacimiento']
        nombres = form_data['nombres']
        apellidos = form_data['apellidos']
        telefono = form_data['telefono']
        correo = form_data['correo']
        username = form_data['username']
        password = form_data['password']
        calle = form_data['calle']
        numero_ext = form_data['numero_ext']
        numero_int = form_data.get('numero_int') or None
        codigo_postal = form_data['codigo_postal']
        municipio = form_data['municipio']
        estado = form_data['estado']
        curp_rfc = form_data['curp_rfc']
        turno = form_data['turno']
        condiciones_medicas = form_data.get('condiciones_medicas', '')
        contacto_emergencia = form_data['contacto_emergencia']
        rol_id = form_data.get('tipo_empleado')
        if (
            not rol_id.isdigit() or int(rol_id) not in role_map
            or sexo not in {"M", "F", "O"}
            or turno not in {"Matutino", "Vespertino", "Nocturno", "Mixto"}
            or len(password) < 8
        ):
            flash("Revisa el rol, sexo, turno y la contraseña antes de guardar.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )
        rol_id = int(rol_id)
        if rol_id == 5 and not selected_permissions:
            flash("Selecciona al menos un permiso para el perfil personalizado.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )

        # Verificar si el usuario ya existe
        existing_user = supabase.table('usuarios').select('id').eq('username', username).execute()
        if existing_user.data:
            flash("El nombre de usuario ya está en uso.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )

        avatar_file = request.files.get("foto_perfil")
        avatar_choice = normalize_avatar_choice(form_data.get("avatar_choice"))
        avatar_extension, avatar_error = validate_employee_avatar(avatar_file)
        if avatar_error:
            flash(avatar_error, "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )
        if avatar_choice == "upload" and not avatar_extension:
            flash("Selecciona una fotografía antes de guardar.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )
        if avatar_choice.startswith("preset:"):
            foto_perfil = avatar_choice
        elif avatar_choice == "upload":
            foto_perfil = save_employee_avatar(avatar_file, avatar_extension)
        else:
            foto_perfil = None

        signature_file = request.files.get("firma_resultados")
        signature_extension, signature_error = validate_employee_avatar(signature_file)
        cedula_profesional = (form_data.get("cedula_profesional") or "").strip() or None
        puede_firmar = (
            form_data.get("puede_firmar_resultados") == "on"
            and rol_id in {1, 4}
        )
        if signature_error:
            flash("La firma debe ser una imagen JPG, PNG, GIF o WEBP válida.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )
        firma_resultados_url = (
            save_employee_signature(signature_file, signature_extension)
            if signature_extension else None
        )
        if puede_firmar and (not cedula_profesional or not firma_resultados_url):
            flash(
                "Para autorizar la firma registra la cédula profesional y su imagen.",
                "error",
            )
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=False,
                role_map=role_map, estados=estados
            )

        # Encriptar la contraseña con bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insertar usuario
        user_data = {"username": username, "password": hashed_password}
        user_response = supabase.table('usuarios').insert(user_data).execute()
        usuario_id = user_response.data[0]['id']

        # Insertar empleado
        employee_data = {
            "sexo": sexo,
            "fecha_nacimiento": fecha_nacimiento,
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo,
            "usuario_id": usuario_id,
            "calle": calle,
            "numero_ext": numero_ext,
            "numero_int": numero_int,
            "codigo_postal": codigo_postal,
            "municipio": municipio,
            "estado": estado, 
            "curp_rfc": curp_rfc,
            "turno": turno,
            "condiciones_medicas": condiciones_medicas,
            "contacto_emergencia": contacto_emergencia,
            "foto_perfil": foto_perfil,
            "cedula_profesional": cedula_profesional,
            "firma_resultados_url": firma_resultados_url,
            "puede_firmar_resultados": puede_firmar,
        }
        employee_response = supabase.table('empleados').insert(employee_data).execute()
        empleado_id = employee_response.data[0]['id']

        # Insertar rol en la tabla empleado_roles
        employee_role_data = {"empleado_id": empleado_id, "rol_id": rol_id}
        role_response = supabase.table('empleado_roles').insert(employee_role_data).execute()
        if rol_id == 5:
            reemplazar_permisos_empleado(empleado_id, selected_permissions)
        attribute_audit_event("empleados", empleado_id)

        flash("Empleado registrado correctamente", "success")
        return redirect(url_for('app_routes.manage_employees'))  # Redirección tras éxito

    return render_template(
        'admin/edit_employee.html',
        empleado={},
        is_edit=False,
        role_map=role_map,
        estados=estados,
    )




@app_routes.route('/admin/edit_employee/<int:empleado_id>', methods=['GET', 'POST'])  #metodo parecido al de añadir pero con la forma de obtener los datos para ponerlos
@require_role("Admin")
    
def edit_employee(empleado_id):
    if request.method == "GET":
        # Obtener los datos del empleado desde la base de datos
        empleado = supabase.table('empleados').select('*').eq('id', empleado_id).execute()
        if not empleado.data:
            flash("Empleado no encontrado", "error")
            return redirect(url_for("app_routes.manage_employees"))

        empleado = empleado.data[0]

        # Obtener el rol del empleado
        rol = supabase.table('empleado_roles').select('rol_id').eq('empleado_id', empleado_id).execute()
        if rol.data:
            empleado['rol_id'] = rol.data[0]['rol_id']
        empleado["permisos"] = (
            obtener_permisos_empleado(empleado_id)
            if empleado.get("rol_id") == 5 else []
        )

        # Obtener únicamente el nombre de usuario; la contraseña nunca se envía al formulario.
        usuario = supabase.table('usuarios').select('username').eq('id', empleado['usuario_id']).execute()
        if usuario.data:
            empleado['username'] = usuario.data[0]['username']

        # Renderizar la plantilla con los datos del empleado y role_map
        return render_template('admin/edit_employee.html', empleado=empleado, is_edit=True, role_map=role_map, estados=estados)

    elif request.method == "POST":
        form_data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in request.form.to_dict().items()
        }
        selected_permissions = normalize_permissions(request.form.getlist("permisos"))
        form_data["permisos"] = selected_permissions
        form_data["rol_id"] = form_data.get("tipo_empleado", "")

        required_fields = [
            "sexo", "fecha_nacimiento", "nombres", "apellidos", "telefono", "correo",
            "username", "calle", "numero_ext", "codigo_postal", "municipio", "estado",
            "curp_rfc", "turno", "contacto_emergencia", "tipo_empleado"
        ]

        if not all(form_data.get(field) for field in required_fields):
            flash("Completa todos los campos obligatorios antes de guardar.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )

        # Datos generales
        sexo = form_data['sexo']
        fecha_nacimiento = form_data['fecha_nacimiento']
        nombres = form_data['nombres']
        apellidos = form_data['apellidos']
        telefono = form_data['telefono']
        correo = form_data['correo']
        username = form_data['username']
        calle = form_data['calle']
        numero_ext = form_data['numero_ext']
        numero_int = form_data.get('numero_int') or None
        codigo_postal = form_data['codigo_postal']
        municipio = form_data['municipio']
        estado = form_data['estado']
        curp_rfc = form_data['curp_rfc']
        turno = form_data['turno']
        condiciones_medicas = form_data.get('condiciones_medicas', '')
        contacto_emergencia = form_data['contacto_emergencia']
        rol_id = form_data.get('tipo_empleado')

        nueva_password = form_data.get('password', '')
        if (
            not rol_id.isdigit() or int(rol_id) not in role_map
            or sexo not in {"M", "F", "O"}
            or turno not in {"Matutino", "Vespertino", "Nocturno", "Mixto"}
            or (nueva_password and len(nueva_password) < 8)
        ):
            flash("Revisa el rol, sexo, turno y la contraseña antes de guardar.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )
        rol_id = int(rol_id)
        if rol_id == 5 and not selected_permissions:
            flash("Selecciona al menos un permiso para el perfil personalizado.", "error")
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )

        # Obtener el empleado actual para recuperar el usuario_id
        empleado_actual = (
            supabase.table('empleados')
            .select('usuario_id, foto_perfil, cedula_profesional, firma_resultados_url, puede_firmar_resultados')
            .eq('id', empleado_id)
            .execute()
        )
        if not empleado_actual.data:
            flash("Empleado no encontrado", "error")
            return redirect(url_for("app_routes.manage_employees"))

        usuario_id = empleado_actual.data[0]['usuario_id']
        foto_actual = empleado_actual.data[0].get('foto_perfil')
        firma_actual = empleado_actual.data[0].get("firma_resultados_url")
        rol_actual_response = (
            supabase.table("empleado_roles")
            .select("rol_id")
            .eq("empleado_id", empleado_id)
            .limit(1)
            .execute()
        )
        rol_actual = (
            rol_actual_response.data[0].get("rol_id")
            if rol_actual_response.data else None
        )

        avatar_file = request.files.get("foto_perfil")
        avatar_choice = normalize_avatar_choice(form_data.get("avatar_choice"))
        avatar_extension, avatar_error = validate_employee_avatar(avatar_file)
        if avatar_error:
            flash(avatar_error, "error")
            form_data["foto_perfil"] = foto_actual
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )
        if avatar_choice == "upload" and not avatar_extension:
            flash("Selecciona una fotografía antes de guardar.", "error")
            form_data["foto_perfil"] = foto_actual
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )
        if avatar_choice.startswith("preset:"):
            nueva_foto = avatar_choice
        elif avatar_choice == "upload":
            nueva_foto = save_employee_avatar(avatar_file, avatar_extension)
        elif avatar_choice == "initials":
            nueva_foto = None
        else:
            nueva_foto = foto_actual

        signature_file = request.files.get("firma_resultados")
        signature_extension, signature_error = validate_employee_avatar(signature_file)
        if signature_error:
            flash("La firma debe ser una imagen JPG, PNG, GIF o WEBP válida.", "error")
            form_data["foto_perfil"] = foto_actual
            form_data["firma_resultados_url"] = firma_actual
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )
        nueva_firma = (
            save_employee_signature(signature_file, signature_extension)
            if signature_extension else firma_actual
        )
        cedula_profesional = (form_data.get("cedula_profesional") or "").strip() or None
        puede_firmar = (
            form_data.get("puede_firmar_resultados") == "on"
            and rol_id in {1, 4}
        )
        if puede_firmar and (not cedula_profesional or not nueva_firma):
            flash(
                "Para autorizar la firma registra la cédula profesional y su imagen.",
                "error",
            )
            form_data["foto_perfil"] = foto_actual
            form_data["firma_resultados_url"] = firma_actual
            return render_template(
                'admin/edit_employee.html', empleado=form_data, is_edit=True,
                role_map=role_map, estados=estados
            )

        # Actualizar el usuario
        usuario_data = {"username": username}
        if nueva_password:  # Si se proporciona una nueva contraseña
            hashed_password = bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            usuario_data['password'] = hashed_password

        supabase.table('usuarios').update(usuario_data).eq('id', usuario_id).execute()

        # Actualizar el empleado
        empleado_data = {
            "sexo": sexo,
            "fecha_nacimiento": fecha_nacimiento,
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo,
            "calle": calle,
            "numero_ext": numero_ext,
            "numero_int": numero_int,
            "codigo_postal": codigo_postal,
            "municipio": municipio,
            "estado": estado,
            "curp_rfc": curp_rfc,
            "turno": turno,
            "condiciones_medicas": condiciones_medicas,
            "contacto_emergencia": contacto_emergencia,
            "foto_perfil": nueva_foto,
            "cedula_profesional": cedula_profesional,
            "firma_resultados_url": nueva_firma,
            "puede_firmar_resultados": puede_firmar,
        }
        supabase.table('empleados').update(empleado_data).eq('id', empleado_id).execute()

        if nueva_foto != foto_actual and foto_actual:
            delete_local_employee_avatar(foto_actual)
        if session.get("empleado_id") == empleado_id:
            session["foto_perfil"] = empleado_data["foto_perfil"]

        # Actualizar el rol del empleado
        supabase.table('empleado_roles').update({"rol_id": rol_id}).eq('empleado_id', empleado_id).execute()
        if rol_id == 5 or rol_actual == 5:
            reemplazar_permisos_empleado(
                empleado_id, selected_permissions if rol_id == 5 else []
            )
        cambios_extra = []
        if nueva_password:
            cambios_extra.append({
                "campo": "password",
                "anterior": "Protegida",
                "nuevo": "Actualizada",
            })
        if rol_actual != rol_id:
            cambios_extra.append({
                "campo": "rol",
                "anterior": role_map.get(rol_actual, "Sin rol"),
                "nuevo": role_map.get(rol_id, "Sin rol"),
            })
        if rol_id == 5:
            cambios_extra.append({
                "campo": "permisos",
                "anterior": "Configuración anterior",
                "nuevo": f"{len(selected_permissions)} permisos asignados",
            })
        attribute_audit_event("empleados", empleado_id, cambios_extra)

        flash("Empleado actualizado correctamente", "success")
        return redirect(url_for("app_routes.manage_employees"))

    
@app_routes.route('/admin/delete_employee/<int:id>', methods=['POST'])
@require_role("Admin")
def delete_employee(id):
    # Verificar si el usuario ha iniciado sesión
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    # Obtener la contraseña del formulario
    password = request.form.get('password', '').strip()  # Eliminar espacios en blanco

    if not password:
        return jsonify({"message": "La contraseña es requerida."}), 400

    # Verificar la contraseña del administrador
    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()

    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404

    admin_user = admin_user_query.data  # Obtener el usuario administrador

    # Validar la contraseña utilizando bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    # Desactivar al empleado (marcar como inactivo)
    try:
        supabase.table('usuarios').update({'estado_usuario': False}).eq('id', id).execute()
        return jsonify({"message": "Empleado desactivado correctamente."}), 200
    except Exception as e:
        print(f"Error al desactivar el empleado: {e}")
        return jsonify({"message": "Error al desactivar el empleado."}), 500
    
@app_routes.route('/admin/activate_employee/<int:user_id>', methods=['POST'])
@require_role("Admin")
def activate_employee(user_id):
    """ Activar un usuario en la base de datos verificando la contraseña del administrador """
    password = request.form.get('password', '').strip()

    # Verificar si el administrador ha iniciado sesión
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    # Obtener el usuario administrador de la sesión
    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    
    if not admin_user_query.data:
        return jsonify({"message": "Administrador no encontrado."}), 404

    admin_user = admin_user_query.data

    # Verificar la contraseña del administrador
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    # Verificar que el usuario a activar existe y está desactivado
    user_query = supabase.table('usuarios').select('*').eq('id', user_id).single().execute()
    
    if not user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404

    user = user_query.data

    if user['estado_usuario']:
        return jsonify({"message": "El usuario ya está activado."}), 400

    try:
        # Activar el usuario en la base de datos
        supabase.table('usuarios').update({'estado_usuario': True}).eq('id', user_id).execute()
        return jsonify({"message": "Usuario activado correctamente."}), 200
    except Exception as e:
        print(f"Error al activar usuario: {e}")
        return jsonify({"message": "Error al activar usuario."}), 500

    
@app_routes.route("/mostrador")
@require_role("Mostrador")
def mostrador_dashboard():
    return render_template(
        "mostrador/mostrador.html",
        resumen=obtener_resumen_mostrador(),
    )

@app_routes.route("/enfermero")
@require_role("Enfermero")
def enfermero_dashboard():
    pendientes = obtener_ordenes_para_muestra()
    en_analisis = obtener_ordenes_para_quimico()
    return render_template(
        "enfermero/enfermero.html",
        pendientes=pendientes,
        en_analisis=en_analisis,
        resumen={
            "muestras_pendientes": len(pendientes),
            "en_analisis": len(en_analisis),
            "carga_operativa": len(pendientes) + len(en_analisis),
        },
    )

@app_routes.route("/quimico")
@require_role("Quimico")
def quimico_dashboard():
    ordenes = obtener_ordenes_para_quimico()
    faltantes = obtener_ordenes_para_muestra()
    finalizados = obtener_historial_resultados()
    return render_template(
        "quimico/quimico.html",
        ordenes=ordenes,
        faltantes=faltantes,
        finalizados=finalizados,
        resumen={
            "ordenes_laboratorio": len(ordenes),
            "faltantes_muestra": len(faltantes),
            "carga_operativa": len(ordenes) + len(faltantes),
            "resultados_finalizados": len(finalizados),
        },
    )

# Ruta para la gestión de hospitales con estados únicos
@app_routes.route('/admin/hospitals')
@require_role("Admin")
def manage_hospitals():
    """Página de gestión de hospitales"""
    hospitales = obtener_hospitales()

    # Obtener estados únicos de hospitales registrados en la base de datos
    estados_registrados_query = supabase.table('hospitales').select("estado").execute()
    estados_registrados = list(set(hospital["estado"] for hospital in estados_registrados_query.data if hospital["estado"]))

    return render_template('admin/hospitals.html', hospitales=hospitales, estados_registrados=sorted(estados_registrados))

# Ruta para agregar un hospital
@app_routes.route('/admin/add_hospital', methods=['GET', 'POST'])
@require_role(["Admin", "Mostrador"])
def add_hospital():
    """Formulario para agregar un hospital"""
    if request.method == 'POST':
        form_data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in request.form.to_dict().items()
        }
        is_embedded = form_data.pop("embed", "") == "1"
        required_fields = ('nombre', 'telefono')
        if not all(form_data.get(field) for field in required_fields):
            flash("Completa todos los campos obligatorios antes de guardar.", "error")
            return render_template(
                'admin/add_hospital.html', hospital=form_data,
                is_edit=False, estados=estados
            )

        nombre = form_data['nombre']
        telefono = form_data['telefono']
        correo = form_data.get('correo') or None
        calle = form_data.get('calle') or None
        numero_ext = form_data.get('numero_ext') or None
        numero_int = form_data.get('numero_int') or None
        codigo_postal = form_data.get('codigo_postal') or None
        municipio = form_data.get('municipio') or None
        estado = form_data.get('estado') or None
        anotaciones = form_data.get('anotaciones', '')

        duplicado = (
            supabase.table("hospitales")
            .select("id")
            .eq("telefono", telefono)
            .execute()
        )
        if duplicado.data:
            flash("Ya existe un hospital registrado con ese teléfono.", "error")
            return render_template(
                "admin/add_hospital.html", hospital=form_data,
                is_edit=False, estados=estados
            )

        creado = crear_hospital(nombre, telefono, correo, calle, numero_ext, numero_int, codigo_postal, municipio, estado, anotaciones)
        if is_embedded and creado:
            return render_template(
                "components/embed_success.html",
                entity="hospital",
                entity_id=creado[0].get("id"),
            )
        flash("Hospital registrado exitosamente", "success")
        if current_workspace_role() == "Mostrador":
            return redirect(url_for("app_routes.manage_orden"))
        return redirect(url_for('app_routes.manage_hospitals'))
    
    return render_template('admin/add_hospital.html', hospital={}, is_edit=False, estados=estados)

# Ruta para editar un hospital
@app_routes.route('/admin/edit_hospital/<int:hospital_id>', methods=['GET', 'POST'])
@require_role("Admin")
def edit_hospital(hospital_id):
    """Formulario para editar un hospital"""
    hospital = obtener_hospital_por_id(hospital_id)
    
    if not hospital:
        flash("Hospital no encontrado", "error")
        return redirect(url_for('app_routes.manage_hospitals'))

    if request.method == 'POST':
        form_data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in request.form.to_dict().items()
        }
        required_fields = ('nombre', 'telefono')
        if not all(form_data.get(field) for field in required_fields):
            flash("Completa todos los campos obligatorios antes de guardar.", "error")
            return render_template(
                'admin/add_hospital.html', hospital=form_data,
                is_edit=True, estados=estados
            )

        nombre = form_data['nombre']
        telefono = form_data['telefono']
        correo = form_data.get('correo') or None
        calle = form_data.get('calle') or None
        numero_ext = form_data.get('numero_ext') or None
        numero_int = form_data.get('numero_int') or None
        codigo_postal = form_data.get('codigo_postal') or None
        municipio = form_data.get('municipio') or None
        estado = form_data.get('estado') or None
        anotaciones = form_data.get('anotaciones', '')

        actualizar_hospital(hospital_id, nombre, telefono, correo, calle, numero_ext, numero_int, codigo_postal, municipio, estado, anotaciones)
        attribute_audit_event("hospitales", hospital_id)
        flash("Hospital actualizado exitosamente", "success")
        return redirect(url_for('app_routes.manage_hospitals'))

    return render_template('admin/add_hospital.html', hospital=hospital, is_edit=True, estados=estados)

# Ruta para eliminar (desactivar) un hospital
@app_routes.route('/admin/delete_hospital/<int:hospital_id>', methods=['POST'])
@require_role("Admin")
def delete_hospital(hospital_id):
    """Eliminar (desactivar) un hospital verificando la contraseña del administrador"""
    password = request.form.get('password', '').strip()
    
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403
    
    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    
    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404
    
    admin_user = admin_user_query.data
    
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401
    
    try:
        eliminar_hospital(hospital_id)
        attribute_audit_event("hospitales", hospital_id)
        return jsonify({"message": "Hospital eliminado correctamente."}), 200
    except Exception:
        return jsonify({"message": "Error al eliminar hospital."}), 500

# Ruta para activar un hospital
@app_routes.route('/admin/activate_hospital/<int:hospital_id>', methods=['POST'])
@require_role("Admin")
def activate_hospital(hospital_id):
    """Activar un hospital en la base de datos verificando la contraseña del administrador"""
    password = request.form.get('password', '').strip()
    
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403
    
    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    
    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404
    
    admin_user = admin_user_query.data
    
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401
    
    try:
        response = supabase.table('hospitales').update({"activo": True}).eq('id', hospital_id).execute()
        attribute_audit_event("hospitales", hospital_id)
        return jsonify({"message": "Hospital activado correctamente."}), 200
    except Exception:
        return jsonify({"message": "Error al activar hospital."}), 500
    
# Rutas de sidebar según rol
@app_routes.route("/reportes")
@require_role("Admin")
def reportes():
    return render_template("admin/reportes.html")

@app_routes.route("/configuracion", methods=["GET", "POST"])
@require_role(role_map.values())
def configuracion():
    # Solo usuarios logueados
    if "usuario" not in session:
        return redirect(url_for("app_routes.login"))

    system_settings = obtener_configuracion_sistema()
    is_admin = session.get("rol") == "Admin"

    if request.method == "POST":
        empleado_id = session.get("empleado_id")
        if not empleado_id:
            flash("No se encontró el perfil del empleado.", "error")
            return redirect(url_for("app_routes.configuracion"))

        override_authorizer = None
        if not is_admin and not system_settings["empleados_cambian_foto"]:
            override_authorizer = admin_override_from_request()
            if not override_authorizer:
                flash(
                    "El cambio de foto está restringido. Ingresa credenciales válidas de un autorizador administrativo.",
                    "error",
                )
                return redirect(url_for("app_routes.configuracion"))

        avatar_file = request.files.get("foto_perfil")
        avatar_choice = normalize_avatar_choice(request.form.get("avatar_choice"))
        avatar_extension, avatar_error = validate_employee_avatar(avatar_file)
        if avatar_error:
            flash(avatar_error, "error")
            return redirect(url_for("app_routes.configuracion"))

        foto_actual = session.get("foto_perfil")
        if avatar_choice == "upload" and not avatar_extension:
            flash("Selecciona una fotografía antes de guardar.", "error")
            return redirect(url_for("app_routes.configuracion"))
        if avatar_choice.startswith("preset:"):
            foto_perfil = avatar_choice
        elif avatar_choice == "upload":
            foto_perfil = save_employee_avatar(avatar_file, avatar_extension)
        elif avatar_choice == "initials":
            foto_perfil = None
        else:
            foto_perfil = foto_actual

        supabase.table("empleados").update(
            {"foto_perfil": foto_perfil}
        ).eq("id", empleado_id).execute()
        attribute_audit_event("empleados", empleado_id)

        if foto_perfil != foto_actual and foto_actual:
            delete_local_employee_avatar(foto_actual)
        session["foto_perfil"] = foto_perfil
        if override_authorizer:
            registrar_excepcion_sistema(
                "cambiar_foto_perfil",
                f"Se autorizó el cambio de foto de @{session.get('usuario')}.",
                override_authorizer,
                override_requester(),
            )
        flash("Foto de perfil actualizada.", "success")
        return redirect(url_for("app_routes.configuracion"))

    user = {
        "username": session.get("usuario"),
        "rol": session.get("rol", "—"),
        "nombres": session.get("nombres", "—"),
        "foto_perfil": session.get("foto_perfil"),  # puede ser None
    }

    return render_template(
        "admin/configuracion.html",
        user=user,
        system_settings=system_settings,
    )


@app_routes.route("/configuracion/password", methods=["POST"])
@require_role(role_map.values())
def cambiar_password_personal():
    current_password = request.form.get("current_password") or ""
    new_password = request.form.get("new_password") or ""
    confirmation = request.form.get("confirm_password") or ""
    if len(new_password) < 8 or new_password != confirmation:
        flash("La contraseña nueva debe tener al menos 8 caracteres y coincidir.", "error")
        return redirect(url_for("app_routes.configuracion"))

    user_response = (
        supabase.table("usuarios").select("id,password")
        .eq("id", session.get("user_id")).limit(1).execute()
    )
    if not user_response.data or not bcrypt.checkpw(
        current_password.encode("utf-8"),
        str(user_response.data[0].get("password") or "").encode("utf-8"),
    ):
        flash("Tu contraseña actual no es correcta.", "error")
        return redirect(url_for("app_routes.configuracion"))

    settings = obtener_configuracion_sistema()
    override_authorizer = None
    if session.get("rol") != "Admin" and not settings["empleados_cambian_password"]:
        override_authorizer = admin_override_from_request()
        if not override_authorizer:
            flash(
                "El cambio de contraseña está restringido. Se requiere autorización administrativa.",
                "error",
            )
            return redirect(url_for("app_routes.configuracion"))

    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    supabase.table("usuarios").update({"password": hashed}).eq(
        "id", session.get("user_id")
    ).execute()
    attribute_audit_event(
        "usuarios", session.get("user_id"),
        [{"campo": "password", "anterior": "Protegida", "nuevo": "Actualizada"}],
    )
    if override_authorizer:
        registrar_excepcion_sistema(
            "cambiar_password",
            f"Se autorizó el cambio de contraseña de @{session.get('usuario')}.",
            override_authorizer,
            override_requester(),
        )
    flash("Contraseña actualizada correctamente.", "success")
    return redirect(url_for("app_routes.configuracion"))


@app_routes.route("/configuracion/sistema", methods=["POST"])
@require_role("Admin")
def guardar_politicas_sistema():
    settings = {
        "empleados_cambian_password": request.form.get("empleados_cambian_password") == "on",
        "empleados_cambian_foto": request.form.get("empleados_cambian_foto") == "on",
        "mostrador_entrega_saldo_pendiente": request.form.get(
            "mostrador_entrega_saldo_pendiente"
        ) == "on",
    }
    guardar_configuracion_sistema(settings, session.get("user_id"))
    registrar_cambio_politicas(settings, override_requester())
    flash("Políticas del sistema actualizadas.", "success")
    return redirect(url_for("app_routes.configuracion_sistema"))


@app_routes.route("/configuracion/sistema/recibos", methods=["POST"])
@require_role("Admin")
def guardar_configuracion_recibos_route():
    boolean_fields = {
        "mostrar_laboratorio_nombre", "mostrar_laboratorio_logo",
        "mostrar_laboratorio_rfc", "mostrar_laboratorio_telefono",
        "mostrar_laboratorio_whatsapp", "mostrar_laboratorio_correo",
        "mostrar_laboratorio_direccion",
        "mostrar_paciente_telefono", "mostrar_paciente_direccion",
        "mostrar_procedencia", "mostrar_medico", "mostrar_estudios",
        "mostrar_observaciones", "mostrar_cajero",
        "mostrar_historial_pagos", "mostrar_saldo",
    }
    receipt_settings = {
        key: request.form.get(key) == "on"
        for key in boolean_fields
    }
    receipt_settings["recibo_mensaje_pie"] = (
        request.form.get("recibo_mensaje_pie") or ""
    ).strip()
    receipt_settings["ticket_ancho_mm"] = (
        request.form.get("ticket_ancho_mm")
        if request.form.get("ticket_ancho_mm") in {"58", "80"}
        else "80"
    )

    try:
        guardar_configuracion_recibos(receipt_settings, session.get("user_id"))
    except Exception:
        logger.exception("No se pudo guardar la configuración de recibos")
        flash(
            "No se pudo guardar. Verifica que la migración de configuración de recibos esté aplicada.",
            "error",
        )
        return redirect(url_for("app_routes.configuracion_sistema"))

    registrar_cambio_politicas(
        {"recibos_mostrador": "Configuración actualizada"}, override_requester()
    )
    flash("Configuración de recibos actualizada.", "success")
    return redirect(url_for("app_routes.configuracion_sistema"))


@app_routes.route("/configuracion/sistema/identidad", methods=["POST"])
@require_role("Admin")
def guardar_identidad_laboratorio_route():
    current = obtener_identidad_laboratorio()
    name = (request.form.get("nombre") or "").strip()
    short_name = (request.form.get("nombre_corto") or "").strip()
    if not name or not short_name:
        flash("El nombre del laboratorio y el nombre corto son obligatorios.", "error")
        return redirect(url_for("app_routes.configuracion_sistema"))

    settings = {
        key: (request.form.get(key) or "").strip()
        for key in {"nombre", "nombre_corto", "rfc", "telefono", "whatsapp", "correo", "direccion"}
    }
    settings["logo_url"] = "" if request.form.get("eliminar_logo") == "on" else current.get("logo_url", "")
    settings["favicon_url"] = "" if request.form.get("eliminar_favicon") == "on" else current.get("favicon_url", "")

    for field_name, asset_type, target_key in (
        ("logo", "logo", "logo_url"),
        ("favicon", "favicon", "favicon_url"),
    ):
        image = request.files.get(field_name)
        extension, error = validate_brand_asset(image, asset_type)
        if error:
            flash(f"{field_name.title()}: {error}", "error")
            return redirect(url_for("app_routes.configuracion_sistema"))
        if extension:
            try:
                settings[target_key] = save_brand_asset(image, extension, asset_type)
            except Exception:
                logger.exception("No se pudo guardar el recurso de identidad")
                flash("No se pudo subir la imagen. Revisa la configuración de Storage.", "error")
                return redirect(url_for("app_routes.configuracion_sistema"))

    try:
        guardar_configuracion_laboratorio(settings, session.get("user_id"))
        for key in ("logo_url", "favicon_url"):
            if current.get(key) and current.get(key) != settings.get(key):
                try:
                    delete_brand_asset(current[key])
                except Exception:
                    logger.warning("No se pudo retirar el recurso anterior %s", key, exc_info=True)
    except Exception:
        logger.exception("No se pudo guardar la identidad del laboratorio")
        flash(
            "No se pudo guardar la identidad. Verifica la conexión y la configuración de recibos en Supabase.",
            "error",
        )
        return redirect(url_for("app_routes.configuracion_sistema"))

    registrar_cambio_politicas(
        {"identidad_laboratorio": "Configuración actualizada"}, override_requester()
    )
    flash("Identidad del laboratorio actualizada.", "success")
    return redirect(url_for("app_routes.configuracion_sistema"))


@app_routes.route("/admin/configuracion-sistema")
@require_role("Admin")
def configuracion_sistema():
    try:
        label_settings = obtener_configuracion_etiquetas()
    except Exception:
        logger.exception("No se pudo cargar la configuración de etiquetas")
        label_settings = {
            "ancho_mm": 60, "alto_mm": 40,
            "copias_predeterminadas": 1, "mostrar_qr": True,
        }
    return render_template(
        "admin/configuracion_sistema.html",
        system_settings=obtener_configuracion_sistema(),
        label_settings=label_settings,
    )


@app_routes.route("/faltantes")
@require_role("Mostrador")
def faltantes():
    return redirect(url_for("app_routes.listos"))


@app_routes.route("/pacientes")
@require_role("Enfermero")
def pacientes():
    return render_template("enfermero/pacientes.html")


@app_routes.route("/admin/doctores", methods=["GET"])
@require_role("Admin")
def manage_doctores():
    doctores = obtener_doctores()
    return render_template("admin/doctores.html", doctores=doctores)

@app_routes.route("/admin/add_doctor", methods=["GET", "POST"])
@require_role(["Admin", "Mostrador"])
def add_doctor():
    hospitales = supabase.table("hospitales").select("id, nombre").execute().data

    if request.method == "POST":
        form_data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in request.form.to_dict().items()
        }
        is_embedded = form_data.pop("embed", "") == "1"
        nombres = form_data.get("nombres", "")
        apellidos = form_data.get("apellidos", "")
        telefono = form_data.get("telefono", "")
        correo = form_data.get("correo", "")
        tipo_consultorio = form_data.get("tipo_consultorio", "")
        anotaciones = form_data.get("anotaciones", "")

        required_data = all((nombres, apellidos, telefono))
        valid_office = tipo_consultorio in {"na", "propio", "hospital"}
        valid_address = tipo_consultorio != "propio" or all(
            form_data.get(field)
            for field in ("calle", "numero_ext", "codigo_postal", "municipio", "estado")
        )
        valid_hospital = tipo_consultorio != "hospital" or form_data.get("hospital_id")

        if not all((required_data, valid_office, valid_address, valid_hospital)):
            flash("Completa todos los campos obligatorios antes de guardar.", "error")
            return render_template(
                "admin/add_doctor.html", doctor=form_data, hospitales=hospitales,
                estados=estados, is_edit=False
            )

        # Validación de duplicados (sin .and_())
        exists_by_data = supabase.table("doctores").select("id") \
            .eq("nombres", nombres) \
            .eq("apellidos", apellidos) \
            .eq("telefono", telefono) \
            .execute()

        exists_by_email = (
            supabase.table("doctores").select("id").eq("correo", correo).execute()
            if correo else None
        )

        if exists_by_data.data or (exists_by_email and exists_by_email.data):
            flash("Ya existe un doctor registrado con el mismo nombre, teléfono o correo.", "error")
            return render_template(
                "admin/add_doctor.html",
                doctor=form_data,
                hospitales=hospitales,
                estados=estados,
                is_edit=False
            )

        # Construcción del objeto para insertar
        data = {
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo or None,
            "tipo_consultorio": tipo_consultorio or "na",
            "anotaciones": anotaciones,
            "activo": True
        }

        if tipo_consultorio == "propio":
            data.update({
                "calle": form_data.get("calle"),
                "numero_ext": form_data.get("numero_ext"),
                "numero_int": form_data.get("numero_int") or None,
                "codigo_postal": form_data.get("codigo_postal"),
                "municipio": form_data.get("municipio"),
                "estado": form_data.get("estado"),
                "hospital_id": None
            })
        elif tipo_consultorio == "hospital":
            data.update({
                "hospital_id": form_data.get("hospital_id"),
                "calle": None,
                "numero_ext": None,
                "numero_int": None,
                "codigo_postal": None,
                "municipio": None,
                "estado": None
            })
        else:
            data.update({
                "hospital_id": None,
                "calle": None,
                "numero_ext": None,
                "numero_int": None,
                "codigo_postal": None,
                "municipio": None,
                "estado": None
            })

        creado = crear_doctor(data)
        if is_embedded and creado:
            return render_template(
                "components/embed_success.html",
                entity="doctor",
                entity_id=creado.get("id"),
            )
        flash("Doctor registrado correctamente.", "success")
        if current_workspace_role() == "Mostrador":
            return redirect(url_for("app_routes.manage_orden"))
        return redirect(url_for("app_routes.manage_doctores"))

    return render_template("admin/add_doctor.html", doctor={}, hospitales=hospitales, estados=estados, is_edit=False)

@app_routes.route("/admin/edit_doctor/<int:doctor_id>", methods=["GET", "POST"])
@require_role("Admin")
def edit_doctor(doctor_id):
    if request.method == "GET":
        doctor = supabase.table("doctores").select("*").eq("id", doctor_id).single().execute().data
        hospitales = supabase.table("hospitales").select("id, nombre").execute().data

        return render_template(
            "admin/add_doctor.html",
            doctor=doctor,
            hospitales=hospitales,
            estados=estados,
            is_edit=True
        )

    elif request.method == "POST":
        form_data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in request.form.to_dict().items()
        }
        nombres = form_data.get("nombres", "")
        apellidos = form_data.get("apellidos", "")
        telefono = form_data.get("telefono", "")
        correo = form_data.get("correo", "")
        tipo_consultorio = form_data.get("tipo_consultorio", "")
        anotaciones = form_data.get("anotaciones", "")
        hospitales = supabase.table("hospitales").select("id, nombre").execute().data

        required_data = all((nombres, apellidos, telefono))
        valid_office = tipo_consultorio in {"na", "propio", "hospital"}
        valid_address = tipo_consultorio != "propio" or all(
            form_data.get(field)
            for field in ("calle", "numero_ext", "codigo_postal", "municipio", "estado")
        )
        valid_hospital = tipo_consultorio != "hospital" or form_data.get("hospital_id")

        if not all((required_data, valid_office, valid_address, valid_hospital)):
            flash("Completa todos los campos obligatorios antes de guardar.", "error")
            return render_template(
                "admin/add_doctor.html", doctor=form_data, hospitales=hospitales,
                estados=estados, is_edit=True
            )

        # Verificar duplicados en otros doctores
        same_data = supabase.table("doctores").select("id") \
            .eq("nombres", nombres) \
            .eq("apellidos", apellidos) \
            .eq("telefono", telefono) \
            .neq("id", doctor_id) \
            .execute()

        same_email = (
            supabase.table("doctores").select("id")
            .eq("correo", correo).neq("id", doctor_id).execute()
            if correo else None
        )

        if same_data.data or (same_email and same_email.data):
            flash("Ya existe otro doctor con los mismos datos. Revisa nombre, teléfono o correo.", "error")
            return render_template(
                "admin/add_doctor.html",
                doctor=form_data,
                hospitales=hospitales,
                estados=estados,
                is_edit=True
            )

        # Actualizar doctor
        data = {
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo or None,
            "tipo_consultorio": tipo_consultorio,
            "anotaciones": anotaciones
        }

        if tipo_consultorio == "propio":
            data.update({
                "calle": form_data.get("calle"),
                "numero_ext": form_data.get("numero_ext"),
                "numero_int": form_data.get("numero_int") or None,
                "codigo_postal": form_data.get("codigo_postal"),
                "municipio": form_data.get("municipio"),
                "estado": form_data.get("estado"),
                "hospital_id": None
            })
        elif tipo_consultorio == "hospital":
            data.update({
                "hospital_id": form_data.get("hospital_id"),
                "calle": None,
                "numero_ext": None,
                "numero_int": None,
                "codigo_postal": None,
                "municipio": None,
                "estado": None
            })
        else:
            data.update({
                "hospital_id": None,
                "calle": None,
                "numero_ext": None,
                "numero_int": None,
                "codigo_postal": None,
                "municipio": None,
                "estado": None
            })

        actualizar_doctor(doctor_id, data)
        attribute_audit_event("doctores", doctor_id)
        flash("Doctor actualizado correctamente.", "success")
        return redirect(url_for("app_routes.manage_doctores"))

@app_routes.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST'])
@require_role("Admin")
def delete_doctor(doctor_id):
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    password = request.form.get('password', '').strip()

    if not password:
        return jsonify({"message": "La contraseña es requerida."}), 400

    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()

    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404

    admin_user = admin_user_query.data

    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        supabase.table('doctores').update({'activo': False}).eq('id', doctor_id).execute()
        attribute_audit_event("doctores", doctor_id)
        return jsonify({"message": "Doctor desactivado correctamente."}), 200
    except Exception as e:
        print(f"Error al desactivar doctor: {e}")
        return jsonify({"message": "Error al desactivar doctor."}), 500

@app_routes.route('/admin/activate_doctor/<int:doctor_id>', methods=['POST'])
@require_role("Admin")
def activate_doctor(doctor_id):
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    password = request.form.get('password', '').strip()

    if not password:
        return jsonify({"message": "La contraseña es requerida."}), 400

    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()

    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404

    admin_user = admin_user_query.data

    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        supabase.table('doctores').update({'activo': True}).eq('id', doctor_id).execute()
        attribute_audit_event("doctores", doctor_id)
        return jsonify({"message": "Doctor activado correctamente."}), 200
    except Exception as e:
        print(f"Error al activar doctor: {e}")
        return jsonify({"message": "Error al activar doctor."}), 500

@app_routes.route("/api/check_doctor", methods=["POST"])
def check_doctor():
    data = request.get_json()
    nombres = data.get("nombres", "").strip()
    apellidos = data.get("apellidos", "").strip()
    telefono = data.get("telefono", "").strip()
    correo = data.get("correo", "").strip()

    if not (nombres and apellidos and telefono and correo):
        return jsonify({"exists": False})

    # Buscar duplicado exacto por nombre, apellido y teléfono
    exists_by_data = supabase.table("doctores").select("id") \
        .eq("nombres", nombres) \
        .eq("apellidos", apellidos) \
        .eq("telefono", telefono) \
        .execute()

    exists_by_email = supabase.table("doctores").select("id") \
        .eq("correo", correo) \
        .execute()

    if exists_by_data.data or exists_by_email.data:
        return jsonify({"exists": True})
    return jsonify({"exists": False})

# LISTAR
@app_routes.route('/admin/pacientes')
@require_role(['Admin', 'Mostrador'])
def manage_patients():
    pacientes = obtener_pacientes()
    return render_template('admin/patients.html', pacientes=pacientes, rol=current_workspace_role())


@app_routes.route("/pacientes/<int:patient_id>/historial")
@require_role(["Admin", "Mostrador"])
def historial_paciente(patient_id):
    paciente = obtener_paciente_por_id(patient_id)
    if not paciente:
        flash("No se encontró el expediente del paciente.", "error")
        return redirect(url_for("app_routes.manage_patients"))
    return render_template(
        "mostrador/historial_paciente.html",
        paciente=paciente,
        ordenes=obtener_historial_ordenes_paciente(patient_id),
    )

# CREAR
@app_routes.route('/admin/add_patient', methods=['GET', 'POST'])
@require_role(['Admin', 'Mostrador'])
def add_patient():
    hospitales = obtener_hospitales()
    if request.method == 'POST':
        data = request.form.to_dict()
        is_embedded = data.pop("embed", "") == "1"
        data["activo"] = True

        ok, result = crear_paciente_seguro(data)
        if not ok:
            flash(result, "error")
            return render_template('admin/add_patient.html', is_edit=False, estados=estados, hospitales=hospitales, patient=data)

        if is_embedded:
            return render_template(
                "components/embed_success.html",
                entity="patient",
                entity_id=result.get("id"),
            )
        flash("Paciente registrado exitosamente.", "success")
        return redirect(url_for('app_routes.manage_patients'))

    return render_template('admin/add_patient.html', is_edit=False, estados=estados, hospitales=hospitales, patient={})

# EDITAR
@app_routes.route('/admin/edit_patient/<int:patient_id>', methods=['GET', 'POST'])
@require_role(['Admin', 'Mostrador'])
def edit_patient(patient_id):
    hospitales = obtener_hospitales()
    paciente = obtener_paciente_por_id(patient_id)

    if request.method == 'POST':
        data = request.form.to_dict()
        is_embedded = data.pop("embed", "") == "1"

        ok, result = actualizar_paciente_seguro(patient_id, data)
        if not ok:
            flash(result, "error")
            data["id"] = patient_id
            return render_template('admin/add_patient.html', is_edit=True, estados=estados, hospitales=hospitales, patient=data)

        attribute_audit_event("pacientes", patient_id)
        if is_embedded:
            return render_template(
                "components/embed_success.html",
                entity="patient",
                entity_id=patient_id,
            )
        flash("Paciente actualizado correctamente.", "success")
        return redirect(url_for('app_routes.manage_patients'))

    return render_template('admin/add_patient.html', is_edit=True, estados=estados, hospitales=hospitales, patient=paciente)

# ELIMINAR (solo Admin con validación de contraseña)
@app_routes.route('/admin/delete_patient/<int:patient_id>', methods=['POST'])
@require_role("Admin")
def delete_patient(patient_id):
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    password = request.form.get('password', '').strip()
    if not password:
        return jsonify({"message": "La contraseña es requerida."}), 400

    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404

    admin_user = admin_user_query.data
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        eliminar_paciente(patient_id)
        attribute_audit_event("pacientes", patient_id)
        return jsonify({"message": "Paciente desactivado correctamente."}), 200
    except Exception as e:
        print(f"Error al desactivar paciente: {e}")
        return jsonify({"message": "Error al desactivar paciente."}), 500

# ACTIVAR (solo Admin con validación de contraseña)
@app_routes.route('/admin/activate_patient/<int:patient_id>', methods=['POST'])
@require_role("Admin")
def activate_patient(patient_id):
    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    password = request.form.get('password', '').strip()
    if not password:
        return jsonify({"message": "La contraseña es requerida."}), 400

    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    if not admin_user_query.data:
        return jsonify({"message": "Usuario no encontrado."}), 404

    admin_user = admin_user_query.data
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        activar_paciente(patient_id)
        return jsonify({"message": "Paciente activado correctamente."}), 200
    except Exception as e:
        print(f"Error al activar paciente: {e}")
        return jsonify({"message": "Error al activar paciente."}), 500

# VERIFICAR DUPLICADOS (AJAX)
@app_routes.route('/api/check_patient', methods=['POST'])
def check_patient():
    data = request.get_json()
    response = supabase.table("pacientes").select("id").or_(
        f"nombres.ilike.%{data['nombres']}%,apellidos.ilike.%{data['apellidos']}%,telefono.eq.{data['telefono']},correo.eq.{data['correo']}"
    ).execute()

    if response.data:
        return jsonify({"exists": True, "id": response.data[0]["id"]})
    return jsonify({"exists": False})

# PROVEEDORES
PROVIDER_CONTACT_FIELDS = ("contacto", "telefono", "correo")
PROVIDER_ADDRESS_FIELDS = (
    "calle", "numero_ext", "numero_int", "codigo_postal", "municipio", "estado"
)


def validar_formulario_proveedor(form_data):
    """Normaliza omisiones autorizadas y valida los datos operativos del proveedor."""
    data = {key: str(value).strip() for key, value in form_data.items()}
    sin_contacto = data.pop("sin_contacto", "") == "1"
    sin_domicilio = data.pop("sin_domicilio", "") == "1"

    if data.get("tipo") not in {"producto", "servicio"} or not data.get("nombre"):
        return data, sin_contacto, sin_domicilio, "Selecciona el tipo y escribe el nombre del proveedor."

    if data["tipo"] == "servicio" and sin_contacto:
        return data, False, sin_domicilio, "Los proveedores de servicios deben tener datos de contacto para coordinar la maquila."

    if sin_contacto:
        for field in PROVIDER_CONTACT_FIELDS:
            data[field] = ""
    elif any(not data.get(field) for field in PROVIDER_CONTACT_FIELDS):
        return data, sin_contacto, sin_domicilio, "Completa todos los datos de contacto o indica que no están disponibles."

    if data["tipo"] == "servicio" and sin_domicilio:
        return data, sin_contacto, False, "Los proveedores de servicios deben tener un domicilio para envíos y traslados."

    if sin_domicilio:
        for field in PROVIDER_ADDRESS_FIELDS:
            data[field] = ""
    elif any(not data.get(field) for field in PROVIDER_ADDRESS_FIELDS):
        return data, sin_contacto, sin_domicilio, "Completa todo el domicilio o indica que no está disponible."

    return data, sin_contacto, sin_domicilio, None


def proveedor_form_state(data, sin_contacto=False, sin_domicilio=False):
    state = dict(data)
    if sin_contacto:
        state["sin_contacto"] = "1"
    if sin_domicilio:
        state["sin_domicilio"] = "1"
    return state

@app_routes.route("/admin/proveedores")
@require_role("Admin")
def manage_proveedores():
    proveedores = obtener_proveedores()
    return render_template("admin/proveedores.html", proveedores=proveedores, rol=session.get("rol"))

@app_routes.route("/api/proveedores/activos")
@require_role("Admin")
def api_proveedores_activos():
    """Catálogo ligero para actualizar selectores sin abandonar el formulario."""
    proveedores = [
        {"id": proveedor.get("id"), "nombre": proveedor.get("nombre", "")}
        for proveedor in obtener_proveedores()
        if proveedor.get("activo", True)
    ]
    proveedores.sort(key=lambda proveedor: proveedor["nombre"].casefold())
    return jsonify({"proveedores": proveedores})

@app_routes.route("/admin/add_proveedor", methods=["GET", "POST"])
@require_role("Admin")
def add_proveedor():
    if request.method == "POST":
        raw_data = request.form.to_dict()
        is_embedded = raw_data.pop("embed", "") == "1"
        data, sin_contacto, sin_domicilio, validation_error = validar_formulario_proveedor(raw_data)
        data["activo"] = True

        if validation_error:
            flash(validation_error, "error")
            return render_template(
                "admin/add_proveedor.html",
                proveedor=proveedor_form_state(data, sin_contacto, sin_domicilio),
                is_edit=False,
                estados=estados,
            )

        ok, result = crear_proveedor_seguro(data)
        if not ok:
            flash(result, "error")
            return render_template(
                "admin/add_proveedor.html",
                proveedor=proveedor_form_state(data, sin_contacto, sin_domicilio),
                is_edit=False,
                estados=estados,
            )

        proveedor_id = result.get("id") if isinstance(result, dict) else None
        if proveedor_id:
            attribute_audit_event("proveedores", proveedor_id)
        if is_embedded:
            return render_template(
                "components/embed_success.html",
                entity="provider",
                entity_id=proveedor_id,
            )

        flash("Proveedor registrado correctamente.", "success")
        return redirect(url_for("app_routes.manage_proveedores"))

    return render_template("admin/add_proveedor.html", proveedor={}, is_edit=False, estados=estados)

@app_routes.route("/admin/edit_proveedor/<int:proveedor_id>", methods=["GET", "POST"])
@require_role("Admin")
def edit_proveedor(proveedor_id):
    proveedor = obtener_proveedor_por_id(proveedor_id)
    if not proveedor:
        flash("Proveedor no encontrado", "error")
        return redirect(url_for("app_routes.manage_proveedores"))

    if request.method == "POST":
        data, sin_contacto, sin_domicilio, validation_error = validar_formulario_proveedor(
            request.form.to_dict()
        )

        if validation_error:
            flash(validation_error, "error")
            state = proveedor_form_state(data, sin_contacto, sin_domicilio)
            state["id"] = proveedor_id
            return render_template(
                "admin/add_proveedor.html", proveedor=state, is_edit=True, estados=estados
            )

        ok, result = actualizar_proveedor_seguro(proveedor_id, data)
        if not ok:
            flash(result, "error")
            data["id"] = proveedor_id
            return render_template("admin/add_proveedor.html", proveedor=data, is_edit=True, estados=estados)

        attribute_audit_event("proveedores", proveedor_id)
        flash("Proveedor actualizado correctamente.", "success")
        return redirect(url_for("app_routes.manage_proveedores"))

    return render_template("admin/add_proveedor.html", proveedor=proveedor, is_edit=True, estados=estados)

@app_routes.route("/admin/delete_proveedor/<int:proveedor_id>", methods=["POST"])
@require_role("Admin")
def delete_proveedor(proveedor_id):
    password = request.form.get('password', '').strip()
    if not password or 'user_id' not in session:
        return jsonify({"message": "No autorizado."}), 403

    admin = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute().data
    if not bcrypt.checkpw(password.encode('utf-8'), admin['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    desactivar_proveedor(proveedor_id)
    attribute_audit_event("proveedores", proveedor_id)
    return jsonify({"message": "Proveedor desactivado correctamente."}), 200

@app_routes.route("/admin/activate_proveedor/<int:proveedor_id>", methods=["POST"])
@require_role("Admin")
def activate_proveedor(proveedor_id):
    password = request.form.get('password', '').strip()
    if not password or 'user_id' not in session:
        return jsonify({"message": "No autorizado."}), 403

    admin = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute().data
    if not bcrypt.checkpw(password.encode('utf-8'), admin['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    activar_proveedor(proveedor_id)
    attribute_audit_event("proveedores", proveedor_id)
    return jsonify({"message": "Proveedor activado correctamente."}), 200

# VERIFICAR DUPLICADOS (AJAX)
@app_routes.route('/api/check_proveedor', methods=['POST'])
def check_proveedor():
    data = request.get_json()
    response = supabase.table("proveedores").select("id").or_(
        f"nombre.ilike.%{data['nombre']}%,telefono.eq.{data['telefono']},correo.eq.{data['correo']}"
    ).execute()

    if response.data:
        return jsonify({"exists": True, "id": response.data[0]["id"]})
    return jsonify({"exists": False})

#Inventario
# Ruta para mostrar todos los reactivos (Inventario)
@app_routes.route("/admin/inventory")
@require_role("Admin")
def manage_inventory():
    reactivos = obtener_reactivos()  # Llamada a la función que obtiene los reactivos de la base de datos
    return render_template("admin/inventory.html", reactivos=reactivos)


@app_routes.route("/admin/inventory/entry", methods=["GET", "POST"])
@require_role("Admin, Quimico")
def registrar_entrada_inventario():
    reactivos = [reactivo for reactivo in obtener_reactivos() if reactivo.get("activo")]
    lotes = obtener_lotes_reactivos(solo_con_existencia=True)

    if request.method == "POST":
        reactivo_id = request.form.get("reactivo_id", "").strip()
        cantidad_raw = request.form.get("cantidad", "").strip()
        costo_raw = request.form.get("costo_unitario", "").strip()

        try:
            cantidad = int(cantidad_raw)
            costo = float(costo_raw) if costo_raw else None
        except ValueError:
            cantidad, costo = 0, None

        if not reactivo_id or cantidad <= 0 or (costo is not None and costo < 0):
            flash("Selecciona un reactivo e ingresa una cantidad válida.", "error")
            return render_template(
                "admin/inventory_entry.html",
                reactivos=reactivos,
                movimientos=obtener_movimientos_inventario(),
                lotes=lotes,
            )

        ok, result = registrar_entrada_reactivo(
            reactivo_id=reactivo_id,
            cantidad=cantidad,
            costo_unitario=costo,
            numero_lote=request.form.get("numero_lote"),
            fecha_vencimiento=request.form.get("fecha_vencimiento"),
            observaciones=request.form.get("observaciones"),
            empleado_id=session.get("empleado_id"),
        )
        if ok:
            nueva_existencia = result.get("existencia_nueva") if isinstance(result, dict) else None
            suffix = f" Nueva existencia: {nueva_existencia}." if nueva_existencia is not None else ""
            flash(f"Entrada registrada correctamente.{suffix}", "success")
            return redirect(url_for("app_routes.registrar_entrada_inventario"))

        flash(result, "error")

    return render_template(
        "admin/inventory_entry.html",
        reactivos=reactivos,
        movimientos=obtener_movimientos_inventario(),
        lotes=lotes,
    )


# Ruta para agregar un nuevo reactivo
@app_routes.route("/admin/add_reactivo", methods=["GET", "POST"])
@require_role("Admin")
def add_reactivo():
    if request.method == "POST":
        data = {key: value.strip() for key, value in request.form.to_dict().items()}
        alert_days = sorted({
            int(value) for value in request.form.getlist("alertas_vencimiento_dias")
            if value.isdigit() and int(value) in {7, 15, 30, 60, 90}
        }, reverse=True)
        data["alertas_vencimiento_dias"] = alert_days

        # CORREGIR clave 'proveedor' → 'proveedor_id'
        if 'proveedor' in data:
            data['proveedor_id'] = data.pop('proveedor')

        for field in ("numero_lote", "fecha_vencimiento", "ubicacion_inventario", "anotaciones"):
            if not (data.get(field) or "").strip():
                data[field] = None

        required = ("nombre", "tipo_reactivo", "proveedor_id", "costo_unidad",
                    "precio_unidad", "fecha_entrada", "cantidad_inicial")
        if any(not str(data.get(field) or "").strip() for field in required):
            flash("Completa todos los campos obligatorios del reactivo.", "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=data,
                proveedores=obtener_proveedores(),
                is_edit=False,
            )

        try:
            data["alerta_existencia_minima"] = int(data.get("alerta_existencia_minima") or 0)
            if (float(data["costo_unidad"]) < 0 or float(data["precio_unidad"]) < 0
                    or int(data["cantidad_inicial"]) < 0 or data["alerta_existencia_minima"] < 0):
                raise ValueError
        except ValueError:
            flash("Costo, precio y cantidad deben ser valores válidos y no negativos.", "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=data,
                proveedores=obtener_proveedores(),
                is_edit=False,
            )

        ok, result = crear_reactivo(data)
        if ok:
            flash(result, "success")
        else:
            flash(result, "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=data,
                proveedores=obtener_proveedores(),
                is_edit=False,
            )

        return redirect(url_for('app_routes.manage_inventory'))

    # Si es GET
    reactivo = None
    if 'reactivo_id' in request.args:
        reactivo_id = request.args.get('reactivo_id')
        reactivo = obtener_reactivo_por_id(reactivo_id)

    proveedores = obtener_proveedores()
    return render_template("admin/add_reactivo.html", reactivo=reactivo, proveedores=proveedores)


@app_routes.route('/admin/edit_reactivo/<int:reactivo_id>', methods=['GET', 'POST'])
@require_role('Admin')
def edit_reactivo(reactivo_id):
    # Obtén los detalles del reactivo desde la base de datos
    reactivo = supabase.table('reactivos').select('*').eq('id', reactivo_id).single().execute().data
    
    # Obtén la lista de proveedores desde la base de datos
    proveedores = supabase.table('proveedores').select('*').execute().data
    
    # Verifica si el reactivo fue encontrado
    if not reactivo:
        flash("Reactivo no encontrado", "error")
        return redirect(url_for('app_routes.manage_inventory'))
    
    # Si el método es POST, es cuando se va a editar el reactivo
    if request.method == 'POST':
        # Recibe los datos del formulario y actualiza el reactivo en la base de datos
        nombre = request.form.get('nombre')
        tipo_reactivo = request.form.get('tipo_reactivo')
        costo_unidad = request.form.get('costo_unidad') 
        precio_unidad = request.form.get('precio_unidad')
        proveedor_id = request.form.get('proveedor')  # El proveedor seleccionado
        fecha_entrada = request.form.get('fecha_entrada')
        numero_lote = request.form.get('numero_lote')
        fecha_vencimiento = request.form.get('fecha_vencimiento')
        ubicacion_inventario = request.form.get('ubicacion_inventario')
        anotaciones = request.form.get('anotaciones')
        alerta_existencia_minima = request.form.get("alerta_existencia_minima", "0")
        alertas_vencimiento_dias = sorted({
            int(value) for value in request.form.getlist("alertas_vencimiento_dias")
            if value.isdigit() and int(value) in {7, 15, 30, 60, 90}
        }, reverse=True)
        submitted_reactivo = {
            **reactivo,
            "id": reactivo_id,
            "nombre": (nombre or "").strip(),
            "tipo_reactivo": (tipo_reactivo or "").strip(),
            "costo_unidad": costo_unidad,
            "precio_unidad": precio_unidad,
            "proveedor_id": int(proveedor_id) if str(proveedor_id or "").isdigit() else proveedor_id,
            "fecha_entrada": fecha_entrada,
            "numero_lote": (numero_lote or "").strip() or None,
            "fecha_vencimiento": fecha_vencimiento or None,
            "ubicacion_inventario": (ubicacion_inventario or "").strip() or None,
            "anotaciones": (anotaciones or "").strip() or None,
            "alerta_existencia_minima": alerta_existencia_minima,
            "alertas_vencimiento_dias": alertas_vencimiento_dias,
        }

        if any(not str(value or "").strip() for value in (
            nombre, tipo_reactivo, costo_unidad, precio_unidad, proveedor_id, fecha_entrada
        )):
            flash("Completa todos los campos obligatorios del reactivo.", "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=submitted_reactivo,
                proveedores=proveedores,
                is_edit=True,
            )

        try:
            alerta_existencia_minima = int(alerta_existencia_minima)
            submitted_reactivo["alerta_existencia_minima"] = alerta_existencia_minima
            if float(costo_unidad) < 0 or float(precio_unidad) < 0 or alerta_existencia_minima < 0:
                raise ValueError
        except ValueError:
            flash("Costo y precio deben ser valores válidos y no negativos.", "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=submitted_reactivo,
                proveedores=proveedores,
                is_edit=True,
            )
        
        update_data = {
            'nombre': submitted_reactivo["nombre"],
            'tipo_reactivo': submitted_reactivo["tipo_reactivo"],
            'costo_unidad': costo_unidad,
            'precio_unidad': precio_unidad,
            'proveedor_id': submitted_reactivo["proveedor_id"],
            'fecha_entrada': fecha_entrada,
            'numero_lote': submitted_reactivo["numero_lote"],
            'fecha_vencimiento': submitted_reactivo["fecha_vencimiento"],
            'ubicacion_inventario': submitted_reactivo["ubicacion_inventario"],
            'anotaciones': submitted_reactivo["anotaciones"],
            'alerta_existencia_minima': alerta_existencia_minima,
            'alertas_vencimiento_dias': alertas_vencimiento_dias,
        }
        try:
            supabase.table('reactivos').update(update_data).eq('id', reactivo_id).execute()
            attribute_audit_event("reactivos", reactivo_id)
        except Exception as error:
            error_text = str(error)
            if (
                "PGRST204" in error_text
                or "alerta_existencia_minima" in error_text
                or "alertas_vencimiento_dias" in error_text
            ):
                flash(
                    "Supabase todavía no tiene las columnas de alertas. "
                    "Ejecuta la migración 20260728_inventory_alert_notifications.sql "
                    "y vuelve a intentarlo.",
                    "error",
                )
            else:
                print(f"Error al actualizar reactivo {reactivo_id}: {error}")
                flash(
                    "No se pudo actualizar el reactivo. Verifica los datos e inténtalo nuevamente.",
                    "error",
                )
            return render_template(
                "admin/add_reactivo.html",
                reactivo=submitted_reactivo,
                proveedores=proveedores,
                is_edit=True,
            )
        
        flash("Reactivo actualizado correctamente", "success")
        return redirect(url_for('app_routes.manage_inventory'))

    # Si el método es GET, solo renderizamos el formulario de edición con los datos del reactivo
    return render_template("admin/add_reactivo.html", reactivo=reactivo, proveedores=proveedores, is_edit=True)

@app_routes.route("/admin/delete_reactivo/<int:reactivo_id>", methods=["POST"])
@require_role("Admin")
def delete_reactivo(reactivo_id):
    password = request.form.get('password', '').strip()
    if not password or 'user_id' not in session:
        return jsonify({"message": "No autorizado."}), 403

    # Verificar la contraseña del administrador
    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user_query.data['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        # Desactivar el reactivo
        supabase.table('reactivos').update({"activo": False}).eq('id', reactivo_id).execute()
        attribute_audit_event("reactivos", reactivo_id)
        return jsonify({"message": "Reactivo desactivado correctamente."}), 200
    except Exception as e:
        print(f"Error al eliminar reactivo: {e}")
        return jsonify({"message": "Error al eliminar reactivo."}), 500


@app_routes.route("/admin/activate_reactivo/<int:reactivo_id>", methods=["POST"])
@require_role("Admin")
def activate_reactivo(reactivo_id):
    password = request.form.get('password', '').strip()
    if not password or 'user_id' not in session:
        return jsonify({"message": "No autorizado."}), 403

    # Verificar la contraseña del administrador
    admin_user_query = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute()
    if not bcrypt.checkpw(password.encode('utf-8'), admin_user_query.data['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        # Activar el reactivo
        supabase.table('reactivos').update({"activo": True}).eq('id', reactivo_id).execute()
        attribute_audit_event("reactivos", reactivo_id)
        return jsonify({"message": "Reactivo activado correctamente."}), 200
    except Exception as e:
        print(f"Error al activar reactivo: {e}")
        return jsonify({"message": "Error al activar reactivo."}), 500


@app_routes.route("/admin/get_reactivo_details/<int:reactivo_id>", methods=["GET"])
@require_role("Admin")
def get_reactivo_details(reactivo_id):
    try:
        # Obtener el reactivo por ID desde la base de datos
        reactivo = supabase.table('reactivos').select('*').eq('id', reactivo_id).single().execute().data
        if reactivo:
            # Obtener el proveedor asociado al reactivo
            proveedor = supabase.table('proveedores').select('nombre').eq('id', reactivo['proveedor_id']).single().execute().data

            # Devolver los detalles del reactivo en formato JSON
            return jsonify({
                "nombre": reactivo['nombre'],
                "tipo_reactivo": reactivo['tipo_reactivo'],
                "cantidad_inicial": reactivo.get('existencia_actual', reactivo['cantidad_inicial']),
                "precio_unidad": reactivo['precio_unidad'],
                "fecha_entrada": reactivo['fecha_entrada'],
                "fecha_vencimiento": reactivo['fecha_vencimiento'],
                "proveedor_nombre": proveedor['nombre'] if proveedor else "N/A",
                "lotes": obtener_lotes_reactivos(reactivo_id, solo_con_existencia=True),
            }), 200
        else:
            return jsonify({"message": "Reactivo no encontrado"}), 404
    except Exception as e:
        print(f"Error al obtener detalles del reactivo: {e}")
        return jsonify({"message": "Error al obtener detalles del reactivo"}), 500
    
# Vista principal de pruebas clínicas
@app_routes.route('/admin/pruebas')
@require_role("Admin")
def pruebas_clinicas():
    pruebas = obtener_pruebas()
    return render_template('admin/pruebas.html', pruebas=pruebas)

# Registrar nueva prueba clínica
@app_routes.route('/admin/add_prueba', methods=['GET', 'POST'])
@require_role("Admin")
def add_prueba():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo = request.form.get('tipo', '').strip()
        precio = request.form.get('precio', '').strip()  # Nuevo campo para precio

        # Lista de IDs de reactivos
        reactivos_ids = request.form.getlist('reactivos')

        # JSON de valores normales
        valores_normales_json = request.form.get('valores_normales_json', '[]')

        try:
            valores_normales = json.loads(valores_normales_json or '[]')
        except (json.JSONDecodeError, TypeError):
            valores_normales = []

        element_errors = validate_clinical_test_elements(valores_normales)
        reactivos_validos, reactivos_error = validar_reactivos_para_prueba(reactivos_ids)

        # Validación básica antes de crear cualquier registro.
        if not nombre or not tipo or not precio:
            flash("Todos los campos son obligatorios.", "error")
            reactivos = obtener_todos_los_reactivos()
            return render_template(
                'admin/add_prueba.html',
                is_edit=False,
                reactivos=reactivos,
                prueba={'valores_normales': []}  # Asegurar lista vacía para valores_normales
            )
        if element_errors:
            flash(element_errors[0], "error")
            return render_template(
                'admin/add_prueba.html',
                is_edit=False,
                reactivos=obtener_todos_los_reactivos(),
                prueba={'valores_normales': valores_normales}
            )
        if not reactivos_validos:
            flash(reactivos_error, "error")
            return render_template(
                'admin/add_prueba.html',
                is_edit=False,
                reactivos=obtener_todos_los_reactivos(),
                prueba={'valores_normales': valores_normales}
            )

        # Crear prueba clínica básica
        nueva_prueba = crear_prueba(nombre, tipo, precio)  # Ahora pasamos el precio
        if not nueva_prueba:
            flash("Error al crear la prueba.", "error")
            reactivos = obtener_todos_los_reactivos()
            return render_template(
                'admin/add_prueba.html',
                is_edit=False,
                reactivos=reactivos,
                prueba={'valores_normales': []}
            )

        # Supabase retorna lista de dicts
        prueba_id = nueva_prueba[0]['id']

        # Asignar reactivos
        if reactivos_ids:
            asignar_reactivos_a_prueba(prueba_id, reactivos_ids)

        if valores_normales:
            for valor in valores_normales:
                nombre_vn = (valor.get('nombre') or '').strip()
                tipo_sep = (valor.get('tipo_separacion') or '').strip()
                estructura = valor.get('estructura') or {}

                # Si faltan datos mínimos, la saltamos
                if not nombre_vn or not tipo_sep:
                    continue

                # Guardar cada valor normal
                crear_valor_normal(prueba_id, nombre_vn, tipo_sep, estructura)

        flash("Prueba registrada exitosamente.", "success")
        return redirect(url_for('app_routes.pruebas_clinicas'))

    # ------- GET: mostrar formulario vacío -------
    reactivos = obtener_todos_los_reactivos()
    return render_template(
        'admin/add_prueba.html',
        is_edit=False,
        reactivos=reactivos,
        prueba={'valores_normales': []}
    )


@app_routes.route('/admin/edit_prueba/<int:prueba_id>', methods=['GET', 'POST'])
@require_role("Admin")
def edit_prueba(prueba_id):
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo = request.form.get('tipo', '').strip()
        precio = request.form.get('precio', '').strip()  # Nuevo campo para precio

        # Lista de IDs de reactivos
        reactivos_ids = request.form.getlist('reactivos')

        # JSON de valores normales
        valores_normales_json = request.form.get('valores_normales_json', '[]')

        try:
            valores_normales = json.loads(valores_normales_json or '[]')
        except (json.JSONDecodeError, TypeError):
            valores_normales = []

        element_errors = validate_clinical_test_elements(valores_normales)
        reactivos_validos, reactivos_error = validar_reactivos_para_prueba(reactivos_ids)

        # Validación básica antes de modificar registros existentes.
        if not nombre or not tipo or not precio:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for('app_routes.edit_prueba', prueba_id=prueba_id))
        if element_errors:
            flash(element_errors[0], "error")
            return redirect(url_for('app_routes.edit_prueba', prueba_id=prueba_id))
        if not reactivos_validos:
            flash(reactivos_error, "error")
            return redirect(url_for('app_routes.edit_prueba', prueba_id=prueba_id))

        # Actualizar prueba básica
        actualizar_prueba(prueba_id, nombre, tipo, precio)  # Ahora pasamos el precio

        # Actualizar reactivos
        actualizar_reactivos_de_prueba(prueba_id, reactivos_ids)

        # Eliminar valores normales antiguos y agregar los nuevos
        eliminar_valores_normales_de_prueba(prueba_id)

        for valor in valores_normales:
            crear_valor_normal(
                prueba_id,
                valor.get('nombre', ''),
                valor.get('tipo_separacion', ''),
                valor.get('estructura', {}) or {}
            )

        attribute_audit_event("pruebas_clinicas", prueba_id)
        flash("Prueba actualizada correctamente", "success")
        return redirect(url_for('app_routes.pruebas_clinicas'))

    # -------- GET: cargar datos para editar --------
    prueba = obtener_prueba_por_id(prueba_id)
    if not prueba:
        flash("Prueba no encontrada", "error")
        return redirect(url_for('app_routes.pruebas_clinicas'))

    reactivos = obtener_todos_los_reactivos()

    # Asegúrate de pasar valores_normales y precio (vacíos si no existen)
    prueba['valores_normales'] = prueba.get('valores_normales', [])
    prueba['precio'] = prueba.get('precio', '')

    # Renderiza el formulario con los valores actuales de la prueba
    return render_template(
        'admin/add_prueba.html',
        is_edit=True,
        prueba=prueba,  # Incluye los valores normales y reactivos asociados
        reactivos=reactivos
    )

# Eliminar (desactivar) prueba clínica
@app_routes.route('/admin/delete_prueba/<int:prueba_id>', methods=['POST'])
@require_role("Admin")
def delete_prueba(prueba_id):
    password = request.form.get('password', '').strip()

    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    user = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute().data
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        supabase.table('pruebas_clinicas').update({'activo': False}).eq('id', prueba_id).execute()
        attribute_audit_event("pruebas_clinicas", prueba_id)
        return jsonify({"message": "Prueba desactivada correctamente."}), 200
    except Exception as e:
        print(f"Error al desactivar prueba: {e}")
        return jsonify({"message": "Error al desactivar la prueba."}), 500


# Activar prueba clínica
@app_routes.route('/admin/activate_prueba/<int:prueba_id>', methods=['POST'])
@require_role("Admin")
def activate_prueba(prueba_id):
    password = request.form.get('password', '').strip()

    if 'user_id' not in session:
        return jsonify({"message": "No estás autorizado."}), 403

    user = supabase.table('usuarios').select('*').eq('id', session['user_id']).single().execute().data
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
        return jsonify({"message": "Contraseña incorrecta."}), 401

    try:
        supabase.table('pruebas_clinicas').update({'activo': True}).eq('id', prueba_id).execute()
        attribute_audit_event("pruebas_clinicas", prueba_id)
        return jsonify({"message": "Prueba activada correctamente."}), 200
    except Exception as e:
        print(f"Error al activar prueba: {e}")
        return jsonify({"message": "Error al activar la prueba."}), 500


#Mostrador
@app_routes.route("/orden/nueva", methods=["GET"])
@require_role("Mostrador")
def nueva_orden():
    """Inicia un expediente limpio sin afectar el borrador al volver de pasos posteriores."""
    session.pop("orden_actual", None)
    session.pop("pruebas_seleccionadas", None)
    session.pop("orden_id_db", None)
    session.modified = True
    return redirect(url_for("app_routes.manage_orden"))


@app_routes.route("/orden", methods=["GET", "POST"])
@require_role("Mostrador")
def manage_orden():
    if request.method == "POST":
        session.pop("orden_id_db", None)
        nombre = (request.form.get("nombre") or "").strip()
        patient_id = (request.form.get("patient_id") or "").strip()
        hospital_id = (request.form.get("hospital") or "").strip()
        cuarto = (request.form.get("cuarto") or "").strip()
        doctor_id = (request.form.get("doctor") or "").strip()
        observaciones = (request.form.get("observaciones") or "").strip()

        errors = validate_order_data(request.form)

        if errors:
            for e in errors:
                flash(e, "error")
            # Volvemos a pintar la vista con los catálogos, fecha y folio sugerido
            fecha_actual = datetime.now().strftime("%d/%m/%Y")
            hospitales = obtener_hospitales()
            doctores = obtener_doctores()
            folio_sugerido = obtener_siguiente_folio_orden()
            return render_template(
                "mostrador/orden.html",
                fecha_actual=fecha_actual,
                hospitales=hospitales,
                doctores=doctores,
                folio_sugerido=folio_sugerido,
                orden_form=request.form,
            )

        # OK: puedes guardar en sesión para siguiente paso
        session["orden_actual"] = {
            "patient_id": int(patient_id),
            "hospital_id": as_int_or_none(hospital_id) if hospital_id != "none" else None,
            "cuarto": cuarto if hospital_id != "none" else None,
            "doctor_id": as_int_or_none(doctor_id) if doctor_id != "none" else None,
            "observaciones": observaciones,
        }
        return redirect(url_for("app_routes.manage_orden_pruebas"))

    # GET normal
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    hospitales = obtener_hospitales()
    doctores = obtener_doctores()
    folio_sugerido = obtener_siguiente_folio_orden()
    draft = session.get("orden_actual") or {}
    patient = obtener_paciente_por_id(draft.get("patient_id")) if draft.get("patient_id") else None
    order_form = {}
    if draft:
        order_form = {
            "patient_id": draft.get("patient_id") or "",
            "nombre": (
                f"{patient.get('nombres', '')} {patient.get('apellidos', '')}".strip()
                if patient else ""
            ),
            "hospital": draft.get("hospital_id") or "none",
            "cuarto": draft.get("cuarto") or "",
            "doctor": draft.get("doctor_id") or "none",
            "observaciones": draft.get("observaciones") or "",
        }
    return render_template(
        "mostrador/orden.html",
        fecha_actual=fecha_actual,
        hospitales=hospitales,
        doctores=doctores,
        folio_sugerido=folio_sugerido,
        orden_form=order_form,
    )


@app_routes.route("/api/validar_orden", methods=["POST"])
@require_role("Mostrador")
def api_validar_orden():
    data = request.get_json() or {}
    errors = validate_order_data(data)

    ok = len(errors) == 0
    return jsonify({"ok": ok, "errors": errors}), (200 if ok else 400)


@app_routes.route("/api/orden/catalogos", methods=["GET"])
@require_role("Mostrador")
def api_catalogos_orden():
    hospitales = [
        {"id": hospital["id"], "nombre": hospital["nombre"]}
        for hospital in obtener_hospitales()
        if hospital.get("activo", True) is True
    ]
    doctores = [
        {
            "id": doctor["id"],
            "nombre": f"{doctor.get('nombres', '')} {doctor.get('apellidos', '')}".strip(),
        }
        for doctor in obtener_doctores()
        if doctor.get("activo", True) is True
    ]
    return jsonify({"hospitales": hospitales, "doctores": doctores})

    
@app_routes.route("/api/buscar_pacientes")
@require_role("Mostrador")  # o quien tenga permiso
def buscar_pacientes():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    # Aquí puedes hacer la búsqueda en la base (ajusta según tu servicio)
    pacientes = obtener_pacientes()  # traer todos o haz función con filtro
    
    # Filtrar pacientes cuyo nombre o apellido contenga el query (ignorar mayúsc/minús)
    resultados = [
        {
            'id': p['id'],
            'nombre_completo': f"{p['nombres']} {p['apellidos']}",
            'telefono': p.get('telefono'),
            'correo': p.get('correo'),
            'sexo': p.get('sexo'),
            'fecha_nacimiento': p.get('fecha_nacimiento'),
            'direccion': ", ".join(filter(None, [
                " ".join(filter(None, [
                    p.get('calle'), p.get('numero_ext'),
                    f"Int. {p.get('numero_int')}" if p.get('numero_int') else None,
                ])),
                p.get('municipio'),
                p.get('estado'),
                p.get('codigo_postal'),
            ])),
        }
        for p in pacientes
        if p.get("activo", True) is True and (
            query.lower() in p['nombres'].lower()
            or query.lower() in p['apellidos'].lower()
        )
    ][:10]  # limitar resultados a 10

    return jsonify(resultados)


@app_routes.route("/api/paciente/<int:patient_id>/resumen")
@require_role("Mostrador")
def resumen_paciente_orden(patient_id):
    paciente = obtener_paciente_por_id(patient_id)
    if not paciente or paciente.get("activo", True) is False:
        return jsonify({"message": "Paciente no encontrado."}), 404
    return jsonify({
        "id": paciente["id"],
        "nombre_completo": f"{paciente.get('nombres', '')} {paciente.get('apellidos', '')}".strip(),
        "telefono": paciente.get("telefono"),
        "correo": paciente.get("correo"),
        "sexo": paciente.get("sexo"),
        "fecha_nacimiento": paciente.get("fecha_nacimiento"),
        "direccion": ", ".join(filter(None, [
            " ".join(filter(None, [
                paciente.get("calle"),
                paciente.get("numero_ext"),
                f"Int. {paciente.get('numero_int')}" if paciente.get("numero_int") else None,
            ])),
            paciente.get("municipio"),
            paciente.get("estado"),
            paciente.get("codigo_postal"),
        ])),
    })


def _receipt_datetime(value):
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return str(value)


def construir_contexto_recibo(orden_id, abono_id=None):
    orden = obtener_orden_por_id(int(orden_id))
    if not orden:
        return None
    paciente = obtener_paciente_por_id(orden.get("paciente_id")) if orden.get("paciente_id") else None
    hospital = obtener_hospital_por_id(orden.get("hospital_id")) if orden.get("hospital_id") else None
    doctor = obtener_doctor_por_id(orden.get("doctor_id")) if orden.get("doctor_id") else None
    detalles = obtener_detalle_pruebas_por_orden(int(orden_id))
    estudios = []
    calculated_total = 0.0
    for detail in detalles:
        quantity = int(detail.get("cantidad") or 1)
        unit_price = float(detail.get("precio_unitario") or detail.get("precio") or 0)
        line_total = float(detail.get("precio_total") or (unit_price * quantity))
        calculated_total += line_total
        estudios.append({
            "nombre": detail.get("nombre_prueba") or "Estudio clínico",
            "cantidad": quantity,
            "precio_unitario": unit_price,
            "total": line_total,
        })

    abonos = obtener_abonos_orden(int(orden_id))
    for payment in abonos:
        payment["fecha_formateada"] = _receipt_datetime(payment.get("fecha_abono"))
        payment["metodo_descripcion"] = (
            payment.get("metodo_pago_otro")
            if payment.get("metodo_pago") == "otro"
            else payment.get("metodo_pago")
        ) or "No especificado"
    selected_payment = None
    if abono_id is not None:
        selected_payment = next(
            (payment for payment in abonos if str(payment.get("id")) == str(abono_id)),
            None,
        )
        if not selected_payment:
            return None

    total = float(orden.get("total_pruebas") or calculated_total)
    paid = sum(float(payment.get("cantidad") or 0) for payment in abonos)
    balance = max(total - paid, 0.0)
    employee_id = (
        selected_payment.get("registrado_por_empleado_id")
        if selected_payment else orden.get("creado_por_empleado_id")
    )
    employee = obtener_empleado_basico(employee_id)
    cashier = (
        f"{employee.get('nombres', '')} {employee.get('apellidos', '')}".strip()
        if employee else (session.get("nombres") or session.get("usuario") or "Personal de mostrador")
    )
    patient_address = ""
    if paciente:
        patient_address = ", ".join(filter(None, [
            " ".join(filter(None, [paciente.get("calle"), paciente.get("numero_ext"),
                                   f"Int. {paciente.get('numero_int')}" if paciente.get("numero_int") else None])),
            paciente.get("municipio"), paciente.get("estado"), paciente.get("codigo_postal"),
        ]))
    system_settings = obtener_configuracion_sistema()
    settings = system_settings.get("recibo_configuracion", DEFAULT_RECEIPT_SETTINGS)
    laboratory = system_settings.get("laboratorio_configuracion", DEFAULT_LAB_SETTINGS)
    return {
        "orden": orden,
        "orden_id": int(orden_id),
        "paciente": paciente,
        "paciente_direccion": patient_address,
        "hospital": hospital,
        "doctor": doctor,
        "estudios": estudios,
        "abonos": abonos,
        "abono": selected_payment,
        "total": total,
        "pagado": paid,
        "saldo": balance,
        "cajero": cashier,
        "fecha_orden": _receipt_datetime(orden.get("creado_en")),
        "fecha_emision": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "config": settings,
        "laboratorio": laboratory,
        "tipo_recibo": "Recibo de abono" if selected_payment else "Comprobante de orden",
    }


def nombre_archivo_recibo(context):
    patient = context.get("paciente") or {}
    patient_name = " ".join(filter(None, [patient.get("nombres"), patient.get("apellidos")]))
    normalized = unicodedata.normalize("NFKD", patient_name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized).strip("-").lower() or "paciente"
    payment_suffix = f"-abono-{context['abono'].get('id')}" if context.get("abono") else ""
    return f"recibo-{slug}-orden-{context['orden_id']:04d}{payment_suffix}.pdf"


def generar_pdf_recibo(context):
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer, pagesize=letter, rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"{context['tipo_recibo']} #{context['orden_id']:04d}",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReceiptTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=17, leading=21, textColor=colors.HexColor("#0b1f33"), alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="ReceiptSmall", parent=styles["BodyText"], fontSize=8.5, leading=12,
        textColor=colors.HexColor("#526273"),
    ))
    story = []
    config = context["config"]
    laboratory = context.get("laboratorio") or config
    if config.get("mostrar_laboratorio_logo", True):
        logo = None
        if laboratory.get("logo_url"):
            try:
                logo = RLImage(laboratory["logo_url"], width=22 * mm, height=22 * mm)
                logo.hAlign = "CENTER"
            except Exception:
                logger.warning("No se pudo incluir el logo personalizado en el PDF", exc_info=True)
        if logo is None:
            logo = Drawing(22 * mm, 22 * mm)
            logo.add(Rect(0, 0, 22 * mm, 22 * mm, rx=5 * mm, ry=5 * mm,
                          fillColor=colors.white, strokeColor=None))
            flask = Path(strokeColor=colors.HexColor("#5b21b6"), strokeWidth=1.55 * mm,
                         fillColor=None, strokeLineCap=1, strokeLineJoin=1)
            flask.moveTo(8.5 * mm, 17.5 * mm); flask.lineTo(13.5 * mm, 17.5 * mm)
            flask.moveTo(9.7 * mm, 17.5 * mm); flask.lineTo(9.7 * mm, 12.5 * mm)
            flask.lineTo(5.8 * mm, 5.5 * mm); flask.curveTo(5 * mm, 4 * mm, 6 * mm, 3.4 * mm, 7.2 * mm, 3.4 * mm)
            flask.lineTo(14.8 * mm, 3.4 * mm); flask.curveTo(16 * mm, 3.4 * mm, 17 * mm, 4 * mm, 16.2 * mm, 5.5 * mm)
            flask.lineTo(12.3 * mm, 12.5 * mm); flask.lineTo(12.3 * mm, 17.5 * mm)
            logo.add(flask)
            liquid = Path(strokeColor=colors.HexColor("#8b5cf6"), strokeWidth=1.1 * mm,
                          fillColor=None, strokeLineCap=1)
            liquid.moveTo(7.2 * mm, 8.3 * mm)
            liquid.curveTo(9 * mm, 8.3 * mm, 9.8 * mm, 7 * mm, 11.2 * mm, 7 * mm)
            liquid.curveTo(12.8 * mm, 7 * mm, 13.6 * mm, 8.3 * mm, 15 * mm, 8.3 * mm)
            logo.add(liquid)
            logo.hAlign = "CENTER"
        story.extend([logo, Spacer(1, 2 * mm)])
    if config.get("mostrar_laboratorio_nombre", True):
        story.append(Paragraph(escape(laboratory.get("nombre") or "AppLab"), styles["ReceiptTitle"]))
    contact_lines = [
        laboratory.get("direccion") if config.get("mostrar_laboratorio_direccion", True) else None,
        laboratory.get("telefono") if config.get("mostrar_laboratorio_telefono", True) else None,
        f"WhatsApp: {laboratory.get('whatsapp')}" if config.get("mostrar_laboratorio_whatsapp", True) and laboratory.get("whatsapp") else None,
        laboratory.get("correo") if config.get("mostrar_laboratorio_correo", True) else None,
        f"RFC: {laboratory.get('rfc')}" if config.get("mostrar_laboratorio_rfc", True) and laboratory.get("rfc") else None,
    ]
    if any(contact_lines):
        story.append(Paragraph(escape(" · ".join(filter(None, contact_lines))), ParagraphStyle(
            "ReceiptCenter", parent=styles["ReceiptSmall"], alignment=TA_CENTER
        )))
    story.append(Spacer(1, 7 * mm))
    story.append(Paragraph(escape(context["tipo_recibo"]), styles["Heading2"]))
    patient_name = (
        f"{context['paciente'].get('nombres', '')} {context['paciente'].get('apellidos', '')}".strip()
        if context["paciente"] else "No disponible"
    )
    info_rows = [
        ["Folio", f"#{context['orden_id']:04d}", "Fecha", context["fecha_emision"]],
        ["Paciente", patient_name, "Estado", str(context["orden"].get("estado") or "pendiente").title()],
    ]
    if config.get("mostrar_paciente_telefono") and context["paciente"]:
        info_rows.append(["Teléfono", context["paciente"].get("telefono") or "—", "", ""])
    if config.get("mostrar_paciente_direccion"):
        info_rows.append(["Domicilio", context["paciente_direccion"] or "—", "", ""])
    if config.get("mostrar_procedencia"):
        info_rows.append(["Procedencia", context["hospital"].get("nombre") if context["hospital"] else "Paciente particular", "", ""])
    if config.get("mostrar_medico"):
        doctor_name = (f"{context['doctor'].get('nombres', '')} {context['doctor'].get('apellidos', '')}".strip()
                       if context["doctor"] else "Sin médico solicitante")
        info_rows.append(["Médico", doctor_name, "", ""])
    info_table = Table(info_rows, colWidths=[24 * mm, 62 * mm, 20 * mm, 58 * mm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, -1), (-1, -1), 0.4, colors.HexColor("#dfe7ee")),
    ]))
    story.extend([info_table, Spacer(1, 5 * mm)])

    if config.get("mostrar_estudios") and context["estudios"]:
        rows = [["Estudio", "Cant.", "Precio", "Importe"]]
        rows.extend([
            [study["nombre"], str(study["cantidad"]), f"${study['precio_unitario']:.2f}", f"${study['total']:.2f}"]
            for study in context["estudios"]
        ])
        table = Table(rows, colWidths=[92 * mm, 18 * mm, 27 * mm, 27 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b1f33")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#dfe7ee")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.extend([table, Spacer(1, 5 * mm)])

    if config.get("mostrar_observaciones") and context["orden"].get("observaciones"):
        story.extend([
            Paragraph("<b>Observaciones</b>", styles["BodyText"]),
            Paragraph(escape(str(context["orden"].get("observaciones"))), styles["ReceiptSmall"]),
            Spacer(1, 4 * mm),
        ])

    if context["abono"]:
        payment = context["abono"]
        story.append(Paragraph(
            f"<b>Abono recibido:</b> ${float(payment.get('cantidad') or 0):.2f} &nbsp;&nbsp; "
            f"<b>Método:</b> {escape(str(payment.get('metodo_descripcion') or 'No especificado').title())}",
            styles["BodyText"],
        ))
        story.append(Spacer(1, 3 * mm))

    if config.get("mostrar_historial_pagos") and context["abonos"]:
        payment_rows = [["Fecha", "Método", "Importe"]]
        payment_rows.extend([
            [payment.get("fecha_formateada") or "—", str(payment.get("metodo_descripcion") or "—").title(),
             f"${float(payment.get('cantidad') or 0):.2f}"]
            for payment in context["abonos"]
        ])
        payment_table = Table(payment_rows, colWidths=[55 * mm, 65 * mm, 35 * mm], repeatRows=1)
        payment_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7f7f8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#087f8c")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#dfe7ee")),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([Paragraph("<b>Movimientos de pago</b>", styles["BodyText"]), Spacer(1, 2 * mm), payment_table, Spacer(1, 5 * mm)])

    if config.get("mostrar_saldo"):
        totals = Table([
            ["Total de la orden", f"${context['total']:.2f}"],
            ["Total pagado", f"${context['pagado']:.2f}"],
            ["Saldo pendiente", f"${context['saldo']:.2f}"],
        ], colWidths=[55 * mm, 35 * mm], hAlign="RIGHT")
        totals.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LINEABOVE", (0, -1), (-1, -1), 0.7, colors.HexColor("#0b1f33")),
        ]))
        story.extend([totals, Spacer(1, 5 * mm)])

    if config.get("mostrar_cajero"):
        story.append(Paragraph(f"<b>Recibió:</b> {escape(context['cajero'])}", styles["ReceiptSmall"]))
    if config.get("recibo_mensaje_pie"):
        story.extend([Spacer(1, 7 * mm), Paragraph(escape(config["recibo_mensaje_pie"]), ParagraphStyle(
            "ReceiptFooter", parent=styles["ReceiptSmall"], alignment=TA_CENTER,
            textColor=colors.HexColor("#087f8c")
        ))])
    document.build(story)
    buffer.seek(0)
    return buffer


@app_routes.route("/reporte", methods=["GET", "POST"])
@require_role("Mostrador")
def reporte():
    # ---------------------------------
    # 1) POST: viene de orden_pruebas (JSON de pruebas)
    # ---------------------------------
    if request.method == "POST":
        datos_raw = request.form.get("datosSeleccionados", "")
        if datos_raw:
            try:
                datos = json.loads(datos_raw)
            except Exception:
                datos = []
            session["pruebas_seleccionadas"] = normalize_order_studies(datos)
            session.modified = True
        orden_actual = session.get("orden_actual")
        estudios = session.get("pruebas_seleccionadas", [])
        if not orden_actual or not estudios:
            flash("Completa la orden y selecciona al menos un estudio.", "error")
            return redirect(url_for("app_routes.manage_orden_pruebas"))
        if not session.get("orden_id_db"):
            try:
                orden_id = crear_orden_atomica(
                    orden_actual,
                    estudios,
                    session.get("empleado_id"),
                )
                session["orden_id_db"] = orden_id
                session.modified = True
                flash(f"Orden #{orden_id} creada. Ya puedes registrar el abono.", "success")
            except Exception as exc:
                logger.exception("No se pudo crear la orden antes del abono")
                flash(str(exc), "error")
                return redirect(url_for("app_routes.manage_orden_pruebas"))
        return redirect(url_for("app_routes.reporte"))

    # ---------------------------------
    # 2) GET con ?orden_id=... => ver nota de una orden guardada (Recientes)
    # ---------------------------------
    orden_id_param = request.args.get("orden_id", type=int)
    if orden_id_param:
        orden_db = obtener_orden_por_id(orden_id_param)
        if not orden_db:
            flash("No se encontró la orden seleccionada.", "error")
            return redirect(url_for("app_routes.recientes"))

        # Guardamos el id en sesión para que Abonar funcione
        session["orden_id_db"] = orden_id_param

        # Usamos la orden de BD como 'orden' para el template
        orden = orden_db

        # Paciente / hospital / doctor desde la orden de BD
        paciente = (
            obtener_paciente_por_id(orden_db.get("paciente_id"))
            if orden_db.get("paciente_id")
            else None
        )
        hospital = (
            obtener_hospital_por_id(orden_db.get("hospital_id"))
            if orden_db.get("hospital_id")
            else None
        )
        doctor = (
            obtener_doctor_por_id(orden_db.get("doctor_id"))
            if orden_db.get("doctor_id")
            else None
        )

        # Detalle de pruebas desde la tabla orden_pruebas_detalle
        detalle = obtener_detalle_pruebas_por_orden(orden_id_param)
        pruebas = []
        total_pruebas = 0.0

        for d in detalle:
            # cantidad
            try:
                cantidad = int(d.get("cantidad", 1) or 1)
            except (TypeError, ValueError):
                cantidad = 1

            # 1) Intentar usar subtotal directo
            raw_subtotal = d.get("precio_total")
            try:
                subtotal = float(raw_subtotal) if raw_subtotal is not None else 0.0
            except (TypeError, ValueError):
                subtotal = 0.0

            # 2) Si subtotal no sirve, recalcular con precio_unitario * cantidad
            if subtotal == 0.0:
                raw_unit = d.get("precio_unitario") or d.get("precio") or 0
                try:
                    unitario = float(raw_unit)
                except (TypeError, ValueError):
                    unitario = 0.0
                subtotal = unitario * cantidad

            pruebas.append(
                {
                    "prueba": d.get("nombre_prueba"),
                    "cantidad": cantidad,
                    # nuestro template espera 'precio' = total de la línea
                    "precio": subtotal,
                }
            )
            total_pruebas += subtotal

        # Abonos y estado desde BD
        abonos = obtener_abonos_orden(orden_id_param)
        total_abonos = float(orden_db.get("total_abonos", 0) or 0)
        estado = orden_db.get("estado", "pendiente")
        total_restante = max(total_pruebas - total_abonos, 0.0)

        # Fecha: usamos creado_en si existe, si no, hoy
        creado_en = orden_db.get("creado_en")
        if creado_en:
            try:
                if isinstance(creado_en, str):
                    # soporta ISO con Z o sin Z
                    if "T" in creado_en:
                        dt = datetime.fromisoformat(creado_en.replace("Z", "+00:00"))
                    else:
                        dt = datetime.fromisoformat(creado_en)
                else:
                    dt = creado_en
                fecha_actual = dt.strftime("%d/%m/%Y")
            except Exception:
                fecha_actual = datetime.now().strftime("%d/%m/%Y")
        else:
            fecha_actual = datetime.now().strftime("%d/%m/%Y")

        # En este caso, ya es una orden guardada → no necesitamos folio_sugerido
        folio_sugerido = None

        return render_template(
            "mostrador/reporte.html",
            fecha_actual=fecha_actual,
            orden=orden,
            paciente=paciente,
            hospital=hospital,
            doctor=doctor,
            pruebas=pruebas,
            total_pruebas=total_pruebas,
            orden_id=orden_id_param,
            estado=estado,
            abonos=abonos,
            total_abonos=total_abonos,
            total_restante=total_restante,
            folio_sugerido=folio_sugerido,
        )

    # ---------------------------------
    # 3) GET sin orden_id => flujo normal (orden en construcción desde sesión)
    # ---------------------------------
    orden = session.get("orden_actual")
    if not orden:
        flash("No hay datos de la orden. Vuelve a generarla.", "error")
        return redirect(url_for("app_routes.manage_orden"))

    pruebas = session.get("pruebas_seleccionadas", [])
    if isinstance(pruebas, str):
        try:
            pruebas = json.loads(pruebas)
        except Exception:
            pruebas = []

    paciente = (
        obtener_paciente_por_id(orden["patient_id"])
        if orden.get("patient_id")
        else None
    )
    hospital = (
        obtener_hospital_por_id(orden["hospital_id"])
        if orden.get("hospital_id")
        else None
    )
    doctor = (
        obtener_doctor_por_id(orden["doctor_id"])
        if orden.get("doctor_id")
        else None
    )

    total_pruebas = 0.0
    for p in pruebas:
        try:
            total_pruebas += float(p.get("precio", 0))
        except (TypeError, ValueError):
            continue

    fecha_actual = datetime.now().strftime("%d/%m/%Y")

    # Aquí SÍ primero obtenemos orden_db
    orden_id_db = session.get("orden_id_db")
    orden_db = obtener_orden_por_id(orden_id_db) if orden_id_db else None

    if orden_db:
        orden_id = orden_db["id"]
        estado = orden_db.get("estado", "pendiente")
        abonos = obtener_abonos_orden(orden_id)
        total_abonos = float(orden_db.get("total_abonos", 0) or 0)
        folio_sugerido = None  # ya hay orden en BD
    else:
        orden_id = None
        estado = "borrador"
        abonos = []
        total_abonos = 0.0
        # solo sugerimos folio cuando aún no está guardada
        folio_sugerido = obtener_siguiente_folio_orden()

    total_restante = max(total_pruebas - total_abonos, 0.0)

    return render_template(
        "mostrador/reporte.html",
        fecha_actual=fecha_actual,
        orden=orden,
        paciente=paciente,
        hospital=hospital,
        doctor=doctor,
        pruebas=pruebas,
        total_pruebas=total_pruebas,
        orden_id=orden_id,
        estado=estado,
        abonos=abonos,
        total_abonos=total_abonos,
        total_restante=total_restante,
        folio_sugerido=folio_sugerido,
    )



@app_routes.route("/reporte/imprimir", methods=["POST"])
@require_role("Mostrador")
def imprimir_orden():
    orden = session.get("orden_actual")
    pruebas = session.get("pruebas_seleccionadas", [])

    if isinstance(pruebas, str):
        try:
            pruebas = json.loads(pruebas)
        except Exception:
            pruebas = []

    if not orden or not pruebas:
        flash("No hay datos de orden o pruebas para guardar.", "error")
        return redirect(url_for("app_routes.reporte"))

    # --- NUEVO: validar si el folio guardado realmente existe en BD ---
    orden_id_db = session.get("orden_id_db")
    if orden_id_db:
        orden_db = obtener_orden_por_id(orden_id_db)
        if orden_db:
            # La orden sí existe -> no la vuelvas a insertar
            flash(f"Orden #{orden_id_db} ya fue guardada.", "info")
            return redirect(url_for("app_routes.reporte"))
        else:
            # Folio fantasma -> lo limpiamos y seguimos como orden nueva
            session.pop("orden_id_db", None)

    # --- Insertar la orden como nueva ---
    empleado_id = session.get("empleado_id")

    try:
        orden_id = guardar_orden_en_bd(orden, pruebas, empleado_id)
        session["orden_id_db"] = orden_id
        flash(f"Orden #{orden_id} guardada correctamente.", "success")
    except Exception as e:
        print("Error al guardar la orden:", e)
        flash("Ocurrió un error al guardar la orden.", "error")

    return redirect(url_for("app_routes.reporte"))


@app_routes.route("/orden/<int:orden_id>/recibo")
@require_role("Mostrador")
def recibo_orden(orden_id):
    abono_id = request.args.get("abono_id", type=int)
    context = construir_contexto_recibo(orden_id, abono_id)
    if not context:
        flash("No se encontró el recibo solicitado.", "error")
        return redirect(url_for("app_routes.reporte", orden_id=orden_id))
    return render_template(
        "mostrador/recibo.html",
        **context,
        pdf_filename=nombre_archivo_recibo(context),
        pdf_url=url_for("app_routes.recibo_orden_pdf", orden_id=orden_id, abono_id=abono_id),
        pdf_download_url=url_for("app_routes.recibo_orden_pdf", orden_id=orden_id, abono_id=abono_id, download=1),
        receipt_url=url_for("app_routes.recibo_orden", orden_id=orden_id, abono_id=abono_id, _external=True),
    )


@app_routes.route("/orden/<int:orden_id>/recibo.pdf")
@require_role("Mostrador")
def recibo_orden_pdf(orden_id):
    abono_id = request.args.get("abono_id", type=int)
    context = construir_contexto_recibo(orden_id, abono_id)
    if not context:
        abort(404)
    return send_file(
        generar_pdf_recibo(context),
        mimetype="application/pdf",
        as_attachment=request.args.get("download") == "1",
        download_name=nombre_archivo_recibo(context),
    )


@app_routes.route("/orden/<int:orden_id>/ticket")
@require_role("Mostrador")
def ticket_orden(orden_id):
    abono_id = request.args.get("abono_id", type=int)
    context = construir_contexto_recibo(orden_id, abono_id)
    if not context:
        flash("No se encontró el ticket solicitado.", "error")
        return redirect(url_for("app_routes.reporte", orden_id=orden_id))
    return render_template("mostrador/ticket.html", **context)

@app_routes.route("/orden/<int:orden_id>/abonar", methods=["POST"])
@require_role("Mostrador")
def abonar_orden(orden_id: int):
    orden_id_session = session.get("orden_id_db")
    reporte_orden_url = url_for("app_routes.reporte", orden_id=orden_id)

    if not orden_id_session or orden_id_session != orden_id:
        flash("Primero guarda la orden (Imprimir) antes de registrar abonos.", "error")
        return redirect(reporte_orden_url)

    orden_db = obtener_orden_por_id(orden_id)
    if not orden_db:
        flash("La orden no existe en la base de datos. Vuelve a guardarla.", "error")
        # limpia el folio fantasma para que al imprimir se vuelva a crear
        session.pop("orden_id_db", None)
        return redirect(reporte_orden_url)

    cantidad_str = request.form.get("cantidad")
    nota = request.form.get("nota")
    metodo_pago = (request.form.get("metodo_pago") or "").strip().lower()
    metodo_pago_otro = (request.form.get("metodo_pago_otro") or "").strip()

    if metodo_pago not in {"efectivo", "tarjeta", "transferencia", "otro"}:
        flash("Selecciona un método de pago válido.", "error")
        return redirect(reporte_orden_url)
    if metodo_pago == "otro" and not metodo_pago_otro:
        flash("Especifica el método de pago utilizado.", "error")
        return redirect(reporte_orden_url)

    try:
        cantidad = float(cantidad_str)
    except (TypeError, ValueError):
        flash("Cantidad de abono inválida.", "error")
        return redirect(reporte_orden_url)

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a cero.", "error")
        return redirect(reporte_orden_url)

    empleado_id = session.get("empleado_id")

    try:
        result = registrar_abono(
            orden_id,
            cantidad,
            empleado_id,
            nota,
            metodo_pago,
            metodo_pago_otro,
        )
        flash("Abono registrado correctamente.", "success")
        abono_id = None
        if isinstance(result, dict):
            abono_id = result.get("id") or result.get("abono_id")
        elif isinstance(result, list) and result and isinstance(result[0], dict):
            abono_id = result[0].get("id") or result[0].get("abono_id")
        elif isinstance(result, (int, str)) and str(result).isdigit():
            abono_id = int(result)
        if not abono_id:
            current_payments = obtener_abonos_orden(orden_id)
            valid_payments = [payment for payment in current_payments if payment.get("id") is not None]
            if valid_payments:
                abono_id = max(valid_payments, key=lambda payment: int(payment["id"]))["id"]
    except Exception as e:
        print("Error al registrar abono:", e)
        flash("Ocurrió un error al registrar el abono.", "error")

        return redirect(reporte_orden_url)

    return redirect(url_for(
        "app_routes.reporte", orden_id=orden_id, abono_guardado=abono_id or ""
    ))

@app_routes.route("/orden_pruebas")
@require_role("Mostrador")
def manage_orden_pruebas():
    if "orden_actual" not in session:
        flash("Primero llena los datos de la orden.", "error")
        return redirect(url_for("app_routes.manage_orden"))

    pruebas = obtener_pruebas()  # usa la función ya existente en services.py
    folio_sugerido = obtener_siguiente_folio_orden()
    return render_template(
        "mostrador/orden_pruebas.html",
        pruebas=pruebas,
        folio_sugerido=folio_sugerido,
        seleccionados=session.get("pruebas_seleccionadas", []),
    )


@app_routes.route("/api/orden/estudios", methods=["POST"])
@require_role("Mostrador")
def guardar_estudios_orden():
    if "orden_actual" not in session:
        return jsonify({"message": "No hay una orden en proceso."}), 400
    data = request.get_json() or {}
    studies = normalize_order_studies(data.get("estudios"))
    session["pruebas_seleccionadas"] = studies
    session.modified = True
    return jsonify({
        "ok": True,
        "cantidad": len(studies),
        "total": round(sum(float(item["precio"]) for item in studies), 2),
        "estudios": studies,
    })


@app_routes.route("/recientes", methods=["GET"])
@require_role("Mostrador")
def recientes():
    ordenes = listar_ordenes_resumen()  

    for o in ordenes:
        total_pruebas = float(o.get("total_pruebas", 0) or 0)
        total_abonos = float(o.get("total_abonos", 0) or 0)
        o["total_restante"] = max(total_pruebas - total_abonos, 0.0)

    return render_template("mostrador/recientes.html", ordenes=ordenes)

@app_routes.route("/listos")
@require_role("Mostrador")
def listos():
    return render_template(
        "mostrador/listos.html",
        resultados_listos=obtener_resultados_listos(),
        ordenes_quimico=obtener_ordenes_para_quimico(),
        system_settings=obtener_configuracion_sistema(),
    )


@app_routes.route("/api/mostrador/resumen")
@require_role("Mostrador")
def api_resumen_mostrador():
    resumen = obtener_resumen_mostrador(limit=6)
    return jsonify({
        key: resumen[key]
        for key in (
            "ordenes_hoy", "pagos_pendientes",
            "muestras_pendientes", "resultados_listos",
        )
    })


@app_routes.route("/resultados/<int:orden_id>/entregar", methods=["POST"])
@require_role("Mostrador")
def entregar_resultado(orden_id):
    medio = (request.form.get("medio_entrega") or "").strip().lower()
    if medio not in {"whatsapp", "impreso", "correo", "directo", "otro"}:
        flash("Selecciona un medio de entrega válido.", "error")
        return redirect(url_for("app_routes.listos"))
    try:
        settings = obtener_configuracion_sistema()
        balance = obtener_saldo_orden(orden_id)
        if balance is None:
            flash("No se encontró la orden solicitada.", "error")
            return redirect(url_for("app_routes.listos"))
        override_authorizer = None
        if (
            balance["saldo"] > 0.009
            and not settings["mostrador_entrega_saldo_pendiente"]
        ):
            override_authorizer = admin_override_from_request()
            if not override_authorizer:
                flash(
                    "La orden tiene saldo pendiente. Solicita autorización administrativa para entregarla.",
                    "error",
                )
                return redirect(url_for("app_routes.listos"))
        finalizar_entrega_resultado(orden_id, session.get("user_id"), medio)
        if override_authorizer:
            registrar_excepcion_sistema(
                "entregar_resultado_con_saldo",
                f"Se autorizó entregar la orden #{orden_id:04d} con saldo de ${balance['saldo']:.2f}.",
                override_authorizer,
                override_requester(),
            )
        flash(
            f"Orden #{orden_id:04d} finalizada y conservada en el historial.",
            "success",
        )
    except Exception:
        logger.exception("No se pudo finalizar la entrega de la orden %s", orden_id)
        flash("No se pudo finalizar la entrega del resultado.", "error")
    return redirect(url_for("app_routes.listos"))


# Enfermero
@app_routes.route("/muestra")
@require_role("Enfermero")
def manage_muestra():
    ordenes = obtener_ordenes_para_muestra()
    return render_template("enfermero/muestra.html", ordenes=ordenes)


@app_routes.route("/api/analisis/<int:orden_id>")
@require_role("Enfermero, Quimico")
def get_analisis(orden_id):
    if current_workspace_role() == "Quimico":
        try:
            captura = obtener_captura_resultados(orden_id) or {}
            estudios = captura.get("estudios") or []
            if estudios:
                return jsonify(estudios)
        except Exception as exc:
            logger.exception("No se pudieron consultar los estudios de la orden %s", orden_id)
            # La consulta básica mantiene disponible "Ver estudios" aunque la
            # migración de captura estructurada todavía no esté aplicada.
            estudios = consultar_analisis_por_folio(orden_id)
            if estudios:
                return jsonify(estudios)
            return jsonify({
                "error": (
                    "No se pudieron consultar los estudios. Verifica que la "
                    "migración 20260729_structured_results_inventory.sql esté aplicada."
                ),
                "detail": str(exc),
            }), 500
    return jsonify(consultar_analisis_por_folio(orden_id))


@app_routes.route("/api/muestra/finalizar/<int:orden_id>", methods=["POST"])
@require_role("Enfermero")
def api_finalizar_muestra(orden_id):
    try:
        ok = finalizar_muestras_orden(orden_id, session.get("user_id"))
        return jsonify({"ok": bool(ok)})
    except Exception as exc:
        logger.exception("No se pudieron finalizar las muestras de la orden %s", orden_id)
        return jsonify({
            "ok": False,
            "error": "Aún existen muestras pendientes o la orden ya fue procesada.",
            "detail": str(exc),
        }), 400


@app_routes.route("/api/muestra/<int:orden_id>/requisitos")
@require_role("Enfermero")
def api_requisitos_muestra(orden_id):
    try:
        muestras = obtener_muestras_orden(orden_id)
        return jsonify({
            "ok": True,
            "muestras": muestras,
            "completa": bool(muestras) and all(
                item.get("recolectada") for item in muestras
            ),
        })
    except Exception:
        logger.exception("No se pudieron consultar las muestras de la orden %s", orden_id)
        return jsonify({
            "ok": False,
            "error": "No se pudieron cargar los requisitos de muestra.",
        }), 500


@app_routes.route("/api/muestra/<int:orden_id>/requisitos", methods=["POST"])
@require_role("Enfermero")
def api_actualizar_requisito_muestra(orden_id):
    payload = request.get_json(silent=True) or {}
    tipo_muestra = (payload.get("tipo_muestra") or "").strip().lower()
    if not tipo_muestra:
        return jsonify({"ok": False, "error": "Indica el tipo de muestra."}), 400
    try:
        actualizar_muestra_orden(
            orden_id,
            tipo_muestra,
            payload.get("recolectada") is True,
            session.get("user_id"),
            payload.get("observaciones"),
        )
        muestras = obtener_muestras_orden(orden_id)
        return jsonify({
            "ok": True,
            "muestras": muestras,
            "completa": bool(muestras) and all(
                item.get("recolectada") for item in muestras
            ),
        })
    except Exception:
        logger.exception("No se pudo actualizar la muestra %s", tipo_muestra)
        return jsonify({
            "ok": False,
            "error": "No se pudo guardar el estado de la muestra.",
        }), 400


@app_routes.route("/enfermero/etiquetas")
@require_role("Admin, Enfermero, Quimico")
def etiquetas_muestra():
    try:
        etiquetas = listar_etiquetas_muestra()
        configuracion = obtener_configuracion_etiquetas()
    except Exception:
        logger.exception("No se pudieron cargar las etiquetas de muestras")
        etiquetas = []
        configuracion = {
            "ancho_mm": 60, "alto_mm": 40,
            "copias_predeterminadas": 1, "mostrar_qr": True,
        }
        flash(
            "No se pudieron cargar las etiquetas. Verifica la migración de Supabase.",
            "error",
        )
    return render_template(
        "enfermero/etiquetas.html",
        etiquetas=etiquetas,
        configuracion=configuracion,
    )


@app_routes.route("/configuracion/etiquetas", methods=["POST"])
@require_role("Admin")
def guardar_configuracion_etiquetas():
    try:
        formato = (request.form.get("formato") or "60x40").split("x", 1)
        ancho, alto = int(formato[0]), int(formato[1])
        copias = int(request.form.get("copias") or 1)
        actualizar_configuracion_etiquetas(
            ancho,
            alto,
            copias,
            request.form.get("mostrar_qr") == "on",
            session.get("user_id"),
        )
        flash("Configuración de etiquetas actualizada.", "success")
    except Exception:
        logger.exception("No se pudo actualizar la configuración de etiquetas")
        flash("No se pudo guardar la configuración de etiquetas.", "error")
    return redirect(url_for("app_routes.configuracion_sistema"))


@app_routes.route("/api/etiquetas/impresion", methods=["POST"])
@require_role("Admin, Enfermero, Quimico")
def api_registrar_impresion_etiquetas():
    payload = request.get_json(silent=True) or {}
    ids = payload.get("muestra_ids") or []
    try:
        copias = int(payload.get("copias") or 1)
        if not ids or copias not in range(1, 11):
            raise ValueError("Selección de impresión inválida")
        registradas = registrar_impresion_etiquetas(
            ids, copias, session.get("user_id")
        )
        return jsonify({"ok": True, "registradas": registradas})
    except Exception:
        logger.exception("No se pudo registrar la impresión de etiquetas")
        return jsonify({
            "ok": False,
            "error": "No se pudo registrar la impresión.",
        }), 400


@app_routes.route("/muestras/escanear/<uuid:token>")
@require_role("Admin, Enfermero, Quimico")
def escanear_etiqueta_muestra(token):
    try:
        muestra = obtener_etiqueta_por_token(token)
    except Exception:
        logger.exception("No se pudo consultar la etiqueta %s", token)
        muestra = None
    if not muestra:
        return render_template("errors/404.html"), 404
    return render_template("enfermero/etiqueta_scan.html", muestra=muestra)

# Químico
@app_routes.route("/resultados")
@require_role("Quimico")
def resultados():
    ordenes = obtener_ordenes_para_quimico()     # flujo = 'en_quimico'
    faltantes = obtener_ordenes_para_muestra()   # flujo = 'muestra_pendiente'
    for orden in ordenes:
        orden["estado_captura"] = "por_analizar"
        try:
            captura = obtener_captura_resultados(orden.get("id")) or {}
            estudios = captura.get("estudios") or []
            if estudios and all(item.get("ejecuciones") for item in estudios):
                orden["estado_captura"] = "listo_para_finalizar"
            elif estudios and all(
                item.get("elementos")
                and all(
                    str(elemento.get("id")) in (
                        (item.get("borrador") or {}).get("valores") or {}
                    )
                    for elemento in item.get("elementos") or []
                )
                for item in estudios
            ):
                orden["estado_captura"] = "listo_para_reportar"
            elif any((item.get("borrador") or {}).get("valores") for item in estudios):
                orden["estado_captura"] = "en_captura"
        except Exception:
            logger.exception(
                "No se pudo calcular el estado de captura de la orden %s",
                orden.get("id"),
            )
    return render_template(
        "quimico/resultados.html",
        ordenes=ordenes,
        faltantes=faltantes
    )


@app_routes.route("/resultados/finalizados")
@require_role("Quimico")
def historial_resultados():
    resultados_finalizados = obtener_historial_resultados()
    return render_template(
        "quimico/resultados_finalizados.html",
        resultados=resultados_finalizados,
        entregados=sum(
            1 for item in resultados_finalizados if item.get("entregado") is True
        ),
        pendientes=sum(
            1 for item in resultados_finalizados if item.get("entregado") is not True
        ),
    )


@app_routes.route('/legacy/orden/<int:orden_id>/captura_resultados', methods=['GET'])
@require_role("Quimico")
def captura_resultados_legacy(orden_id):
    # Paso 1: Obtener las pruebas asociadas con la orden desde 'orden_pruebas_detalle'
    pruebas_query = supabase.table('orden_pruebas_detalle') \
        .select('id, nombre_prueba, prueba_id, orden_id') \
        .eq('orden_id', orden_id) \
        .execute()

    # Depurar: Verificar si estamos obteniendo las pruebas correctamente

    # Verificar si hay pruebas asociadas a la orden
    if not pruebas_query.data:
        return "No se encontraron pruebas para esta orden", 404  # Manejar la falta de pruebas

    pruebas = pruebas_query.data  # Obtener las pruebas

    # Paso 2: Obtener el 'paciente_id' a partir de la tabla 'ordenes' usando 'orden_id'
    orden_query = supabase.table('ordenes') \
        .select('paciente_id') \
        .eq('id', orden_id) \
        .execute()

    # Depurar: Verificar si estamos obteniendo el paciente_id correctamente

    # Verificar si la orden existe y contiene el 'paciente_id'
    if not orden_query.data:
        return "Orden no encontrada", 404  # Manejar la falta de la orden

    paciente_id = orden_query.data[0]['paciente_id']  # Obtener el paciente_id

    # Paso 3: Obtener el paciente relacionado con la orden
    paciente_query = supabase.table('pacientes') \
        .select('nombres, apellidos') \
        .eq('id', paciente_id) \
        .execute()

    # Depurar: Verificar si estamos obteniendo los datos del paciente correctamente

    # Verificar si el paciente existe
    if not paciente_query.data:
        return "Paciente no encontrado", 404  # Manejar la falta del paciente

    paciente = paciente_query.data[0]  # Tomamos el primer (y único) resultado
    paciente['orden'] = orden_id  # Agregar la orden_id al objeto paciente

    # Paso 4: Obtener los valores normales de las pruebas
    for prueba in pruebas:
        prueba_id = prueba['prueba_id']

        # Consultar los valores normales desde Supabase
        valores_normales_query = supabase.table('valores_normales').select('nombre, estructura') \
            .eq('prueba_id', prueba_id).execute()

        prueba['valores_normales'] = valores_normales_query.data  # Asignar los valores normales a la prueba

    # Depurar: Verificar los datos que vamos a pasar a la plantilla

    # Pasar el paciente y las pruebas junto con la orden a la plantilla
    return render_template('quimico/resultados_captura.html', orden=orden_id, paciente=paciente, pruebas=pruebas)


@app_routes.route('/orden/<int:orden_id>/captura_resultados', methods=['GET'])
@require_role("Quimico")
def captura_resultados(orden_id):
    try:
        captura = obtener_captura_resultados(orden_id)
    except Exception:
        logger.exception("No se pudo cargar la captura de la orden %s", orden_id)
        flash("No se pudo cargar la orden. Verifica la migración de resultados.", "error")
        return redirect(url_for("app_routes.resultados"))
    if not captura or not captura.get("estudios"):
        flash("La orden no existe o no tiene estudios registrados.", "error")
        return redirect(url_for("app_routes.resultados"))

    paciente = captura.get("paciente") or {}
    for estudio in captura["estudios"]:
        for elemento in estudio.get("elementos") or []:
            elemento["referencia_aplicable"] = resolve_clinical_reference(
                elemento, paciente
            )
        ejecuciones = estudio.get("ejecuciones") or []
        estudio["ultima_ejecucion"] = ejecuciones[0] if ejecuciones else None
        estudio["tiene_resultado_fuera"] = bool(
            ejecuciones and any(
                item.get("estado") in {"alto", "bajo", "fuera"}
                for item in (ejecuciones[0].get("evaluaciones") or {}).values()
            )
        )
        estudio["verificacion_registrada"] = bool(
            ejecuciones and (
                ejecuciones[0].get("es_verificacion")
                or any(
                    item.get("verificado") is True
                    for item in (ejecuciones[0].get("evaluaciones") or {}).values()
                )
            )
        )
    return render_template(
        "quimico/resultados_captura.html",
        orden=captura.get("orden") or {},
        paciente=paciente,
        estudios=captura["estudios"],
    )


@app_routes.route("/api/resultados/ejecutar", methods=["POST"])
@require_role("Quimico")
def api_ejecutar_resultado():
    payload = request.get_json(silent=True) or {}
    try:
        orden_id = int(payload.get("orden_id"))
        detalle_id = int(payload.get("detalle_id"))
        captura = obtener_captura_resultados(orden_id) or {}
        estudio = next(
            (
                item for item in captura.get("estudios") or []
                if int(item.get("detalle_id")) == detalle_id
            ),
            None,
        )
        if not estudio:
            return jsonify({"ok": False, "error": "El estudio no pertenece a la orden."}), 404

        valores_entrada = payload.get("valores") or {}
        verificaciones_entrada = payload.get("verificaciones") or {}
        valores = {}
        evaluaciones = {}
        for elemento in estudio.get("elementos") or []:
            key = str(elemento.get("id"))
            value = str(valores_entrada.get(key, "")).strip()
            if not value:
                return jsonify({
                    "ok": False,
                    "error": f"Captura el resultado de {elemento.get('nombre')}.",
                    "campo": key,
                }), 400
            reference = resolve_clinical_reference(
                elemento, captura.get("paciente") or {}
            )
            evaluation = evaluate_clinical_value(value, reference)
            if evaluation["estado"] == "invalido":
                return jsonify({
                    "ok": False,
                    "error": f"El resultado de {elemento.get('nombre')} no es válido.",
                    "campo": key,
                }), 400
            valores[key] = value
            evaluation["verificado"] = verificaciones_entrada.get(key) is True
            evaluaciones[key] = evaluation

        result = registrar_ejecucion_resultado(
            orden_id,
            detalle_id,
            valores,
            evaluaciones,
            session.get("user_id"),
            payload.get("clave_idempotencia") or uuid.uuid4(),
            payload.get("verificacion_de_id"),
        )
        return jsonify({"ok": True, "ejecucion": result, "evaluaciones": evaluaciones})
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Los datos de la captura no son válidos."}), 400
    except Exception as exc:
        logger.exception("No se pudo registrar la ejecución del estudio")
        message = str(exc)
        if "Inventario insuficiente" in message or "lotes vigentes" in message:
            message = (
                "El reactivo no tiene lotes vigentes suficientes. Ejecuta la "
                "migración actualizada para registrar el déficit sin bloquear "
                "el resultado."
            )
            status = 409
        else:
            message = "No se pudo completar el estudio. Revisa los datos e intenta nuevamente."
            status = 400
        return jsonify({"ok": False, "error": message}), status


@app_routes.route("/api/resultados/borrador", methods=["POST"])
@require_role("Quimico")
def api_guardar_borrador_resultado():
    payload = request.get_json(silent=True) or {}
    try:
        orden_id = int(payload.get("orden_id"))
        detalle_id = int(payload.get("detalle_id"))
        captura = obtener_captura_resultados(orden_id) or {}
        estudio = next(
            (
                item for item in captura.get("estudios") or []
                if int(item.get("detalle_id")) == detalle_id
            ),
            None,
        )
        if not estudio:
            return jsonify({"ok": False, "error": "El estudio no pertenece a la orden."}), 404

        allowed = {str(item.get("id")) for item in estudio.get("elementos") or []}
        valores = {
            str(key): str(value).strip()
            for key, value in (payload.get("valores") or {}).items()
            if str(key) in allowed and str(value).strip()
        }
        for key, checked in (payload.get("verificaciones") or {}).items():
            if str(key) in allowed and checked is True:
                valores[f"__verificado_{key}"] = True
        if not valores:
            return jsonify({
                "ok": False,
                "error": "Captura al menos un resultado para guardar el avance.",
            }), 400
        borrador = guardar_borrador_resultado(
            orden_id, detalle_id, valores, session.get("user_id")
        )
        return jsonify({
            "ok": True,
            "borrador": borrador,
            "message": "Avance guardado. Puedes continuar después.",
        })
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Los datos del avance no son válidos."}), 400
    except Exception as exc:
        logger.exception("No se pudo guardar el avance del resultado")
        message = str(exc)
        if "PGRST202" in message or "guardar_borrador_resultado_app" in message:
            message = (
                "Falta habilitar el guardado parcial en Supabase. "
                "Ejecuta la migración 20260729_result_drafts_patch.sql."
            )
        else:
            message = "No se pudo guardar el avance. Intenta nuevamente."
        return jsonify({"ok": False, "error": message}), 400


@app_routes.route('/ordenes/resultados', methods=['GET'])
@require_role("Quimico")
def obtener_ordenes_pendientes():
    return redirect(url_for("app_routes.resultados"))


@app_routes.route('/guardar_resultados', methods=['POST'])
@require_role("Quimico")
def guardar_resultados():
    orden_id = request.form['orden_id']
    paciente_id = request.form['paciente_id']
    resultado_parcial = request.form['resultado_parcial']  # Recibe los resultados parciales

    # Si no se proporciona resultado parcial, se retorna un error
    if not resultado_parcial:
        return jsonify({"error": "El resultado parcial es requerido"}), 400

    # Intentamos obtener el resultado actual de la base de datos
    existing_result = (
        supabase.table('resultados_paciente')
        .select('*')
        .eq('orden_id', orden_id)
        .eq('paciente_id', paciente_id)
        .limit(1)
        .execute()
    )

    if existing_result.data:
        # Si ya existe un resultado, vamos a actualizarlo parcialmente
        current_result = existing_result.data[0].get('resultado')

        # Si hay datos previos, los agregamos al resultado parcial
        if current_result:
            current_result = json.loads(current_result) if isinstance(current_result, str) else current_result
        else:
            current_result = []
        current_result.append(resultado_parcial)

        # Actualizar el resultado parcial
        supabase.table('resultados_paciente').update({
            'resultado': json.dumps(current_result),
            'estado': 'en_proceso',  # Estado 'en_proceso' mientras no se complete
            'semaforo': False  # Semáforo en 'False' hasta que se finalice
        }).eq('orden_id', orden_id).eq('paciente_id', paciente_id).execute()

        return jsonify({"message": "Resultado actualizado parcialmente"}), 200
    else:
        # Si no existe un resultado, crear uno nuevo
        resultado_json = [resultado_parcial]  # Guardar el resultado como una lista de resultados

        supabase.table('resultados_paciente').insert({
            'orden_id': orden_id,
            'paciente_id': paciente_id,
            'resultado': json.dumps(resultado_json),
            'estado': 'en_proceso',
            'semaforo': False
        }).execute()

        return jsonify({"message": "Resultado guardado parcialmente"}), 201




@app_routes.route('/legacy/finalizar_resultados', methods=['POST'])
@require_role("Quimico")
def finalizar_resultados_legacy():
    orden_id = request.json.get('orden_id')  # ID de la orden
    # Verificar que todos los campos estén llenos y los resultados están completos
    resultado_query = supabase.table('resultados_paciente') \
        .select('*') \
        .eq('orden_id', orden_id) \
        .execute()
    
    if not resultado_query.data:
        return jsonify({"message": "No se encontraron resultados para esta orden"}), 404

    resultados = resultado_query.data[0]
    
    # Verificar que todos los campos estén completos (esto puede incluir validación adicional)
    if not resultados['resultado']:
        return jsonify({"message": "Faltan resultados por completar"}), 400
    
    # Marcar la orden como finalizada
    supabase.table('resultados_paciente') \
        .update({
            'estado': 'finalizado',
            'semaforo': True  # Marcar el semáforo como True
        }) \
        .eq('orden_id', orden_id) \
        .execute()
    
    return jsonify({"message": "Resultados finalizados y listos para mostrador"}), 200

@app_routes.route('/finalizar_resultados', methods=['POST'])
@require_role("Quimico")
def finalizar_resultados():
    payload = request.get_json(silent=True) or {}
    try:
        orden_id = int(payload.get("orden_id"))
        finalizar_resultados_orden(orden_id, session.get("user_id"))
        return jsonify({
            "ok": True,
            "message": "Resultados finalizados y enviados a mostrador.",
        })
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "La orden no es válida."}), 400
    except Exception as exc:
        logger.exception("No se pudieron finalizar los resultados")
        message = str(exc)
        if "Faltan estudios por capturar" in message:
            message = (
                "Aún faltan estudios por completar. Guardar un avance no "
                "equivale a completar el estudio."
            )
        else:
            message = "No se pudo finalizar la orden. Intenta nuevamente."
        return jsonify({"ok": False, "error": message}), 400


@app_routes.route("/resultados/<int:orden_id>/imprimir")
@require_role("Mostrador, Quimico")
def imprimir_resultados_laboratorio(orden_id):
    try:
        captura = obtener_captura_resultados(orden_id) or {}
    except Exception:
        logger.exception("No se pudo preparar la impresión de la orden %s", orden_id)
        flash("No se pudieron cargar los resultados para imprimir.", "error")
        return redirect(url_for("app_routes.listos"))
    if not captura:
        flash("No se encontró la orden solicitada.", "error")
        return redirect(url_for("app_routes.listos"))

    estudios_impresos = []
    for estudio in captura.get("estudios") or []:
        ejecuciones = estudio.get("ejecuciones") or []
        if not ejecuciones:
            continue
        latest = ejecuciones[0]
        rows = []
        for elemento in estudio.get("elementos") or []:
            key = str(elemento.get("id"))
            evaluation = (latest.get("evaluaciones") or {}).get(key) or {}
            rows.append({
                "nombre": elemento.get("nombre"),
                "valor": (latest.get("valores") or {}).get(key),
                "unidad": evaluation.get("unidad") or "",
                "referencia": evaluation.get("referencia") or "Sin referencia",
                "estado": evaluation.get("estado") or "sin_referencia",
                "verificado": evaluation.get("verificado") is True,
            })
        estudios_impresos.append({
            "nombre": estudio.get("nombre_prueba"),
            "tipo": estudio.get("tipo_prueba"),
            "resultados": rows,
            "verificado": bool(latest.get("es_verificacion")) or any(
                row.get("verificado") for row in rows
            ),
            "numero_ejecucion": latest.get("numero_ejecucion"),
            "capturado_en": latest.get("creado_en"),
        })
    if not estudios_impresos:
        flash("La orden todavía no tiene estudios terminados para imprimir.", "error")
        return redirect(url_for("app_routes.resultados"))
    try:
        firma = obtener_firma_resultado(orden_id)
    except Exception:
        logger.exception("No se pudo cargar la firma de la orden %s", orden_id)
        firma = {}
    return render_template(
        "resultados/imprimir.html",
        orden=captura.get("orden") or {},
        paciente=captura.get("paciente") or {},
        estudios=estudios_impresos,
        firma=firma,
        fecha_impresion=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )


@app_routes.route('/mostrar_resultados', methods=['GET'])
@require_role("Mostrador")
def mostrar_resultados():
    return redirect(url_for("app_routes.listos"))
