# app.py
import os
from dotenv import load_dotenv
from flask import Flask, session, render_template

load_dotenv()

# --- Supabase (opcional) ---
try:
    from supabase_client import supabase
except Exception:
    supabase = None

# --- Menú por rol ---
try:
    from menus import ROLE_MENU
except Exception:
    ROLE_MENU = {
        "Admin": [
            {"text": "Pruebas", "icon": "fa-clipboard-check", "url": "app_routes.pruebas_clinicas"},
            {"text": "Inventario", "icon": "fa-vial", "url": "app_routes.manage_inventory"},
            {"text": "Pacientes", "icon": "fa-id-card", "url": "app_routes.manage_patients"},
            {"text": "Proveedores", "icon": "fa-truck", "url": "app_routes.manage_proveedores"},
            {"text": "Doctores", "icon": "fa-stethoscope", "url": "app_routes.manage_doctores"},
            {"text": "Hospitales", "icon": "fa-hospital", "url": "app_routes.manage_hospitals"},
            {"text": "Empleados", "icon": "fa-user-tie", "url": "app_routes.manage_employees"},
            {"text": "Backlog", "icon": "fa-history", "url": "app_routes.backlog"},
            {"text": "Configuración", "icon": "fa-cog", "url": "#"},
        ]
    }

# Dashboard de inicio por rol (botón "Inicio" en sidebar)
ROLE_HOME = {
    "Admin":      "app_routes.admin_dashboard",
    "Mostrador":  "app_routes.mostrador_dashboard",
    "Quimico":    "app_routes.quimico_dashboard",
    "Enfermero": "app_routes.enfermero_dashboard",
}


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Configuración base ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecreto")
    app.config["SUPABASE_URL"] = os.getenv("SUPABASE_URL", "")
    app.config["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY", "")
    if supabase is not None:
        app.config["SUPABASE"] = supabase

    # --- Validación de envs (si estás sin Supabase en dev y quieres seguir, comenta este bloque) ---
    if not app.config["SUPABASE_URL"] or not app.config["SUPABASE_KEY"]:
        raise RuntimeError("Faltan SUPABASE_URL y/o SUPABASE_KEY en .env")

    # --- Registro de rutas (import tardío para evitar import circular) ---
    from routes import app_routes
    app.register_blueprint(app_routes)

    # --- Variables globales para Jinja ---
    @app.context_processor
    def inject_role_menu():
        # Endpoints disponibles para validar antes de url_for en plantillas
        available_endpoints = set(app.view_functions.keys())
        return {
            "role_sidebar_items": ROLE_MENU,
            "rol_actual": session.get("rol", ""),
            "role_home": ROLE_HOME,
            "available_endpoints": available_endpoints,
        }
    
        # --- Páginas de error personalizadas ---

    @app.errorhandler(404)
    def page_not_found(e):
        # Puedes loguear el error aquí si quieres
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        # Aquí también puedes loguear e, mandarlo a Supabase, etc.
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403


    # --- Healthcheck ---
    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
