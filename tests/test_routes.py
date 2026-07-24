import os
import unittest
from pathlib import Path
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
import services
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


class ClinicalTestValidationTests(unittest.TestCase):
    def test_at_least_one_element_is_required(self):
        self.assertEqual(
            routes.validate_clinical_test_elements([]),
            ["Agrega al menos un elemento a la prueba."],
        )

    def test_empty_reference_values_are_rejected(self):
        errors = routes.validate_clinical_test_elements([{
            "nombre": "Glucosa",
            "tipo_separacion": "min-max",
            "estructura": {"min": None, "max": 110, "unidad": "mg/dL"},
        }])
        self.assertTrue(errors)

    def test_complete_reference_values_are_accepted(self):
        errors = routes.validate_clinical_test_elements([{
            "nombre": "Glucosa",
            "tipo_separacion": "min-max",
            "estructura": {"min": 70, "max": 110, "unidad": "mg/dL"},
        }])
        self.assertEqual(errors, [])


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


class EmployeeServiceTests(unittest.TestCase):
    def test_employee_user_id_remains_scalar(self):
        class FakeQuery:
            def __init__(self, table):
                self.table = table

            def select(self, *_):
                return self

            def in_(self, *_):
                return self

            def execute(self):
                if self.table == "empleados":
                    return SimpleNamespace(data=[{
                        "id": 1,
                        "nombres": "Ana",
                        "apellidos": "López",
                        "usuario_id": 10,
                        "contacto_emergencia": None,
                        "condiciones_medicas": None,
                        "fecha_nacimiento": "1990-01-01",
                        "empleado_roles": [{"rol_id": {"id": 1, "nombre": "Admin"}}],
                    }])
                return SimpleNamespace(data=[{"id": 10, "estado_usuario": True}])

        fake_supabase = SimpleNamespace(table=lambda name: FakeQuery(name))
        with patch.object(services, "supabase", fake_supabase):
            employees = services.obtener_empleados()

        self.assertEqual(employees[0]["usuario_id"], 10)
        self.assertTrue(employees[0]["estado"])


class ClinicalTestServiceTests(unittest.TestCase):
    class FakeQuery:
        def __init__(self):
            self.selected_table = None
            self.filters = []

        def table(self, table_name):
            self.selected_table = table_name
            return self

        def delete(self):
            return self

        def eq(self, field, value):
            self.filters.append((field, value))
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    def test_replacing_reagents_supports_current_api_response(self):
        fake = self.FakeQuery()
        with patch.object(services, "supabase", fake):
            result = services.actualizar_reactivos_de_prueba(8, [])

        self.assertEqual(result, [])
        self.assertEqual(fake.selected_table, "pruebas_reactivos")
        self.assertIn(("prueba_id", 8), fake.filters)

    def test_normal_values_can_be_deleted_before_edit_save(self):
        fake = self.FakeQuery()
        with patch.object(services, "supabase", fake):
            result = services.eliminar_valores_normales_de_prueba(8)

        self.assertEqual(result, [])
        self.assertEqual(fake.selected_table, "valores_normales")
        self.assertIn(("prueba_id", 8), fake.filters)

    def test_reagent_must_be_active_and_complete(self):
        complete = {
            "nombre": "Reactivo A",
            "tipo_reactivo": "Química",
            "costo_unidad": 10,
            "precio_unidad": 15,
            "proveedor_id": 2,
            "fecha_entrada": "2026-07-21",
            "cantidad_inicial": 5,
            "activo": True,
        }
        self.assertTrue(services.reactivo_tiene_datos_completos(complete))
        self.assertFalse(services.reactivo_tiene_datos_completos({**complete, "proveedor_id": None}))
        self.assertFalse(services.reactivo_tiene_datos_completos({**complete, "activo": False}))


