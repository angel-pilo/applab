from supabase import create_client, Client
from flask import current_app

# Función para obtener el cliente de Supabase
def get_supabase_client() -> Client:
    url = current_app.config['SUPABASE_URL']  # URL de Supabase desde la configuración
    key = current_app.config['SUPABASE_KEY']  # Clave de Supabase desde la configuración
    supabase = create_client(url, key)  # Crear el cliente con las credenciales
    return supabase
