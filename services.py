import bcrypt
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from supabase_client import supabase, supabase_admin, supabase_storage


logger = logging.getLogger(__name__)
_LAB_IDENTITY_CACHE = {"value": None, "expires_at": 0.0}

try:
    _APP_UTC_OFFSET_HOURS = float(os.getenv("APP_UTC_OFFSET_HOURS", "-6"))
except (TypeError, ValueError):
    _APP_UTC_OFFSET_HOURS = -6.0
APP_LOCAL_TIMEZONE = timezone(timedelta(hours=_APP_UTC_OFFSET_HOURS))


def convertir_fecha_hora_local(value):
    """Convierte timestamps de Supabase (UTC) a la hora local de AppLab."""
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip()
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            return raw
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(APP_LOCAL_TIMEZONE).isoformat()

DEFAULT_SYSTEM_SETTINGS = {
    "empleados_cambian_password": True,
    "empleados_cambian_foto": True,
    "mostrador_entrega_saldo_pendiente": False,
}

DEFAULT_LAB_SETTINGS = {
    "nombre": "AppLab Laboratorio clínico",
    "nombre_corto": "AppLab",
    "rfc": "",
    "telefono": "",
    "whatsapp": "",
    "correo": "",
    "direccion": "",
    "logo_url": "",
    "favicon_url": "",
}

DEFAULT_RECEIPT_SETTINGS = {
    "recibo_mensaje_pie": "Gracias por confiar en nuestro laboratorio.",
    "ticket_ancho_mm": "80",
    "mostrar_laboratorio_nombre": True,
    "mostrar_laboratorio_logo": True,
    "mostrar_laboratorio_rfc": True,
    "mostrar_laboratorio_telefono": True,
    "mostrar_laboratorio_whatsapp": True,
    "mostrar_laboratorio_correo": True,
    "mostrar_laboratorio_direccion": True,
    "mostrar_paciente_telefono": True,
    "mostrar_paciente_direccion": False,
    "mostrar_procedencia": True,
    "mostrar_medico": True,
    "mostrar_estudios": True,
    "mostrar_observaciones": True,
    "mostrar_cajero": True,
    "mostrar_historial_pagos": True,
    "mostrar_saldo": True,
}


def obtener_configuracion_sistema():
    """Carga las políticas globales conservando valores seguros de respaldo."""
    settings = dict(DEFAULT_SYSTEM_SETTINGS)
    try:
        response = (
            supabase_admin.table("configuracion_sistema")
            .select("*")
            .eq("id", 1).limit(1).execute()
        )
        if response.data:
            row = response.data[0]
            settings.update({
                key: row.get(key, default)
                for key, default in DEFAULT_SYSTEM_SETTINGS.items()
            })
            settings["actualizado_en"] = row.get("actualizado_en")
            receipt_settings = row.get("recibo_configuracion") or {}
            settings["recibo_configuracion"] = {
                **DEFAULT_RECEIPT_SETTINGS,
                **receipt_settings,
            }
            # Compatibilidad con la configuración anterior, donde la identidad
            # estaba guardada dentro del recibo.
            legacy_identity = {
                "nombre": receipt_settings.get("laboratorio_nombre"),
                "rfc": receipt_settings.get("laboratorio_rfc"),
                "telefono": receipt_settings.get("laboratorio_telefono"),
                "whatsapp": receipt_settings.get("laboratorio_whatsapp"),
                "correo": receipt_settings.get("laboratorio_correo"),
                "direccion": receipt_settings.get("laboratorio_direccion"),
            }
            laboratory_settings = (
                row.get("laboratorio_configuracion")
                or receipt_settings.get("identidad_laboratorio")
                or {}
            )
            settings["laboratorio_configuracion"] = {
                **DEFAULT_LAB_SETTINGS,
                **{key: value for key, value in legacy_identity.items() if value},
                **laboratory_settings,
            }
    except Exception:
        logger.warning("La configuración global todavía no está disponible", exc_info=True)
    settings.setdefault("recibo_configuracion", dict(DEFAULT_RECEIPT_SETTINGS))
    settings.setdefault("laboratorio_configuracion", dict(DEFAULT_LAB_SETTINGS))
    return settings


