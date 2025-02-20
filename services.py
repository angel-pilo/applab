from werkzeug.security import check_password_hash
from supabase import create_client, Client
import os

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def verificar_usuario(usuario, password):
    result = supabase.rpc('check_user_password', {'p_username': usuario, 'p_password': password}).execute()
    
    if result.data and len(result.data) > 0:
        user = result.data[0]  # Obtén el primer resultado
        user_id = user['user_id']
        
        # Obtener el rol del usuario
        rol_result = supabase.table('empleado_roles').select('rol_id').eq('empleado_id', user_id).execute()
        
        if rol_result.data:
            rol_id = rol_result.data[0]['rol_id']
            
            # Obtener el nombre y foto del empleado
            empleado = supabase.table('empleados').select('nombres, foto_perfil').eq('id', user_id).execute()
            if empleado.data:
                user['nombres'] = empleado.data[0]['nombres']
                user['foto_perfil'] = empleado.data[0]['foto_perfil']
                user['rol_id'] = rol_id
                return user  # Devuelve el usuario con su rol
    return None





