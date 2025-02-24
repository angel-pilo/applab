import os
import io
import bcrypt

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from functools import wraps
from services import obtener_empleados, verificar_usuario
from supabase import Client, create_client
from utils import *
from werkzeug.security import generate_password_hash
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

@app_routes.route("/admin/add_employee", methods=["GET", "POST"])
@require_role("Admin")
def add_employee():
    if request.method == "POST":
        print(request.form)
        # Obtener los datos del formulario
        tipo_empleado = request.form['tipo_empleado']
        sexo = request.form.get('sexo')
        if not sexo:
            return "No se seleccionó el sexo", 400
        fecha_nacimiento = request.form['fecha_nacimiento']
        nombres = request.form['nombres']
        apellidos = request.form['apellidos']
        telefono = request.form['telefono']
        correo = request.form['correo']
        username = request.form['username']
        password = request.form['password']  # Considera encriptar esta contraseña
        calle = request.form['calle']
        numero_ext = request.form['numero_ext']
        numero_int = request.form['numero_int']
        codigo_postal = request.form['codigo_postal']
        municipio = request.form['municipio']
        curp_rfc = request.form['curp_rfc']
        turno = request.form['turno']
        condiciones_medicas = request.form['condiciones_medicas']
        contacto_emergencia = request.form['contacto_emergencia']

        # Paso 1: Inserta el nuevo usuario en la tabla `usuarios`
        user_data = {
            "username": username,
            "password": password  # Recuerda encriptar la contraseña
        }

        user_response = supabase.table('usuarios').insert(user_data).execute()

        if user_response.status_code != 201:  # Verifica si la inserción fue exitosa
            return f"Error al agregar usuario: {user_response.data}", user_response.status_code

        # Obtener el ID del nuevo usuario
        usuario_id = user_response.data[0]['id']  # Asegúrate de que la respuesta contiene el ID

        # Paso 2: Prepara los datos del empleado, incluyendo el usuario_id
        employee_data = {
            "tipo_empleado": tipo_empleado,
            "sexo": sexo,
            "fecha_nacimiento": fecha_nacimiento,
            "nombres": nombres,
            "apellidos": apellidos,
            "telefono": telefono,
            "correo": correo,
            "usuario_id": usuario_id,  # Asigna el ID del usuario aquí
            "calle": calle,
            "numero_ext": numero_ext,
            "numero_int": numero_int,
            "codigo_postal": codigo_postal,
            "municipio": municipio,
            "curp_rfc": curp_rfc,
            "turno": turno,
            "condiciones_medicas": condiciones_medicas,
            "contacto_emergencia": contacto_emergencia
        }

        # Inserta el nuevo empleado en la tabla `empleados`
        employee_response = supabase.table('empleados').insert(employee_data).execute()

        if employee_response.status_code == 201:  # Verifica si la inserción fue exitosa
            return redirect(url_for('admin.success'))  # Redirige a una página de éxito o similar
        else:
            return f"Error al agregar empleado: {employee_response.data}", employee_response.status_code

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