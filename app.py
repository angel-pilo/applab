from flask import Flask
from dotenv import load_dotenv
import os
import bcrypt

# Cargar las variables de entorno
load_dotenv()

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')

# Verifica que las variables se hayan cargado correctamente
if url is None or key is None:
    raise ValueError("Las variables de entorno SUPABASE_URL y SUPABASE_KEY deben estar definidas")

from supabase import create_client, Client
supabase: Client = create_client(url, key)

# Crear la instancia de la aplicación Flask
app = Flask(__name__)

# Agrega la clave secreta
app.secret_key = 'supersecreto'  

# Importar y registrar las rutas
from routes import app_routes
app.register_blueprint(app_routes)

# Iniciar la aplicación solo si este archivo se ejecuta directamente
if __name__ == "__main__":
    app.run(debug=True)
