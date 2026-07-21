import bcrypt
from supabase_client import supabase

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

def crear_prueba(nombre, tipo, precio):
    """Crea una nueva prueba clínica con el precio."""
    try:
        data = {
            "nombre": nombre,
            "tipo": tipo,
            "precio": precio,  # Agregar el precio aquí
            "activo": True
        }
        response = supabase.table('pruebas_clinicas').insert(data).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Error al crear prueba clínica: {response.error}")
            return None

        return response.data  # Devuelve la fila de la prueba creada
    except Exception as e:
        print(f"Error al crear prueba clínica: {e}")
        return None


def asignar_reactivos_a_prueba(prueba_id, lista_reactivos_ids):
    """
    Inserta uno o varios reactivos para una prueba en pruebas_reactivos.
    lista_reactivos_ids: lista de strings o ints.
    """
    try:
        if not lista_reactivos_ids:
            return None

        data = [
            {"prueba_id": prueba_id, "reactivo_id": int(rid)}
            for rid in lista_reactivos_ids
        ]

        response = supabase.table('pruebas_reactivos').insert(data).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Error en asignar_reactivos_a_prueba: {response.error}")
            return None

        return response.data
    except Exception as e:
        print(f"Error al asignar reactivos a prueba: {e}")
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
        # Obtener prueba por ID
        resp_prueba = (
            supabase
            .table('pruebas_clinicas')
            .select('*')
            .eq('id', prueba_id)
            .single()
            .execute()
        )
        prueba_data = getattr(resp_prueba, 'data', None)
        if not prueba_data:
            return None

        # Obtener reactivos asociados
        resp_reactivos = (
            supabase
            .table('pruebas_reactivos')
            .select('reactivo_id')
            .eq('prueba_id', prueba_id)
            .execute()
        )
        prueba_data['reactivos'] = [r['reactivo_id'] for r in resp_reactivos.data]

        # Obtener valores normales asociados
        resp_vals = (
            supabase
            .table('valores_normales')
            .select('*')
            .eq('prueba_id', prueba_id)
            .execute()
        )
        prueba_data['valores_normales'] = resp_vals.data  # Los valores normales

        return prueba_data

    except Exception as e:
        print(f"Error al obtener prueba por ID: {e}")
        return None


def actualizar_prueba(prueba_id, nombre, tipo, precio):
    """Actualiza los datos básicos de una prueba clínica, incluyendo el precio."""
    try:
        data = {
            "nombre": nombre,
            "tipo": tipo,
            "precio": precio,  # Actualizar el precio
        }
        response = supabase.table('pruebas_clinicas').update(data).eq('id', prueba_id).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Error al actualizar prueba clínica: {response.error}")
            return None

        return response.data  # Datos actualizados
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
    """Inserta un valor normal para una prueba en la base de datos."""
    try:
        data = {
            "prueba_id": prueba_id,
            "nombre": nombre,
            "tipo_separacion": tipo_separacion,
            "estructura": estructura_json  # Asegúrate de que esta sea la estructura correcta
        }
        response = supabase.table('valores_normales').insert(data).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Error al crear valor normal: {response.error}")
            return None

        return response.data
    except Exception as e:
        print(f"Error al crear valor normal: {e}")
        return None

def obtener_todos_los_reactivos():
    """Devuelve id y nombre de todos los reactivos activos, ordenados por nombre."""
    try:
        response = (
            supabase
            .table('reactivos')
            .select('id,nombre')
            .eq('activo', True)
            .order('nombre')
            .execute()
        )

        if hasattr(response, 'error') and response.error:
            print(f"Error en obtener_todos_los_reactivos: {response.error}")
            return []

        if not response.data:
            return []

        return response.data
    except Exception as e:
        print(f"Error al obtener todos los reactivos: {e}")
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


