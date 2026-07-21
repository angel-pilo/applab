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
        {"text": "Configuración","icon": "fa-cog",              "url": "app_routes.configuracion"},  
    ],

    "Mostrador": [
        {"text": "Generar orden",    "icon": "fa-file-medical", "url": "app_routes.manage_orden"},
        {"text": "Resultados listos","icon": "fa-file-export",  "url": "app_routes.listos"},
        {"text": "Pacientes",        "icon": "fa-id-card",      "url": "app_routes.manage_patients"},
        {"text": "Corte de caja",    "icon": "fa-cash-register","url": "app_routes.proximamente"},
        {"text": "Órdenes recientes","icon": "fa-stream",       "url": "app_routes.recientes"},
        {"text": "Configuración",    "icon": "fa-cog",          "url": "app_routes.proximamente"},
    ],

    "Quimico": [
        {"text": "Resultados",       "icon": "fa-clipboard-check", "url": "app_routes.resultados"},
        {"text": "Control de calidad","icon":"fa-vials",            "url": "app_routes.proximamente"},
        {"text": "Equipos",          "icon": "fa-tools",            "url": "app_routes.proximamente"},
        {"text": "Incidencias",      "icon": "fa-flag",             "url": "app_routes.proximamente"},
        {"text": "Configuración",    "icon": "fa-cog",              "url": "app_routes.configuracion"},
    ],

    "Enfermero": [
        {"text": "Faltantes de muestra","icon":"fa-vial",          "url": "app_routes.manage_muestra"},
        {"text": "Registro de toma",    "icon":"fa-syringe",       "url": "app_routes.proximamente"},
        {"text": "Etiquetas / QR",      "icon":"fa-qrcode",        "url": "app_routes.proximamente"},
        {"text": "Bioseguridad",        "icon":"fa-shield-virus",  "url": "app_routes.proximamente"},
        {"text": "Envío / Traslado",    "icon":"fa-truck",         "url": "app_routes.proximamente"},
        {"text": "Configuración",       "icon":"fa-cog",           "url": "app_routes.configuracion"},
    ],
}
