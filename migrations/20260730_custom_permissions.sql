-- Perfil Personalizado y permisos combinables por empleado.
begin;

insert into public.roles (id, nombre)
values (5, 'Personalizado')
on conflict (id) do update set nombre = excluded.nombre;

select setval(
    pg_get_serial_sequence('public.roles', 'id'),
    greatest((select max(id) from public.roles), 5),
    true
);

create table if not exists public.permisos (
    codigo text primary key,
    modulo text not null,
    nombre text not null,
    creado_en timestamp with time zone not null default now()
);

create table if not exists public.empleado_permisos (
    empleado_id integer not null references public.empleados(id) on delete cascade,
    permiso_codigo text not null references public.permisos(codigo) on delete cascade,
    creado_en timestamp with time zone not null default now(),
    primary key (empleado_id, permiso_codigo)
);

insert into public.permisos (codigo, modulo, nombre) values
    ('admin.dashboard', 'admin', 'Ver panel administrativo'),
    ('admin.system_settings', 'admin', 'Administrar políticas del sistema'),
    ('admin.override', 'admin', 'Autorizar excepciones con contraseña'),
    ('admin.employees', 'admin', 'Administrar empleados y permisos'),
    ('admin.tests', 'admin', 'Administrar pruebas clínicas'),
    ('admin.inventory', 'admin', 'Administrar catálogo de reactivos'),
    ('admin.providers', 'admin', 'Administrar proveedores'),
    ('admin.doctors', 'admin', 'Administrar médicos'),
    ('admin.hospitals', 'admin', 'Administrar hospitales'),
    ('admin.patients', 'admin', 'Desactivar o reactivar pacientes'),
    ('admin.backlog', 'admin', 'Consultar bitácora de cambios'),
    ('admin.labels', 'admin', 'Configurar impresión de etiquetas'),
    ('front.dashboard', 'mostrador', 'Ver panel de mostrador'),
    ('front.orders.create', 'mostrador', 'Crear órdenes y registrar abonos'),
    ('front.orders.view', 'mostrador', 'Consultar órdenes recientes'),
    ('front.results.deliver', 'mostrador', 'Consultar y entregar resultados'),
    ('front.patients', 'mostrador', 'Registrar y editar pacientes'),
    ('nursing.dashboard', 'enfermeria', 'Ver panel de enfermería'),
    ('nursing.samples', 'enfermeria', 'Gestionar faltantes y toma de muestras'),
    ('nursing.labels', 'enfermeria', 'Generar, imprimir y escanear etiquetas'),
    ('lab.dashboard', 'quimico', 'Ver panel de químico'),
    ('lab.results.capture', 'quimico', 'Capturar y finalizar resultados'),
    ('lab.results.history', 'quimico', 'Consultar resultados finalizados'),
    ('lab.inventory.entry', 'quimico', 'Registrar entradas de inventario')
on conflict (codigo) do update
set modulo = excluded.modulo, nombre = excluded.nombre;

-- AppLab autentica a sus empleados en Flask; estas tablas siguen el mismo
-- modelo de acceso REST que las tablas actuales del proyecto.
grant select on public.permisos to anon, authenticated, service_role;
grant select, insert, update, delete on public.empleado_permisos
    to anon, authenticated, service_role;

notify pgrst, 'reload schema';
commit;
