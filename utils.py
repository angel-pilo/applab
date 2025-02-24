import os
from werkzeug.security import generate_password_hash
from supabase import create_client
from dotenv import load_dotenv

# Cargar las variables de entorno
load_dotenv()

# Obtener URL y clave de Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

# Crear el cliente de Supabase
supabase = create_client(supabase_url, supabase_key)