def guardar_configuracion_sistema(settings, usuario_id):
    payload = {
        key: bool(settings.get(key))
        for key in DEFAULT_SYSTEM_SETTINGS
    }
    payload.update({
        "id": 1,
        "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    })
    response = supabase_admin.table("configuracion_sistema").upsert(
        payload, on_conflict="id"
    ).execute()
    return bool(response.data)


def guardar_configuracion_recibos(settings, usuario_id):
    """Guarda el contenido y visibilidad de los comprobantes de mostrador."""
    normalized = dict(DEFAULT_RECEIPT_SETTINGS)
    for key, default in DEFAULT_RECEIPT_SETTINGS.items():
        value = settings.get(key, default)
        normalized[key] = bool(value) if isinstance(default, bool) else str(value or "").strip()
    # Conserva la identidad cuando una instalación anterior todavía la guarda
    # dentro del JSON de recibos y no en una columna independiente.
    current_receipt = obtener_configuracion_sistema().get("recibo_configuracion", {})
    if current_receipt.get("identidad_laboratorio"):
        normalized["identidad_laboratorio"] = current_receipt["identidad_laboratorio"]
    payload = {
        "id": 1,
        "recibo_configuracion": normalized,
        "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    response = supabase_admin.table("configuracion_sistema").upsert(
        payload, on_conflict="id"
    ).execute()
    return bool(response.data)


def guardar_configuracion_laboratorio(settings, usuario_id):
    """Guarda una única identidad para toda la aplicación y sus documentos."""
    normalized = {
        key: str(settings.get(key, default) or "").strip()
        for key, default in DEFAULT_LAB_SETTINGS.items()
    }
    payload = {
        "id": 1,
        "laboratorio_configuracion": normalized,
        "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    try:
        response = supabase_admin.table("configuracion_sistema").upsert(
            payload, on_conflict="id"
        ).execute()
    except Exception as error:
        # Compatibilidad inmediata para proyectos donde aún no se ha aplicado
        # la columna laboratorio_configuracion. La identidad se conserva en el
        # JSON ya existente de recibos, sin almacenar archivos binarios.
        error_text = str(error)
        missing_identity_column = (
            getattr(error, "code", None) in {"PGRST204", "42703"}
            or "laboratorio_configuracion" in error_text
        )
        if not missing_identity_column:
            raise
        current_receipt = obtener_configuracion_sistema().get(
            "recibo_configuracion", dict(DEFAULT_RECEIPT_SETTINGS)
        )
        current_receipt["identidad_laboratorio"] = normalized
        fallback_payload = {
            "id": 1,
            "recibo_configuracion": current_receipt,
            "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
            "actualizado_en": datetime.now(timezone.utc).isoformat(),
        }
        response = supabase_admin.table("configuracion_sistema").upsert(
            fallback_payload, on_conflict="id"
        ).execute()
    _LAB_IDENTITY_CACHE["value"] = dict(normalized)
    _LAB_IDENTITY_CACHE["expires_at"] = time.monotonic() + 60
    return bool(response.data)


def obtener_identidad_laboratorio():
    if _LAB_IDENTITY_CACHE["value"] and time.monotonic() < _LAB_IDENTITY_CACHE["expires_at"]:
        return dict(_LAB_IDENTITY_CACHE["value"])
    identity = obtener_configuracion_sistema().get(
        "laboratorio_configuracion", dict(DEFAULT_LAB_SETTINGS)
    )
    _LAB_IDENTITY_CACHE["value"] = dict(identity)
    _LAB_IDENTITY_CACHE["expires_at"] = time.monotonic() + 60
    return identity


def validar_autorizador_admin_detallado(username, password):
    """Valida una excepción administrativa y devuelve un mensaje utilizable."""
    username = str(username or "").strip()
    password = str(password or "")
    if not username or not password:
        return None, "Escribe el usuario y la contraseña del administrador."
    try:
        user_response = (
            supabase_admin.table("usuarios")
            .select("id,username,password,estado_usuario")
            .eq("username", username).limit(1).execute()
        )
        if not user_response.data:
            return None, "Usuario o contraseña incorrectos."
        user = user_response.data[0]
        if not user.get("estado_usuario") or not bcrypt.checkpw(
            password.encode("utf-8"), str(user.get("password") or "").encode("utf-8")
        ):
            return None, "Usuario o contraseña incorrectos."
        employee_response = (
            supabase_admin.table("empleados")
            .select("id,nombres,apellidos")
            .eq("usuario_id", user["id"]).limit(1).execute()
        )
        if not employee_response.data:
            return None, "El usuario es válido, pero no tiene un perfil de empleado asociado."
        employee = employee_response.data[0]
        role_response = (
            supabase_admin.table("empleado_roles").select("rol_id")
            .eq("empleado_id", employee["id"]).execute()
        )
        role_ids = {row.get("rol_id") for row in (role_response.data or [])}
        authorized = 1 in role_ids
        if not authorized and 5 in role_ids:
            permission_response = (
                supabase_admin.table("empleado_permisos").select("permiso_codigo")
                .eq("empleado_id", employee["id"])
                .eq("permiso_codigo", "admin.override").limit(1).execute()
            )
            authorized = bool(permission_response.data)
        if not authorized:
            return None, "El usuario es correcto, pero no tiene permiso para autorizar esta operación."
        return {
            "usuario_id": user["id"],
            "empleado_id": employee["id"],
            "username": user.get("username"),
            "nombre": f"{employee.get('nombres', '')} {employee.get('apellidos', '')}".strip(),
        }, None
    except Exception:
        logger.exception("No se pudo validar al autorizador administrativo")
        return None, "No se pudieron validar las credenciales. Intenta nuevamente."


def verificar_autorizador_admin(username, password):
    """Compatibilidad para los formularios que solo requieren el autorizador."""
    authorizer, _error = validar_autorizador_admin_detallado(username, password)
    return authorizer


def registrar_excepcion_sistema(accion, detalle, autorizador, solicitante=None):
    """Registra quién autorizó una excepción sin almacenar contraseñas."""
    try:
        supabase_storage.table("bitacora_eventos").insert({
            "modulo": "Sistema",
            "accion": "actualizar",
            "severidad": "warning",
            "titulo": "Excepción administrativa autorizada",
            "detalle": str(detalle),
            "entidad_tipo": "configuracion_sistema",
            "entidad_id": str(accion),
            "actor_usuario_id": autorizador.get("usuario_id"),
            "actor_empleado_id": autorizador.get("empleado_id"),
            "actor_username": autorizador.get("username"),
            "actor_nombre": autorizador.get("nombre"),
            "metadata": {
                "solicitante": solicitante or {},
                "accion_sistema": "autorizar_excepcion",
                "excepcion": accion,
            },
        }).execute()
        return True
    except Exception:
        logger.exception("No se pudo registrar la excepción administrativa")
        return False


def registrar_cambio_politicas(settings, actor):
    try:
        supabase_storage.table("bitacora_eventos").insert({
            "modulo": "Sistema",
            "accion": "actualizar",
            "severidad": "info",
            "titulo": "Políticas del sistema actualizadas",
            "detalle": "Se modificaron las reglas globales de operación y seguridad.",
            "entidad_tipo": "configuracion_sistema",
            "entidad_id": "1",
            "actor_usuario_id": actor.get("usuario_id"),
            "actor_empleado_id": actor.get("empleado_id"),
            "actor_username": actor.get("username"),
            "actor_nombre": actor.get("nombre"),
            "metadata": {
                "accion_sistema": "actualizar_politicas",
                "cambios": [
                    {"campo": key, "anterior": "—", "nuevo": value}
                    for key, value in settings.items()
                ]
            },
        }).execute()
        return True
    except Exception:
        logger.exception("No se pudo registrar el cambio de políticas")
        return False


def obtener_resumen_admin():
    """Devuelve contadores reales y alertas comprobables para el dashboard."""
    table_fields = {
        "pacientes": ("pacientes", "id,activo"),
        "pruebas": ("pruebas_clinicas", "id,activo"),
        "doctores": ("doctores", "id,activo"),
        "proveedores": ("proveedores", "id,activo"),
        "hospitales": ("hospitales", "id,activo"),
    }
    counts = {
        key: 0
        for key in (*table_fields.keys(), "empleados", "reactivos")
    }

    for key, (table, fields) in table_fields.items():
        try:
            response = supabase.table(table).select(fields).execute()
            counts[key] = sum(
                row.get("activo", True) is True
                for row in (response.data or [])
            )
        except Exception:
            logger.exception("No se pudo contar la tabla %s", table)

    inventory_alerts = []
    try:
        employees_response = (
            supabase.table("empleados")
            .select("id,usuario_id")
            .execute()
        )
        user_ids = {
            employee.get("usuario_id")
            for employee in (employees_response.data or [])
            if employee.get("usuario_id") is not None
        }
        if user_ids:
            users_response = (
                supabase.table("usuarios")
                .select("id,estado_usuario")
                .in_("id", list(user_ids))
                .execute()
            )
            active_user_ids = {
                user["id"] for user in (users_response.data or [])
                if user.get("estado_usuario") is True
            }
            counts["empleados"] = sum(
                employee.get("usuario_id") in active_user_ids
                for employee in (employees_response.data or [])
            )
    except Exception:
        logger.exception("No se pudieron contar los empleados activos")

    try:
        try:
            response = (
                supabase.table("reactivos")
                .select(
                    "id,nombre,activo,cantidad_inicial,existencia_actual,"
                    "fecha_vencimiento,alerta_existencia_minima,alertas_vencimiento_dias"
                )
                .execute()
            )
        except Exception:
            # Compatibilidad con instalaciones que aún no ejecutan la
            # migración de movimientos de inventario.
            response = (
                supabase.table("reactivos")
                .select("id,nombre,activo,cantidad_inicial,fecha_vencimiento")
                .execute()
            )
        reactivos = response.data or []
        counts["reactivos"] = sum(
            reactivo.get("activo", True) is True
            for reactivo in reactivos
        )
        today = datetime.now().date()

        for reactivo in reactivos:
            if reactivo.get("activo") is False:
                continue
            stock = reactivo.get("existencia_actual")
            if stock is None:
                stock = reactivo.get("cantidad_inicial") or 0

            expiry_text = reactivo.get("fecha_vencimiento")
            expiry = None
            if expiry_text:
                try:
                    expiry = datetime.fromisoformat(str(expiry_text)[:10]).date()
                except ValueError:
                    expiry = None

            days_to_expiry = (expiry - today).days if expiry else None
            expiry_windows = reactivo.get("alertas_vencimiento_dias") or []
            expiry_warning = (
                days_to_expiry is not None
                and days_to_expiry >= 0
                and any(days_to_expiry <= int(days) for days in expiry_windows)
            )
            try:
                stock_value = int(stock)
            except (TypeError, ValueError):
                stock_value = 0

            if expiry and expiry < today:
                inventory_alerts.append({
                    "nombre": reactivo.get("nombre") or "Reactivo sin nombre",
                    "detalle": f"Venció el {expiry.isoformat()}",
                    "tipo": "vencido",
                    "etiqueta": "Vencido",
                })
            elif expiry_warning:
                inventory_alerts.append({
                    "nombre": reactivo.get("nombre") or "Reactivo sin nombre",
                    "detalle": (
                        "Vence hoy" if days_to_expiry == 0
                        else f"Vence en {days_to_expiry} días"
                    ),
                    "tipo": "vencimiento",
                    "etiqueta": "Por vencer",
                })

            minimum = int(reactivo.get("alerta_existencia_minima") or 0)
            if stock_value <= minimum:
                inventory_alerts.append({
                    "nombre": reactivo.get("nombre") or "Reactivo sin nombre",
                    "detalle": f"Existencia {stock_value}; mínimo configurado {minimum}",
                    "tipo": "agotado",
                    "etiqueta": "Stock bajo",
                })
    except Exception:
        logger.exception("No se pudo obtener el resumen de reactivos")

    return {"counts": counts, "inventory_alerts": inventory_alerts[:6]}


INVENTORY_NOTIFICATION_ROLES = {"Admin", "Quimico"}


def obtener_notificaciones_inventario(usuario_id, rol=None):
    """Genera alertas de inventario únicamente para los roles responsables."""
    if rol not in INVENTORY_NOTIFICATION_ROLES:
        return []
    if not usuario_id:
        return []
    today = datetime.now().date()
    notifications = []
    try:
        response = (
            supabase.table("reactivos")
            .select(
                "id,nombre,activo,cantidad_inicial,existencia_actual,"
                "fecha_vencimiento,alerta_existencia_minima,alertas_vencimiento_dias"
            )
            .execute()
        )
        for reactivo in response.data or []:
            if reactivo.get("activo") is False:
                continue
            reagent_id = reactivo["id"]
            name = reactivo.get("nombre") or "Reactivo sin nombre"
            stock = reactivo.get("existencia_actual")
            stock = reactivo.get("cantidad_inicial") or 0 if stock is None else stock
            minimum = int(reactivo.get("alerta_existencia_minima") or 0)
            if int(stock) <= minimum:
                has_deficit = int(stock) < 0
                notifications.append({
                    "key": f"reactivo:{reagent_id}:stock",
                    "title": "Completar inventario" if has_deficit else "Existencia baja",
                    "detail": (
                        f"{name}: existe un déficit de {abs(int(stock))} "
                        "unidad(es). Registra una nueva entrada."
                        if has_deficit
                        else f"{name}: quedan {stock} unidades (mínimo {minimum})."
                    ),
                    "type": "stock",
                    "reactivo_id": reagent_id,
                })

            expiry_text = reactivo.get("fecha_vencimiento")
            if not expiry_text:
                continue
            try:
                expiry = datetime.fromisoformat(str(expiry_text)[:10]).date()
            except ValueError:
                continue
            remaining = (expiry - today).days
            windows = [int(day) for day in (reactivo.get("alertas_vencimiento_dias") or [])]
            if remaining < 0:
                title = "Reactivo vencido"
                detail = f"{name} venció el {expiry.isoformat()}."
            elif windows and any(remaining <= day for day in windows):
                title = "Reactivo próximo a vencer"
                detail = f"{name} vence hoy." if remaining == 0 else f"{name} vence en {remaining} días."
            else:
                continue
            notifications.append({
                "key": f"reactivo:{reagent_id}:expiry",
                "title": title,
                "detail": detail,
                "type": "expiry",
                "reactivo_id": reagent_id,
            })

        read_response = (
            supabase.table("notificaciones_leidas")
            .select("clave")
            .eq("usuario_id", int(usuario_id))
            .eq("fecha", today.isoformat())
            .execute()
        )
        read_keys = {item["clave"] for item in (read_response.data or [])}
        for notification in notifications:
            notification["read"] = notification["key"] in read_keys
        return notifications
    except Exception:
        logger.exception("No se pudieron generar las notificaciones de inventario")
        return []


def marcar_notificaciones_leidas(usuario_id, keys):
    """Persiste las lecturas del usuario únicamente para la fecha actual."""
    today = datetime.now().date().isoformat()
    clean_keys = sorted({str(key) for key in keys if str(key).strip()})
    if not clean_keys:
        return True
    try:
        rows = [
            {"usuario_id": int(usuario_id), "clave": key, "fecha": today}
            for key in clean_keys
        ]
        supabase.table("notificaciones_leidas").upsert(
            rows, on_conflict="usuario_id,clave,fecha"
        ).execute()
        return True
    except Exception:
        logger.exception("No se pudieron marcar las notificaciones como leídas")
        return False


def obtener_eventos_bitacora(limit=150):
    """Obtiene la actividad reciente usando el cliente privado del servidor."""
    try:
        response = (
            supabase_storage.table("bitacora_eventos")
            .select(
                "id,creado_en,modulo,accion,severidad,titulo,detalle,"
                "entidad_tipo,entidad_id,actor_usuario_id,actor_username,"
                "actor_nombre,metadata"
            )
            .order("creado_en", desc=True)
            .limit(max(1, min(int(limit), 300)))
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception("No se pudo consultar la bitácora de Supabase")
        return None


def atribuir_ultimo_evento(
    entidad_tipo,
    entidad_id,
    actor_usuario_id=None,
    actor_empleado_id=None,
    actor_username=None,
    actor_nombre=None,
    cambios_extra=None,
):
    """Asocia el evento creado por el trigger con el usuario de la sesión Flask."""
    try:
        response = (
            supabase_storage.table("bitacora_eventos")
            .select("id,metadata")
            .eq("entidad_tipo", str(entidad_tipo))
            .eq("entidad_id", str(entidad_id))
            .is_("actor_usuario_id", "null")
            .order("creado_en", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return False

        event = response.data[0]
        metadata = event.get("metadata") or {}
        changes = list(metadata.get("cambios") or [])
        changes.extend(cambios_extra or [])
        metadata["cambios"] = changes

        supabase_storage.table("bitacora_eventos").update({
            "actor_usuario_id": actor_usuario_id,
            "actor_empleado_id": actor_empleado_id,
            "actor_username": (actor_username or "").strip() or None,
            "actor_nombre": (actor_nombre or "").strip() or None,
            "metadata": metadata,
        }).eq("id", event["id"]).execute()
        return True
    except Exception:
        logger.exception("No se pudo atribuir el evento de bitácora")
        return False

def verificar_usuario(usuario, password):
    """Verifica si un usuario existe y su contraseña es correcta."""
    if not usuario or not password:
        return None

    try:
        result = (
            supabase.table("usuarios")
            .select("id, password, estado_usuario")
            .eq("username", usuario)
            .limit(1)
            .execute()
        )
        if not result.data:
            return None

        user = result.data[0]
        hashed_password = user.get("password")
        if not user.get("estado_usuario") or not hashed_password:
            return None
        if not bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8")):
            return None

        empleado_result = (
            supabase.table("empleados")
            .select("id, nombres, foto_perfil")
            .eq("usuario_id", user["id"])
            .limit(1)
            .execute()
        )
        if not empleado_result.data:
            return None

        empleado = empleado_result.data[0]
        rol_result = (
            supabase.table("empleado_roles")
            .select("rol_id")
            .eq("empleado_id", empleado["id"])
            .limit(1)
            .execute()
        )
        if not rol_result.data:
            return None

        rol_id = rol_result.data[0].get("rol_id")
        return {
            "id": user["id"],
            "empleado_id": empleado["id"],
            "nombres": empleado.get("nombres"),
            "foto_perfil": empleado.get("foto_perfil"),
            "rol_id": rol_id,
            "permisos": (
                obtener_permisos_empleado(empleado["id"])
                if rol_id == 5 else []
            ),
        }
    except Exception:
        logger.exception("No se pudo verificar al usuario")
        return None


def obtener_empleados():
    """Obtiene una lista de empleados con los campos especificados."""
    try:
        empleados_result = supabase.table('empleados').select(
            '''
            id,
            nombres,
            apellidos,
            usuario_id,
            contacto_emergencia,
            condiciones_medicas,
            fecha_nacimiento,
            foto_perfil,
            empleado_roles(rol_id(id, nombre)) 
            '''
        ).execute()

        if not empleados_result.data:
            print("No se encontraron empleados.")
            return []

        user_ids = [emp.get("usuario_id") for emp in empleados_result.data if emp.get("usuario_id")]
        estados_por_usuario = {}
        if user_ids:
            usuarios_result = (
                supabase.table("usuarios")
                .select("id, estado_usuario")
                .in_("id", user_ids)
                .execute()
            )
            estados_por_usuario = {
                usuario["id"]: usuario.get("estado_usuario", False)
                for usuario in (usuarios_result.data or [])
            }

        empleados_con_datos = []
        for emp in empleados_result.data:
            # Extraer rol_id y nombre del rol
            roles = emp.get("empleado_roles", [{}])
            rol_data = roles[0].get("rol_id", {}) if roles else {}
            usuario_id = emp.get("usuario_id")
            
            empleados_con_datos.append({
                "id": emp["id"],
                "nombres": emp["nombres"],
                "apellidos": emp["apellidos"],
                "usuario_id": usuario_id,
                "contacto_emergencia": emp.get("contacto_emergencia") or "",
                "condiciones_medicas": emp.get("condiciones_medicas") or "",
                "fecha_nacimiento": emp.get("fecha_nacimiento") or "",
                "foto_perfil": emp.get("foto_perfil"),
                "estado": estados_por_usuario.get(usuario_id, False),
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
    data = dict(data)
    data["correo"] = (data.get("correo") or "").strip() or None
    if paciente_duplicado(
        data.get('nombres'), data.get('apellidos'),
        data.get('telefono'), data.get('correo')
    ):
        return False, "Ya existe un paciente con estos datos."
    
    paciente = crear_paciente(data)
    if not paciente:
        return False, (
            "No se pudo registrar el paciente. Si el correo está vacío, "
            "verifica que la migración de correo opcional esté aplicada."
        )
    return True, paciente

# Obtener todos los pacientes
def obtener_pacientes():
    try:
        response = supabase.table('pacientes').select(
            'id,nombres,apellidos,sexo,fecha_nacimiento,telefono,correo,'
            'calle,numero_ext,numero_int,codigo_postal,municipio,estado,activo'
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
        data = dict(data)
        data["correo"] = (data.get("correo") or "").strip() or None
        respuesta = (
            supabase.table("pacientes")
            .select("id")
            .eq("nombres", data.get("nombres"))
            .eq("apellidos", data.get("apellidos"))
            .eq("telefono", data.get("telefono"))
            .neq("id", paciente_id)
            .execute()
        )

        if respuesta.data:
            return False, "Otro paciente ya tiene estos datos."
        if data["correo"]:
            correo_duplicado = (
                supabase.table("pacientes")
                .select("id")
                .eq("correo", data["correo"])
                .neq("id", paciente_id)
                .execute()
            )
            if correo_duplicado.data:
                return False, "Otro paciente ya tiene este correo electrónico."

        paciente = actualizar_paciente(paciente_id, data)
        if not paciente:
            return False, (
                "No se pudo actualizar el paciente. Si el correo está vacío, "
                "verifica que la migración de correo opcional esté aplicada."
            )
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
        response = (
            supabase.table("pacientes")
            .select("id")
            .eq("nombres", nombres)
            .eq("apellidos", apellidos)
            .eq("telefono", telefono)
            .execute()
        )
        if response.data:
            return True
        if correo:
            email_response = (
                supabase.table("pacientes")
                .select("id")
                .eq("correo", correo)
                .execute()
            )
            return bool(email_response.data)
        return False
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


def obtener_proveedores_servicio(solo_activos=True):
    """Devuelve proveedores habilitados para procesar pruebas de referencia."""
    try:
        query = (
            supabase_admin.table("proveedores")
            .select("id,nombre,tipo,telefono,correo,activo")
            .eq("tipo", "servicio")
        )
        if solo_activos:
            query = query.eq("activo", True)
        response = query.order("nombre").execute()
        return response.data or []
    except Exception:
        logger.exception("No se pudieron consultar los proveedores de servicio")
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
        same_name = supabase.table("proveedores").select("id").ilike(
            "nombre", data["nombre"]
        ).neq("id", proveedor_id).limit(1).execute()
        same_phone = None
        same_email = None
        if data.get("telefono"):
            same_phone = supabase.table("proveedores").select("id").eq(
                "telefono", data["telefono"]
            ).neq("id", proveedor_id).limit(1).execute()
        if data.get("correo"):
            same_email = supabase.table("proveedores").select("id").eq(
                "correo", data["correo"]
            ).neq("id", proveedor_id).limit(1).execute()

        if same_name.data or (same_phone and same_phone.data) or (same_email and same_email.data):
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
        if supabase.table("proveedores").select("id").ilike("nombre", nombre).limit(1).execute().data:
            return True
        if telefono and supabase.table("proveedores").select("id").eq("telefono", telefono).limit(1).execute().data:
            return True
        if correo and supabase.table("proveedores").select("id").eq("correo", correo).limit(1).execute().data:
            return True
        return False
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


def obtener_permisos_empleado(empleado_id):
    """Obtiene los códigos de acceso asignados directamente al empleado."""
    if not empleado_id:
        return []
    response = (
        supabase.table("empleado_permisos")
        .select("permiso_codigo")
        .eq("empleado_id", int(empleado_id))
        .execute()
    )
    return sorted({
        row.get("permiso_codigo")
        for row in (response.data or [])
        if row.get("permiso_codigo")
    })


def reemplazar_permisos_empleado(empleado_id, permisos):
    """Reemplaza de forma determinista la selección de permisos de un empleado."""
    empleado_id = int(empleado_id)
    supabase.table("empleado_permisos").delete().eq(
        "empleado_id", empleado_id
    ).execute()
    rows = [
        {"empleado_id": empleado_id, "permiso_codigo": codigo}
        for codigo in sorted(set(permisos or []))
    ]
    if rows:
        supabase.table("empleado_permisos").insert(rows).execute()
    return True


def registrar_entrada_reactivo(reactivo_id, cantidad, costo_unitario=None,
                               numero_lote=None, fecha_vencimiento=None,
                               observaciones=None, empleado_id=None):
    """Registra una entrada y actualiza la existencia de forma atómica en Supabase."""
    try:
        params = {
            "p_reactivo_id": int(reactivo_id),
            "p_cantidad": int(cantidad),
            "p_costo_unitario": float(costo_unitario) if costo_unitario not in (None, "") else None,
            "p_numero_lote": (numero_lote or "").strip() or None,
            "p_fecha_vencimiento": fecha_vencimiento or None,
            "p_observaciones": (observaciones or "").strip() or None,
            "p_empleado_id": int(empleado_id) if empleado_id else None,
        }
        response = supabase.rpc("registrar_entrada_inventario", params).execute()
        return True, response.data
    except (TypeError, ValueError):
        return False, "Los datos de la entrada no son válidos."
    except Exception as e:
        logger.exception("Error al registrar entrada de inventario")
        error_text = str(e)
        if "PGRST202" in error_text or "registrar_entrada_inventario" in error_text:
            return False, (
                "Falta actualizar Supabase. Ejecuta la migración "
                "20260728_inventory_lots.sql y vuelve a intentarlo."
            )
        if "42501" in error_text or "row-level security" in error_text:
            return False, (
                "Supabase bloqueó el registro por seguridad. Vuelve a ejecutar "
                "la migración 20260728_inventory_lots.sql actualizada."
            )
        return False, f"No se pudo registrar la entrada: {error_text}"


def obtener_lotes_reactivos(reactivo_id=None, solo_con_existencia=False):
    """Obtiene las existencias separadas por lote y vencimiento."""
    try:
        query = (
            supabase.table("lotes_reactivos")
            .select(
                "id,reactivo_id,numero_lote,cantidad_inicial,existencia_actual,"
                "fecha_entrada,fecha_vencimiento,costo_unitario,observaciones,"
                "activo,creado_en,reactivo:reactivo_id(id,nombre,activo)"
            )
            .eq("activo", True)
        )
        if reactivo_id is not None:
            query = query.eq("reactivo_id", int(reactivo_id))
        if solo_con_existencia:
            query = query.gt("existencia_actual", 0)
        response = query.order("fecha_vencimiento", desc=False).execute()
        return response.data or []
    except Exception:
        logger.exception("No se pudieron obtener los lotes de reactivos")
        return []


def obtener_movimientos_inventario(limit=20):
    """Obtiene los movimientos recientes con el nombre del reactivo."""
    try:
        response = (
            supabase.table("movimientos_inventario")
            .select("id,lote_id,tipo,cantidad,existencia_anterior,existencia_nueva,costo_unitario,numero_lote,fecha_vencimiento,creado_en,reactivo_id(id,nombre)")
            .order("creado_en", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data or []
    except Exception:
        return []

def crear_prueba(nombre, tipo, precio, configuracion=None):
    """Crea una nueva prueba clínica con el precio."""
    try:
        data = {
            "nombre": nombre,
            "tipo": tipo,
            "precio": precio,  # Agregar el precio aquí
            "activo": True
        }
        if configuracion:
            data.update(configuracion)
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
        proveedor_ids = {
            int(item["proveedor_servicio_id"])
            for item in pruebas_data if item.get("proveedor_servicio_id")
        }
        proveedores = {}
        if proveedor_ids:
            proveedor_rows = (
                supabase_admin.table("proveedores").select("id,nombre")
                .in_("id", sorted(proveedor_ids)).execute()
            ).data or []
            proveedores = {int(item["id"]): item["nombre"] for item in proveedor_rows}

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
            prueba["nombre_proveedor"] = proveedores.get(
                int(prueba.get("proveedor_servicio_id") or 0)
            )

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


def actualizar_prueba(prueba_id, nombre, tipo, precio, configuracion=None):
    """Actualiza los datos básicos de una prueba clínica, incluyendo el precio."""
    try:
        data = {
            "nombre": nombre,
            "tipo": tipo,
            "precio": precio,  # Actualizar el precio
        }
        if configuracion:
            data.update(configuracion)
        response = supabase.table('pruebas_clinicas').update(data).eq('id', prueba_id).execute()

        if hasattr(response, 'error') and response.error:
            print(f"Error al actualizar prueba clínica: {response.error}")
            return None

        return response.data  # Datos actualizados
    except Exception as e:
        print(f"Error al actualizar prueba clínica: {e}")
        return None


def actualizar_reactivos_de_prueba(prueba_id, lista_reactivos_ids):
    """Reemplaza las relaciones de reactivos de una prueba."""
    try:
        supabase.table('pruebas_reactivos').delete().eq('prueba_id', prueba_id).execute()
        if lista_reactivos_ids:
            return asignar_reactivos_a_prueba(prueba_id, lista_reactivos_ids)
        return []
    except Exception as e:
        print(f"Error al actualizar reactivos: {e}")
        return None


def eliminar_valores_normales_de_prueba(prueba_id):
    """Elimina los valores de referencia anteriores antes de guardar la edición."""
    try:
        response = (
            supabase.table('valores_normales')
            .delete()
            .eq('prueba_id', prueba_id)
            .execute()
        )
        return response.data or []
    except Exception as e:
        print(f"Error al eliminar valores normales de la prueba: {e}")
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


def reactivo_tiene_datos_completos(reactivo):
    """Comprueba los datos mínimos requeridos para usar un reactivo."""
    text_fields = ("nombre", "tipo_reactivo", "fecha_entrada")
    relation_fields = ("proveedor_id",)
    numeric_fields = ("costo_unidad", "precio_unidad", "cantidad_inicial")
    return (
        isinstance(reactivo, dict)
        and reactivo.get("activo") is True
        and all(str(reactivo.get(field) or "").strip() for field in text_fields)
        and all(reactivo.get(field) is not None for field in relation_fields)
        and all(reactivo.get(field) is not None for field in numeric_fields)
    )


def validar_reactivos_para_prueba(reactivos_ids):
    """Valida existencia, estado y datos de todos los reactivos seleccionados."""
    try:
        ids = list(dict.fromkeys(int(value) for value in reactivos_ids))
    except (TypeError, ValueError):
        return False, "La selección de reactivos no es válida."

    if not ids:
        return False, "Selecciona al menos un reactivo."

    try:
        response = (
            supabase.table("reactivos")
            .select("id,nombre,tipo_reactivo,costo_unidad,precio_unidad,proveedor_id,fecha_entrada,cantidad_inicial,activo")
            .in_("id", ids)
            .execute()
        )
        records = response.data or []
    except Exception as e:
        print(f"Error al validar reactivos de la prueba: {e}")
        return False, "No fue posible validar los reactivos seleccionados."

    if len(records) != len(ids):
        return False, "Uno de los reactivos seleccionados ya no existe."

    incomplete = [record.get("nombre") or f"#{record.get('id')}" for record in records if not reactivo_tiene_datos_completos(record)]
    if incomplete:
        return False, f"Completa o activa el reactivo: {', '.join(incomplete)}."

    return True, ""


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


def crear_orden_atomica(orden: dict, pruebas: list, empleado_id=None) -> int:
    """Crea cabecera y estudios en una sola transacción mediante RPC."""
    params = {
        "p_paciente_id": int(orden.get("patient_id")),
        "p_hospital_id": int(orden["hospital_id"]) if orden.get("hospital_id") else None,
        "p_doctor_id": int(orden["doctor_id"]) if orden.get("doctor_id") else None,
        "p_cuarto": orden.get("cuarto") or None,
        "p_observaciones": orden.get("observaciones") or None,
        "p_empleado_id": int(empleado_id) if empleado_id else None,
        "p_estudios": pruebas,
    }
    try:
        response = supabase.rpc("crear_orden_con_estudios", params).execute()
        if response.data is None:
            raise RuntimeError("Supabase no devolvió el folio.")
        return int(response.data)
    except Exception as exc:
        raise RuntimeError(
            "Ejecuta la migración 20260728_atomic_orders_and_payments.sql. "
            f"Detalle de Supabase: {exc}"
        ) from exc


def obtener_orden_por_id(orden_id: int):
    try:
        rpc_response = supabase.rpc(
            "obtener_orden_app", {"p_orden_id": int(orden_id)}
        ).execute()
        if rpc_response.data:
            return rpc_response.data
    except Exception:
        pass
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
        rpc_response = supabase.rpc(
            "obtener_abonos_orden_app", {"p_orden_id": int(orden_id)}
        ).execute()
        if isinstance(rpc_response.data, list):
            return rpc_response.data
    except Exception:
        pass
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

def registrar_abono(
    orden_id: int,
    cantidad: float,
    empleado_id: int | None = None,
    nota: str | None = None,
    metodo_pago: str = "efectivo",
    metodo_pago_otro: str | None = None,
):
    params = {
        "p_orden_id": int(orden_id),
        "p_cantidad": float(cantidad),
        "p_empleado_id": int(empleado_id) if empleado_id else None,
        "p_nota": (nota or "").strip() or None,
        "p_metodo_pago": (metodo_pago or "").strip().lower(),
        "p_metodo_pago_otro": (metodo_pago_otro or "").strip() or None,
    }
    return supabase.rpc("registrar_abono_orden", params).execute().data

def listar_ordenes_resumen(limit: int = 50):

    try:
        resp = supabase.rpc(
            "listar_ordenes_app", {"p_limite": max(1, min(int(limit), 200))}
        ).execute()
        ordenes_raw = resp.data if isinstance(resp.data, list) else []
    except Exception as e:
        logger.warning("RPC listar_ordenes_app no disponible: %s", e)
        try:
            resp = (
                supabase.table("ordenes").select("*")
                .order("creado_en", desc=True).limit(limit).execute()
            )
            ordenes_raw = resp.data or []
        except Exception:
            logger.exception("Error al obtener ordenes")
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


def obtener_historial_ordenes_paciente(paciente_id):
    """Órdenes, estudios, resultados y saldo de un expediente."""
    try:
        response = (
            supabase_admin.table("ordenes")
            .select("id,creado_en,total_pruebas,total_abonos,estado,flujo,hospital_id,doctor_id")
            .eq("paciente_id", int(paciente_id))
            .order("creado_en", desc=True)
            .execute()
        )
        orders = response.data or []
        if not orders:
            return []
        order_ids = [item["id"] for item in orders]
        detail_response = (
            supabase_admin.table("orden_pruebas_detalle")
            .select("orden_id,nombre_prueba,cantidad")
            .in_("orden_id", order_ids)
            .execute()
        )
        result_response = (
            supabase_admin.table("resultados_paciente")
            .select("orden_id,estado,semaforo")
            .in_("orden_id", order_ids)
            .execute()
        )
        details = {}
        for item in detail_response.data or []:
            details.setdefault(item["orden_id"], []).append(item)
        results = {
            item["orden_id"]: item
            for item in (result_response.data or [])
        }
        for order in orders:
            total = float(order.get("total_pruebas") or 0)
            paid = float(order.get("total_abonos") or 0)
            order["saldo"] = max(total - paid, 0)
            order["estudios"] = details.get(order["id"], [])
            order["resultado_estado"] = (
                results.get(order["id"], {}).get("estado") or "pendiente"
            )
            order["fecha"] = str(order.get("creado_en") or "")[:10]
        return orders
    except Exception:
        logger.exception("No se pudo obtener el historial del paciente %s", paciente_id)
        return []


def obtener_resumen_mostrador(limit=6):
    """Indicadores y actividad reciente del mostrador usando datos reales."""
    summary = {
        "ordenes_hoy": 0,
        "pagos_pendientes": 0,
        "muestras_pendientes": 0,
        "resultados_listos": 0,
        "ordenes_recientes": [],
    }
    counters_loaded = False
    try:
        try:
            counters_response = supabase.rpc(
                "obtener_contadores_mostrador_app"
            ).execute()
            if isinstance(counters_response.data, dict):
                counters_loaded = True
                for key in (
                    "ordenes_hoy", "pagos_pendientes",
                    "muestras_pendientes", "resultados_listos",
                ):
                    summary[key] = int(counters_response.data.get(key) or 0)
        except Exception:
            logger.warning(
                "RPC obtener_contadores_mostrador_app no disponible",
                exc_info=True,
            )
        response = supabase.rpc(
            "listar_ordenes_app", {"p_limite": 100}
        ).execute()
        orders = response.data if isinstance(response.data, list) else []
        today = datetime.now().date()

        patient_ids = sorted({
            order.get("paciente_id")
            for order in orders[:limit]
            if order.get("paciente_id") is not None
        })
        patients = {}
        if patient_ids:
            patient_response = (
                supabase.table("pacientes")
                .select("id,nombres,apellidos")
                .in_("id", patient_ids)
                .execute()
            )
            patients = {
                patient["id"]: patient
                for patient in (patient_response.data or [])
            }

        for order in orders:
            created_at = order.get("creado_en")
            order_date = None
            if created_at:
                try:
                    order_date = datetime.fromisoformat(
                        str(created_at).replace("Z", "+00:00")
                    ).date()
                except (TypeError, ValueError):
                    pass
            if order_date == today and not counters_loaded:
                summary["ordenes_hoy"] += 1
            if order.get("estado") != "pagada" and not counters_loaded:
                summary["pagos_pendientes"] += 1
            if order.get("flujo") == "muestra_pendiente" and not counters_loaded:
                summary["muestras_pendientes"] += 1

        for order in orders[:limit]:
            patient = patients.get(order.get("paciente_id"))
            total = float(order.get("total_pruebas") or 0)
            paid = float(order.get("total_abonos") or 0)
            created_at = str(order.get("creado_en") or "")
            summary["ordenes_recientes"].append({
                "id": order.get("id"),
                "paciente": (
                    f"{patient.get('nombres', '')} {patient.get('apellidos', '')}".strip()
                    if patient else "Paciente no disponible"
                ),
                "fecha": created_at[:10] if created_at else "—",
                "estado": order.get("estado") or "pendiente",
                "flujo": order.get("flujo") or "muestra_pendiente",
                "saldo": max(total - paid, 0),
            })

        try:
            ready_response = supabase.rpc("contar_resultados_listos_app").execute()
            summary["resultados_listos"] = int(ready_response.data or 0)
        except Exception:
            ready_response = (
                supabase.table("resultados_paciente")
                .select("orden_id,estado").eq("estado", "finalizado").execute()
            )
            summary["resultados_listos"] = len({
                result.get("orden_id")
                for result in (ready_response.data or [])
                if result.get("orden_id") is not None
            })
    except Exception:
        logger.exception("No se pudo obtener el resumen de mostrador")

    return summary


def obtener_resultados_listos():
    """Resultados finalizados que todavía no han sido entregados."""
    try:
        response = supabase.rpc("listar_resultados_listos_app").execute()
        results = response.data if isinstance(response.data, list) else []
        order_ids = sorted({
            item.get("orden_id") for item in results if item.get("orden_id") is not None
        })
        balances = {}
        if order_ids:
            order_response = (
                supabase_admin.table("ordenes")
                .select("id,total_pruebas,total_abonos,estado")
                .in_("id", order_ids).execute()
            )
            for order in order_response.data or []:
                total = float(order.get("total_pruebas") or 0)
                paid = float(order.get("total_abonos") or 0)
                balances[order["id"]] = {
                    "total": total,
                    "pagado": paid,
                    "saldo": max(total - paid, 0),
                    "estado_pago": order.get("estado") or "pendiente",
                }
        for item in results:
            item.update(balances.get(item.get("orden_id"), {
                "total": 0.0, "pagado": 0.0, "saldo": 0.0,
                "estado_pago": "pendiente",
            }))
            item["actualizado_en_local"] = convertir_fecha_hora_local(
                item.get("actualizado_en")
            )
        return results
    except Exception:
        logger.exception("No se pudieron obtener los resultados listos")
        return []


def obtener_empleado_basico(empleado_id):
    if not empleado_id:
        return None
    try:
        response = supabase.table("empleados").select(
            "id,nombres,apellidos"
        ).eq("id", int(empleado_id)).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception:
        logger.exception("No se pudo consultar al empleado %s", empleado_id)
        return None


def obtener_saldo_orden(orden_id):
    """Consulta la orden desde el servidor, sin quedar bloqueado por RLS del cliente."""
    response = (
        supabase_admin.table("ordenes")
        .select("id,total_pruebas,total_abonos,estado")
        .eq("id", int(orden_id)).limit(1).execute()
    )
    if not response.data:
        return None
    order = response.data[0]
    total = float(order.get("total_pruebas") or 0)
    paid = float(order.get("total_abonos") or 0)
    return {
        "total": total,
        "pagado": paid,
        "saldo": max(total - paid, 0),
        "estado": order.get("estado") or "pendiente",
    }


def obtener_historial_resultados():
    """Resultados finalizados, pendientes de entrega y ya entregados."""
    try:
        response = supabase.rpc("listar_historial_resultados_app").execute()
        results = response.data if isinstance(response.data, list) else []
        for item in results:
            item["actualizado_en_local"] = convertir_fecha_hora_local(
                item.get("actualizado_en")
            )
            item["entregado_en_local"] = convertir_fecha_hora_local(
                item.get("entregado_en")
            )
            item["orden_creada_en_local"] = convertir_fecha_hora_local(
                item.get("orden_creada_en")
            )
        return results
    except Exception:
        logger.exception("No se pudo obtener el historial de resultados")
        return []


def obtener_historial_resultados_mostrador():
    """Todos los resultados finalizados, con entrega, estudios y estado de cuenta."""
    results = obtener_historial_resultados()
    if not results:
        return []

    order_ids = sorted({
        int(item["orden_id"])
        for item in results
        if item.get("orden_id") is not None
    })
    balances = {}
    studies_by_order = {}

    try:
        response = (
            supabase_admin.table("ordenes")
            .select("id,total_pruebas,total_abonos,estado,creado_en")
            .in_("id", order_ids)
            .execute()
        )
        for order in response.data or []:
            total = float(order.get("total_pruebas") or 0)
            paid = float(order.get("total_abonos") or 0)
            balance = max(total - paid, 0)
            balances[int(order["id"])] = {
                "total": total,
                "pagado": paid,
                "saldo": balance,
                "estado_pago": "pagada" if balance <= 0.009 else "pendiente",
                "fecha_orden": convertir_fecha_hora_local(order.get("creado_en"))[:10],
            }
    except Exception:
        logger.exception("No se pudo enriquecer el estado de cuenta del historial de resultados")

    try:
        response = (
            supabase_admin.table("orden_pruebas_detalle")
            .select("orden_id,nombre_prueba,tipo_prueba,cantidad")
            .in_("orden_id", order_ids)
            .order("id", desc=False)
            .execute()
        )
        for study in response.data or []:
            order_id = int(study["orden_id"])
            studies_by_order.setdefault(order_id, []).append({
                "nombre": study.get("nombre_prueba") or "Estudio sin nombre",
                "tipo": study.get("tipo_prueba") or "",
                "cantidad": int(study.get("cantidad") or 1),
            })
    except Exception:
        logger.exception("No se pudieron enriquecer los estudios del historial de resultados")

    for item in results:
        order_id = int(item["orden_id"])
        item.update(balances.get(order_id, {
            "total": 0.0,
            "pagado": 0.0,
            "saldo": 0.0,
            "estado_pago": "pagada",
            "fecha_orden": "",
        }))
        item["estudios"] = studies_by_order.get(order_id, [])
        item["entregado"] = (
            item.get("entregado") is True
            or str(item.get("entregado") or "").strip().lower()
            in {"true", "1", "t", "yes"}
        )
        item["estado_entrega"] = "entregado" if item["entregado"] else "pendiente"
        item["fecha_resultado"] = (
            item.get("actualizado_en_local")
            or convertir_fecha_hora_local(item.get("actualizado_en"))
        )
        item["fecha_entrega"] = (
            item.get("entregado_en_local")
            or convertir_fecha_hora_local(item.get("entregado_en"))
            if item["entregado"] else ""
        )

    results.sort(key=lambda item: item.get("fecha_resultado") or "", reverse=True)
    return results


def obtener_resultados_entregados():
    """Compatibilidad: devuelve únicamente resultados ya entregados."""
    return [
        item for item in obtener_historial_resultados_mostrador()
        if item.get("entregado") is True
    ]


def finalizar_entrega_resultado(orden_id, usuario_id, medio_entrega):
    """Marca la entrega conservando resultado, orden y trazabilidad."""
    response = supabase.rpc(
        "finalizar_entrega_resultado_app",
        {
            "p_orden_id": int(orden_id),
            "p_usuario_id": int(usuario_id),
            "p_medio_entrega": str(medio_entrega).strip().lower(),
        },
    ).execute()
    return bool(response.data)


def obtener_notificaciones_resultados(usuario_id):
    """Avisos de resultados listos, con lectura diaria individual."""
    if not usuario_id:
        return []
    today = datetime.now().date()
    results = obtener_resultados_listos()
    notifications = [
        {
            "key": f"resultado:{item['orden_id']}:ready",
            "title": "Resultado listo para entregar",
            "detail": (
                f"Orden #{int(item['orden_id']):04d} · "
                f"{item.get('nombres', '')} {item.get('apellidos', '')}".strip()
            ),
            "type": "result_ready",
            "url": "/listos",
            "orden_id": item["orden_id"],
        }
        for item in results
    ]
    try:
        read_response = (
            supabase.table("notificaciones_leidas").select("clave")
            .eq("usuario_id", int(usuario_id))
            .eq("fecha", today.isoformat()).execute()
        )
        read_keys = {item["clave"] for item in (read_response.data or [])}
        for notification in notifications:
            notification["read"] = notification["key"] in read_keys
    except Exception:
        logger.exception("No se pudo consultar la lectura de resultados listos")
        for notification in notifications:
            notification["read"] = False
    return notifications

def obtener_detalle_pruebas_por_orden(orden_id: int):
    try:
        rpc_response = supabase.rpc(
            "obtener_detalle_orden_app", {"p_orden_id": int(orden_id)}
        ).execute()
        if isinstance(rpc_response.data, list):
            return rpc_response.data
    except Exception:
        pass
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
        resp = supabase.rpc("siguiente_folio_orden_app").execute()
        if resp.data is not None:
            return int(resp.data)
    except Exception:
        logger.warning("RPC siguiente_folio_orden_app no disponible", exc_info=True)
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
        try:
            resp = supabase.rpc("listar_ordenes_muestra_app").execute()
            if isinstance(resp.data, list):
                return resp.data
            ordenes = []
        except Exception:
            resp = (
                supabase.table("ordenes")
                .select("id,paciente_id,cuarto,flujo,creado_en")
                .eq("flujo", "muestra_pendiente")
                .order("creado_en", desc=True).execute()
            )
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


def obtener_muestras_orden(orden_id):
    response = supabase.rpc(
        "obtener_muestras_orden_app", {"p_orden_id": int(orden_id)}
    ).execute()
    return response.data if isinstance(response.data, list) else []


def actualizar_muestra_orden(
    orden_id, tipo_muestra, recolectada, usuario_id, observaciones=None
):
    response = supabase.rpc(
        "actualizar_muestra_orden_app",
        {
            "p_orden_id": int(orden_id),
            "p_tipo_muestra": str(tipo_muestra).strip().lower(),
            "p_recolectada": bool(recolectada),
            "p_usuario_id": int(usuario_id),
            "p_observaciones": (observaciones or "").strip() or None,
        },
    ).execute()
    return bool(response.data)


def finalizar_muestras_orden(orden_id, usuario_id):
    response = supabase.rpc(
        "finalizar_muestras_orden_app",
        {"p_orden_id": int(orden_id), "p_usuario_id": int(usuario_id)},
    ).execute()
    return bool(response.data)


def registrar_comunicacion_resultado(orden_id, usuario_id, accion, medio,
                                     saldo=0, detalle=None):
    """Audita avisos y envíos digitales sin guardar datos sensibles del archivo."""
    try:
        actor = {}
        if usuario_id:
            user_rows = (
                supabase_admin.table("usuarios").select("id,username")
                .eq("id", int(usuario_id)).limit(1).execute()
            ).data or []
            employee_rows = (
                supabase_admin.table("empleados").select("id,nombres,apellidos")
                .eq("usuario_id", int(usuario_id)).limit(1).execute()
            ).data or []
            user = user_rows[0] if user_rows else {}
            employee = employee_rows[0] if employee_rows else {}
            actor = {
                "empleado_id": employee.get("id"),
                "username": user.get("username"),
                "nombre": " ".join(filter(None, [
                    employee.get("nombres"), employee.get("apellidos")
                ])),
            }
        titles = {
            "aviso": "Paciente notificado de resultados listos",
            "envio_pdf": "Resultado PDF compartido con el paciente",
            "finalizacion": "Entrega de resultados finalizada",
        }
        event_type = str(accion)
        supabase_storage.table("bitacora_eventos").insert({
            "modulo": "Mostrador",
            # La tabla usa una nomenclatura cerrada para esta columna.
            # El tipo operativo concreto se conserva en titulo y metadata.
            "accion": "actualizar",
            "severidad": "warning" if float(saldo or 0) > 0.009 else "info",
            "titulo": titles.get(event_type, "Resultado comunicado al paciente"),
            "detalle": detalle or (
                f"Orden #{int(orden_id):04d}: {event_type} por {medio}. "
                f"Saldo al momento: ${float(saldo or 0):.2f}."
            ),
            "entidad_tipo": "ordenes",
            "entidad_id": str(int(orden_id)),
            "actor_usuario_id": usuario_id,
            "actor_empleado_id": actor.get("empleado_id"),
            "actor_username": actor.get("username"),
            "actor_nombre": actor.get("nombre"),
            "metadata": {
                "orden_id": int(orden_id), "accion_resultado": event_type,
                "medio": str(medio), "saldo": float(saldo or 0),
            },
        }).execute()
        return True
    except Exception:
        logger.exception("No se pudo auditar la comunicación de la orden %s", orden_id)
        return False


ESTADOS_EXTERNOS_ACTIVOS = (
    "muestra_pendiente", "listo_envio", "enviado", "recibido_proveedor",
    "resultado_recibido", "rechazado", "requiere_nueva_muestra",
)


def _hidratar_estudios_externos(rows):
    """Agrega nombres sin depender de relaciones embebidas de PostgREST."""
    rows = [dict(row) for row in (rows or [])]
    if not rows:
        return []

    def indexed(table, ids, columns):
        ids = sorted({int(value) for value in ids if value is not None})
        if not ids:
            return {}
        response = supabase_admin.table(table).select(columns).in_("id", ids).execute()
        return {int(item["id"]): item for item in (response.data or [])}

    detalles = indexed(
        "orden_pruebas_detalle", (r.get("orden_detalle_id") for r in rows),
        "id,nombre_prueba,tipo_prueba",
    )
    ordenes = indexed(
        "ordenes", (r.get("orden_id") for r in rows),
        "id,paciente_id,creado_en,cuarto",
    )
    proveedores = indexed(
        "proveedores", (r.get("proveedor_id") for r in rows),
        "id,nombre,telefono,correo,calle,numero_ext,numero_int,codigo_postal,municipio,estado",
    )
    pacientes = indexed(
        "pacientes", (o.get("paciente_id") for o in ordenes.values()),
        "id,nombres,apellidos,telefono,fecha_nacimiento,sexo",
    )
    for row in rows:
        detalle = detalles.get(int(row.get("orden_detalle_id") or 0), {})
        orden = ordenes.get(int(row.get("orden_id") or 0), {})
        paciente = pacientes.get(int(orden.get("paciente_id") or 0), {})
        proveedor = proveedores.get(int(row.get("proveedor_id") or 0), {})
        row["nombre_prueba"] = detalle.get("nombre_prueba") or "Prueba externa"
        row["tipo_prueba"] = detalle.get("tipo_prueba") or ""
        row["nombre_paciente"] = " ".join(filter(None, (
            paciente.get("nombres"), paciente.get("apellidos")
        ))) or "Paciente desconocido"
        row["paciente"] = paciente
        row["proveedor"] = proveedor
        row["nombre_proveedor"] = proveedor.get("nombre") or "Proveedor sin nombre"
        row["orden_creada_en"] = orden.get("creado_en")
    return rows


def listar_estudios_externos(estados=None, orden_id=None):
    try:
        query = supabase_admin.table("estudios_externos").select("*")
        if estados:
            query = query.in_("estado", list(estados))
        if orden_id is not None:
            query = query.eq("orden_id", int(orden_id))
        response = query.order("creado_en", desc=True).execute()
        return _hidratar_estudios_externos(response.data or [])
    except Exception:
        logger.exception("No se pudieron consultar los estudios externos")
        return []


def marcar_estudios_externos_listos(orden_id, usuario_id):
    """Enfermería libera las pruebas externas al completar todas las muestras."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        response = (
            supabase_admin.table("estudios_externos")
            .update({
                "estado": "listo_envio",
                "listo_envio_en": now,
                "actualizado_en": now,
                "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
            })
            .eq("orden_id", int(orden_id))
            .in_("estado", ["muestra_pendiente", "requiere_nueva_muestra"])
            .execute()
        )
        return response.data or []
    except Exception:
        logger.exception("No se pudieron liberar los estudios externos de la orden")
        return []


def crear_envio_proveedor(estudio_ids, usuario_id, mensajeria=None,
                          numero_guia=None, fecha_prometida=None,
                          observaciones=None):
    ids = sorted({int(item) for item in estudio_ids or []})
    if not ids:
        raise ValueError("Selecciona al menos un estudio para el envío.")
    estudios = listar_estudios_externos(estados=["listo_envio"], orden_id=None)
    estudios = [item for item in estudios if int(item["id"]) in ids]
    if len(estudios) != len(ids):
        raise ValueError("Uno o más estudios ya no están listos para envío.")
    proveedores = {int(item["proveedor_id"]) for item in estudios}
    if len(proveedores) != 1:
        raise ValueError("Cada envío debe contener estudios de un solo proveedor.")

    proveedor_id = proveedores.pop()
    if not fecha_prometida:
        dias = max(int(item.get("tiempo_entrega_dias") or 0) for item in estudios)
        fecha_prometida = (
            datetime.now(APP_LOCAL_TIMEZONE).date() + timedelta(days=dias)
        ).isoformat()
    now = datetime.now(timezone.utc).isoformat()
    envio_data = {
        "proveedor_id": proveedor_id,
        "estado": "enviado",
        "mensajeria": (mensajeria or "").strip() or None,
        "numero_guia": (numero_guia or "").strip() or None,
        "fecha_prometida": fecha_prometida,
        "enviado_en": now,
        "observaciones": (observaciones or "").strip() or None,
        "creado_por_usuario_id": int(usuario_id) if usuario_id else None,
    }
    envio = supabase_admin.table("envios_proveedor").insert(envio_data).execute().data[0]
    try:
        supabase_admin.table("envios_proveedor_detalle").insert([
            {"envio_id": envio["id"], "estudio_externo_id": item_id}
            for item_id in ids
        ]).execute()
        supabase_admin.table("estudios_externos").update({
            "estado": "enviado", "enviado_en": now,
            "fecha_prometida": fecha_prometida, "actualizado_en": now,
            "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
        }).in_("id", ids).execute()
    except Exception:
        supabase_admin.table("envios_proveedor").delete().eq("id", envio["id"]).execute()
        raise
    return envio


def actualizar_estado_estudio_externo(estudio_id, estado, usuario_id,
                                      referencia=None, observaciones=None):
    permitidos = {
        "recibido_proveedor", "resultado_recibido", "validado", "rechazado",
        "requiere_nueva_muestra", "cancelado",
    }
    if estado not in permitidos:
        raise ValueError("Estado de estudio externo no permitido.")
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "estado": estado, "actualizado_en": now,
        "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
    }
    timestamp_fields = {
        "recibido_proveedor": "recibido_proveedor_en",
        "resultado_recibido": "resultado_recibido_en",
        "validado": "validado_en",
    }
    if estado in timestamp_fields:
        data[timestamp_fields[estado]] = now
    if referencia is not None:
        data["referencia_proveedor"] = (referencia or "").strip() or None
    if observaciones is not None:
        data["observaciones"] = (observaciones or "").strip() or None
    response = (
        supabase_admin.table("estudios_externos").update(data)
        .eq("id", int(estudio_id)).execute()
    )
    return response.data[0] if response.data else None


def validar_estudios_externos_orden(orden_id, usuario_id):
    now = datetime.now(timezone.utc).isoformat()
    try:
        response = (
            supabase_admin.table("estudios_externos")
            .update({
                "estado": "validado", "validado_en": now,
                "actualizado_en": now,
                "actualizado_por_usuario_id": int(usuario_id) if usuario_id else None,
            })
            .eq("orden_id", int(orden_id))
            .eq("estado", "resultado_recibido").execute()
        )
        return response.data or []
    except Exception:
        logger.exception("No se pudieron validar los estudios externos de la orden")
        return []


def obtener_envio_proveedor(envio_id):
    response = (
        supabase_admin.table("envios_proveedor").select("*")
        .eq("id", int(envio_id)).limit(1).execute()
    )
    if not response.data:
        return None
    envio = dict(response.data[0])
    detalles = (
        supabase_admin.table("envios_proveedor_detalle")
        .select("estudio_externo_id").eq("envio_id", int(envio_id)).execute()
    ).data or []
    ids = [item["estudio_externo_id"] for item in detalles]
    estudios = listar_estudios_externos()
    envio["estudios"] = [item for item in estudios if item["id"] in ids]
    proveedores = obtener_proveedores()
    envio["proveedor"] = next(
        (item for item in proveedores if item["id"] == envio["proveedor_id"]), {}
    )
    return envio


def obtener_configuracion_etiquetas():
    response = supabase.rpc("obtener_configuracion_etiquetas_app").execute()
    return response.data if isinstance(response.data, dict) else {
        "ancho_mm": 60, "alto_mm": 40,
        "copias_predeterminadas": 1, "mostrar_qr": True,
    }


def actualizar_configuracion_etiquetas(
    ancho_mm, alto_mm, copias, mostrar_qr, usuario_id
):
    response = supabase.rpc(
        "actualizar_configuracion_etiquetas_app",
        {
            "p_ancho_mm": int(ancho_mm),
            "p_alto_mm": int(alto_mm),
            "p_copias": int(copias),
            "p_mostrar_qr": bool(mostrar_qr),
            "p_usuario_id": int(usuario_id),
        },
    ).execute()
    return response.data


def listar_etiquetas_muestra():
    response = supabase.rpc("listar_etiquetas_muestra_app").execute()
    return response.data if isinstance(response.data, list) else []


def obtener_etiqueta_por_token(token):
    response = supabase.rpc(
        "obtener_etiqueta_por_token_app", {"p_token": str(token)}
    ).execute()
    return response.data if isinstance(response.data, dict) else None


def registrar_impresion_etiquetas(muestra_ids, copias, usuario_id):
    response = supabase.rpc(
        "registrar_impresion_etiquetas_app",
        {
            "p_muestra_ids": [int(item) for item in muestra_ids],
            "p_copias": int(copias),
            "p_usuario_id": int(usuario_id),
        },
    ).execute()
    return int(response.data or 0)


def obtener_captura_resultados(orden_id):
    response = supabase.rpc(
        "obtener_captura_resultados_app", {"p_orden_id": int(orden_id)}
    ).execute()
    return response.data if isinstance(response.data, dict) else None


def guardar_borrador_resultado(orden_id, detalle_id, valores, usuario_id):
    response = supabase.rpc(
        "guardar_borrador_resultado_app",
        {
            "p_orden_id": int(orden_id),
            "p_detalle_id": int(detalle_id),
            "p_valores": valores,
            "p_usuario_id": int(usuario_id),
        },
    ).execute()
    return response.data


def registrar_ejecucion_resultado(
    orden_id,
    detalle_id,
    valores,
    evaluaciones,
    usuario_id,
    clave_idempotencia,
    verificacion_de_id=None,
):
    response = supabase.rpc(
        "registrar_ejecucion_resultado_app",
        {
            "p_orden_id": int(orden_id),
            "p_detalle_id": int(detalle_id),
            "p_valores": valores,
            "p_evaluaciones": evaluaciones,
            "p_usuario_id": int(usuario_id),
            "p_clave_idempotencia": str(clave_idempotencia),
            "p_verificacion_de_id": (
                int(verificacion_de_id) if verificacion_de_id else None
            ),
        },
    ).execute()
    return response.data


def finalizar_resultados_orden(orden_id, usuario_id):
    response = supabase.rpc(
        "finalizar_resultados_orden_app",
        {"p_orden_id": int(orden_id), "p_usuario_id": int(usuario_id)},
    ).execute()
    return bool(response.data)


def obtener_firma_resultado(orden_id):
    response = supabase.rpc(
        "obtener_firma_resultado_app", {"p_orden_id": int(orden_id)}
    ).execute()
    return response.data if isinstance(response.data, dict) else {}


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
        try:
            resp = supabase.rpc(
                "listar_ordenes_app", {"p_limite": 200}
            ).execute()
            ordenes = [
                orden for orden in (resp.data or [])
                if orden.get("flujo") == "en_quimico"
            ]
        except Exception:
            resp = (
                supabase.table("ordenes")
                .select("id,paciente_id,cuarto,flujo,creado_en")
                .eq("flujo", "en_quimico")
                .order("creado_en", desc=True).execute()
            )
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
