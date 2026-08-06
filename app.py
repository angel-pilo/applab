# app.py
import os
from dotenv import load_dotenv
from flask import Flask, session, render_template
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

# --- Supabase (opcional) ---
from supabase_client import supabase


from menus import ROLE_MENU
from permissions import (
    PERMISSION_GROUPS,
    endpoint_is_allowed,
)

# Dashboard de inicio por rol (botón "Inicio" en sidebar)
ROLE_HOME = {
    "Admin":      "app_routes.admin_dashboard",
    "Mostrador":  "app_routes.mostrador_dashboard",
    "Quimico":    "app_routes.quimico_dashboard",
    "Enfermero": "app_routes.enfermero_dashboard",
    "Personalizado": "app_routes.dashboard",
}


def build_custom_menu(permissions):
    """Combina módulos de varios roles y elimina accesos repetidos."""
    permissions = set(permissions or [])
    dashboard_items = [
        ("admin.dashboard", "Panel administrativo", "fa-user-shield", "app_routes.admin_operational_dashboard"),
        ("front.dashboard", "Panel de mostrador", "fa-concierge-bell", "app_routes.mostrador_dashboard"),
        ("nursing.dashboard", "Panel de enfermería", "fa-syringe", "app_routes.enfermero_dashboard"),
        ("lab.dashboard", "Panel de químico", "fa-flask", "app_routes.quimico_dashboard"),
    ]
    items = [
        {"text": text, "icon": icon, "url": endpoint}
        for code, text, icon, endpoint in dashboard_items
        if code in permissions
    ]
    seen = {item["url"] for item in items}
    for role in ("Admin", "Mostrador", "Enfermero", "Quimico"):
        for source in ROLE_MENU.get(role, []):
            endpoint = source.get("url")
            if endpoint == "app_routes.configuracion":
                continue
            if endpoint in seen or not endpoint_is_allowed(endpoint, permissions):
                continue
            item = dict(source)
            item["text"] = f"{role} · {item['text']}"
            items.append(item)
            seen.add(endpoint)
    items.append({
        "text": "Mi cuenta",
        "icon": "fa-user-cog",
        "url": "app_routes.configuracion",
    })
    return items


def create_app() -> Flask:
    app = Flask(__name__)

    # --- Configuración base ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    public_https = os.getenv("APP_PUBLIC_HTTPS", "").lower() in {"1", "true", "yes"}
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=public_https,
    )
    if public_https:
        # El servidor solo escucha en localhost; Tailscale termina HTTPS.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.config["SUPABASE_URL"] = os.getenv("SUPABASE_URL", "")
    app.config["SUPABASE_KEY"] = os.getenv("SUPABASE_KEY", "")
    app.config["SUPABASE_AVATAR_BUCKET"] = os.getenv("SUPABASE_AVATAR_BUCKET", "")
    if supabase is not None:
        app.config["SUPABASE"] = supabase

    # --- Validación de envs (si estás sin Supabase en dev y quieres seguir, comenta este bloque) ---
    missing_settings = [
        name
        for name in ("SECRET_KEY", "SUPABASE_URL", "SUPABASE_KEY")
        if not app.config[name]
    ]
    if missing_settings:
        raise RuntimeError(
            f"Faltan variables de entorno obligatorias: {', '.join(missing_settings)}"
        )

    # --- Registro de rutas (import tardío para evitar import circular) ---
    from routes import app_routes
    app.register_blueprint(app_routes)

    # --- Variables globales para Jinja ---
    @app.context_processor
    def inject_role_menu():
        from services import obtener_identidad_laboratorio
        # Endpoints disponibles para validar antes de url_for en plantillas
        available_endpoints = set(app.view_functions.keys())
        menus = dict(ROLE_MENU)
        actual_role = session.get("rol", "")
        navigation_role = actual_role
        if actual_role == "Admin":
            requested_area = session.get("area_activa", "Admin")
            if requested_area in {"Admin", "Mostrador", "Enfermero", "Quimico"}:
                navigation_role = requested_area
        if actual_role == "Personalizado":
            menus["Personalizado"] = build_custom_menu(session.get("permisos", []))
        return {
            "role_sidebar_items": menus,
            "rol_actual": actual_role,
            "rol_navegacion": navigation_role,
            "role_home": ROLE_HOME,
            "available_endpoints": available_endpoints,
            "permission_groups": PERMISSION_GROUPS,
            "has_permission": lambda code: (
                session.get("rol") != "Personalizado"
                or code in session.get("permisos", [])
            ),
            "laboratorio_config": obtener_identidad_laboratorio(),
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
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)
