from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecreto")

# Configuración de la base de datos PostgreSQL
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "applab")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "password")

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST, 
        database=DB_NAME, 
        user=DB_USER, 
        password=DB_PASS, 
        cursor_factory=RealDictCursor
    )

# Ruta principal - Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password, role_id FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role_id'] = user['role_id']
            
            flash('Inicio de sesión exitoso', 'success')

            # Redirigir según el rol
            if user['role_id'] == 1:
                return redirect(url_for('admin_dashboard'))
            elif user['role_id'] == 2:
                return redirect(url_for('quimico_dashboard'))
            elif user['role_id'] == 3:
                return redirect(url_for('enfermero_dashboard'))
            elif user['role_id'] == 4:
                return redirect(url_for('mostrador_dashboard'))
            else:
                flash('Rol desconocido', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    
    return render_template('login.html')

# Rutas de los Dashboards según el rol del usuario
@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role_id'] != 1:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/quimico')
def quimico_dashboard():
    if 'user_id' not in session or session['role_id'] != 2:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))
    return render_template('quimico.html')

@app.route('/enfermero')
def enfermero_dashboard():
    if 'user_id' not in session or session['role_id'] != 3:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))
    return render_template('enfermero.html')

@app.route('/mostrador')
def mostrador_dashboard():
    if 'user_id' not in session or session['role_id'] != 4:
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('login'))
    return render_template('mostrador.html')

# Ruta para cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'success')
    return redirect(url_for('login'))

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run(debug=True)
