from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'  # Necesario para las sesiones

# Conexión a la base de datos Supabase
DB_URL = "postgresql://postgres.wuigomoezwsihmvxyhah:Angelitopilo14201#@aws-0-us-west-1.pooler.supabase.com:6543/postgres"
conn = psycopg2.connect(DB_URL)

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cur = conn.cursor()
        cur.execute("SELECT id, password FROM usuarios WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[1], password):
            session['user_id'] = user[0]  # Guardamos el usuario en sesión
            flash("Inicio de sesión exitoso", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return "Bienvenido al sistema"

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("Sesión cerrada", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
