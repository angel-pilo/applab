from werkzeug.security import check_password_hash
from supabase import create_client, Client
import os

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def verificar_usuario(usuario, password):
    # Llama a la función almacenada en Supabase
    result = supabase.rpc('check_user_password', {'p_username': usuario, 'p_password': password}).execute()
    
    # Imprimir el resultado para depuración
    print("Resultado de Supabase:", result.data)

    # Verifica si el resultado contiene datos
    if result.data and isinstance(result.data, list) and len(result.data) > 0:
        # Retorna el primer resultado (el objeto del usuario)
        return result.data[0]
    
    return None


