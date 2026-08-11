create table if not exists public.argus_pipeline_state (
    pipeline_key text primary key,
    reference_date date not null,
    last_success_at timestamptz not null default now()
);

alter table public.argus_pipeline_state
enable row level security;

drop policy if exists "Authenticated users can read pipeline state"
on public.argus_pipeline_state;

create policy "Authenticated users can read pipeline state"
on public.argus_pipeline_state
for select
to authenticated
using (true);

comment on table public.argus_pipeline_state is
'Estado técnico da última publicação completa e bem-sucedida de cada domínio do ARGUS.';