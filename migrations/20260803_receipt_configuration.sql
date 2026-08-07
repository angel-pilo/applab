-- Configuración editable del contenido de recibos y comprobantes.
-- Ejecutar en Supabase SQL Editor antes de guardar esta sección.
begin;

alter table public.configuracion_sistema
    add column if not exists recibo_configuracion jsonb not null default jsonb_build_object(
        'laboratorio_nombre', 'AppLab Laboratorio clínico',
        'laboratorio_rfc', '',
        'laboratorio_telefono', '',
        'laboratorio_whatsapp', '',
        'laboratorio_correo', '',
        'laboratorio_direccion', '',
        'recibo_mensaje_pie', 'Gracias por confiar en nuestro laboratorio.',
        'mostrar_paciente_telefono', true,
        'mostrar_paciente_direccion', false,
        'mostrar_procedencia', true,
        'mostrar_medico', true,
        'mostrar_estudios', true,
        'mostrar_observaciones', true,
        'mostrar_cajero', true,
        'mostrar_historial_pagos', true,
        'mostrar_saldo', true
    );

commit;
