"""Catálogo central de permisos combinables de AppLab."""

PERMISSION_GROUPS = [
    {
        "key": "admin",
        "label": "Administración",
        "description": "Configuración y catálogos generales del laboratorio.",
        "icon": "fa-user-shield",
        "permissions": [
            ("admin.dashboard", "Ver panel administrativo"),
            ("admin.system_settings", "Administrar políticas del sistema"),
            ("admin.override", "Autorizar excepciones con contraseña"),
            ("admin.employees", "Administrar empleados y permisos"),
            ("admin.tests", "Administrar pruebas clínicas"),
            ("admin.inventory", "Administrar catálogo de reactivos"),
            ("admin.providers", "Administrar proveedores"),
            ("admin.doctors", "Administrar médicos"),
            ("admin.hospitals", "Administrar hospitales"),
            ("admin.patients", "Desactivar o reactivar pacientes"),
            ("admin.backlog", "Consultar bitácora de cambios"),
            ("admin.labels", "Configurar impresión de etiquetas"),
        ],
    },
    {
        "key": "mostrador",
        "label": "Mostrador",
        "description": "Recepción, órdenes, pagos y entrega de resultados.",
        "icon": "fa-concierge-bell",
        "permissions": [
            ("front.dashboard", "Ver panel de mostrador"),
            ("front.orders.create", "Crear órdenes y registrar abonos"),
            ("front.orders.view", "Consultar órdenes recientes"),
            ("front.results.deliver", "Consultar y entregar resultados"),
            ("front.patients", "Registrar y editar pacientes"),
        ],
    },
    {
        "key": "nursing",
        "label": "Enfermería",
        "description": "Recepción, seguimiento e identificación de muestras.",
        "icon": "fa-syringe",
        "permissions": [
            ("nursing.dashboard", "Ver panel de enfermería"),
            ("nursing.samples", "Gestionar faltantes y toma de muestras"),
            ("nursing.labels", "Generar, imprimir y escanear etiquetas"),
        ],
    },
    {
        "key": "lab",
        "label": "Químico",
        "description": "Captura, verificación y consulta de resultados clínicos.",
        "icon": "fa-flask",
        "permissions": [
            ("lab.dashboard", "Ver panel de químico"),
            ("lab.results.capture", "Capturar y finalizar resultados"),
            ("lab.results.history", "Consultar resultados finalizados"),
            ("lab.inventory.entry", "Registrar entradas de inventario"),
            ("lab.external.manage", "Gestionar pruebas enviadas a proveedores"),
        ],
    },
]

VALID_PERMISSIONS = {
    code
    for group in PERMISSION_GROUPS
    for code, _label in group["permissions"]
}

