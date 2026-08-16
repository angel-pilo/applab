import os
from io import BytesIO
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
from flask import render_template, session
from supabase_client import normalize_supabase_url
from werkzeug.datastructures import FileStorage


class EmployeeAvatarValidationTests(unittest.TestCase):
    def test_valid_png_avatar_is_accepted(self):
        avatar = FileStorage(
            stream=BytesIO(b"\x89PNG\r\n\x1a\n" + b"image-data"),
            filename="avatar.png",
        )

        extension, error = routes.validate_employee_avatar(avatar)

        self.assertEqual(extension, "png")
        self.assertIsNone(error)

    def test_fake_image_is_rejected(self):
        avatar = FileStorage(
            stream=BytesIO(b"not-an-image"),
            filename="avatar.png",
        )

        extension, error = routes.validate_employee_avatar(avatar)

        self.assertIsNone(extension)
        self.assertIn("imagen válida", error)

    def test_only_known_preset_avatars_are_accepted(self):
        self.assertEqual(routes.normalize_avatar_choice("preset:4"), "preset:4")
        self.assertEqual(routes.normalize_avatar_choice("preset:99"), "initials")
        self.assertEqual(routes.normalize_avatar_choice("unknown"), "initials")


class ReceiptPdfTests(unittest.TestCase):
    def test_receipt_pdf_is_generated_as_a_real_pdf(self):
        context = {
            "tipo_recibo": "Recibo de abono",
            "orden_id": 12,
            "config": {
                "laboratorio_nombre": "Laboratorio prueba",
                "laboratorio_direccion": "Centro 1",
                "laboratorio_telefono": "123",
                "laboratorio_correo": "contacto@example.com",
                "laboratorio_rfc": "",
                "mostrar_paciente_telefono": True,
                "mostrar_paciente_direccion": True,
                "mostrar_procedencia": True,
                "mostrar_medico": True,
                "mostrar_estudios": True,
                "mostrar_observaciones": True,
                "mostrar_historial_pagos": True,
                "mostrar_saldo": True,
                "mostrar_cajero": True,
                "recibo_mensaje_pie": "Gracias",
            },
            "paciente": {"nombres": "Ana", "apellidos": "López", "telefono": "123"},
            "paciente_direccion": "Centro 1",
            "hospital": None,
            "doctor": None,
            "orden": {"estado": "credito", "observaciones": "Ayuno"},
            "fecha_emision": "04/08/2026 10:00",
            "estudios": [{"nombre": "QS3", "cantidad": 1, "precio_unitario": 300.0, "total": 300.0}],
            "abono": {"cantidad": 100, "metodo_descripcion": "efectivo", "fecha_formateada": "04/08/2026"},
            "abonos": [{"cantidad": 100, "metodo_descripcion": "efectivo", "fecha_formateada": "04/08/2026"}],
            "total": 300.0,
            "pagado": 100.0,
            "saldo": 200.0,
            "cajero": "Nombre Mostrador",
        }

        pdf = routes.generar_pdf_recibo(context).getvalue()

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1000)

    def test_cash_register_ticket_pdf_is_generated_as_thermal_pdf(self):
        app = create_app()
        corte = {
            "id": 7,
            "fecha_apertura_local": "2026-08-16T08:00:00-06:00",
            "fecha_cierre_local": "2026-08-16T18:00:00-06:00",
            "total_esperado_cuentas": 1350,
            "cuentas": [{
                "nombre": "Terminal BBVA", "tipo": "terminal", "inicial": 0,
                "abonos": 1250, "depositos": 100, "salidas": 0,
                "esperado": 1350, "contado": 1350, "diferencia": 0,
            }],
            "eventos": [{
                "titulo": "Abono con tarjeta", "naturaleza": "entrada",
                "monto": 1250, "detalle": "Orden #12",
                "cuenta": "Terminal BBVA", "referencia": "AUTH-1",
            }],
            "notas_cierre": "Sin diferencias",
        }
        with app.test_request_context("/"):
            session.update({"usuario": "cajero", "nombres": "Caja Uno"})
            pdf = routes.generar_pdf_corte_caja(
                corte,
                dict(services.DEFAULT_CASH_TICKET_SETTINGS),
                {"ticket_ancho_mm": "80"},
                {"nombre_corto": "AppLab"},
            ).getvalue()

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1000)