class InventoryServiceTests(unittest.TestCase):
    def test_inventory_entry_uses_atomic_supabase_function(self):
        class FakeRpc:
            def __init__(self):
                self.name = None
                self.params = None

            def rpc(self, name, params):
                self.name = name
                self.params = params
                return self

            def execute(self):
                return SimpleNamespace(data={
                    "movimiento_id": 3,
                    "existencia_anterior": 10,
                    "existencia_nueva": 15,
                })

        fake = FakeRpc()
        with patch.object(services, "supabase", fake):
            ok, result = services.registrar_entrada_reactivo(
                reactivo_id=2,
                cantidad=5,
                costo_unitario=12.5,
                numero_lote="L-01",
                empleado_id=1,
            )

        self.assertTrue(ok)
        self.assertEqual(fake.name, "registrar_entrada_inventario")
        self.assertEqual(fake.params["p_cantidad"], 5)
        self.assertEqual(result["existencia_nueva"], 15)


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
            "admin/employees.html": {
                "empleados": [SimpleNamespace(
                    id=1, estado=True, nombres="Ana", apellidos="López",
                    rol_nombre="Admin", contacto_emergencia="Contacto",
                    condiciones_medicas="", fecha_nacimiento="1990-01-01",
                    usuario_id=10,
                )],
            },
            "admin/inventory.html": {
                "reactivos": [SimpleNamespace(
                    id=1, activo=True, nombre="Reactivo A",
                    tipo_reactivo="Química", cantidad_inicial=10,
                    precio_unidad=25,
                )],
            },
            "admin/pruebas.html": {
                "pruebas": [SimpleNamespace(
                    id=1, activo=True, nombre="Biometría",
                    tipo="Sangre", reactivos=["Reactivo A"],
                )],
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

    def test_employee_and_inventory_use_detail_drawer(self):
        catalog_js = Path("static/js/admin_catalog.js").read_text(encoding="utf-8")
        admin_js = Path("static/js/admin.js").read_text(encoding="utf-8")
        inventory_js = Path("static/js/inventario.js").read_text(encoding="utf-8")

        self.assertIn("function openAdminDetailDrawer", catalog_js)
        self.assertIn("function closeAdminDetailDrawer", catalog_js)
        self.assertIn("openAdminDetailDrawer();", admin_js)
        self.assertIn("openAdminDetailDrawer();", inventory_js)

    def test_shared_create_and_edit_forms_render_in_both_modes(self):
        hospital = SimpleNamespace(
            nombre="Hospital Central",
            telefono="5551234567",
            correo="hospital@example.com",
            calle="Centro",
            numero_ext="10",
            numero_int="",
            codigo_postal="44100",
            municipio="Guadalajara",
            estado="Jalisco",
            anotaciones="",
        )
        employee = SimpleNamespace(
            rol_id=1,
            sexo="M",
            fecha_nacimiento="1990-01-01",
            nombres="Admin",
            apellidos="Principal",
            telefono="5551234567",
            correo="admin@example.com",
            username="admin",
            calle="Centro",
            numero_ext="10",
            numero_int="",
            codigo_postal="44100",
            municipio="Guadalajara",
            estado="Jalisco",
            curp_rfc="TEST900101",
            turno="Matutino",
            condiciones_medicas="",
            contacto_emergencia="Contacto 5550000000",
        )

        with self.app.test_request_context("/admin/add_hospital"):
            create_hospital = render_template(
                "admin/add_hospital.html",
                hospital={},
                is_edit=False,
                estados=["Jalisco"],
            )
            edit_hospital = render_template(
                "admin/add_hospital.html",
                hospital=hospital,
                is_edit=True,
                estados=["Jalisco"],
            )
            create_employee = render_template(
                "admin/edit_employee.html",
                empleado={},
                is_edit=False,
                role_map={1: "Admin"},
                estados=["Jalisco"],
            )
            edit_employee = render_template(
                "admin/edit_employee.html",
                empleado=employee,
                is_edit=True,
                role_map={1: "Admin"},
                estados=["Jalisco"],
            )

        self.assertIn("Registrar hospital", create_hospital)
        self.assertIn("Guardar cambios", edit_hospital)
        self.assertIn("Registrar empleado", create_employee)
        self.assertIn("Guardar cambios", edit_employee)


if __name__ == "__main__":
    unittest.main()
