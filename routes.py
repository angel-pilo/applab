import os
import bcrypt
import re
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, jsonify
from functools import wraps
from services import *
from datetime import datetime
import json
from supabase_client import supabase



app_routes = Blueprint('app_routes', __name__)

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
    4: "Quimico"
}

# Decorador para restringir acceso según rol
def require_role(roles):
    if isinstance(roles, str):
        roles = {role.strip() for role in roles.split(",")}
    else:
        roles = set(roles)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("rol") not in roles:
                return redirect(url_for("app_routes.login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


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
    if not hospital_id:
        errors.append("Selecciona un hospital.")
    if not cuarto:
        errors.append("Ingresa el número/nombre de cuarto.")
    if not doctor_id:
        errors.append("Selecciona un doctor.")
    if cuarto and not re.fullmatch(r"[A-Za-z0-9\-# ]{1,15}", cuarto):
        errors.append("El campo 'Cuarto' solo permite letras, números, espacio, -, # (máx. 15).")
    if patient_id and not existe_paciente_activo(as_int_or_none(patient_id)):
        errors.append("El paciente seleccionado no existe o está inactivo.")
    if hospital_id and not existe_hospital_activo(as_int_or_none(hospital_id)):
        errors.append("El hospital seleccionado no existe o está inactivo.")
    if doctor_id and not existe_doctor_activo(as_int_or_none(doctor_id)):
        errors.append("El doctor seleccionado no existe o está inactivo.")

    return errors


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

# Ruta principal
@app_routes.route("/")
def home():
    if "usuario" in session:
        rol = session.get("rol", "").capitalize()  # Asegurar que el rol esté bien escrito
        if rol in role_map.values():
            return redirect(url_for(f"app_routes.{rol.lower()}_dashboard"))
    
    return redirect(url_for("app_routes.login"))

@app_routes.route("/proximamente")
def proximamente():
    feature = request.args.get("feature")
    return render_template("proximamente.html", feature=feature)

# Ruta de Dashboard
@app_routes.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("app_routes.login"))
    
    rol = session.get("rol", "")
    if rol not in role_map.values():
        session.clear()
        return redirect(url_for("app_routes.login"))
    return redirect(url_for(f"app_routes.{rol.lower()}_dashboard"))


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

        session['user_id'] = user['id']  # Establecer user_id en la sesión correctamente
        session['empleado_id'] = user.get('empleado_id')

        return redirect(url_for(f"app_routes.{rol.lower()}_dashboard"))

    return render_template('auth/login.html')


@app_routes.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('app_routes.home'))

@app_routes.route("/admin")
@require_role("Admin")
def admin_dashboard():
    return render_template("admin/admin.html")

