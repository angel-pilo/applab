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
        {"text": "Generar orden",    "icon": "fa-file-medical", "url": "app_routes.nueva_orden"},
        {"text": "Resultados listos","icon": "fa-file-export",  "url": "app_routes.listos"},
        {"text": "Pacientes",        "icon": "fa-id-card",      "url": "app_routes.manage_patients"},
        {"text": "Órdenes recientes","icon": "fa-stream",       "url": "app_routes.recientes"},
        {
            "text": "Corte de caja",
            "icon": "fa-cash-register",
            "url": "app_routes.proximamente",
            "params": {"feature": "Corte de caja"},
            "badge": "Próximamente",
        },
        {"text": "Configuración",    "icon": "fa-cog",          "url": "app_routes.configuracion"},
    ],

    "Quimico": [
        {"text": "Resultados",       "icon": "fa-clipboard-check", "url": "app_routes.resultados"},
        {"text": "Resultados finalizados", "icon": "fa-file-medical-alt", "url": "app_routes.historial_resultados"},
        {"text": "Ingresar inventario", "icon": "fa-dolly-flatbed", "url": "app_routes.registrar_entrada_inventario"},
        {"text": "Control de calidad","icon":"fa-vials", "url": "app_routes.proximamente", "params": {"feature": "Control de calidad"}, "badge": "Próximamente"},
        {"text": "Equipos",          "icon": "fa-tools", "url": "app_routes.proximamente", "params": {"feature": "Equipos"}, "badge": "Próximamente"},
        {"text": "Incidencias",      "icon": "fa-flag", "url": "app_routes.proximamente", "params": {"feature": "Incidencias"}, "badge": "Próximamente"},
        {"text": "Configuración",    "icon": "fa-cog",              "url": "app_routes.configuracion"},
    ],

    "Enfermero": [
        {"text": "Faltantes de muestra","icon":"fa-vial",          "url": "app_routes.manage_muestra"},
        {"text": "Registro de toma",    "icon":"fa-syringe", "url": "app_routes.proximamente", "params": {"feature": "Registro de toma"}, "badge": "Próximamente"},
        {"text": "Etiquetas / QR",      "icon":"fa-qrcode",        "url": "app_routes.etiquetas_muestra"},
        {"text": "Bioseguridad",        "icon":"fa-shield-virus", "url": "app_routes.proximamente", "params": {"feature": "Bioseguridad"}, "badge": "Próximamente"},
        {"text": "Envío / Traslado",    "icon":"fa-truck", "url": "app_routes.proximamente", "params": {"feature": "Envío / Traslado"}, "badge": "Próximamente"},
        {"text": "Configuración",       "icon":"fa-cog",           "url": "app_routes.configuracion"},
    ],
}