def guardar_orden_en_bd(orden: dict, pruebas: list, empleado_id: int) -> int:
    # Total de todas las pruebas (precio ya viene como total por renglón)
    total_pruebas = 0.0
    for p in pruebas:
        try:
            total_pruebas += float(p.get("precio", 0))
        except (TypeError, ValueError):
            continue

    # 1) Insertar la orden
    data_orden = {
        "paciente_id": orden.get("patient_id"),
        "hospital_id": orden.get("hospital_id"),
        "doctor_id": orden.get("doctor_id"),
        "cuarto": orden.get("cuarto"),
        "observaciones": orden.get("observaciones"),
        "total_pruebas": total_pruebas,
        "total_abonos": 0,
        "estado": "pendiente",
        # nombre real de la columna en la tabla ordenes
        "creado_por_empleado_id": empleado_id,
    }

    res_orden = supabase.table("ordenes").insert(data_orden).execute()
    if not res_orden.data:
        raise RuntimeError(f"No se pudo insertar la orden: {res_orden}")
    orden_id = res_orden.data[0]["id"]

    # 2) Insertar el detalle de pruebas
    detalles = []
    for p in pruebas:
        # cantidad
        try:
            cantidad = int(p.get("cantidad", 1))
        except (TypeError, ValueError):
            cantidad = 1

        # subtotal = total de ese renglón que viene de orden_pruebas
        try:
            subtotal = float(p.get("precio", 0) or 0)
        except (TypeError, ValueError):
            subtotal = 0.0

        # precio_unitario = subtotal / cantidad
        precio_unitario = subtotal / cantidad if cantidad else subtotal

        # --- NUEVO: prueba_id y tipo_prueba ---
        raw_prueba_id = p.get("prueba_id")
        try:
            # viene como string desde el front, lo convertimos a int
            prueba_id = int(raw_prueba_id) if raw_prueba_id not in (None, "", "null") else None
        except (TypeError, ValueError):
            prueba_id = None

        tipo_prueba = p.get("tipo_prueba") or None
        # --------------------------------------

        detalle = {
            "orden_id": orden_id,
            "nombre_prueba": p.get("prueba"),
            "cantidad": cantidad,
            "precio_unitario": precio_unitario,
            # nombre de la columna NOT NULL con el total de la línea
            "precio_total": subtotal,
        }

        # ahora sí guardamos el id real de la prueba
        if prueba_id is not None:
            detalle["prueba_id"] = prueba_id

        # y también el tipo de prueba
        if tipo_prueba:
            detalle["tipo_prueba"] = tipo_prueba

        detalles.append(detalle)

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

def listar_ordenes_resumen(limit: int = 50):

    try:
        resp = (
            supabase
            .table("ordenes")
            .select("*")
            .order("creado_en", desc=True)
            .limit(limit)
            .execute()
        )
        ordenes_raw = resp.data or []
    except Exception as e:
        print(f"Error al obtener ordenes: {e}")
        return []

    ordenes = []
    for o in ordenes_raw:
        paciente = obtener_paciente_por_id(o.get("paciente_id")) if o.get("paciente_id") else None
        hospital = obtener_hospital_por_id(o.get("hospital_id")) if o.get("hospital_id") else None
        doctor = obtener_doctor_por_id(o.get("doctor_id")) if o.get("doctor_id") else None

        total_pruebas = float(o.get("total_pruebas") or 0)
        total_abonos = float(o.get("total_abonos") or 0)
        total_restante = max(total_pruebas - total_abonos, 0.0)

        # Formatear fecha (asumiendo creado_en es timestamptz de Supabase)
        creado_en = o.get("creado_en")
        if creado_en:
            try:
                dt = datetime.fromisoformat(creado_en.replace("Z", "+00:00"))
                fecha_str = dt.strftime("%d/%m/%Y")
            except Exception:
                fecha_str = creado_en[:10]
        else:
            fecha_str = ""

        ordenes.append(
            {
                "id": o["id"],
                "fecha": fecha_str,
                "paciente_nombre": f"{paciente['nombres']} {paciente['apellidos']}" if paciente else None,
                "hospital_nombre": hospital["nombre"] if hospital else None,
                "doctor_nombre": f"{doctor['nombres']} {doctor['apellidos']}" if doctor else None,
                "total_pruebas": total_pruebas,
                "total_abonos": total_abonos,
                "total_restante": total_restante,
                "estado": o.get("estado", "pendiente"),
            }
        )

    return ordenes