@app_routes.route("/backlog")
@require_role("Admin")
def backlog():
    # Dummy: lista de eventos (solo frontend por ahora)
    events = [
        {
            "when": "2025-09-22 10:14",
            "module": "Pruebas",
            "icon": "fas fa-clipboard-check",
            "severity": "info",
            "title": "Resultado validado",
            "detail": "Prueba #A-293014 validada por QFB Martínez"
        },
        {
            "when": "2025-09-22 09:31",
            "module": "Inventario",
            "icon": "fas fa-vial",
            "severity": "warning",
            "title": "Stock bajo detectado",
            "detail": "Reactivo Hematoxilina: 5 u (mín. 10)"
        },
        {
            "when": "2025-09-21 18:02",
            "module": "Pacientes",
            "icon": "fas fa-id-card",
            "severity": "success",
            "title": "Paciente registrado",
            "detail": "María P. (ID: P-1209) por Mostrador"
        },
        {
            "when": "2025-09-21 16:45",
            "module": "Proveedores",
            "icon": "fas fa-truck",
            "severity": "info",
            "title": "Orden de compra creada",
            "detail": "OC-7781 a QuimiLab SA de CV"
        },
        {
            "when": "2025-09-21 12:20",
            "module": "Doctores",
            "icon": "fas fa-stethoscope",
            "severity": "success",
            "title": "Doctor agregado",
            "detail": "Dr. Luis R. (CMP 33210)"
        },
    ]
    return render_template("backlog.html", events=events)

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

        # Obtener y validar datos del formulario
        required_fields = [
            "sexo", "fecha_nacimiento", "nombres", "apellidos", "telefono", "correo",
            "username", "password", "calle", "numero_ext", "codigo_postal", "municipio",
            "estado", "curp_rfc", "turno", "condiciones_medicas", "contacto_emergencia", "tipo_empleado"
        ]

        for field in required_fields:
            if not request.form.get(field):
                return f"El campo {field} es obligatorio", 400

        # Datos generales
        sexo = request.form['sexo']
        fecha_nacimiento = request.form['fecha_nacimiento']
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        telefono = request.form['telefono']
        correo = request.form['correo']
        username = request.form['username']
        password = request.form['password']
        calle = request.form['calle']
        numero_ext = request.form['numero_ext']
        numero_int = request.form.get('numero_int', None)  # Puede ser opcional
        codigo_postal = request.form['codigo_postal']
        municipio = request.form['municipio']
        estado = request.form['estado']
        curp_rfc = request.form['curp_rfc']
        turno = request.form['turno']
        condiciones_medicas = request.form['condiciones_medicas']
        contacto_emergencia = request.form['contacto_emergencia']
        rol_id = request.form.get('tipo_empleado')
        foto_perfil = None  # O asigna un valor predeterminado si se requiere

        if not rol_id.isdigit():
            return "Tipo de empleado inválido", 400
        rol_id = int(rol_id)

        # Verificar si el usuario ya existe
        existing_user = supabase.table('usuarios').select('id').eq('username', username).execute()
        if existing_user.data:
            return "El nombre de usuario ya está en uso. Por favor elige otro.", 400

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
            "foto_perfil": foto_perfil
        }
        employee_response = supabase.table('empleados').insert(employee_data).execute()
        empleado_id = employee_response.data[0]['id']

        # Insertar rol en la tabla empleado_roles
        employee_role_data = {"empleado_id": empleado_id, "rol_id": rol_id}
        role_response = supabase.table('empleado_roles').insert(employee_role_data).execute()

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

        # Obtener el usuario asociado al empleado (incluyendo la contraseña)
        usuario = supabase.table('usuarios').select('username, password').eq('id', empleado['usuario_id']).execute()
        if usuario.data:
            empleado['username'] = usuario.data[0]['username']
            empleado['password'] = usuario.data[0]['password']  # Recuperar la contraseña

        # Renderizar la plantilla con los datos del empleado y role_map
        return render_template('admin/edit_employee.html', empleado=empleado, is_edit=True, role_map=role_map, estados=estados)

    elif request.method == "POST":
        # Obtener y validar datos del formulario
        required_fields = [
            "sexo", "fecha_nacimiento", "nombres", "apellidos", "telefono", "correo",
            "username", "calle", "numero_ext", "codigo_postal", "municipio", "estado",
            "curp_rfc", "turno", "condiciones_medicas", "contacto_emergencia", "tipo_empleado"
        ]

        for field in required_fields:
            if not request.form.get(field):
                return f"El campo {field} es obligatorio", 400

        # Datos generales
        sexo = request.form['sexo']
        fecha_nacimiento = request.form['fecha_nacimiento']
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        telefono = request.form['telefono']
        correo = request.form['correo']
        username = request.form['username']
        calle = request.form['calle']
        numero_ext = request.form['numero_ext']
        numero_int = request.form.get('numero_int', None)
        codigo_postal = request.form['codigo_postal']
        municipio = request.form['municipio']
        estado = request.form['estado']
        curp_rfc = request.form['curp_rfc']
        turno = request.form['turno']
        condiciones_medicas = request.form['condiciones_medicas']
        contacto_emergencia = request.form['contacto_emergencia']
        rol_id = request.form.get('tipo_empleado')

        if not rol_id.isdigit():
            return "Tipo de empleado inválido", 400
        rol_id = int(rol_id)

        # Obtener el empleado actual para recuperar el usuario_id
        empleado_actual = supabase.table('empleados').select('usuario_id').eq('id', empleado_id).execute()
        if not empleado_actual.data:
            flash("Empleado no encontrado", "error")
            return redirect(url_for("app_routes.manage_employees"))

        usuario_id = empleado_actual.data[0]['usuario_id']

        # Actualizar el usuario
        usuario_data = {"username": username}
        nueva_password = request.form.get('password')
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
            "contacto_emergencia": contacto_emergencia
        }
        supabase.table('empleados').update(empleado_data).eq('id', empleado_id).execute()

        # Actualizar el rol del empleado
        supabase.table('empleado_roles').update({"rol_id": rol_id}).eq('empleado_id', empleado_id).execute()

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
    return render_template("mostrador/mostrador.html")

