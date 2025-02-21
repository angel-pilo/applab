from flask import render_template, request, redirect, session, url_for, Blueprint, flash
from functools import wraps  # Importa wraps
from services import verificar_usuario, obtener_empleados
from utils import add_user_and_employee

app_routes = Blueprint('app_routes', __name__)

role_map = {
    1: "Admin",
    2: "Mostrador",
    3: "Enfermero",
    4: "Quimico"
}

def require_role(role):
    """ Decorador para verificar el rol del usuario """
    def decorator(f):
        @wraps(f)  # Usa wraps para mantener el nombre original
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
    empleados = obtener_empleados()  # Obtiene la lista de empleados

    if request.method == "POST":
        # Aquí puedes manejar la lógica para añadir un empleado si es necesario
        flash("Empleado añadido correctamente", "success")
        return redirect(url_for("app_routes.manage_employees"))
    
    return render_template("admin/employees.html", empleados=empleados)


@app_routes.route("/admin/add_employee", methods=["GET", "POST"])
@require_role("Admin")
def add_employee():
    if request.method == "POST":
        # Obtener datos del formulario
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        birthdate = request.form.get("birthdate")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")

        # Validaciones básicas
        if not all([first_name, last_name, birthdate, email, phone, password]):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("app_routes.add_employee"))

        # Usar la función para guardar los datos
        _, message = add_user_and_employee(first_name, last_name, birthdate, email, phone, password)
        flash(message, "success" if "correctamente" in message else "danger")

        return redirect(url_for("app_routes.manage_employees"))

    return render_template("admin/add_employee.html")

@app_routes.route('/admin/edit_employee/<int:empleado_id>', methods=['GET', 'POST'])
@require_role("Admin")
def edit_employee(empleado_id):
    # Lógica para obtener el empleado existente y permitir su edición
    # Aquí puedes usar 'empleado_id' para buscar al empleado en la base de datos
    if request.method == "POST":
        # Lógica para guardar los cambios del empleado
        flash("Empleado actualizado correctamente", "success")
        return redirect(url_for("app_routes.manage_employees"))
    
    # Renderiza la plantilla para editar al empleado, pasando los datos del empleado
    return render_template("admin/edit_employee.html", empleado_id=empleado_id)

@app_routes.route('/admin/delete_employee/<int:id>', methods=['POST'])
@require_role("Admin")
def delete_employee(id):
    # Lógica para eliminar el empleado con el ID proporcionado
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
