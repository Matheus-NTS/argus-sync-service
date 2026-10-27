-- ARGUS | Profitability Channel
-- 007: Corrige DELETE sem WHERE na RPC de clientes.
-- Preserva as validacoes e a publicacao transacional.
-- Nao executa a publicacao de cargas pendentes.

BEGIN;

CREATE OR REPLACE FUNCTION public.argus_publish_profitability_channel_customers(p_run_id uuid)
 RETURNS bigint
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
DECLARE
    v_load public.mart_profitability_channel_customers_load%rowtype;
    v_count bigint;
    v_inserted bigint;
    v_published_count bigint;
BEGIN
    PERFORM pg_catalog.pg_advisory_xact_lock(62016, 2);

    LOCK TABLE public.mart_profitability_channel_customers_stage
        IN SHARE ROW EXCLUSIVE MODE;

    SELECT * INTO v_load
      FROM public.mart_profitability_channel_customers_load
     WHERE run_id = p_run_id
     FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_LOAD_NOT_FOUND';
    END IF;
    IF v_load.status <> 'staging' THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_LOAD_ALREADY_PUBLISHED';
    END IF;
    IF v_load.source_as_of > pg_catalog.now() THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_FUTURE_SOURCE';
    END IF;
    IF EXISTS (
        SELECT 1 FROM public.mart_profitability_channel_customers_load
         WHERE status = 'published'
           AND source_as_of >= v_load.source_as_of
    ) THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_STALE_SOURCE';
    END IF;

    SELECT count(*) INTO v_count
      FROM public.mart_profitability_channel_customers_stage
     WHERE run_id = p_run_id;

    IF v_count <> v_load.expected_rows THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_ROW_COUNT_MISMATCH: expected %, actual %',
            v_load.expected_rows, v_count;
    END IF;

    -- DELETE e INSERT permanecem na mesma transacao.
    -- A chave NOT NULL garante a substituicao integral.
    DELETE FROM public.mart_profitability_channel_customers
     WHERE codigo_cliente_normalizado IS NOT NULL;

    INSERT INTO public.mart_profitability_channel_customers (
        codigo_cliente_normalizado, segmento
    )
    SELECT codigo_cliente_normalizado, segmento
      FROM public.mart_profitability_channel_customers_stage
     WHERE run_id = p_run_id;

    GET DIAGNOSTICS v_inserted = ROW_COUNT;
    IF v_inserted <> v_count THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_INSERT_COUNT_MISMATCH';
    END IF;

    SELECT count(*) INTO v_published_count
      FROM public.mart_profitability_channel_customers;
    IF v_published_count <> v_count THEN
        RAISE EXCEPTION 'ARGUS_CHANNEL_CUSTOMERS_PUBLISHED_COUNT_MISMATCH';
    END IF;

    UPDATE public.mart_profitability_channel_customers_load
       SET status = 'published', published_at = pg_catalog.now()
     WHERE run_id = p_run_id;

    DELETE FROM public.mart_profitability_channel_customers_stage
     WHERE run_id = p_run_id;

    RETURN v_inserted;
END;
$function$;

COMMIT;
