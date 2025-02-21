from supabase import create_client, Client
from flask import current_app

# Función para obtener el cliente de Supabase
def get_supabase_client() -> Client:
    url = current_app.config['SUPABASE_URL']  
    key = current_app.config['SUPABASE_KEY']  
    supabase = create_client(url, key)  
    return supabase
