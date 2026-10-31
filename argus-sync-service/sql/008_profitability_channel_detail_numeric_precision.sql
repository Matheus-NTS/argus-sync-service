-- ARGUS 3F.3G.8 - E5.48
-- Registro e verificacao da precisao financeira do canal.
--
-- HISTORICO:
-- A conversao das seis colunas financeiras para numeric
-- foi aplicada diretamente no Supabase em 30/10/2026.
-- A paridade financeira posterior foi validada.
--
-- Este arquivo NAO executa a conversao historica.
-- Ele verifica o estado esperado da estrutura atual.
--
-- Ambientes antigos que ainda utilizam double precision
-- exigem migracao especifica, baseada no DDL original.
--
-- Nenhuma tabela oficial de Rentabilidade e modificada.

BEGIN;

DO $verification$
DECLARE
    v_table text;
    v_column text;
    v_type text;
    v_constraint text;
    v_definition text;
    v_validated boolean;
    v_expected text;
BEGIN
    FOREACH v_table IN ARRAY ARRAY[
        'mart_profitability_channel_detail',
        'mart_profitability_channel_detail_stage'
    ]
    LOOP
        IF to_regclass(format('public.%I', v_table)) IS NULL THEN
            RAISE EXCEPTION
                'ARGUS 008: tabela ausente: %',
                v_table;
        END IF;

        FOREACH v_column IN ARRAY ARRAY[
            'faturamento_analisavel',
            'custo_analisavel',
            'lucro_analisavel'
        ]
        LOOP
            SELECT format_type(a.atttypid, a.atttypmod)
              INTO v_type
            FROM pg_attribute a
            WHERE a.attrelid =
                format('public.%I', v_table)::regclass
              AND a.attname = v_column
              AND a.attnum > 0
              AND NOT a.attisdropped;

            IF v_type IS DISTINCT FROM 'numeric' THEN
                RAISE EXCEPTION
                    'ARGUS 008: %.% deveria ser numeric; encontrado: %',
                    v_table,
                    v_column,
                    COALESCE(v_type, 'AUSENTE');
            END IF;
        END LOOP;

        v_constraint := CASE v_table
            WHEN 'mart_profitability_channel_detail'
                THEN 'channel_detail_finite'
            ELSE 'channel_detail_stage_finite'
        END;

        SELECT
            pg_get_constraintdef(con.oid),
            con.convalidated
        INTO
            v_definition,
            v_validated
        FROM pg_constraint con
        WHERE con.conrelid =
            format('public.%I', v_table)::regclass
          AND con.conname = v_constraint
          AND con.contype = 'c';

        IF v_definition IS NULL
           OR v_validated IS DISTINCT FROM TRUE
        THEN
            RAISE EXCEPTION
                'ARGUS 008: restricao financeira ausente ou nao validada: %.%',
                v_table,
                v_constraint;
        END IF;

        -- Verificacao conservadora dos componentes conhecidos.
        -- Nao substitui uma auditoria de equivalencia logica.
        FOREACH v_expected IN ARRAY ARRAY[
            'faturamento_analisavel',
            'custo_analisavel',
            'lucro_analisavel',
            '''NaN''::numeric',
            '''Infinity''::numeric',
            '''-Infinity''::numeric'
        ]
        LOOP
            IF position(v_expected IN v_definition) = 0 THEN
                RAISE EXCEPTION
                    'ARGUS 008: componente ausente em %.%: %',
                    v_table,
                    v_constraint,
                    v_expected;
            END IF;
        END LOOP;
    END LOOP;

    RAISE NOTICE
        'ARGUS 008: esquema financeiro verificado; nenhuma alteracao realizada';
END;
$verification$;

COMMIT;