@app_routes.route("/enfermero")
@require_role("Enfermero")
def enfermero_dashboard():
    return render_template("enfermero/enfermero.html")

@app_routes.route("/quimico")
@require_role("Quimico")
def quimico_dashboard():
    return render_template("quimico/quimico.html")

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
@require_role("Admin")
def add_hospital():
    """Formulario para agregar un hospital"""
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        calle = request.form['calle']
        numero_ext = request.form['numero_ext']
        numero_int = request.form.get('numero_int', None)
        codigo_postal = request.form['codigo_postal']
        municipio = request.form['municipio']
        estado = request.form['estado']
        anotaciones = request.form.get('anotaciones', '')

        crear_hospital(nombre, telefono, correo, calle, numero_ext, numero_int, codigo_postal, municipio, estado, anotaciones)
        flash("Hospital registrado exitosamente", "success")
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
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        correo = request.form['correo']
        calle = request.form['calle']
        numero_ext = request.form['numero_ext']
        numero_int = request.form.get('numero_int', None)
        codigo_postal = request.form['codigo_postal']
        municipio = request.form['municipio']
        estado = request.form['estado']
        anotaciones = request.form.get('anotaciones', '')

        actualizar_hospital(hospital_id, nombre, telefono, correo, calle, numero_ext, numero_int, codigo_postal, municipio, estado, anotaciones)
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
        return jsonify({"message": "Hospital activado correctamente."}), 200
    except Exception:
        return jsonify({"message": "Error al activar hospital."}), 500
    
# Rutas de sidebar según rol
@app_routes.route("/reportes")
@require_role("Admin")
def reportes():
    return render_template("admin/reportes.html")

