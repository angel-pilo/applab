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

def obtener_doctor_por_id(doctor_id: int):
    try:
        response = (
            supabase.table("doctores")
            .select("*")
            .eq("id", doctor_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"Error al obtener doctor {doctor_id}:", e)
        return None
    

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

# Crear proveedor (sin validación)
def crear_proveedor(data):
    try:
        response = supabase.table('proveedores').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al crear proveedor: {e}")
        return None

# Crear proveedor (con validación)
def crear_proveedor_seguro(data):
    if proveedor_duplicado(data['nombre'], data['telefono'], data['correo']):
        return False, "Ya existe un proveedor con estos datos."
    
    proveedor = crear_proveedor(data)
    return True, proveedor

# Obtener todos los proveedores
def obtener_proveedores():
    try:
        response = supabase.table('proveedores').select(
            'id, nombre, tipo, telefono, correo, activo'
        ).execute()
        return response.data or []
    except Exception as e:
        print(f"Error al obtener proveedores: {e}")
        return []

# Obtener proveedor por ID
def obtener_proveedor_por_id(proveedor_id):
    try:
        response = supabase.table('proveedores').select("*").eq("id", proveedor_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error al obtener proveedor por ID: {e}")
        return None

# Actualizar proveedor (sin validación)
def actualizar_proveedor(proveedor_id, data):
    try:
        response = supabase.table('proveedores').update(data).eq('id', proveedor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al actualizar proveedor: {e}")
        return None

# Actualizar proveedor (con validación)
def actualizar_proveedor_seguro(proveedor_id, data):
    try:
        respuesta = supabase.table("proveedores").select("id").or_(
            f"nombre.ilike.%{data['nombre']}%,telefono.eq.{data['telefono']},correo.eq.{data['correo']}"
        ).neq("id", proveedor_id).execute()

        if respuesta.data:
            return False, "Otro proveedor ya tiene estos datos."

        proveedor = actualizar_proveedor(proveedor_id, data)
        return True, proveedor
    except Exception as e:
        print(f"Error al validar duplicado en actualización: {e}")
        return False, "Error en validación de datos."

# Eliminar (desactivar)
def desactivar_proveedor(proveedor_id):
    try:
        response = supabase.table('proveedores').update({'activo': False}).eq('id', proveedor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al desactivar proveedor: {e}")
        return None

# Activar
def activar_proveedor(proveedor_id):
    try:
        response = supabase.table('proveedores').update({'activo': True}).eq('id', proveedor_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al activar proveedor: {e}")
        return None
    
def proveedor_duplicado(nombre, telefono, correo):
    try:
        response = supabase.table("proveedores").select("id").or_(
            f"nombre.ilike.%{nombre}%,telefono.eq.{telefono},correo.eq.{correo}"
        ).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error en verificación de duplicado: {e}")
        return False
    
#reactivos
# Obtener todos los reactivos
def obtener_reactivos():
    try:
        response = supabase.table('reactivos').select('*').execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error al obtener reactivos: {e}")
        return []

# Validar si ya existe un reactivo con el mismo nombre y proveedor
def reactivo_duplicado(nombre, proveedor_id):
    try:
        response = supabase.table("reactivos").select("id").eq("nombre", nombre).eq("proveedor_id", proveedor_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Error al verificar duplicado de reactivo: {e}")
        return False

# Crear un nuevo reactivo
def crear_reactivo(data):
    try:
        # Insertar el nuevo reactivo en la base de datos
        response = supabase.table('reactivos').insert(data).execute()

        if response.data and len(response.data) > 0:
            return True, "Reactivo creado exitosamente"
        else:
            return False, "No se pudo crear el reactivo"
    except Exception as e:
        print(f"Error al crear reactivo: {e}")
        return False, f"Error al crear el reactivo: {e}"


def obtener_reactivo_por_id(reactivo_id):
    try:
        response = supabase.table('reactivos').select('*').eq('id', reactivo_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error al obtener el reactivo por ID: {e}")
        return None

# Actualizar un reactivo
def actualizar_reactivo(reactivo_id, data):
    try:
        response = supabase.table('reactivos').update(data).eq('id', reactivo_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al actualizar reactivo: {e}")
        return None

def crear_prueba(nombre, tipo):
    try:
        data = {
            "nombre": nombre,
            "tipo": tipo,
            "activo": True
        }
        response = supabase.table('pruebas_clinicas').insert(data).execute()
        if response.error:
            print(f"Error en crear_prueba: {response.error}")
            return None
        return response.data
    except Exception as e:
        print(f"Error al crear prueba clínica: {e}")
        return None


def asignar_reactivos_a_prueba(prueba_id, lista_reactivos_ids):
    try:
        data = [{"prueba_id": prueba_id, "reactivo_id": int(rid)} for rid in lista_reactivos_ids]
        response = supabase.table('pruebas_reactivos').insert(data).execute()
        if response.error:
            print(f"Error en asignar_reactivos_a_prueba: {response.error}")
            return None
        return response.data
    except Exception as e:
        print(f"Error al asignar reactivos: {e}")
        return None


def obtener_pruebas():
    """
    Obtiene todas las pruebas clínicas desde Supabase y agrega,
    si existen, los nombres de los reactivos relacionados.
    """
    try:
        # Traer todas las pruebas (puedes agregar .eq("activo", True) si quieres solo activas)
        response = (
            supabase
            .table("pruebas_clinicas")
            .select("*")
            .order("id", desc=False)
            .execute()
        )

        pruebas_data = response.data or []

        # Para cada prueba, traer sus reactivos (opcional)
        for prueba in pruebas_data:
            try:
                rel_resp = (
                    supabase
                    .table("pruebas_reactivos")
                    .select("reactivo_id(nombre)")
                    .eq("prueba_id", prueba["id"])
                    .execute()
                )
                relacion_data = rel_resp.data or []

                prueba["reactivos"] = [
                    r["reactivo_id"]["nombre"]
                    for r in relacion_data
                    if r.get("reactivo_id")
                ]
            except Exception as e:
                print(f"Error al obtener reactivos para prueba {prueba['id']}: {e}")
                prueba["reactivos"] = []

        return pruebas_data

    except Exception as e:
        print(f"Error al obtener pruebas clínicas: {e}")
        return []


def obtener_prueba_por_id(prueba_id):
    try:
        prueba = supabase.table('pruebas_clinicas').select('*').eq('id', prueba_id).single().execute()
        if prueba.error or not prueba.data:
            print(f"Error o prueba no encontrada: {prueba.error}")
            return None
        prueba_data = prueba.data
        
        relacion = supabase.table('pruebas_reactivos').select('reactivo_id').eq('prueba_id', prueba_id).execute()
        if relacion.error:
            print(f"Error al obtener reactivos para prueba {prueba_id}: {relacion.error}")
            prueba_data['reactivos'] = []
        else:
            prueba_data['reactivos'] = [r['reactivo_id'] for r in relacion.data] if relacion.data else []
        
        valores = supabase.table('valores_normales').select('*').eq('prueba_id', prueba_id).execute()
        if valores.error:
            print(f"Error al obtener valores normales para prueba {prueba_id}: {valores.error}")
            prueba_data['valores_normales'] = []
        else:
            prueba_data['valores_normales'] = valores.data if valores.data else []
        
        return prueba_data
    except Exception as e:
        print(f"Error al obtener prueba por ID: {e}")
        return None


def actualizar_prueba(prueba_id, nombre, tipo):
    try:
        data = {
            "nombre": nombre,
            "tipo": tipo
        }
        response = supabase.table('pruebas_clinicas').update(data).eq('id', prueba_id).execute()
        if response.error:
            print(f"Error en actualizar_prueba: {response.error}")
            return None
        return response.data
    except Exception as e:
        print(f"Error al actualizar prueba clínica: {e}")
        return None


def actualizar_reactivos_de_prueba(prueba_id, lista_reactivos_ids):
    try:
        del_response = supabase.table('pruebas_reactivos').delete().eq('prueba_id', prueba_id).execute()
        if del_response.error:
            print(f"Error eliminando reactivos previos: {del_response.error}")
            return None
        return asignar_reactivos_a_prueba(prueba_id, lista_reactivos_ids)
    except Exception as e:
        print(f"Error al actualizar reactivos: {e}")
        return None


def crear_valor_normal(prueba_id, nombre, tipo_separacion, estructura_json):
    try:
        data = {
            "prueba_id": prueba_id,
            "nombre": nombre,
            "tipo_separacion": tipo_separacion,
            "estructura": estructura_json
        }
        response = supabase.table('valores_normales').insert(data).execute()
        if response.error:
            print(f"Error en crear_valor_normal: {response.error}")
            return None
        return response.data
    except Exception as e:
        print(f"Error al crear valor normal: {e}")
        return None

def obtener_todos_los_reactivos():
    try:
        response = supabase.table('reactivos').select('id,nombre').eq('activo', True).order('nombre').execute()
        # Intenta acceder al atributo error de forma segura:
        if hasattr(response, 'error') and response.error:
            print(f"Error en obtener_todos_los_reactivos: {response.error}")
            return []
        # En caso que no tenga error, pero data sea None
        if not response.data:
            print("No se recibieron datos de reactivos")
            return []
        return response.data
    except Exception as e:
        print(f"Error al obtener reactivos: {e}")
        return []


#para validar para orden
def existe_paciente_activo(paciente_id):
    try:
        res = supabase.table('pacientes').select('id, activo').eq('id', paciente_id).single().execute()
        if not res.data:
            return False
        # si no existe campo 'activo' lo consideramos True por compatibilidad
        return res.data.get('activo', True) is True
    except Exception:
        return False

def existe_hospital_activo(hospital_id):
    try:
        res = supabase.table('hospitales').select('id, activo').eq('id', hospital_id).single().execute()
        if not res.data:
            return False
        return res.data.get('activo', True) is True
    except Exception:
        return False

def existe_doctor_activo(doctor_id):
    try:
        res = supabase.table('doctores').select('id, activo').eq('id', doctor_id).single().execute()
        if not res.data:
            return False
        return res.data.get('activo', True) is True
    except Exception:
        return False


def guardar_orden_en_bd(orden: dict, pruebas: list[dict], empleado_id: int | None = None) -> int:
    total_pruebas = 0.0
    for p in pruebas:
        try:
            total_pruebas += float(p.get("precio", 0))
        except (TypeError, ValueError):
            continue

    data_orden = {
        "paciente_id": int(orden["patient_id"]),
        "doctor_id": int(orden["doctor_id"]),
        "hospital_id": int(orden["hospital_id"]),
        "cuarto": orden["cuarto"],
        "observaciones": orden.get("observaciones") or None,
        "total_pruebas": total_pruebas,
        "total_abonos": 0,
        "estado": "pendiente",
        "creado_por_empleado_id": empleado_id,
    }

    resp = supabase.table("ordenes").insert(data_orden).execute()
    if not resp.data:
        raise RuntimeError("No se pudo insertar la orden.")

    orden_id = resp.data[0]["id"]

    detalles = []
    for p in pruebas:
        try:
            cantidad = int(p.get("cantidad", 1))
        except (TypeError, ValueError):
            cantidad = 1

        try:
            precio_unit = float(p.get("precio_unitario", p.get("precio", 0)))
        except (TypeError, ValueError):
            precio_unit = 0.0

        try:
            precio_total = float(p.get("precio", precio_unit * cantidad))
        except (TypeError, ValueError):
            precio_total = precio_unit * cantidad

        detalles.append(
            {
                "orden_id": orden_id,
                "prueba_id": int(p["prueba_id"]) if p.get("prueba_id") else None,
                "nombre_prueba": p.get("prueba"),
                "tipo_prueba": p.get("tipo_prueba"),
                "cantidad": cantidad,
                "precio_unitario": precio_unit,
                "precio_total": precio_total,
            }
        )

    if detalles:
        supabase.table("orden_pruebas_detalle").insert(detalles).execute()

    return orden_id

def obtener_orden_por_id(orden_id: int):
    try:
        resp = (
            supabase.table("ordenes")
            .select("*")
            .eq("id", orden_id)
            .single()
            .execute()
        )
        return resp.data
    except Exception as e:
        print(f"Error al obtener orden {orden_id}:", e)
        return None


def obtener_abonos_orden(orden_id: int):
    try:
        resp = (
            supabase.table("orden_abonos")
            .select("*")
            .eq("orden_id", orden_id)
            .order("fecha_abono", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"Error al obtener abonos de orden {orden_id}:", e)
        return []
    
def recalcular_totales_y_estado_orden(orden_id: int):
    orden = obtener_orden_por_id(orden_id)
    if not orden:
        return

    total_pruebas = float(orden.get("total_pruebas", 0) or 0)

    abonos = obtener_abonos_orden(orden_id)
    total_abonos = 0.0
    for a in abonos:
        try:
            total_abonos += float(a.get("cantidad", 0) or 0)
        except (TypeError, ValueError):
            continue

    if total_abonos >= total_pruebas and total_pruebas > 0:
        estado = "pagada"
    elif total_abonos > 0:
        estado = "credito"
    else:
        estado = "pendiente"

    supabase.table("ordenes").update(
        {
            "total_abonos": total_abonos,
            "estado": estado,
        }
    ).eq("id", orden_id).execute()

def registrar_abono(orden_id: int, cantidad: float, empleado_id: int | None = None, nota: str | None = None):
    supabase.table("orden_abonos").insert(
        {
            "orden_id": orden_id,
            "cantidad": cantidad,
            "registrado_por_empleado_id": empleado_id,
            "nota": nota,
        }
    ).execute()

    recalcular_totales_y_estado_orden(orden_id)