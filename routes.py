import os
import bcrypt
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from functools import wraps
from services import obtener_empleados, verificar_usuario
from supabase import Client, create_client
from utils import *
from werkzeug.utils import secure_filename

app_routes = Blueprint('app_routes', __name__)

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

role_map = {
    1: "Admin",
    2: "Mostrador",
    3: "Enfermero",
    4: "Quimico"
}

def require_role(role):
    """ Decorador para verificar el rol del usuario """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("rol") != role:
                return redirect(url_for("app_routes.login"))
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app_routes.route("/")
def home():
    if "usuario" in session:
        rol = session.get("rol", "").lower()
        if rol in role_map.values():
            return redirect(url_for(f"app_routes.{rol}_dashboard"))
    return redirect(url_for("app_routes.login"))

@app_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('username')
        password = request.form.get('password')
        user = verificar_usuario(usuario, password)

        if user:
            session["usuario"] = usuario
            session["rol"] = role_map.get(user.get('rol_id'))
            session["nombres"] = user.get('nombres')
            session["foto_perfil"] = user.get('foto_perfil')

            if session["rol"]:
                return redirect(url_for(f"app_routes.{session['rol'].lower()}_dashboard"))
            flash('Error: Usuario sin rol asignado.', 'error')
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
        return redirect(url_for('app_routes.login'))
    
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
        password = request.form['password']
        calle = request.form['calle']
        numero_ext = request.form['numero_ext']
        numero_int = request.form.get('numero_int', None)  # Puede ser opcional
        codigo_postal = request.form['codigo_postal']
        municipio = request.form['municipio']
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

    return render_template('admin/add_employee.html')




@app_routes.route('/admin/edit_employee/<int:empleado_id>', methods=['GET', 'POST'])
@require_role("Admin")
def edit_employee(empleado_id):
    # Lógica para obtener el empleado existente y permitir su edición
    if request.method == "POST":
        flash("Empleado actualizado correctamente", "success")
        return redirect(url_for("app_routes.manage_employees"))
    
    return render_template("admin/edit_employee.html", empleado_id=empleado_id)

@app_routes.route('/admin/delete_employee/<int:id>', methods=['POST'])
@require_role("Admin")
def delete_employee(id):
    print(f"Empleado con ID {id} eliminado")  # Solo para pruebas
    flash("Empleado eliminado correctamente", "success")
    return redirect(url_for('app_routes.manage_employees'))

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