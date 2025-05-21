import os
import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, jsonify
from functools import wraps
from services import *
from supabase import Client, create_client
from utils import *
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
from datetime import datetime
import json
import hashlib


app_routes = Blueprint('app_routes', __name__)

# Obtener la ruta del archivo JSON con estados
ruta_estados = os.path.join(os.path.dirname(__file__), 'static', 'JSON', 'estados.json')

# Cargar estados desde el JSON
with open(ruta_estados, 'r', encoding='utf-8') as file:
    estados_data = json.load(file)
    estados = estados_data["estados"]  # Extrae la lista de estados del JSON

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

# Mapeo de roles por ID
role_map = {
    1: "Admin",
    2: "Mostrador",
    3: "Enfermero",
    4: "Quimico"
}

# Decorador para restringir acceso según rol
def require_role(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("rol") not in roles:
                return redirect(url_for("app_routes.login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Ruta principal
@app_routes.route("/")
def home():
    if "usuario" in session:
        rol = session.get("rol", "").capitalize()  # Asegurar que el rol esté bien escrito
        if rol in role_map.values():
            return redirect(url_for(f"app_routes.{rol.lower()}_dashboard"))
    
    return redirect(url_for("app_routes.login"))

# Ruta de Dashboard
@app_routes.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("app_routes.login"))
    
    return render_template("dashboard.html")


@app_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('username')
        password = request.form.get('password')

        # Consultar usuario y verificar si está activo
        user_query = supabase.table("usuarios").select("*").eq("username", usuario).eq("estado_usuario", True).execute()

        # Verificar si el usuario existe
        if not user_query.data:
            flash('Usuario no encontrado o desactivado.', 'error')
            return redirect(url_for('app_routes.login'))

        user = user_query.data[0]  # Obtener el primer usuario activo

        # Validar contraseña
        if not verificar_usuario(usuario, password):
            flash('Usuario o contraseña incorrectos.', 'error')
            return redirect(url_for('app_routes.login'))

        # Obtener id, nombres y foto_perfil del usuario en una sola consulta
        empleado_query = (
            supabase.table("empleados")
            .select("id, nombres, foto_perfil")
            .eq("usuario_id", user['id'])
            .execute()
        )

        # Extraer los datos si la consulta fue exitosa
        if empleado_query.data:
            empleado = empleado_query.data[0]  # Tomamos el primer resultado
            empleado_id = empleado.get("id")
            nombres = empleado.get("nombres")
            foto_perfil = empleado.get("foto_perfil")
        else:
            empleado_id = None
            nombres = None
            foto_perfil = None


        if not empleado_query.data:
            flash('Error: No se encontró un empleado asociado al usuario.', 'error')
            return redirect(url_for('app_routes.login'))

        empleado_id = empleado_query.data[0]['id']

        # Obtener rol del empleado
        rol_query = supabase.table("empleado_roles").select("rol_id").eq("empleado_id", empleado_id).execute()

        if not rol_query.data:
            flash('Error: El empleado no tiene roles asignados.', 'error')
            return redirect(url_for('app_routes.login'))

        # Asignar rol
        rol_id = rol_query.data[0]['rol_id']
        rol = role_map.get(rol_id)

        if not rol:
            flash('Error: Rol no reconocido.', 'error')
            return redirect(url_for('app_routes.login'))

        # Guardar sesión
        session["usuario"] = usuario
        session["rol"] = rol
        session["nombres"] = nombres
        session["foto_perfil"] = foto_perfil

        session['user_id'] = user['id']  # Establecer user_id en la sesión correctamente

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
        print("Datos del formulario:", request.form)  # Depuración: Imprimir los datos del formulario

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
            print("Usuario existente:", existing_user.data)  # Depuración
            return "El nombre de usuario ya está en uso. Por favor elige otro.", 400

        # Encriptar la contraseña con bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        print(f"Contraseña encriptada: {hashed_password}")  # Depuración

        # Insertar usuario
        user_data = {"username": username, "password": hashed_password}
        user_response = supabase.table('usuarios').insert(user_data).execute()
        print("Respuesta de la inserción de usuario:", user_response.data)  # Depuración
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
        print("Respuesta de la inserción de empleado:", employee_response.data)  # Depuración
        empleado_id = employee_response.data[0]['id']

        # Insertar rol en la tabla empleado_roles
        employee_role_data = {"empleado_id": empleado_id, "rol_id": rol_id}
        role_response = supabase.table('empleado_roles').insert(employee_role_data).execute()
        print("Respuesta de la inserción de rol:", role_response.data)  # Depuración

        return redirect(url_for('app_routes.manage_employees'))  # Redirección tras éxito

    return render_template('admin/add_employee.html', estados=estados)




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
    
    return render_template('admin/add_hospital.html', estados=estados)

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

    return render_template('admin/edit_hospital.html', hospital=hospital, estados=estados)

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
def reportes():
    return render_template("admin/reportes.html")

@app_routes.route("/configuracion")
def configuracion():
    return render_template("admin/configuracion.html")

@app_routes.route("/faltantes")
def faltantes():
    return render_template("mostrador/faltantes.html")


@app_routes.route("/pacientes")
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

        if 'id' in data:
            ok, result = actualizar_reactivo(data['id'], data)
            if ok:
                flash("Reactivo actualizado correctamente.", "success")
            else:
                flash(result, "error")
                return render_template("admin/add_reactivo.html", reactivo=data, proveedores=obtener_proveedores())
        else:
            ok, result = crear_reactivo(data)
            if ok:
                flash(result, "success")
            else:
                flash(result, "error")
                return render_template("admin/add_reactivo.html", reactivo=None, proveedores=obtener_proveedores())

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
        return redirect(url_for('app_routes.inventory_reactivos'))
    
    # Si el método es POST, es cuando se va a editar el reactivo
    if request.method == 'POST':
        # Recibe los datos del formulario y actualiza el reactivo en la base de datos
        nombre = request.form.get('nombre')
        tipo_reactivo = request.form.get('tipo_reactivo')
        costo_unidad = request.form.get('costo_unidad')
        precio_unidad = request.form.get('precio_unidad')
        proveedor_id = request.form.get('proveedor')  # El proveedor seleccionado
        fecha_entrada = request.form.get('fecha_entrada')
        cantidad_inicial = request.form.get('cantidad_inicial')
        numero_lote = request.form.get('numero_lote')
        fecha_vencimiento = request.form.get('fecha_vencimiento')
        ubicacion_inventario = request.form.get('ubicacion_inventario')
        anotaciones = request.form.get('anotaciones')
        
        # Actualiza el reactivo en la base de datos
        supabase.table('reactivos').update({
            'nombre': nombre,
            'tipo_reactivo': tipo_reactivo,
            'costo_unidad': costo_unidad,
            'precio_unidad': precio_unidad,
            'proveedor_id': proveedor_id,
            'fecha_entrada': fecha_entrada,
            'cantidad_inicial': cantidad_inicial,
            'numero_lote': numero_lote,
            'fecha_vencimiento': fecha_vencimiento,
            'ubicacion_inventario': ubicacion_inventario,
            'anotaciones': anotaciones
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
                "cantidad_inicial": reactivo['cantidad_inicial'],
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
        reactivos = request.form.getlist('reactivos')  # Lista de reactivos seleccionados
        valores_normales_json = request.form.get('valores_normales_json', '[]')

        if not nombre or not tipo:
            flash("Todos los campos son obligatorios.", "error")
            return render_template('admin/add_prueba.html', is_edit=False)

        # Crear prueba
        nueva_prueba = crear_prueba(nombre, tipo)
        if not nueva_prueba:
            flash("Error al crear la prueba.", "error")
            return render_template('admin/add_prueba.html', is_edit=False)

        prueba_id = nueva_prueba[0]['id']  # asumiendo que retorna lista con dicts

        # Asignar reactivos
        asignar_reactivos_a_prueba(prueba_id, reactivos)

        # Guardar valores normales
        import json
        valores_normales = json.loads(valores_normales_json)
        for valor in valores_normales:
            crear_valor_normal(prueba_id, valor.get('nombre', ''),
                              valor.get('tipo_separacion', ''),
                              valor.get('estructura', {}))

        flash("Prueba registrada exitosamente", "success")
        return redirect(url_for('app_routes.pruebas_clinicas'))

    # GET
    reactivos = obtener_todos_los_reactivos()
    return render_template('admin/add_prueba.html', is_edit=False, reactivos=reactivos)


# Editar prueba clínica existente
@app_routes.route('/admin/edit_prueba/<int:prueba_id>', methods=['GET', 'POST'])
@require_role("Admin")
def edit_prueba(prueba_id):
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        tipo = request.form.get('tipo', '').strip()
        reactivos = request.form.getlist('reactivos')
        valores_normales_json = request.form.get('valores_normales_json', '[]')

        if not nombre or not tipo:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for('app_routes.edit_prueba', prueba_id=prueba_id))

        actualizar_prueba(prueba_id, nombre, tipo)

        actualizar_reactivos_de_prueba(prueba_id, reactivos)

        import json
        valores_normales = json.loads(valores_normales_json)
        # Por simplicidad elimina los valores normales previos y crea nuevos (puedes optimizar)
        eliminar_valores_normales_de_prueba(prueba_id)
        for valor in valores_normales:
            crear_valor_normal(prueba_id, valor.get('nombre', ''),
                              valor.get('tipo_separacion', ''),
                              valor.get('estructura', {}))

        flash("Prueba actualizada correctamente", "success")
        return redirect(url_for('app_routes.pruebas_clinicas'))

    # GET
    prueba = obtener_prueba_por_id(prueba_id)
    if not prueba:
        flash("Prueba no encontrada", "error")
        return redirect(url_for('app_routes.pruebas_clinicas'))

    reactivos = obtener_todos_los_reactivos()
    return render_template('admin/add_prueba.html', is_edit=True, prueba=prueba, reactivos=reactivos)


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
        # Aquí procesas los datos del formulario, por ejemplo:
        nombre = request.form.get("nombre")
        hospital_id = request.form.get("hospital")
        cuarto = request.form.get("cuarto")
        doctor_id = request.form.get("doctor")
        observaciones = request.form.get("observaciones")

        # Validaciones opcionales aquí...

        # Guardar en la base de datos o pasar a la siguiente vista
        # Redirige a la página de pruebas seleccionadas
        return redirect(url_for("app_routes.manage_orden_pruebas"))

    # GET normal
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    hospitales = obtener_hospitales()
    doctores = obtener_doctores()
    return render_template("mostrador/orden.html", fecha_actual=fecha_actual, hospitales=hospitales, doctores=doctores)
    
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
    if request.method == "POST":
        datos = request.form.get("datosSeleccionados")
        if datos:
            session["pruebas_seleccionadas"] = datos
        return redirect(url_for("app_routes.reporte"))

    pruebas = session.get("pruebas_seleccionadas", "[]")
    fecha_actual = datetime.now().strftime("%d/%m/%Y")  # si usas esto

    return render_template("mostrador/reporte.html", pruebas_json=pruebas, fecha_actual=fecha_actual)

@app_routes.route("/orden_pruebas")
@require_role("Mostrador")  
def manage_orden_pruebas():
    return render_template("mostrador/orden_pruebas.html")

@app_routes.route("/listos")
@require_role("Mostrador")  
def listos():
    return render_template("mostrador/listos.html")


#Enfermero
@app_routes.route("/muestra")
@require_role("Enfermero") 
def manage_muestra():
    return render_template("enfermero/muestra.html")

@app_routes.route("/api/analisis/<folio>")
def get_analisis(folio):
    datos = consultar_analisis_por_folio(folio)  
    return jsonify(datos)

#Quimico
@app_routes.route("/resultados")
@require_role("Quimico") 
def resultados():
    return render_template("quimico/resultados.html")

# Ruta de prueba solo para front
@app_routes.route('/quimico/captura_resultados/<folio>')
def captura_resultados(folio):
    paciente = {"nombre": "Paciente Demo", "orden": folio}

    # Diccionario de nombres demo
    nombres_pacientes = {
        "00010": "María Fernanda López Hernández",
        "00008": "José Manuel Pérez Rodríguez",
        "00007": "Ana Sofía Ramírez García",
        "00006": "Juan Carlos Martínez Torres",
        "00005": "Valeria González Chávez",
        "00011": "María José Hernández Gómez",
        "00012": "Jorge Luis Vargas Martínez",
        "00013": "Carmen Patricia Flores López",
        "00014": "Carlos Eduardo Pérez Gutiérrez",
        "00015": "Sofía Elena Jiménez Morales",
    }

    paciente = {
        "nombre": nombres_pacientes.get(folio, "Paciente Demo"),
        "orden": folio
    }

    # Define pruebas por folio
    folio_pruebas = {
        "00010": ["EGO", "BH (Biometría Hemática)"],  # <--- agrega las pruebas que lleva
        "00008": ["EGO"],
        "00007": ["Coprológico"],
        "00006": ["Grupo Sanguíneo"],
        "00005": ["Cultivo de Heridas"],
        "00011": ["BH (Biometría Hemática)", "EGO"],
        "00012": ["Coprológico"],
        "00013": ["Grupo Sanguíneo"],
        "00014": ["Cultivo de Heridas"],
        "00015": ["Grupo Sanguíneo"]
    }

    # Diccionario de pruebas como arriba
    catalogo_pruebas = {
        "BH (Biometría Hemática)": {
            "nombre": "BH (Biometría Hemática)",
            "campos": [
                {"key": "hemoglobina", "nombre": "Hemoglobina", "tipo": "input", "unidad": "g/dL", "valores_normales": "13.8 a 17.2"},
                {"key": "hematocrito", "nombre": "Hematocrito", "tipo": "input", "unidad": "%", "valores_normales": "40 a 50"},
                {"key": "eritrocitos", "nombre": "Eritrocitos", "tipo": "input", "unidad": "millones/µL", "valores_normales": "4.7 a 6.1"},
            ]
        },  
        "EGO": {
            "nombre": "EGO",
            "campos": [
                {"key": "bilirrubinas", "nombre": "Bilirrubinas", "tipo": "select", "opciones": ["Negativo", "Positivo", "Escasos"], "unidad": "-", "valores_normales": "Negativo"},
                {"key": "cetonas", "nombre": "Cetonas", "tipo": "select", "opciones": ["Negativo", "Positivo", "Escasos"], "unidad": "-", "valores_normales": "Negativo"},
                {"key": "cristales", "nombre": "Cristales", "tipo": "select", "opciones": ["Negativo", "Positivo", "Escasos"], "unidad": "-", "valores_normales": "Ausente o escasos"},
                {"key": "urobilinogeno", "nombre": "Urobilinógeno", "tipo": "input", "unidad": "mg/dl", "valores_normales": "0.1 a 1.0"},
            ]
        },
        "Coprológico": {
            "nombre": "Coprológico",
            "campos": [
                {"key": "color", "nombre": "Color", "tipo": "select", "opciones": ["Amarillo", "Marrón", "Verde", "Negro"], "unidad": "-", "valores_normales": "Marrón"},
                {"key": "consistencia", "nombre": "Consistencia", "tipo": "select", "opciones": ["Sólida", "Semi-sólida", "Líquida"], "unidad": "-", "valores_normales": "Sólida"},
                {"key": "sangre_oculta", "nombre": "Sangre Oculta", "tipo": "select", "opciones": ["Negativo", "Positivo"], "unidad": "-", "valores_normales": "Negativo"},
            ]
        },
        "Grupo Sanguíneo": {
            "nombre": "Grupo Sanguíneo",
            "campos": [
                {"key": "grupo", "nombre": "Grupo", "tipo": "select", "opciones": ["A", "B", "AB", "O"], "unidad": "-", "valores_normales": "-"},
                {"key": "rh", "nombre": "RH", "tipo": "select", "opciones": ["+", "-"], "unidad": "-", "valores_normales": "-"},
            ]
        },
        "Cultivo de Heridas": {
            "nombre": "Cultivo de Heridas",
            "campos": [
                {"key": "leucocitos", "nombre": "Leucocitos", "tipo": "select", "opciones": ["Ausentes", "Escasos", "Moderados", "Abundantes"], "unidad": "-", "valores_normales": "Ausentes"},
                {"key": "bacterias", "nombre": "Bacterias", "tipo": "select", "opciones": ["Ausentes", "Presentes"], "unidad": "-", "valores_normales": "Ausentes"},
                {"key": "flora", "nombre": "Flora", "tipo": "input", "unidad": "-", "valores_normales": "-"},
            ]
        },
    }
    # Obtén solo las pruebas del folio
    pruebas = [catalogo_pruebas[n] for n in folio_pruebas.get(folio, [])]

    return render_template(
        "quimico/resultados_captura.html",
        paciente=paciente,
        pruebas=pruebas
    )
