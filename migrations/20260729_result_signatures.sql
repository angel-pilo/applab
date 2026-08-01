-- Responsables autorizados y firma visible en reportes de laboratorio.
begin;

alter table public.empleados
    add column if not exists cedula_profesional text,
    add column if not exists firma_resultados_url text,
    add column if not exists puede_firmar_resultados boolean not null default false;

alter table public.resultados_paciente
    add column if not exists firmante_usuario_id integer references public.usuarios(id),
    add column if not exists firmante_nombre text,
    add column if not exists firmante_cedula text,
    add column if not exists firmante_firma_url text,
    add column if not exists firmado_en timestamp with time zone;

create or replace function public.finalizar_resultados_orden_app(
    p_orden_id bigint,
    p_usuario_id integer
) returns boolean language plpgsql security definer set search_path = public as $$
declare
    v_paciente_id integer;
    v_resultado jsonb;
    v_firmante record;
begin
    select paciente_id into v_paciente_id
    from public.ordenes
    where id = p_orden_id and flujo = 'en_quimico'
    for update;
    if not found then raise exception 'La orden no está disponible'; end if;

    if exists (
        select 1 from public.orden_pruebas_detalle d
        where d.orden_id = p_orden_id and not exists (
            select 1 from public.resultados_ejecuciones e
            where e.orden_detalle_id = d.id
        )
    ) then raise exception 'Faltan estudios por capturar'; end if;

    select jsonb_agg(to_jsonb(latest) order by latest.orden_detalle_id)
    into v_resultado
    from (
        select distinct on (e.orden_detalle_id)
            e.orden_detalle_id, e.numero_ejecucion, e.valores,
            e.evaluaciones, e.es_verificacion, e.creado_en
        from public.resultados_ejecuciones e
        where e.orden_id = p_orden_id
        order by e.orden_detalle_id, e.numero_ejecucion desc
    ) latest;

    -- Primero firma el usuario que finaliza, solamente si está autorizado.
    select
        e.usuario_id,
        trim(concat_ws(' ', e.nombres, e.apellidos)) as nombre,
        e.cedula_profesional,
        e.firma_resultados_url
    into v_firmante
    from public.empleados e
    where e.usuario_id = p_usuario_id
      and e.puede_firmar_resultados is true
      and nullif(trim(e.cedula_profesional), '') is not null
      and nullif(trim(e.firma_resultados_url), '') is not null
      and exists (
          select 1
          from public.empleado_roles er
          join public.roles ro on ro.id = er.rol_id
          where er.empleado_id = e.id
            and lower(ro.nombre) in ('admin', 'quimico', 'químico')
      )
    limit 1;

    -- Si es practicante o no tiene cédula/firma, usa al Admin responsable.
    if not found then
        select
            e.usuario_id,
            trim(concat_ws(' ', e.nombres, e.apellidos)) as nombre,
            e.cedula_profesional,
            e.firma_resultados_url
        into v_firmante
        from public.empleados e
        join public.empleado_roles er on er.empleado_id = e.id
        join public.roles ro on ro.id = er.rol_id
        where lower(ro.nombre) = 'admin'
          and e.puede_firmar_resultados is true
          and nullif(trim(e.cedula_profesional), '') is not null
          and nullif(trim(e.firma_resultados_url), '') is not null
        order by e.id
        limit 1;
    end if;

    insert into public.resultados_paciente(
        orden_id, paciente_id, resultado, estado, semaforo,
        entregado, entregado_en, entregado_por_usuario_id, medio_entrega,
        firmante_usuario_id, firmante_nombre, firmante_cedula,
        firmante_firma_url, firmado_en
    ) values (
        p_orden_id, v_paciente_id, v_resultado, 'finalizado', true,
        false, null, null, null,
        v_firmante.usuario_id, v_firmante.nombre, v_firmante.cedula_profesional,
        v_firmante.firma_resultados_url,
        case when v_firmante.usuario_id is not null then now() else null end
    )
    on conflict (orden_id, paciente_id) do update
    set resultado = excluded.resultado,
        estado = 'finalizado',
        semaforo = true,
        actualizado_en = now(),
        entregado = false,
        entregado_en = null,
        entregado_por_usuario_id = null,
        medio_entrega = null,
        firmante_usuario_id = excluded.firmante_usuario_id,
        firmante_nombre = excluded.firmante_nombre,
        firmante_cedula = excluded.firmante_cedula,
        firmante_firma_url = excluded.firmante_firma_url,
        firmado_en = excluded.firmado_en;

    update public.ordenes set flujo = 'finalizada' where id = p_orden_id;
    return true;
end;
$$;

create or replace function public.obtener_firma_resultado_app(p_orden_id bigint)
returns jsonb language plpgsql stable security definer set search_path = public as $$
declare v_firma record;
begin
    select firmante_nombre as nombre, firmante_cedula as cedula,
           firmante_firma_url as firma_url, firmado_en
    into v_firma
    from public.resultados_paciente
    where orden_id = p_orden_id and estado = 'finalizado'
    order by id desc limit 1;

    if v_firma.nombre is null then
        select trim(concat_ws(' ', e.nombres, e.apellidos)) as nombre,
               e.cedula_profesional as cedula,
               e.firma_resultados_url as firma_url,
               null::timestamp with time zone as firmado_en
        into v_firma
        from public.empleados e
        join public.empleado_roles er on er.empleado_id = e.id
        join public.roles ro on ro.id = er.rol_id
        where lower(ro.nombre) = 'admin'
          and e.puede_firmar_resultados is true
          and nullif(trim(e.cedula_profesional), '') is not null
          and nullif(trim(e.firma_resultados_url), '') is not null
        order by e.id limit 1;
    end if;

    return jsonb_build_object(
        'nombre', v_firma.nombre,
        'cedula', v_firma.cedula,
        'firma_url', v_firma.firma_url,
        'firmado_en', v_firma.firmado_en
    );
end;
$$;

revoke all on function public.finalizar_resultados_orden_app(bigint,integer) from public;
grant execute on function public.finalizar_resultados_orden_app(bigint,integer)
    to anon, authenticated, service_role;
revoke all on function public.obtener_firma_resultado_app(bigint) from public;
grant execute on function public.obtener_firma_resultado_app(bigint)
    to anon, authenticated, service_role;

notify pgrst, 'reload schema';
commit;