# Permiso requerido por endpoint. Una colección significa "cualquiera de estos".
ENDPOINT_PERMISSIONS = {
    # Paneles
    "app_routes.admin_dashboard": "admin.dashboard",
    "app_routes.admin_operational_dashboard": "admin.dashboard",
    "app_routes.guardar_politicas_sistema": "admin.system_settings",
    "app_routes.guardar_configuracion_recibos_route": "admin.system_settings",
    "app_routes.guardar_identidad_laboratorio_route": "admin.system_settings",
    "app_routes.configuracion_sistema": "admin.system_settings",
    "app_routes.mostrador_dashboard": "front.dashboard",
    "app_routes.enfermero_dashboard": "nursing.dashboard",
    "app_routes.quimico_dashboard": "lab.dashboard",
    "app_routes.cambiar_area": "admin.dashboard",

    # Administración
    "app_routes.backlog": "admin.backlog",
    "app_routes.backlog_events": "admin.backlog",
    "app_routes.manage_employees": "admin.employees",
    "app_routes.add_employee": "admin.employees",
    "app_routes.edit_employee": "admin.employees",
    "app_routes.delete_employee": "admin.employees",
    "app_routes.activate_employee": "admin.employees",
    "app_routes.pruebas_clinicas": "admin.tests",
    "app_routes.add_prueba": "admin.tests",
    "app_routes.edit_prueba": "admin.tests",
    "app_routes.delete_prueba": "admin.tests",
    "app_routes.activate_prueba": "admin.tests",
    "app_routes.manage_inventory": "admin.inventory",
    "app_routes.add_reactivo": "admin.inventory",
    "app_routes.edit_reactivo": "admin.inventory",
    "app_routes.delete_reactivo": "admin.inventory",
    "app_routes.activate_reactivo": "admin.inventory",
    "app_routes.get_reactivo_details": "admin.inventory",
    "app_routes.manage_proveedores": "admin.providers",
    "app_routes.add_proveedor": {"admin.providers", "admin.inventory"},
    "app_routes.api_proveedores_activos": {"admin.providers", "admin.inventory"},
    "app_routes.edit_proveedor": "admin.providers",
    "app_routes.delete_proveedor": "admin.providers",
    "app_routes.activate_proveedor": "admin.providers",
    "app_routes.manage_doctores": "admin.doctors",
    "app_routes.edit_doctor": "admin.doctors",
    "app_routes.delete_doctor": "admin.doctors",
    "app_routes.activate_doctor": "admin.doctors",
    "app_routes.manage_hospitals": "admin.hospitals",
    "app_routes.edit_hospital": "admin.hospitals",
    "app_routes.delete_hospital": "admin.hospitals",
    "app_routes.activate_hospital": "admin.hospitals",
    "app_routes.delete_patient": "admin.patients",
    "app_routes.activate_patient": "admin.patients",
    "app_routes.reportes": "admin.dashboard",
    "app_routes.guardar_configuracion_etiquetas": "admin.labels",

    # Catálogos compartidos con el flujo de recepción
    "app_routes.add_hospital": {"admin.hospitals", "front.orders.create"},
    "app_routes.add_doctor": {"admin.doctors", "front.orders.create"},
    "app_routes.manage_patients": {"front.patients", "admin.patients"},
    "app_routes.historial_paciente": {"front.patients", "front.orders.view"},
    "app_routes.add_patient": "front.patients",
    "app_routes.edit_patient": "front.patients",

    # Mostrador
    "app_routes.nueva_orden": "front.orders.create",
    "app_routes.manage_orden": "front.orders.create",
    "app_routes.api_validar_orden": "front.orders.create",
    "app_routes.api_catalogos_orden": "front.orders.create",
    "app_routes.buscar_pacientes": "front.orders.create",
    "app_routes.resumen_paciente_orden": "front.orders.create",
    "app_routes.reporte": "front.orders.create",
    "app_routes.imprimir_orden": "front.orders.create",
    "app_routes.recibo_orden": {"front.orders.create", "front.orders.view"},
    "app_routes.recibo_orden_pdf": {"front.orders.create", "front.orders.view"},
    "app_routes.ticket_orden": {"front.orders.create", "front.orders.view"},
    "app_routes.abonar_orden": "front.orders.create",
    "app_routes.manage_orden_pruebas": "front.orders.create",
    "app_routes.guardar_estudios_orden": "front.orders.create",
    "app_routes.recientes": "front.orders.view",
    "app_routes.api_resumen_mostrador": {"front.dashboard", "front.orders.view"},
    "app_routes.faltantes": "front.orders.view",
    "app_routes.listos": "front.results.deliver",
    "app_routes.entregar_resultado": "front.results.deliver",
    "app_routes.mostrar_resultados": "front.results.deliver",

    # Enfermería
    "app_routes.manage_muestra": "nursing.samples",
    "app_routes.pacientes": "nursing.samples",
    "app_routes.api_finalizar_muestra": "nursing.samples",
    "app_routes.api_requisitos_muestra": "nursing.samples",
    "app_routes.api_actualizar_requisito_muestra": "nursing.samples",
    "app_routes.etiquetas_muestra": {"nursing.labels", "admin.labels", "lab.results.capture"},
    "app_routes.api_registrar_impresion_etiquetas": {"nursing.labels", "admin.labels", "lab.results.capture"},

    # Químico y acciones compartidas
    "app_routes.resultados": "lab.results.capture",
    "app_routes.historial_resultados": "lab.results.history",
    "app_routes.captura_resultados": "lab.results.capture",
    "app_routes.captura_resultados_legacy": "lab.results.capture",
    "app_routes.api_ejecutar_resultado": "lab.results.capture",
    "app_routes.api_guardar_borrador_resultado": "lab.results.capture",
    "app_routes.obtener_ordenes_pendientes": "lab.results.capture",
    "app_routes.guardar_resultados": "lab.results.capture",
    "app_routes.registrar_entrada_inventario": {"lab.inventory.entry", "admin.inventory"},
    "app_routes.estudios_externos": "lab.external.manage",
    "app_routes.api_crear_envio_externo": "lab.external.manage",
    "app_routes.api_estado_estudio_externo": "lab.external.manage",
    "app_routes.subir_resultado_externo": "lab.external.manage",
    "app_routes.documento_resultado_externo": "lab.external.manage",
    "app_routes.manifiesto_envio_externo": "lab.external.manage",
    "app_routes.get_analisis": {"nursing.samples", "lab.results.capture"},
    "app_routes.escanear_etiqueta_muestra": {"nursing.labels", "lab.results.capture"},
    "app_routes.imprimir_resultados_laboratorio": {
        "lab.results.capture", "lab.results.history", "front.results.deliver",
        "front.patients", "front.orders.view"
    },
    "app_routes.finalizar_resultados": "lab.results.capture",
    "app_routes.finalizar_resultados_legacy": "lab.results.capture",
}


