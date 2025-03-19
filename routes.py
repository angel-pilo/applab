import os
import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for, jsonify
from functools import wraps
from services import *
from supabase import Client, create_client
from utils import *
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
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
def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("rol") != role:
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

@app_routes.route("/resultados")
def resultados():
    return render_template("quimico/resultados.html")