-- ============================================================
-- ARGUS ? Revenue Intelligence ? F2.6
-- Evolu??o aditiva do mart_revenue_monthly
-- Ticket m?dio: compara??o mensal e anual
-- ============================================================

alter table public.mart_revenue_monthly
    add column if not exists ticket_medio_mes_anterior numeric(18, 2);

alter table public.mart_revenue_monthly
    add column if not exists crescimento_ticket_mom numeric(18, 6);

alter table public.mart_revenue_monthly
    add column if not exists ticket_medio_ano_anterior numeric(18, 2);

alter table public.mart_revenue_monthly
    add column if not exists crescimento_ticket_yoy numeric(18, 6);
