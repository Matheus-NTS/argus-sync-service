BEGIN;

CREATE FUNCTION public.argus_channel_server_time()
RETURNS timestamptz
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path TO ''
AS $function$
    SELECT pg_catalog.now();
$function$;

REVOKE ALL ON FUNCTION public.argus_channel_server_time()
    FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.argus_channel_server_time()
    TO service_role;

COMMIT;