@app_routes.route("/configuracion")
@require_role(role_map.values())
def configuracion():
    # Solo usuarios logueados
    if "usuario" not in session:
        return redirect(url_for("app_routes.login"))

    user = {
        "username": session.get("usuario"),
        "rol": session.get("rol", "—"),
        "nombres": session.get("nombres", "—"),
        "foto_perfil": session.get("foto_perfil"),  # puede ser None
    }

    return render_template("admin/configuracion.html", user=user)


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
@require_role("Admin")
def add_doctor():
    hospitales = supabase.table("hospitales").select("id, nombre").execute().data

    if request.method == "POST":
        nombres = request.form["nombres"].strip()
        apellidos = request.form["apellidos"].strip()
        telefono = request.form["telefono"].strip()
        correo = request.form["correo"].strip()
        tipo_consultorio = request.form["tipo_consultorio"]
        anotaciones = request.form.get("anotaciones", "")

        # Validación de duplicados (sin .and_())
        exists_by_data = supabase.table("doctores").select("id") \
            .eq("nombres", nombres) \
            .eq("apellidos", apellidos) \
            .eq("telefono", telefono) \
            .execute()

        exists_by_email = supabase.table("doctores").select("id") \
            .eq("correo", correo) \
            .execute()

        if exists_by_data.data or exists_by_email.data:
            flash("Ya existe un doctor registrado con el mismo nombre, teléfono o correo.", "error")
            return render_template(
                "admin/add_doctor.html",
                doctor=request.form,
                hospitales=hospitales,
                estados=estados,
                is_edit=False
            )

        # Construcción del objeto para insertar
        data = {
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo,
            "tipo_consultorio": tipo_consultorio,
            "anotaciones": anotaciones,
            "activo": True
        }

        if tipo_consultorio == "propio":
            data.update({
                "calle": request.form.get("calle"),
                "numero_ext": request.form.get("numero_ext"),
                "numero_int": request.form.get("numero_int"),
                "codigo_postal": request.form.get("codigo_postal"),
                "municipio": request.form.get("municipio"),
                "estado": request.form.get("estado"),
                "hospital_id": None
            })
        elif tipo_consultorio == "hospital":
            data.update({
                "hospital_id": request.form.get("hospital_id"),
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

        crear_doctor(data)
        flash("Doctor registrado correctamente.", "success")
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
        nombres = request.form["nombres"].strip()
        apellidos = request.form["apellidos"].strip()
        telefono = request.form["telefono"].strip()
        correo = request.form["correo"].strip()
        tipo_consultorio = request.form["tipo_consultorio"]
        anotaciones = request.form.get("anotaciones", "")

        # Verificar duplicados en otros doctores
        same_data = supabase.table("doctores").select("id") \
            .eq("nombres", nombres) \
            .eq("apellidos", apellidos) \
            .eq("telefono", telefono) \
            .neq("id", doctor_id) \
            .execute()

        same_email = supabase.table("doctores").select("id") \
            .eq("correo", correo) \
            .neq("id", doctor_id) \
            .execute()

        if same_data.data or same_email.data:
            flash("Ya existe otro doctor con los mismos datos. Revisa nombre, teléfono o correo.", "error")
            hospitales = supabase.table("hospitales").select("id, nombre").execute().data
            return render_template(
                "admin/add_doctor.html",
                doctor=request.form,
                hospitales=hospitales,
                estados=estados,
                is_edit=True
            )

        # Actualizar doctor
        data = {
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo,
            "tipo_consultorio": tipo_consultorio,
            "anotaciones": anotaciones
        }

        if tipo_consultorio == "propio":
            data.update({
                "calle": request.form.get("calle"),
                "numero_ext": request.form.get("numero_ext"),
                "numero_int": request.form.get("numero_int"),
                "codigo_postal": request.form.get("codigo_postal"),
                "municipio": request.form.get("municipio"),
                "estado": request.form.get("estado"),
                "hospital_id": None
            })
        elif tipo_consultorio == "hospital":
            data.update({
                "hospital_id": request.form.get("hospital_id"),
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
    return render_template('admin/patients.html', pacientes=pacientes, rol=session.get("rol"))

# CREAR
@app_routes.route('/admin/add_patient', methods=['GET', 'POST'])
@require_role(['Admin', 'Mostrador'])
def add_patient():
    hospitales = obtener_hospitales()
    if request.method == 'POST':
        data = request.form.to_dict()
        data["activo"] = True

        ok, result = crear_paciente_seguro(data)
        if not ok:
            flash(result, "error")
            return render_template('admin/add_patient.html', is_edit=False, estados=estados, hospitales=hospitales, patient=data)

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

        ok, result = actualizar_paciente_seguro(patient_id, data)
        if not ok:
            flash(result, "error")
            return render_template('admin/add_patient.html', is_edit=True, estados=estados, hospitales=hospitales, patient=data)

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
@app_routes.route("/admin/proveedores")
@require_role("Admin")
def manage_proveedores():
    proveedores = obtener_proveedores()
    return render_template("admin/proveedores.html", proveedores=proveedores, rol=session.get("rol"))

@app_routes.route("/admin/add_proveedor", methods=["GET", "POST"])
@require_role("Admin")
def add_proveedor():
    if request.method == "POST":
        data = request.form.to_dict()
        data["activo"] = True

        ok, result = crear_proveedor_seguro(data)
        if not ok:
            flash(result, "error")
            return render_template("admin/add_proveedor.html", proveedor=data, is_edit=False, estados=estados)

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
        data = request.form.to_dict()

        ok, result = actualizar_proveedor_seguro(proveedor_id, data)
        if not ok:
            flash(result, "error")
            return render_template("admin/add_proveedor.html", proveedor=data, is_edit=True, estados=estados)

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

# Ruta para agregar un nuevo reactivo
@app_routes.route("/admin/add_reactivo", methods=["GET", "POST"])
@require_role("Admin")
def add_reactivo():
    if request.method == "POST":
        data = request.form.to_dict()

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
            if float(data["costo_unidad"]) < 0 or float(data["precio_unidad"]) < 0 or int(data["cantidad_inicial"]) < 0:
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

        if any(not str(value or "").strip() for value in (
            nombre, tipo_reactivo, costo_unidad, precio_unidad, proveedor_id, fecha_entrada
        )):
            flash("Completa todos los campos obligatorios del reactivo.", "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=reactivo,
                proveedores=proveedores,
                is_edit=True,
            )

        try:
            if float(costo_unidad) < 0 or float(precio_unidad) < 0:
                raise ValueError
        except ValueError:
            flash("Costo y precio deben ser valores válidos y no negativos.", "error")
            return render_template(
                "admin/add_reactivo.html",
                reactivo=reactivo,
                proveedores=proveedores,
                is_edit=True,
            )
        
        # Actualiza el reactivo en la base de datos
        supabase.table('reactivos').update({
            'nombre': nombre,
            'tipo_reactivo': tipo_reactivo,
            'costo_unidad': costo_unidad,
            'precio_unidad': precio_unidad,
            'proveedor_id': proveedor_id,
            'fecha_entrada': fecha_entrada,
            'numero_lote': numero_lote.strip() or None,
            'fecha_vencimiento': fecha_vencimiento or None,
            'ubicacion_inventario': ubicacion_inventario.strip() or None,
            'anotaciones': anotaciones.strip() or None
        }).eq('id', reactivo_id).execute()
        
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
                "proveedor_nombre": proveedor['nombre'] if proveedor else "N/A"  # Retorna el nombre del proveedor
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
        return jsonify({"message": "Prueba activada correctamente."}), 200
    except Exception as e:
        print(f"Error al activar prueba: {e}")
        return jsonify({"message": "Error al activar la prueba."}), 500


#Mostrador
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
            )

        # OK: puedes guardar en sesión para siguiente paso
        session["orden_actual"] = {
            "patient_id": int(patient_id),
            "hospital_id": int(hospital_id),
            "cuarto": cuarto,
            "doctor_id": int(doctor_id),
            "observaciones": observaciones,
        }
        return redirect(url_for("app_routes.manage_orden_pruebas"))

    # GET normal
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
    )


@app_routes.route("/api/validar_orden", methods=["POST"])
@require_role("Mostrador")
def api_validar_orden():
    data = request.get_json() or {}
    errors = validate_order_data(data)

    ok = len(errors) == 0
    return jsonify({"ok": ok, "errors": errors}), (200 if ok else 400)

    
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
            'nombre_completo': f"{p['nombres']} {p['apellidos']}"
        }
        for p in pacientes
        if query.lower() in p['nombres'].lower() or query.lower() in p['apellidos'].lower()
    ][:10]  # limitar resultados a 10

    return jsonify(resultados)


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
            session["pruebas_seleccionadas"] = datos
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

