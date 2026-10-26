-- ARGUS | Validacao transacional da dimensao de clientes
-- SOMENTE REVISAO. NAO EXECUTAR SEM AUTORIZACAO.
-- Pre-requisito: migracao 004 aplicada e revisada.
-- Os testes funcionais utilizam dados ficticios e ROLLBACK.
-- IMPORTANTE: executar como um unico script na mesma transacao.
-- Nao executar em paralelo com o Sync de producao.

BEGIN;

DO $validation$
DECLARE
    v_run_valid uuid := pg_catalog.gen_random_uuid();
    v_run_incomplete uuid := pg_catalog.gen_random_uuid();
    v_run_stale uuid := pg_catalog.gen_random_uuid();
    v_result bigint;
    v_count bigint;
    v_source timestamptz := pg_catalog.now() - interval '1 minute';
BEGIN
    -- Bloqueia escritas concorrentes durante toda a validacao.
    LOCK TABLE
        public.mart_profitability_channel_customers,
        public.mart_profitability_channel_customers_load,
        public.mart_profitability_channel_customers_stage
    IN SHARE ROW EXCLUSIVE MODE;

    -- Protecao: executar somente antes da primeira carga real.
    IF EXISTS (
        SELECT 1 FROM public.mart_profitability_channel_customers
    ) OR EXISTS (
        SELECT 1 FROM public.mart_profitability_channel_customers_load
    ) OR EXISTS (
        SELECT 1 FROM public.mart_profitability_channel_customers_stage
    ) THEN
        RAISE EXCEPTION 'VALIDATION_REQUIRES_EMPTY_DIMENSION';
    END IF;

    -- A publicacao valida deve ocorrer antes da incompleta.
    INSERT INTO public.mart_profitability_channel_customers_load
        (run_id, source_as_of, expected_rows)
    VALUES (v_run_valid, v_source, 2);

    INSERT INTO public.mart_profitability_channel_customers_stage
        (run_id, codigo_cliente_normalizado, segmento)
    VALUES
        (v_run_valid, 'ARGUS_TEST_001', 'Atacado'),
        (v_run_valid, 'ARGUS_TEST_002', 'Varejo');

    v_result := public.argus_publish_profitability_channel_customers(
        v_run_valid
    );

    IF v_result <> 2 THEN
        RAISE EXCEPTION 'VALIDATION_VALID_COUNT_FAILED';
    END IF;

    SELECT count(*) INTO v_count
    FROM public.mart_profitability_channel_customers
    WHERE codigo_cliente_normalizado IN (
        'ARGUS_TEST_001', 'ARGUS_TEST_002'
    );

    IF v_count <> 2 THEN
        RAISE EXCEPTION 'VALIDATION_VALID_DATA_FAILED';
    END IF;

    -- Confirma estado publicado e limpeza do staging.
    IF NOT EXISTS (
        SELECT 1
        FROM public.mart_profitability_channel_customers_load
        WHERE run_id = v_run_valid
          AND status = 'published'
          AND published_at IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'VALIDATION_PUBLICATION_STATUS_FAILED';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM public.mart_profitability_channel_customers_stage
        WHERE run_id = v_run_valid
    ) THEN
        RAISE EXCEPTION 'VALIDATION_STAGE_CLEANUP_FAILED';
    END IF;

    -- Carga incompleta: a RPC deve falhar sem substituir a dimensao.
    INSERT INTO public.mart_profitability_channel_customers_load
        (run_id, source_as_of, expected_rows)
    VALUES (v_run_incomplete, v_source + interval '1 second', 2);

    INSERT INTO public.mart_profitability_channel_customers_stage
        (run_id, codigo_cliente_normalizado, segmento)
    VALUES (v_run_incomplete, 'ARGUS_TEST_003', 'Varejo');

    BEGIN
        PERFORM public.argus_publish_profitability_channel_customers(
            v_run_incomplete
        );
        RAISE EXCEPTION 'VALIDATION_INCOMPLETE_ACCEPTED';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLERRM NOT LIKE 'ARGUS_CHANNEL_CUSTOMERS_ROW_COUNT_MISMATCH:%'
            THEN
                RAISE;
            END IF;
    END;

    -- Carga anterior: a RPC deve rejeitar o source_as_of.
    INSERT INTO public.mart_profitability_channel_customers_load
        (run_id, source_as_of, expected_rows)
    VALUES (v_run_stale, v_source - interval '1 second', 1);

    INSERT INTO public.mart_profitability_channel_customers_stage
        (run_id, codigo_cliente_normalizado, segmento)
    VALUES (v_run_stale, 'ARGUS_TEST_004', 'Atacado');

    BEGIN
        PERFORM public.argus_publish_profitability_channel_customers(
            v_run_stale
        );
        RAISE EXCEPTION 'VALIDATION_STALE_ACCEPTED';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLERRM <> 'ARGUS_CHANNEL_CUSTOMERS_STALE_SOURCE'
            THEN
                RAISE;
            END IF;
    END;

    -- As tentativas rejeitadas nao podem alterar o snapshot valido.
    SELECT count(*) INTO v_count
    FROM public.mart_profitability_channel_customers;

    IF v_count <> 2 THEN
        RAISE EXCEPTION 'VALIDATION_ROLLBACK_INTEGRITY_FAILED';
    END IF;

    RAISE NOTICE 'ARGUS_CHANNEL_CUSTOMERS_FUNCTIONAL_TESTS_PASSED';
END;
$validation$;

-- Nao persiste as cargas ficticias.
ROLLBACK;

-- As verificacoes de privilegios e RLS devem ser feitas
-- separadamente, em consultas de leitura, apos a instalacao.
