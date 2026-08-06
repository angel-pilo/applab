-- Identidad central del laboratorio y opciones para tickets/PDF.
-- Ejecutar una sola vez en Supabase SQL Editor.
begin;

alter table public.configuracion_sistema
    add column if not exists laboratorio_configuracion jsonb not null default '{}'::jsonb;

update public.configuracion_sistema
set laboratorio_configuracion = jsonb_build_object(
        'nombre', coalesce(nullif(recibo_configuracion->>'laboratorio_nombre', ''), 'AppLab Laboratorio clínico'),
        'nombre_corto', 'AppLab',
        'rfc', coalesce(recibo_configuracion->>'laboratorio_rfc', ''),
        'telefono', coalesce(recibo_configuracion->>'laboratorio_telefono', ''),
        'whatsapp', coalesce(recibo_configuracion->>'laboratorio_whatsapp', ''),
        'correo', coalesce(recibo_configuracion->>'laboratorio_correo', ''),
        'direccion', coalesce(recibo_configuracion->>'laboratorio_direccion', ''),
        'logo_url', '',
        'favicon_url', ''
    ) || coalesce(laboratorio_configuracion, '{}'::jsonb),
    recibo_configuracion = jsonb_build_object(
        'ticket_ancho_mm', '80',
        'mostrar_laboratorio_nombre', true,
        'mostrar_laboratorio_logo', true,
        'mostrar_laboratorio_rfc', true,
        'mostrar_laboratorio_telefono', true,
        'mostrar_laboratorio_whatsapp', true,
        'mostrar_laboratorio_correo', true,
        'mostrar_laboratorio_direccion', true
    ) || coalesce(recibo_configuracion, '{}'::jsonb)
where id = 1;

commit;
