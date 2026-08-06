-- Políticas globales de seguridad y operación de AppLab.
begin;

create table if not exists public.configuracion_sistema (
    id smallint primary key default 1 check (id = 1),
    empleados_cambian_password boolean not null default true,
    empleados_cambian_foto boolean not null default true,
    mostrador_entrega_saldo_pendiente boolean not null default false,
    actualizado_por_usuario_id integer references public.usuarios(id),
    actualizado_en timestamp with time zone not null default now()
);

insert into public.configuracion_sistema (id)
values (1)
on conflict (id) do nothing;

insert into public.permisos (codigo, modulo, nombre) values
    ('admin.system_settings', 'admin', 'Administrar políticas del sistema'),
    ('admin.override', 'admin', 'Autorizar excepciones con contraseña')
on conflict (codigo) do update
set modulo = excluded.modulo, nombre = excluded.nombre;

grant select, insert, update on public.configuracion_sistema
    to anon, authenticated, service_role;

-- La aplicación escribe esta configuración desde el backend con service_role.
-- No se crean políticas públicas: así RLS puede permanecer habilitado sin
-- permitir que un cliente anónimo modifique las reglas globales.

notify pgrst, 'reload schema';
commit;
