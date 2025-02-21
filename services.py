from supabase import create_client, Client
import os

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def verificar_usuario(usuario, password):
    result = supabase.rpc('check_user_password', {'p_username': usuario, 'p_password': password}).execute()
    
    if result.data and len(result.data) > 0:
        user = result.data[0]  
        user_id = user['user_id']
        
        rol_result = supabase.table('empleado_roles').select('rol_id').eq('empleado_id', user_id).execute()
        
        if not rol_result.data:
            return None  # Usuario sin rol

        rol_id = rol_result.data[0]['rol_id']
        
        empleado = supabase.table('empleados').select('nombres, foto_perfil').eq('id', user_id).execute()
        if empleado.data:
            user.update({
                'nombres': empleado.data[0]['nombres'],
                'foto_perfil': empleado.data[0]['foto_perfil'],
                'rol_id': rol_id
            })
            return user

    return None

def obtener_empleados():
    # Consulta para obtener empleados junto con sus roles
    result = supabase \
        .table('empleados') \
        .select('id, nombres, apellidos, empleado_roles(rol_id)') \
        .execute()

    # Imprime para depuración
    print(result.data)  
    
    # Verifica si se obtuvieron resultados
    if not result.data:
        return []  # Retorna una lista vacía si no hay empleados
    
    # Retorna una lista de diccionarios
    return [
        {
            "id": emp['id'],
            "nombres": emp['nombres'],
            "apellidos": emp['apellidos'],
            "rol_id": emp['empleado_roles'][0]['rol_id'] if emp['empleado_roles'] else None
        } 
        for emp in result.data
    ]

