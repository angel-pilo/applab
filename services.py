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
    """Obtiene una lista de empleados con los campos especificados."""
    try:
        # Consulta corregida con sintaxis válida para joins
        empleados_result = supabase.table('empleados').select(
            '''
            id,
            nombres,
            apellidos,
            usuario_id,
            contacto_emergencia,
            condiciones_medicas,
            fecha_nacimiento,
            usuario_id(estado_usuario),  
            empleado_roles(rol_id(id, nombre)) 
            '''
        ).execute()

        if not empleados_result.data:
            print("No se encontraron empleados.")
            return []

        empleados_con_datos = []
        for emp in empleados_result.data:
            # Extraer estado_usuario del join con usuarios
            estado_usuario = emp.get("usuario_id", {}).get("estado_usuario", False)
            
            # Extraer rol_id y nombre del rol
            roles = emp.get("empleado_roles", [{}])
            rol_data = roles[0].get("rol_id", {}) if roles else {}
            
            empleados_con_datos.append({
                "id": emp["id"],
                "nombres": emp["nombres"],
                "apellidos": emp["apellidos"],
                "usuario_id": emp["usuario_id"].get("id") if isinstance(emp["usuario_id"], dict) else emp["usuario_id"],
                "contacto_emergencia": emp["contacto_emergencia"],
                "condiciones_medicas": emp["condiciones_medicas"],
                "fecha_nacimiento": emp["fecha_nacimiento"],
                "estado": estado_usuario,
                "rol_id": rol_data.get("id"),
                "rol_nombre": rol_data.get("nombre", "Sin rol")
            })

        return empleados_con_datos

    except Exception as e:
        print(f"Error al obtener empleados: {e}")
        return []