@app_routes.route("/orden/<int:orden_id>/abonar", methods=["POST"])
@require_role("Mostrador")
def abonar_orden(orden_id: int):
    orden_id_session = session.get("orden_id_db")

    if not orden_id_session or orden_id_session != orden_id:
        flash("Primero guarda la orden (Imprimir) antes de registrar abonos.", "error")
        return redirect(url_for("app_routes.reporte"))

    orden_db = obtener_orden_por_id(orden_id)
    if not orden_db:
        flash("La orden no existe en la base de datos. Vuelve a guardarla.", "error")
        # limpia el folio fantasma para que al imprimir se vuelva a crear
        session.pop("orden_id_db", None)
        return redirect(url_for("app_routes.reporte"))

    cantidad_str = request.form.get("cantidad")
    nota = request.form.get("nota")

    try:
        cantidad = float(cantidad_str)
    except (TypeError, ValueError):
        flash("Cantidad de abono inválida.", "error")
        return redirect(url_for("app_routes.reporte"))

    if cantidad <= 0:
        flash("La cantidad debe ser mayor a cero.", "error")
        return redirect(url_for("app_routes.reporte"))

    empleado_id = session.get("empleado_id")

    try:
        registrar_abono(orden_id, cantidad, empleado_id, nota)
        flash("Abono registrado correctamente.", "success")
    except Exception as e:
        print("Error al registrar abono:", e)
        flash("Ocurrió un error al registrar el abono.", "error")

    return redirect(url_for("app_routes.reporte"))

