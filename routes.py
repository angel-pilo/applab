from flask import render_template, request, redirect, session, url_for, Blueprint, flash
from services import verificar_usuario

app_routes = Blueprint('app_routes', __name__)

# Mapeo de role_id a nombres de roles
role_map = {
    1: "Admin",
    2: "Mostrador",
    3: "Enfermero",
    4: "Quimico"
}

@app_routes.route("/")
def home():
    if "usuario" in session:
        rol = session["rol"]
        return redirect(url_for(f"{rol.lower()}_dashboard"))  # Redirigir según el rol del usuario en minúsculas
    return redirect(url_for("app_routes.login"))  # Redirigir al login si no hay sesión

@app_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['username']
        password = request.form['password']
        user = verificar_usuario(usuario, password)
        if user:
            session["usuario"] = usuario
            session["rol"] = role_map.get(user['rol_id'], "default")  # Mapeo de rol_id a nombre de rol con mayúscula
            session["nombres"] = user['nombres']  # Agregar nombre del empleado
            session["foto_perfil"] = user['foto_perfil']  # Agregar foto del empleado
            return redirect(url_for('app_routes.' + f"{session['rol'].lower()}_dashboard"))  
        else:
            flash('Usuario o contraseña incorrectos.', 'error')
            return redirect(url_for('app_routes.login'))
    return render_template('auth/login.html')

@app_routes.route("/logout")
def logout():
    # Lógica para cerrar sesión, como limpiar la sesión del usuario
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('app_routes.home'))  

@app_routes.route("/admin")
def admin_dashboard():
    if session.get("rol") == "Admin":
        return render_template("admin/admin.html")  
    return redirect(url_for("app_routes.login"))

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

@app_routes.route("/admin/add_employee")
def add_employee():
    # Lógica para mostrar el formulario de agregar empleado
    if session.get("rol") == "Admin":
        return render_template("admin/add_employee.html")  
    return redirect(url_for("app_routes.login"))
