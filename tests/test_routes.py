import os
import unittest
from unittest.mock import patch


os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")

import routes
from app import create_app


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


if __name__ == "__main__":
    unittest.main()
