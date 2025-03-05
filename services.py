from supabase import create_client, Client
import os
import bcrypt

# Inicializa la conexión a Supabase
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

def verificar_usuario(usuario, password):
    """Verifica si un usuario existe y su contraseña es correcta."""
    try:
        # Obtiene el usuario por nombre de usuario
        result = supabase.table('usuarios').select('id, password').eq('username', usuario).execute()

        if result.data and len(result.data) > 0:
            user = result.data[0]
            user_id = user['id']
            hashed_password = user['password']

            # Verifica la contraseña utilizando bcrypt
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
                # Obtener el empleado correspondiente al usuario
                empleado_result = supabase.table('empleados').select('id').eq('usuario_id', user_id).execute()

                if empleado_result.data:
                    empleado_id = empleado_result.data[0]['id']

                    # Obtener el rol del empleado
                    rol_result = supabase.table('empleado_roles').select('rol_id').eq('empleado_id', empleado_id).execute()

                    if not rol_result.data:
                        return None  # Usuario sin rol

                    rol_id = rol_result.data[0]['rol_id']

                    # Obtener información adicional del empleado
                    empleado_info = supabase.table('empleados').select('nombres, foto_perfil').eq('usuario_id', user_id).execute()
                    if empleado_info.data:
                        user.update({
                            'nombres': empleado_info.data[0]['nombres'],
                            'foto_perfil': empleado_info.data[0]['foto_perfil'],
                            'rol_id': rol_id
                        })
                        return user

    except Exception:
        return None
    
    return None


def obtener_empleados():
    """Obtiene una lista de empleados junto con sus roles y estado."""
    try:
        # Obtiene los empleados junto con sus roles
        empleados_result = supabase \
            .table('empleados') \
            .select('id, nombres, apellidos, usuario_id, empleado_roles(rol_id)') \
            .execute()

        if not empleados_result.data:
            print("No se encontraron empleados.")  # Mensaje para depuración
            return []  # Retorna una lista vacía si no hay empleados
        
        # Crea una lista para almacenar los empleados con estado
        empleados_con_estado = []

        for emp in empleados_result.data:
            # Obtiene el estado del usuario correspondiente al empleado
            usuario_result = supabase \
                .table('usuarios') \
                .select('estado_usuario') \
                .eq('id', emp['usuario_id']) \
                .execute()

            # Verifica si se encontró el usuario
            estado_usuario = usuario_result.data[0]['estado_usuario'] if usuario_result.data else False

            empleados_con_estado.append({
                "id": emp['id'],
                "nombres": emp['nombres'],
                "apellidos": emp['apellidos'],
                "rol_id": emp['empleado_roles'][0]['rol_id'] if emp['empleado_roles'] else None,
                "estado": estado_usuario
            })

        return empleados_con_estado
    
    except Exception as e:
        print(f"Error al obtener empleados: {e}")  # Imprimir error para depuración
        return []



