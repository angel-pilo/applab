from werkzeug.security import check_password_hash
from supabase import create_client, Client
import os

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def verificar_usuario(usuario, password):
    # Llamar a la función de RPC que verifica el usuario y la contraseña
    result = supabase.rpc('check_user_password', {'p_username': usuario, 'p_password': password}).execute()
    
    # Verifica si el resultado tiene algún usuario
    if result.data and len(result.data) > 0:
        user = result.data[0]  # Obtén el primer resultado
        user_id = user['user_id']  # Cambia 'id' por 'user_id'
        
        # Obtén el rol del usuario
        rol_result = supabase.table('empleado_roles').select('rol_id').eq('empleado_id', user_id).execute()
        
        if rol_result.data:
            return user  # Devuelve el usuario con su rol
    return None  # Retorna None si no se encontró el usuario




