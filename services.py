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


def crear_hospital(nombre, telefono, correo, calle, numero_ext, numero_int, codigo_postal, municipio, estado, anotaciones):
    """Registra un nuevo hospital en la base de datos"""
    try:
        hospital_data = {
            "nombre": nombre,
            "telefono": telefono,
            "correo": correo,
            "calle": calle,
            "numero_ext": numero_ext,
            "numero_int": numero_int,
            "codigo_postal": codigo_postal,
            "municipio": municipio,
            "estado": estado,
            "anotaciones": anotaciones,
            "activo": True
        }
        response = supabase.table('hospitales').insert(hospital_data).execute()
        return response.data
    except Exception as e:
        print(f"Error al crear hospital: {e}")
        return None

def obtener_hospitales():
    """Obtiene todos los hospitales activos"""
    try:
        response = supabase.table('hospitales').select('*').execute()
        return response.data
    except Exception as e:
        print(f"Error al obtener hospitales: {e}")
        return []

def obtener_hospital_por_id(hospital_id):
    """Obtiene un hospital por su ID"""
    try:
        response = supabase.table('hospitales').select('*').eq('id', hospital_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error al obtener hospital: {e}")
        return None

def actualizar_hospital(hospital_id, nombre, telefono, correo, calle, numero_ext, numero_int, codigo_postal, municipio, estado, anotaciones):
    """Actualiza la información de un hospital"""
    try:
        hospital_data = {
            "nombre": nombre,
            "telefono": telefono,
            "correo": correo,
            "calle": calle,
            "numero_ext": numero_ext,
            "numero_int": numero_int,
            "codigo_postal": codigo_postal,
            "municipio": municipio,
            "estado": estado,
            "anotaciones": anotaciones
        }
        response = supabase.table('hospitales').update(hospital_data).eq('id', hospital_id).execute()
        return response.data
    except Exception as e:
        print(f"Error al actualizar hospital: {e}")
        return None

def eliminar_hospital(hospital_id):
    """Desactiva un hospital en la base de datos"""
    try:
        response = supabase.table('hospitales').update({"activo": False}).eq('id', hospital_id).execute()
        return response.data
    except Exception as e:
        print(f"Error al eliminar hospital: {e}")
        return None
    
def crear_doctor(data):
    try:
        response = supabase.table('doctores').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al crear doctor: {e}")
        return None


def obtener_doctores():
    try:
        response = supabase.table('doctores').select(
            '''
            id,
            nombres,
            apellidos,
            telefono,
            correo,
            tipo_consultorio,
            calle,
            numero_ext,
            numero_int,
            codigo_postal,
            municipio,
            estado,
            anotaciones,
            activo,
            hospital_id(id, nombre)
            '''
        ).execute()

        doctores = response.data if response.data else []
        for d in doctores:
            if d.get("hospital_id"):
                d["hospital_nombre"] = d["hospital_id"]["nombre"]
                d["hospital_id"] = d["hospital_id"]["id"]
            else:
                d["hospital_nombre"] = None
        return doctores

    except Exception as e:
        print(f"Error al obtener doctores: {e}")
        return []


def actualizar_doctor(doctor_id, data):
    try:
        response = supabase.table('doctores').update(data).eq('id', doctor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al actualizar doctor: {e}")
        return None


def desactivar_doctor(doctor_id):
    """Desactiva (elimina lógicamente) al doctor"""
    try:
        response = supabase.table('doctores').update({'activo': False}).eq('id', doctor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al desactivar doctor: {e}")
        return None


def activar_doctor(doctor_id):
    """Activa a un doctor previamente desactivado"""
    try:
        response = supabase.table('doctores').update({'activo': True}).eq('id', doctor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al activar doctor: {e}")
        return None

# Crear paciente (sin validación)
def crear_paciente(data):
    try:
        response = supabase.table('pacientes').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al crear paciente: {e}")
        return None

# Crear paciente (con validación de duplicado)
def crear_paciente_seguro(data):
    if paciente_duplicado(data['nombres'], data['apellidos'], data['telefono'], data['correo']):
        return False, "Ya existe un paciente con estos datos."
    
    paciente = crear_paciente(data)
    return True, paciente

# Obtener todos los pacientes
def obtener_pacientes():
    try:
        response = supabase.table('pacientes').select(
            'id, nombres, apellidos, telefono, correo, activo'
        ).execute()
        return response.data or []
    except Exception as e:
        print(f"Error al obtener pacientes: {e}")
        return []

# Obtener paciente por ID
def obtener_paciente_por_id(paciente_id):
    try:
        response = supabase.table('pacientes').select("*").eq("id", paciente_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error al obtener paciente por ID: {e}")
        return None

# Actualizar paciente (sin validación)
def actualizar_paciente(paciente_id, data):
    try:
        response = supabase.table('pacientes').update(data).eq("id", paciente_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al actualizar paciente: {e}")
        return None

# Actualizar paciente (con validación de duplicado)
def actualizar_paciente_seguro(paciente_id, data):
    try:
        respuesta = supabase.table("pacientes").select("id").or_(
            f"nombres.ilike.%{data['nombres']}%,apellidos.ilike.%{data['apellidos']}%,telefono.eq.{data['telefono']},correo.eq.{data['correo']}"
        ).neq("id", paciente_id).execute()

        if respuesta.data:
            return False, "Otro paciente ya tiene estos datos."

        paciente = actualizar_paciente(paciente_id, data)
        return True, paciente
    except Exception as e:
        print(f"Error al validar duplicado en actualización: {e}")
        return False, "Error en validación de datos."

# Eliminar (desactivar)
def eliminar_paciente(paciente_id):
    try:
        response = supabase.table('pacientes').update({"activo": False}).eq("id", paciente_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al eliminar paciente: {e}")
        return None

# Activar
def activar_paciente(paciente_id):
    try:
        response = supabase.table('pacientes').update({"activo": True}).eq("id", paciente_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al activar paciente: {e}")
        return None

# Verificar duplicados
def paciente_duplicado(nombres, apellidos, telefono, correo):
    try:
        response = supabase.table("pacientes").select("id").or_(
            f"nombres.ilike.%{nombres}%,apellidos.ilike.%{apellidos}%,telefono.eq.{telefono},correo.eq.{correo}"
        ).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error en verificación de duplicado: {e}")
        return False