class DeliveredResultsServiceTests(unittest.TestCase):
    def test_utc_timestamp_is_converted_to_mexico_local_date(self):
        converted = services.convertir_fecha_hora_local(
            "2026-08-12T00:44:08.974232+00:00"
        )

        self.assertTrue(converted.startswith("2026-08-11T18:44:08"))

    def test_delivered_history_includes_studies_and_real_balance(self):
        class FakeQuery:
            def __init__(self, data):
                self.data = data

            def select(self, *_args, **_kwargs):
                return self

            def in_(self, *_args, **_kwargs):
                return self

            def order(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(data=self.data)

        class FakeAdmin:
            def table(self, name):
                if name == "ordenes":
                    return FakeQuery([{
                        "id": 9,
                        "total_pruebas": 650,
                        "total_abonos": 210,
                        "estado": "credito",
                        "creado_en": "2026-07-30T19:14:49+00:00",
                    }])
                return FakeQuery([{
                    "orden_id": 9,
                    "nombre_prueba": "EGO",
                    "tipo_prueba": "orina",
                    "cantidad": 1,
                }])

        history = [{
            "orden_id": 9,
            "nombres": "Raul",
            "apellidos": "Aceves",
            "entregado": True,
            "entregado_en": "2026-08-12T00:44:08+00:00",
        }, {
            "orden_id": 10,
            "entregado": False,
        }]

        with patch.object(services, "obtener_historial_resultados", return_value=history), patch.object(
            services, "supabase_admin", FakeAdmin()
        ):
            full_history = services.obtener_historial_resultados_mostrador()

        self.assertEqual(len(full_history), 2)
        self.assertEqual(full_history[0]["estado_entrega"], "entregado")
        self.assertEqual(full_history[1]["estado_entrega"], "pendiente")
        results = [item for item in full_history if item["entregado"]]

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["estudios"][0]["nombre"], "EGO")
        self.assertEqual(results[0]["estudios"][0]["tipo"], "orina")
        self.assertEqual(results[0]["saldo"], 440)
        self.assertEqual(results[0]["estado_pago"], "pendiente")
        self.assertTrue(results[0]["fecha_entrega"].startswith("2026-08-11T18:44"))


