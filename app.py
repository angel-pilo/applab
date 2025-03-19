from flask import Flask, session
from dotenv import load_dotenv
import os
import bcrypt
from supabase import create_client, Client

# Cargar las variables de entorno
load_dotenv()

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

# Verifica que las variables se hayan cargado correctamente
if url is None or key is None:
    raise ValueError("Las variables de entorno SUPABASE_URL y SUPABASE_KEY deben estar definidas")

# Crear la instancia de la aplicación Flask
app = Flask(__name__)

# Agrega la clave secreta
app.secret_key = 'supersecreto'

# Definir los ítems de la sidebar según el rol, evitando `"#"` en `url`
role_sidebar_items = {
    "Admin": [
        {"icon": "fa-home", "text": "Inicio", "url": "app_routes.admin_dashboard"},
        {"icon": "fa-users", "text": "Gestión de Empleados", "url": "app_routes.manage_employees"},
        {"icon": "fa-chart-bar", "text": "Reportes", "url": "app_routes.reportes"},
        {"icon": "fa-cog", "text": "Configuración", "url": "app_routes.configuracion"}
    ],
    "Mostrador": [
        {"icon": "fa-home", "text": "Inicio", "url": "app_routes.mostrador_dashboard"},
        {"icon": "fa-file-alt", "text": "Faltantes de Reportar", "url": "app_routes.faltantes"}
    ],
    "Enfermero": [
        {"icon": "fa-home", "text": "Inicio", "url": "app_routes.enfermero_dashboard"},
        {"icon": "fa-user-nurse", "text": "Pacientes", "url": "app_routes.pacientes"}
    ],
    "Quimico": [
        {"icon": "fa-home", "text": "Inicio", "url": "app_routes.quimico_dashboard"},
        {"icon": "fa-vials", "text": "Resultados de Laboratorio", "url": "app_routes.resultados"}
    ]
}

# Registrar la variable en el contexto global
@app.context_processor
def inject_sidebar_items():
    return {"role_sidebar_items": role_sidebar_items}

# Importar y registrar las rutas
from routes import app_routes
app.register_blueprint(app_routes)

# Iniciar la aplicación solo si este archivo se ejecuta directamente
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))  # Usa el puerto asignado por Heroku
    app.run(host='0.0.0.0', port=port, debug=True)  # Configura el host y puerto dinámicos