@app_routes.route("/orden_pruebas")
@require_role("Mostrador")
def manage_orden_pruebas():
    if "orden_actual" not in session:
        flash("Primero llena los datos de la orden.", "error")
        return redirect(url_for("app_routes.manage_orden"))

    pruebas = obtener_pruebas()  # usa la función ya existente en services.py
    folio_sugerido = obtener_siguiente_folio_orden()
    return render_template("mostrador/orden_pruebas.html", pruebas=pruebas, folio_sugerido=folio_sugerido)


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
    # Obtener las órdenes que ya llegaron a Químico
    ordenes_quimico = obtener_ordenes_para_quimico()  
    return render_template("mostrador/listos.html", ordenes_quimico=ordenes_quimico)


# Enfermero
@app_routes.route("/muestra")
@require_role("Enfermero")
def manage_muestra():
    ordenes = obtener_ordenes_para_muestra()
    return render_template("enfermero/muestra.html", ordenes=ordenes)


@app_routes.route("/api/analisis/<int:orden_id>")
@require_role("Enfermero, Quimico")
def get_analisis(orden_id):
    datos = consultar_analisis_por_folio(orden_id)
    return jsonify(datos)


@app_routes.route("/api/muestra/finalizar/<int:orden_id>", methods=["POST"])
@require_role("Enfermero")
def api_finalizar_muestra(orden_id):
    ok = actualizar_flujo_orden(orden_id, "en_quimico")
    if not ok:
        return jsonify({"ok": False, "error": "No se pudo actualizar el flujo de la orden"}), 500
    return jsonify({"ok": True})

# Químico
@app_routes.route("/resultados")
@require_role("Quimico")
def resultados():
    ordenes = obtener_ordenes_para_quimico()     # flujo = 'en_quimico'
    faltantes = obtener_ordenes_para_muestra()   # flujo = 'muestra_pendiente'
    return render_template(
        "quimico/resultados.html",
        ordenes=ordenes,
        faltantes=faltantes
    )

@app_routes.route('/orden/<int:orden_id>/captura_resultados', methods=['GET'])
@require_role("Quimico")
def captura_resultados(orden_id):
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




@app_routes.route('/finalizar_resultados', methods=['POST'])
@require_role("Quimico")
def finalizar_resultados():
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

@app_routes.route('/mostrar_resultados', methods=['GET'])
@require_role("Mostrador")
def mostrar_resultados():
    return redirect(url_for("app_routes.listos"))
