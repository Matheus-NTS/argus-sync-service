-- ARGUS | Customer channel dimension publication
-- REVIEW ONLY: do not apply without explicit authorization.
-- Depends on the Python publisher contract and standard Supabase roles.
BEGIN;

CREATE TABLE public.mart_profitability_channel_customers_load (
    run_id uuid PRIMARY KEY,
    source_as_of timestamptz NOT NULL,
    expected_rows bigint NOT NULL CHECK (expected_rows > 0),
    status text NOT NULL DEFAULT 'staging' CHECK (status IN ('staging', 'published')),
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    CONSTRAINT customers_load_publication_state CHECK (
        (status = 'staging' AND published_at IS NULL)
        OR (status = 'published' AND published_at IS NOT NULL)
    )
);

CREATE TABLE public.mart_profitability_channel_customers_stage (
    run_id uuid NOT NULL REFERENCES public.mart_profitability_channel_customers_load(run_id),
    codigo_cliente_normalizado text NOT NULL CHECK (
        codigo_cliente_normalizado <> '' AND codigo_cliente_normalizado = btrim(codigo_cliente_normalizado)
    ),
    segmento text NOT NULL CHECK (segmento IN ('Atacado', 'Varejo', 'Não classificados')),
    PRIMARY KEY (run_id, codigo_cliente_normalizado)
);

CREATE TABLE public.mart_profitability_channel_customers (
    codigo_cliente_normalizado text PRIMARY KEY CHECK (
        codigo_cliente_normalizado <> '' AND codigo_cliente_normalizado = btrim(codigo_cliente_normalizado)
    ),
    segmento text NOT NULL CHECK (segmento IN ('Atacado', 'Varejo', 'Não classificados'))
);

CREATE INDEX customers_load_published_source_idx
    ON public.mart_profitability_channel_customers_load (source_as_of DESC)
    WHERE status = 'published';

ALTER TABLE public.mart_profitability_channel_customers_load ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mart_profitability_channel_customers_stage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mart_profitability_channel_customers ENABLE ROW LEVEL SECURITY;

CREATE POLICY mart_profitability_channel_customers_select_authenticated
ON public.mart_profitability_channel_customers
FOR SELECT
TO authenticated
USING (true);


REVOKE ALL ON TABLE
    public.mart_profitability_channel_customers_load,
    public.mart_profitability_channel_customers_stage,
    public.mart_profitability_channel_customers
FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    public.mart_profitability_channel_customers_load,
    public.mart_profitability_channel_customers_stage,
    public.mart_profitability_channel_customers
TO service_role;

GRANT SELECT ON TABLE public.mart_profitability_channel_customers TO authenticated;
-- No anon read access by default. Review before granting if the Pulse Core needs it.

CREATE FUNCTION public.argus_publish_profitability_channel_customers(p_run_id uuid)
RETURNS bigint
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path TO ''
AS $function$
DECLARE
    v_load public.mart_profitability_channel_customers_load%rowtype;
    v_count bigint;
    v_inserted bigint;
    v_published_count bigint;
BEGIN
    -- Isolated from the daily channel publication's advisory lock (62016, 1).
    PERFORM pg_catalog.pg_advisory_xact_lock(62016, 2);

    -- Prevent stage writes while the snapshot is validated and copied.
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

    -- The stage primary key and CHECK constraints enforce unique valid codes/segments.
    -- DELETE and INSERT run in the same transaction: failure rolls back both.
    DELETE FROM public.mart_profitability_channel_customers;

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

REVOKE ALL ON FUNCTION public.argus_publish_profitability_channel_customers(uuid)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.argus_publish_profitability_channel_customers(uuid)
    TO service_role;

COMMIT;
