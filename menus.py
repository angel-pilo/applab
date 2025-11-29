# menus.py
ROLE_MENU = {
    "Admin": [
        {"text": "Pruebas",      "icon": "fa-clipboard-check", "url": "app_routes.pruebas_clinicas"},
        {"text": "Inventario",   "icon": "fa-vial",             "url": "app_routes.manage_inventory"},
        {"text": "Pacientes",    "icon": "fa-id-card",          "url": "app_routes.manage_patients"},
        {"text": "Proveedores",  "icon": "fa-truck",            "url": "app_routes.manage_proveedores"},
        {"text": "Doctores",     "icon": "fa-stethoscope",      "url": "app_routes.manage_doctores"},
        {"text": "Hospitales",   "icon": "fa-hospital",         "url": "app_routes.manage_hospitals"},
        {"text": "Empleados",    "icon": "fa-user-tie",         "url": "app_routes.manage_employees"},
        {"text": "Backlog",      "icon": "fa-history",          "url": "app_routes.backlog"},
        {"text": "Configuración","icon": "fa-cog",              "url": "#"},  # sin badge, placeholder
    ],

    "Mostrador": [
        {"text": "Generar orden",    "icon": "fa-file-medical", "url": "app_routes.manage_orden"},
        {"text": "Resultados listos","icon": "fa-file-export",  "url": "#"},
        {"text": "Pacientes",        "icon": "fa-id-card",      "url": "app_routes.manage_patients"},
        {"text": "Corte de caja",    "icon": "fa-cash-register","url": "#"},
        {"text": "Órdenes recientes","icon": "fa-stream",       "url": "#"},
        {"text": "Configuración",    "icon": "fa-cog",          "url": "#"},
    ],

    "Químico": [
        {"text": "Resultados",       "icon": "fa-clipboard-check", "url": "app_routes.resultados"},
        {"text": "Control de calidad","icon":"fa-vials",            "url": "#"},
        {"text": "Equipos",          "icon": "fa-tools",            "url": "#"},
        {"text": "Incidencias",      "icon": "fa-flag",             "url": "#"},
        {"text": "Configuración",    "icon": "fa-cog",              "url": "#"},
    ],

    "Enfermería": [
        {"text": "Faltantes de muestra","icon":"fa-vial",          "url": "app_routes.manage_muestra"},
        {"text": "Registro de toma",    "icon":"fa-syringe",       "url": "#"},
        {"text": "Etiquetas / QR",      "icon":"fa-qrcode",        "url": "#"},
        {"text": "Bioseguridad",        "icon":"fa-shield-virus",  "url": "#"},
        {"text": "Envío / Traslado",    "icon":"fa-truck",         "url": "#"},
        {"text": "Configuración",       "icon":"fa-cog",           "url": "#"},
    ],
}