class CashRegisterServiceTests(unittest.TestCase):
    def test_cash_expected_excludes_card_and_transfer_payments(self):
        class FakeQuery:
            def __init__(self, data):
                self.data = data

            def select(self, *_args, **_kwargs):
                return self

            def eq(self, *_args, **_kwargs):
                return self

            def order(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(data=self.data)

        class FakeAdmin:
            def table(self, name):
                if name == "orden_abonos":
                    return FakeQuery([
                        {"id": 1, "orden_id": 8, "cantidad": 100, "metodo_pago": "efectivo", "fecha_abono": "2026-08-15T10:00:00+00:00"},
                        {"id": 2, "orden_id": 9, "cantidad": 50, "metodo_pago": "tarjeta", "fecha_abono": "2026-08-15T10:05:00+00:00"},
                        {"id": 3, "orden_id": 10, "cantidad": 75, "metodo_pago": "transferencia", "fecha_abono": "2026-08-15T10:10:00+00:00"},
                    ])
                return FakeQuery([
                    {"id": 1, "tipo": "deposito", "monto": 20, "concepto": "Cambio adicional", "creado_en": "2026-08-15T10:15:00+00:00"},
                    {"id": 2, "tipo": "retiro", "monto": 10, "concepto": "Retiro parcial", "creado_en": "2026-08-15T10:20:00+00:00"},
                    {"id": 3, "tipo": "gasto", "monto": 5, "concepto": "Mensajería", "creado_en": "2026-08-15T10:25:00+00:00"},
                ])

        with patch.object(services, "supabase_admin", FakeAdmin()):
            detail = services._detalle_corte_caja({
                "id": 4,
                "monto_inicial": 200,
                "fecha_apertura": "2026-08-15T09:00:00+00:00",
            })

        self.assertEqual(detail["efectivo_abonos"], 100)
        self.assertEqual(detail["total_cobrado"], 225)
        self.assertEqual(detail["efectivo_esperado"], 305)
        self.assertEqual(detail["salidas"], 15)
        self.assertEqual(len(detail["eventos"]), 6)


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

        self.assertEqual(len(errors), 3)

    @patch.object(routes, "existe_paciente_activo", return_value=True)
    def test_private_patient_does_not_require_hospital_room_or_doctor(self, *_):
        data = {
            "nombre": "Paciente Particular",
            "patient_id": "1",
            "hospital": "none",
            "cuarto": "",
            "doctor": "none",
        }

        self.assertEqual(routes.validate_order_data(data), [])


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

    def test_internal_test_does_not_require_external_provider(self):
        config = routes._configuracion_procesamiento_prueba({
            "procesamiento": "interno",
        })
        self.assertEqual(config["procesamiento"], "interno")
        self.assertIsNone(config["proveedor_servicio_id"])

    def test_external_test_requires_active_service_provider(self):
        form = {
            "procesamiento": "externo",
            "proveedor_servicio_id": "7",
            "tipo_muestra_externa": "Suero",
            "recipiente_muestra": "Tubo rojo",
            "conservacion_muestra": "Refrigerada",
            "tiempo_entrega_dias": "3",
            "costo_proveedor": "150.50",
        }
        with patch.object(
            routes, "obtener_proveedores_servicio",
            return_value=[{"id": 7, "nombre": "Referencia"}],
        ):
            config = routes._configuracion_procesamiento_prueba(form)
        self.assertEqual(config["procesamiento"], "externo")
        self.assertEqual(config["proveedor_servicio_id"], 7)
        self.assertEqual(config["tiempo_entrega_dias"], 3)


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


class AdminDashboardServiceTests(unittest.TestCase):
    def test_dashboard_counts_use_supabase_rows(self):
        table_rows = {
            "pacientes": [{"id": 1, "activo": True}, {"id": 2, "activo": False}],
            "pruebas_clinicas": [{"id": 1, "activo": True}],
            "doctores": [{"id": 1, "activo": True}, {"id": 2, "activo": True}, {"id": 3, "activo": False}],
            "proveedores": [],
            "hospitales": [{"id": 1, "activo": True}],
            "empleados": [{"id": index, "usuario_id": index} for index in range(5)],
            "usuarios": [
                {"id": 0, "estado_usuario": True},
                {"id": 1, "estado_usuario": True},
                {"id": 2, "estado_usuario": False},
                {"id": 3, "estado_usuario": True},
                {"id": 4, "estado_usuario": True},
            ],
            "reactivos": [{
                "id": 1,
                "nombre": "Glucosa",
                "activo": True,
                "cantidad_inicial": 10,
                "existencia_actual": 8,
                "fecha_vencimiento": None,
            }],
        }

        class FakeQuery:
            def __init__(self, table):
                self.table = table

            def select(self, *_):
                return self

            def in_(self, *_):
                return self

            def execute(self):
                return SimpleNamespace(data=table_rows[self.table])

        fake_supabase = SimpleNamespace(table=lambda name: FakeQuery(name))
        with patch.object(services, "supabase", fake_supabase):
            dashboard = services.obtener_resumen_admin()

        self.assertEqual(dashboard["counts"]["empleados"], 4)
        self.assertEqual(dashboard["counts"]["doctores"], 2)
        self.assertEqual(dashboard["counts"]["pacientes"], 1)
        self.assertEqual(dashboard["counts"]["reactivos"], 1)
        self.assertEqual(dashboard["inventory_alerts"], [])


class PatientHistoryServiceTests(unittest.TestCase):
    def test_history_uses_backend_client_when_public_rls_hides_orders(self):
        table_rows = {
            "ordenes": [{
                "id": 9,
                "creado_en": "2026-08-06T10:00:00+00:00",
                "total_pruebas": 500,
                "total_abonos": 100,
                "estado": "credito",
                "flujo": "finalizada",
                "hospital_id": None,
                "doctor_id": None,
            }],
            "orden_pruebas_detalle": [{
                "orden_id": 9,
                "nombre_prueba": "QS3",
                "cantidad": 1,
            }],
            "resultados_paciente": [{
                "orden_id": 9,
                "estado": "finalizado",
                "semaforo": True,
            }],
        }

        class FakeQuery:
            def __init__(self, table):
                self.table = table

            def select(self, *_):
                return self

            def eq(self, *_):
                return self

            def in_(self, *_):
                return self

            def order(self, *_args, **_kwargs):
                return self

            def execute(self):
                return SimpleNamespace(data=table_rows[self.table])

        fake_admin = SimpleNamespace(table=lambda name: FakeQuery(name))
        public_client = SimpleNamespace(
            table=lambda _name: self.fail("El historial no debe consultar con la clave pública")
        )
        with patch.object(services, "supabase_admin", fake_admin), patch.object(
            services, "supabase", public_client
        ):
            history = services.obtener_historial_ordenes_paciente(5)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["id"], 9)
        self.assertEqual(history[0]["saldo"], 400)
        self.assertEqual(history[0]["estudios"][0]["nombre_prueba"], "QS3")
        self.assertEqual(history[0]["resultado_estado"], "finalizado")


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

    def test_order_balance_uses_server_client_to_avoid_rls_false_not_found(self):
        class FakeQuery:
            def select(self, *_):
                return self

            def eq(self, *_):
                return self

            def limit(self, *_):
                return self

            def execute(self):
                return SimpleNamespace(data=[{
                    "id": 12, "total_pruebas": 500,
                    "total_abonos": 100, "estado": "credito",
                }])

        fake_admin = SimpleNamespace(table=lambda name: FakeQuery())
        public_client = SimpleNamespace(
            table=lambda _name: self.fail("El saldo no debe consultarse con la clave pública")
        )
        with patch.object(services, "supabase_admin", fake_admin), patch.object(
            services, "supabase", public_client
        ):
            balance = services.obtener_saldo_orden(12)

        self.assertEqual(balance["saldo"], 400)

    def test_result_communication_uses_supported_backlog_action(self):
        class FakeInsert:
            payload = None

            def table(self, name):
                self.table_name = name
                return self

            def insert(self, payload):
                self.payload = payload
                return self

            def execute(self):
                return SimpleNamespace(data=[self.payload])

        fake_storage = FakeInsert()
        with patch.object(services, "supabase_storage", fake_storage):
            saved = services.registrar_comunicacion_resultado(
                12, None, "envio_pdf", "whatsapp", 100
            )

        self.assertTrue(saved)
        self.assertEqual(fake_storage.table_name, "bitacora_eventos")
        self.assertEqual(fake_storage.payload["accion"], "actualizar")
        self.assertEqual(
            fake_storage.payload["metadata"]["accion_resultado"], "envio_pdf"
        )


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

    def test_admin_can_switch_workspace_without_changing_identity_role(self):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "admin",
                "rol": "Admin",
                "area_activa": "Admin",
            })

        response = client.post("/cambiar-area/quimico", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/quimico"))
        with client.session_transaction() as flask_session:
            self.assertEqual(flask_session["rol"], "Admin")
            self.assertEqual(flask_session["area_activa"], "Quimico")

    def test_admin_area_card_opens_operational_admin_dashboard(self):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "admin",
                "rol": "Admin",
                "area_activa": "Mostrador",
            })

        response = client.post("/cambiar-area/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/admin/panel"))
        with client.session_transaction() as flask_session:
            self.assertEqual(flask_session["rol"], "Admin")
            self.assertEqual(flask_session["area_activa"], "Admin")

    def test_non_admin_cannot_switch_workspace(self):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({"usuario": "mostrador", "rol": "Mostrador"})

        response = client.post("/cambiar-area/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 403)

    def test_custom_profile_redirects_to_first_authorized_workspace(self):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["usuario"] = "mixto"
            flask_session["rol"] = "Personalizado"
            flask_session["permisos"] = ["nursing.samples", "lab.results.capture"]

        response = client.get("/dashboard", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/muestra"))

    @patch.object(routes, "obtener_eventos_bitacora", return_value=[])
    def test_custom_profile_can_use_an_explicit_permission(self, _):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["usuario"] = "supervisor"
            flask_session["rol"] = "Personalizado"
            flask_session["permisos"] = ["admin.backlog"]

        response = client.get("/api/backlog/events")

        self.assertEqual(response.status_code, 200)

    def test_custom_profile_cannot_use_an_unassigned_permission(self):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["usuario"] = "supervisor"
            flask_session["rol"] = "Personalizado"
            flask_session["permisos"] = ["front.orders.view"]

        response = client.get("/api/backlog/events")

        self.assertEqual(response.status_code, 403)

    @patch.object(routes, "guardar_configuracion_sistema", return_value=True)
    @patch.object(routes, "registrar_cambio_politicas", return_value=True)
    def test_custom_system_manager_can_update_policies(self, *_):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "supervisor",
                "rol": "Personalizado",
                "permisos": ["admin.system_settings"],
                "user_id": 9,
            })

        response = client.post(
            "/configuracion/sistema",
            data={"empleados_cambian_foto": "on"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)

    @patch.object(routes, "guardar_configuracion_ticket_corte", return_value=True)
    @patch.object(routes, "registrar_cambio_politicas", return_value=True)
    def test_admin_can_configure_cash_register_ticket(self, _audit, save_settings):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "admin",
                "rol": "Admin",
                "user_id": 1,
            })

        response = client.post(
            "/configuracion/sistema/ticket-corte-caja",
            data={
                "mostrar_laboratorio": "on",
                "mostrar_cuentas": "on",
                "mostrar_total": "on",
            },
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        settings = save_settings.call_args.args[0]
        self.assertTrue(settings["mostrar_laboratorio"])
        self.assertTrue(settings["mostrar_cuentas"])
        self.assertFalse(settings["mostrar_movimientos"])

    @patch.object(routes, "finalizar_entrega_resultado")
    @patch.object(routes, "verificar_autorizador_admin", return_value=None)
    @patch.object(routes, "obtener_saldo_orden", return_value={
        "total": 500.0, "pagado": 100.0, "saldo": 400.0, "estado": "credito"
    })
    @patch.object(routes, "obtener_configuracion_sistema", return_value={
        "empleados_cambian_password": True,
        "empleados_cambian_foto": True,
        "mostrador_entrega_saldo_pendiente": False,
    })
    def test_unpaid_delivery_requires_admin_override(
        self, _settings, _balance, _authorizer, finalize
    ):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "mostrador", "rol": "Mostrador", "user_id": 3
            })

        response = client.post(
            "/resultados/12/entregar",
            data={"medio_entrega": "impreso"},
            follow_redirects=False,
        )

        self.assertEqual(response.status_code, 302)
        finalize.assert_not_called()

    @patch.object(routes, "registrar_comunicacion_resultado", return_value=True)
    @patch.object(routes, "finalizar_entrega_resultado", return_value=True)
    @patch.object(routes, "obtener_saldo_orden", return_value={
        "total": 500.0, "pagado": 500.0, "saldo": 0.0, "estado": "pagado"
    })
    @patch.object(routes, "obtener_configuracion_sistema", return_value={
        "empleados_cambian_password": True,
        "empleados_cambian_foto": True,
        "mostrador_entrega_saldo_pendiente": False,
    })
    def test_finalize_delivery_api_accepts_medium_from_confirmation_dialog(
        self, _settings, _balance, finalize, _audit
    ):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "mostrador", "rol": "Mostrador", "user_id": 3
            })

        response = client.post(
            "/api/resultados/12/finalizar-entrega",
            json={"medio_entrega": "whatsapp"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        finalize.assert_called_once_with(12, 3, "whatsapp")

    @patch.object(routes, "obtener_corte_caja", return_value={"disponible": True, "corte": None, "historial": []})
    def test_custom_profile_can_open_cash_register_with_permission(self, _):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "cajero-mixto",
                "user_id": 7,
                "rol": "Personalizado",
                "permisos": ["front.cash.manage"],
            })

        response = client.get("/mostrador/corte-caja")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Corte de caja", response.data)

    @patch.object(
        routes, "validar_autorizador_admin_detallado",
        return_value=(None, "Usuario o contraseña incorrectos."),
    )
    @patch.object(routes, "obtener_saldo_orden", return_value={
        "total": 500.0, "pagado": 100.0, "saldo": 400.0, "estado": "credito"
    })
    @patch.object(routes, "obtener_configuracion_sistema", return_value={
        "empleados_cambian_password": True,
        "empleados_cambian_foto": True,
        "mostrador_entrega_saldo_pendiente": False,
    })
    def test_finalize_delivery_api_explains_invalid_admin_credentials(
        self, _settings, _balance, _authorization
    ):
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session.update({
                "usuario": "mostrador", "rol": "Mostrador", "user_id": 3
            })

        response = client.post(
            "/api/resultados/12/finalizar-entrega",
            json={
                "medio_entrega": "whatsapp",
                "admin_username": "admin",
                "admin_password": "incorrecta",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.get_json()["error"], "Usuario o contraseña incorrectos."
        )

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

    @patch.object(routes, "obtener_eventos_bitacora")
    def test_backlog_api_reads_supabase_events(self, mock_events):
        mock_events.return_value = [{
            "id": 1,
            "creado_en": "2026-07-28T12:00:00+00:00",
            "modulo": "Pacientes",
            "accion": "crear",
            "severidad": "success",
            "titulo": "Pacientes: registro creado",
            "detalle": "Ana López",
            "entidad_tipo": "pacientes",
            "entidad_id": "7",
            "actor_nombre": None,
            "actor_username": "admin",
            "metadata": {
                "cambios": [{
                    "campo": "telefono",
                    "anterior": "3311111111",
                    "nuevo": "3322222222",
                }]
            },
        }]
        client = self.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["usuario"] = "admin"
            flask_session["rol"] = "Admin"

        response = client.get("/api/backlog/events?module=Pacientes")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["events"][0]["entidad_id"], "7")
        self.assertEqual(payload["events"][0]["actor_username"], "admin")
        self.assertEqual(
            payload["events"][0]["metadata"]["cambios"][0]["campo"],
            "telefono",
        )
        self.assertEqual(payload["stats"]["modules"], 1)


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

    def test_backlog_uses_live_supabase_endpoint(self):
        with self.app.test_request_context("/backlog"):
            session["rol"] = "Admin"
            html = render_template("backlog.html")

        self.assertIn("Bitácora de actividad", html)
        self.assertIn("/api/backlog/events", html)
        self.assertIn("Actualización en vivo", html)
        self.assertIn("Cambios realizados", html)
        self.assertIn("Realizado por", html)
        self.assertNotIn("OC-7781", html)

    def test_navbar_accepts_null_and_preset_profile_images(self):
        with self.app.test_request_context("/admin"):
            session["foto_perfil"] = None
            null_avatar_html = render_template("components/navbar.html")

            session["foto_perfil"] = "preset:4"
            preset_avatar_html = render_template("components/navbar.html")

        self.assertIn("app-avatar-fallback", null_avatar_html)
        self.assertIn("avatar-preset-4", preset_avatar_html)

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
        self.assertIn("Perfil laboral", create_employee)
        self.assertIn("Información de emergencia", create_employee)
        self.assertIn('type="file"', create_employee)
        self.assertIn("Imagen de perfil", create_employee)
        self.assertIn("Avatares ilustrados", create_employee)
        self.assertIn("Guardar cambios", edit_employee)

    def test_patient_form_renders_in_create_and_edit_modes(self):
        patient = SimpleNamespace(
            id=9,
            nombres="María",
            apellidos="López",
            sexo="F",
            fecha_nacimiento="1994-05-10",
            telefono="3312345678",
            correo="maria@example.com",
            calle="Juárez",
            numero_ext="10",
            numero_int="",
            codigo_postal="44100",
            municipio="Guadalajara",
            estado="Jalisco",
            condiciones_medicas="",
        )

        with self.app.test_request_context("/admin/add_patient"):
            session["rol"] = "Admin"
            create_html = render_template(
                "admin/add_patient.html",
                patient={},
                is_edit=False,
                estados=["Jalisco"],
            )
            edit_html = render_template(
                "admin/add_patient.html",
                patient=patient,
                is_edit=True,
                estados=["Jalisco"],
            )

        self.assertIn("Registrar paciente", create_html)
        self.assertIn("Información clínica", create_html)
        self.assertIn("Guardar cambios", edit_html)

    def test_provider_form_renders_in_create_and_edit_modes(self):
        provider = SimpleNamespace(
            id=4,
            tipo="producto",
            nombre="Insumos Clínicos",
            telefono="3312345678",
            correo="ventas@example.com",
            contacto="María López",
            calle="Industria",
            numero_ext="25",
            numero_int="",
            codigo_postal="44900",
            municipio="Guadalajara",
            estado="Jalisco",
            anotaciones="",
        )

        with self.app.test_request_context("/admin/add_proveedor"):
            create_html = render_template(
                "admin/add_proveedor.html",
                proveedor={},
                is_edit=False,
                estados=["Jalisco"],
            )
            edit_html = render_template(
                "admin/add_proveedor.html",
                proveedor=provider,
                is_edit=True,
                estados=["Jalisco"],
            )

        self.assertIn("Registrar proveedor", create_html)
        self.assertIn("Información del proveedor", create_html)
        self.assertIn("Guardar cambios", edit_html)

    def test_doctor_form_renders_in_create_and_edit_modes(self):
        doctor = SimpleNamespace(
            id=7,
            nombres="Andrea",
            apellidos="Martínez",
            telefono="3312345678",
            correo="andrea@example.com",
            tipo_consultorio="hospital",
            hospital_id=2,
            calle=None,
            numero_ext=None,
            numero_int=None,
            codigo_postal=None,
            municipio=None,
            estado=None,
            anotaciones="",
        )
        hospitals = [SimpleNamespace(id=2, nombre="Hospital Central")]

        with self.app.test_request_context("/admin/add_doctor"):
            create_html = render_template(
                "admin/add_doctor.html",
                doctor={},
                hospitales=hospitals,
                estados=["Jalisco"],
                is_edit=False,
            )
            edit_html = render_template(
                "admin/add_doctor.html",
                doctor=doctor,
                hospitales=hospitals,
                estados=["Jalisco"],
                is_edit=True,
            )

        self.assertIn("Registrar doctor", create_html)
        self.assertIn("Lugar de consulta", create_html)
        self.assertIn("Hospital Central", edit_html)
        self.assertIn("Guardar cambios", edit_html)

    def test_hospital_form_renders_in_create_and_edit_modes(self):
        hospital = SimpleNamespace(
            id=5,
            nombre="Hospital Clínico del Centro",
            telefono="3312345678",
            correo="contacto@hospital.com",
            calle="Salud",
            numero_ext="120",
            numero_int="",
            codigo_postal="44100",
            municipio="Guadalajara",
            estado="Jalisco",
            anotaciones="",
        )

        with self.app.test_request_context("/admin/add_hospital"):
            create_html = render_template(
                "admin/add_hospital.html",
                hospital={},
                estados=["Jalisco"],
                is_edit=False,
            )
            edit_html = render_template(
                "admin/add_hospital.html",
                hospital=hospital,
                estados=["Jalisco"],
                is_edit=True,
            )

        self.assertIn("Registrar hospital", create_html)
        self.assertIn("Información del hospital", create_html)
        self.assertIn("Hospital Clínico del Centro", edit_html)
        self.assertIn("Guardar cambios", edit_html)


if __name__ == "__main__":
    unittest.main()