def obtener_detalle_pruebas_por_orden(orden_id: int):
    try:
        resp = (
            supabase.table("orden_pruebas_detalle")
            .select("*")
            .eq("orden_id", orden_id)
            .order("id", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"Error al obtener detalle de pruebas para orden {orden_id}: {e}")
        return []

def obtener_siguiente_folio_orden():

    try:
        resp = (
            supabase.table("ordenes")
            .select("id")
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        datos = resp.data or []
        if datos:
            ultimo_id = int(datos[0]["id"])
            return ultimo_id + 1
        # Si no hay órdenes aún, empezamos en 1
        return 1
    except Exception as e:
        print(f"Error al obtener siguiente folio de orden: {e}")
        # En caso de error, devolvemos None o 0
        return None
    
def obtener_ordenes_pendientes_con_detalle():

    try:
        # Ajusta el estado según cómo lo manejes en tu sistema
        resp_ordenes = supabase.table("ordenes") \
            .select("id, paciente_id, cuarto, estado, creado_en") \
            .order("creado_en", desc=True) \
            .execute()

        if getattr(resp_ordenes, "error", None):
            print(f"Error al obtener órdenes: {resp_ordenes.error}")
            return []

        ordenes = resp_ordenes.data or []
        if not ordenes:
            return []

        # Cache sencillo para no consultar al mismo paciente muchas veces
        pacientes_idx = {}

        for orden in ordenes:
            pid = orden.get("paciente_id")
            if not pid:
                continue

            if pid not in pacientes_idx:
                resp_p = supabase.table("pacientes") \
                    .select("id, nombres, apellidos") \
                    .eq("id", pid) \
                    .single() \
                    .execute()

                if not getattr(resp_p, "error", None) and resp_p.data:
                    pacientes_idx[pid] = resp_p.data

            p = pacientes_idx.get(pid)
            if p:
                orden["nombre_paciente"] = f'{p["nombres"]} {p["apellidos"]}'
            else:
                orden["nombre_paciente"] = "Paciente desconocido"

        return ordenes

    except Exception as e:
        print(f"Error en obtener_ordenes_pendientes_con_detalle: {e}")
        return []


def obtener_ordenes_para_muestra():

    try:
        resp = supabase.table("ordenes") \
            .select("id, paciente_id, cuarto, flujo, creado_en") \
            .eq("flujo", "muestra_pendiente") \
            .order("creado_en", desc=True) \
            .execute()

        if hasattr(resp, "error") and resp.error:
            print(f"Error al obtener órdenes para muestra: {resp.error}")
            return []

        ordenes = resp.data or []
        if not ordenes:
            return []

        pacientes_cache = {}

        for orden in ordenes:
            pid = orden.get("paciente_id")
            if not pid:
                orden["nombre_paciente"] = "Paciente desconocido"
                continue

            if pid not in pacientes_cache:
                resp_p = supabase.table("pacientes") \
                    .select("id, nombres, apellidos") \
                    .eq("id", pid) \
                    .single() \
                    .execute()
                if not (hasattr(resp_p, "error") and resp_p.error) and resp_p.data:
                    pacientes_cache[pid] = resp_p.data

            p = pacientes_cache.get(pid)
            if p:
                orden["nombre_paciente"] = f'{p["nombres"]} {p["apellidos"]}'
            else:
                orden["nombre_paciente"] = "Paciente desconocido"

        return ordenes

    except Exception as e:
        print(f"Error en obtener_ordenes_para_muestra: {e}")
        return []


def consultar_analisis_por_folio(orden_id):

    try:
        resp = supabase.table("orden_pruebas_detalle") \
            .select("id, nombre_prueba, tipo_prueba") \
            .eq("orden_id", orden_id) \
            .execute()

        if hasattr(resp, "error") and resp.error:
            print(f"Error al consultar análisis por folio: {resp.error}")
            return []

        filas = resp.data or []
        resultados = []
        for row in filas:
            resultados.append({
                "id": row.get("id"),
                "nombre": row.get("nombre_prueba", ""),
                "tipo": row.get("tipo_prueba", "")
            })
        return resultados

    except Exception as e:
        print(f"Error en consultar_analisis_por_folio: {e}")
        return []


def actualizar_flujo_orden(orden_id, nuevo_flujo):

    try:
        resp = supabase.table("ordenes") \
            .update({"flujo": nuevo_flujo}) \
            .eq("id", orden_id) \
            .execute()

        if hasattr(resp, "error") and resp.error:
            print(f"Error al actualizar flujo de orden: {resp.error}")
            return False

        return True

    except Exception as e:
        print(f"Error en actualizar_flujo_orden: {e}")
        return False


def obtener_ordenes_para_quimico():

    try:
        resp = supabase.table("ordenes") \
            .select("id, paciente_id, cuarto, flujo, creado_en") \
            .eq("flujo", "en_quimico") \
            .order("creado_en", desc=True) \
            .execute()

        if hasattr(resp, "error") and resp.error:
            print(f"Error al obtener órdenes para químico: {resp.error}")
            return []

        ordenes = resp.data or []
        if not ordenes:
            return []

        pacientes_cache = {}

        for orden in ordenes:
            pid = orden.get("paciente_id")
            if not pid:
                orden["nombre_paciente"] = "Paciente desconocido"
                continue

            if pid not in pacientes_cache:
                resp_p = supabase.table("pacientes") \
                    .select("id, nombres, apellidos") \
                    .eq("id", pid) \
                    .single() \
                    .execute()
                if not (hasattr(resp_p, "error") and resp_p.error) and resp_p.data:
                    pacientes_cache[pid] = resp_p.data

            p = pacientes_cache.get(pid)
            if p:
                orden["nombre_paciente"] = f'{p["nombres"]} {p["apellidos"]}'
            else:
                orden["nombre_paciente"] = "Paciente desconocido"

        return ordenes

    except Exception as e:
        print(f"Error en obtener_ordenes_para_quimico: {e}")
        return []
