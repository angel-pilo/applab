from flask import render_template, request, redirect, session, url_for, Blueprint, flash
from services import verificar_usuario

app_routes = Blueprint('app_routes', __name__)

role_map = {
    1: "Admin",
    2: "Mostrador",
    3: "Enfermero",
    4: "Quimico"
}

@app_routes.route("/")
def home():
    if "usuario" in session:
        rol = session.get("rol", "").lower()
        if rol in ["admin", "mostrador", "enfermero", "quimico"]:
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
            session["rol"] = role_map.get(user.get('rol_id'), None)
            session["nombres"] = user.get('nombres')
            session["foto_perfil"] = user.get('foto_perfil')

            if session["rol"]:
                return redirect(url_for(f"app_routes.{session['rol'].lower()}_dashboard"))
            else:
                flash('Error: Usuario sin rol asignado.', 'error')
                return redirect(url_for('app_routes.login'))

        flash('Usuario o contraseña incorrectos.', 'error')
        return redirect(url_for('app_routes.login'))
    
    return render_template('auth/login.html')

@app_routes.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('app_routes.home'))

# Rutas para cada rol
@app_routes.route("/admin")
def admin_dashboard():
    if session.get("rol") == "Admin":
        return render_template("admin/admin.html")
    return redirect(url_for("app_routes.login"))

@app_routes.route("/admin/employees", methods=["GET", "POST"])
def manage_employees():
    if session.get("rol") != "Admin":
        return redirect(url_for("app_routes.login"))
    if request.method == "POST":
        flash("Empleado añadido correctamente", "success")
        return redirect(url_for("app_routes.manage_employees"))

    return render_template("admin/employees.html")

@app_routes.route("/admin/add_employee", methods=["GET", "POST"])
def add_employee():
    if session.get("rol") == "Admin":
        if request.method == "POST":
            # Lógica para guardar el nuevo empleado en la base de datos
            flash("Empleado añadido correctamente", "success")
            return redirect(url_for("app_routes.manage_employees"))
        
        return render_template("admin/add_employee.html")
    
    return redirect(url_for("app_routes.login"))

@app_routes.route('/admin/delete_employee/<int:id>', methods=['POST', 'GET'])
def delete_employee(id):
    print(f"Empleado con ID {id} eliminado")  # Solo para pruebas
    return redirect(url_for('app_routes.manage_employees'))  # Redirige de vuelta a la lista de empleados

@app_routes.route("/mostrador")
def mostrador_dashboard():
    if session.get("rol") == "Mostrador":
        return render_template("mostrador/mostrador.html")
    return redirect(url_for("app_routes.login"))

@app_routes.route("/enfermero")
def enfermero_dashboard():
    if session.get("rol") == "Enfermero":
        return render_template("enfermero/enfermero.html")
    return redirect(url_for("app_routes.login"))

@app_routes.route("/quimico")
def quimico_dashboard():
    if session.get("rol") == "Quimico":
        return render_template("quimico/quimico.html")
    return redirect(url_for("app_routes.login"))