def normalize_permissions(values):
    """Filtra valores desconocidos y devuelve una lista estable."""
    return sorted({str(value) for value in (values or []) if value in VALID_PERMISSIONS})


def endpoint_is_allowed(endpoint, permissions):
    required = ENDPOINT_PERMISSIONS.get(endpoint)
    if not required:
        return False
    required = {required} if isinstance(required, str) else set(required)
    return bool(required.intersection(permissions or []))


def preferred_home(permissions):
    options = (
        ("admin.dashboard", "app_routes.admin_dashboard"),
        ("front.dashboard", "app_routes.mostrador_dashboard"),
        ("nursing.dashboard", "app_routes.enfermero_dashboard"),
        ("lab.dashboard", "app_routes.quimico_dashboard"),
        ("front.orders.create", "app_routes.nueva_orden"),
        ("front.orders.view", "app_routes.recientes"),
        ("front.results.deliver", "app_routes.listos"),
        ("front.patients", "app_routes.manage_patients"),
        ("nursing.samples", "app_routes.manage_muestra"),
        ("nursing.labels", "app_routes.etiquetas_muestra"),
        ("lab.results.capture", "app_routes.resultados"),
        ("lab.results.history", "app_routes.historial_resultados"),
        ("lab.inventory.entry", "app_routes.registrar_entrada_inventario"),
        ("lab.external.manage", "app_routes.estudios_externos"),
        ("admin.tests", "app_routes.pruebas_clinicas"),
        ("admin.inventory", "app_routes.manage_inventory"),
        ("admin.providers", "app_routes.manage_proveedores"),
        ("admin.doctors", "app_routes.manage_doctores"),
        ("admin.hospitals", "app_routes.manage_hospitals"),
        ("admin.patients", "app_routes.manage_patients"),
        ("admin.employees", "app_routes.manage_employees"),
        ("admin.backlog", "app_routes.backlog"),
        ("admin.system_settings", "app_routes.configuracion_sistema"),
    )
    granted = set(permissions or [])
    return next((endpoint for code, endpoint in options if code in granted), None)
