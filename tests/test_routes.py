import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch


os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJyb2xlIjoiYW5vbiIsImlhdCI6MTUxNjIzOTAyMn0.dGVzdA",
)

import routes
from app import create_app
from flask import render_template
from supabase_client import normalize_supabase_url


class OrderValidationTests(unittest.TestCase):
    @patch.object(routes, "existe_doctor_activo", return_value=True)
    @patch.object(routes, "existe_hospital_activo", return_value=True)
    @patch.object(routes, "existe_paciente_activo", return_value=True)
    def test_valid_order_has_no_errors(self, *_):
        data = {
            "nombre": "Paciente Uno",
            "patient_id": "1",
            "hospital": "2",
            "cuarto": "A-12",
            "doctor": "3",
        }

        self.assertEqual(routes.validate_order_data(data), [])

    def test_missing_order_fields_are_reported(self):
        errors = routes.validate_order_data({})

        self.assertEqual(len(errors), 4)


class SupabaseConfigurationTests(unittest.TestCase):
    def test_rest_endpoint_is_normalized_to_project_url(self):
        self.assertEqual(
            normalize_supabase_url("https://project.supabase.co/rest/v1/"),
            "https://project.supabase.co",
        )

    def test_project_url_is_preserved(self):
        self.assertEqual(
            normalize_supabase_url("https://project.supabase.co"),
            "https://project.supabase.co",
        )


class AuthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config.update(TESTING=True)

    def test_anonymous_user_cannot_capture_results(self):
        response = self.app.test_client().get(
            "/orden/1/captura_resultados", follow_redirects=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/login"))

    def test_dashboard_redirects_to_role_home(self):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session["usuario"] = "quimico"
            session["rol"] = "Quimico"

        response = client.get("/dashboard", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/quimico"))

    @patch.object(
        routes,
        "verificar_usuario",
        return_value={
            "id": 10,
            "nombres": "Administrador",
            "foto_perfil": None,
            "rol_id": 1,
        },
    )
    def test_admin_login_redirects_to_dashboard(self, _):
        response = self.app.test_client().post(
            "/login",
            data={"username": "admin", "password": "correcta"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/admin"))


class AdminTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()

    def test_catalog_templates_render_with_shared_layout(self):
        active = SimpleNamespace(
            id=1,
            activo=True,
            nombres="Ana",
            apellidos="López",
            nombre="Registro",
            tipo="local",
            telefono="5551234567",
            correo="ana@example.com",
            tipo_consultorio="hospital",
            hospital_nombre="Hospital Central",
            calle="Centro",
            numero_ext="10",
            municipio="Centro",
            estado="Jalisco",
        )
        contexts = {
            "admin/patients.html": {"pacientes": [active], "rol": "Admin"},
            "admin/proveedores.html": {"proveedores": [active], "rol": "Admin"},
            "admin/doctores.html": {"doctores": [active]},
            "admin/hospitals.html": {
                "hospitales": [active],
                "estados_registrados": ["Jalisco"],
            },
        }

        with self.app.test_request_context():
            for template_name, context in contexts.items():
                with self.subTest(template=template_name):
                    html = render_template(template_name, **context)
                    self.assertIn("Administración", html)
                    self.assertIn("filter-menu", html)
                    self.assertIn("admin-primary-action", html)
                    self.assertIn("admin-action-group", html)

    def test_every_template_compiles(self):
        for template_name in self.app.jinja_env.list_templates():
            with self.subTest(template=template_name):
                self.app.jinja_env.get_template(template_name)


if __name__ == "__main__":
    unittest.main()
