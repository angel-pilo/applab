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
        
        # Comprueba si se encontró el usuario
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
                        print("El usuario no tiene rol asignado.")  # Mensaje indicando que no hay rol
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
                        print("Resultado de check_user_password:", user)
                        return user

            else:
                print("Contraseña incorrecta.")

    except Exception as e:
        print(f"Error en verificar_usuario: {e}")
    
    return None




def obtener_empleados():
    """Obtiene una lista de empleados junto con sus roles."""
    try:
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
    
    except Exception as e:
        print(f"Error en obtener_empleados: {e}")
        return []
