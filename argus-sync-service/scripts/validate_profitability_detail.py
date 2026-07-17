"""Valida a mart detalhada contra o overview do mesmo snapshot."""
import argparse
import os
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from supabase import create_client

DETAIL = "mart_profitability_detail_snapshot"
OVERVIEW = "mart_profitability_overview"
PAGE_SIZE = 1000
TOLERANCE = Decimal("0.05")


def decimal(value):
    return Decimal("0") if value is None else Decimal(str(value))


def client():
    env_path = (
        Path(__file__)
        .resolve()
        .parents[1]
        / "config"
        / ".env"
    )

    load_dotenv(env_path)

    url = os.getenv("SUPABASE_URL")

    key = (
        os.getenv("SUPABASE_SECRET_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
    )

    if not url or not key:
        raise RuntimeError(
            "Credenciais do Supabase não encontradas em config/.env."
        )

    return create_client(url, key)


def latest_reference_date(sb):
    result = sb.table(DETAIL).select("reference_date").order(
        "reference_date", desc=True
    ).limit(1).execute()
    if not result.data:
        raise RuntimeError(f"A tabela {DETAIL} está vazia.")
    return result.data[0]["reference_date"]


def fetch_detail(sb, reference_date, period_type):
    rows, start = [], 0
    fields = (
        "numero_pedido,codigo_cliente_normalizado,codigo_produto,"
        "faturamento_analisavel,custo_analisavel,lucro_analisavel,"
        "status_analise,elegivel_kpi"
    )
    while True:
        batch = sb.table(DETAIL).select(fields).eq(
            "reference_date", reference_date
        ).eq("period_type", period_type).range(
            start, start + PAGE_SIZE - 1
        ).execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            return rows
        start += PAGE_SIZE


def fetch_overview(sb, reference_date, period_type):
    fields = (
        "linhas_total,linhas_analisaveis,faturamento_analisavel,"
        "custo_analisavel,lucro_bruto,pedidos,produtos,clientes"
    )
    result = sb.table(OVERVIEW).select(fields).eq(
        "reference_date", reference_date
    ).eq("period_type", period_type).limit(1).execute()
    if not result.data:
        raise RuntimeError("Overview correspondente não encontrado.")
    return result.data[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="ytd")
    parser.add_argument("--reference-date")
    args = parser.parse_args()

    try:
        sb = client()
        ref = args.reference_date or latest_reference_date(sb)
        rows = fetch_detail(sb, ref, args.period)
        overview = fetch_overview(sb, ref, args.period)
        eligible = [row for row in rows if row.get("elegivel_kpi") is True]

        calculated = {
            "linhas_total": Decimal(len(rows)),
            "linhas_analisaveis": Decimal(len(eligible)),
            "faturamento_analisavel": sum(decimal(r.get("faturamento_analisavel")) for r in rows),
            "custo_analisavel": sum(decimal(r.get("custo_analisavel")) for r in rows),
            "lucro_bruto": sum(decimal(r.get("lucro_analisavel")) for r in rows),
            "pedidos": Decimal(len({r.get("numero_pedido") for r in eligible if r.get("numero_pedido")})),
            "produtos": Decimal(len({r.get("codigo_produto") for r in eligible if r.get("codigo_produto")})),
            "clientes": Decimal(len({r.get("codigo_cliente_normalizado") for r in eligible if r.get("codigo_cliente_normalizado")})),
        }

        errors = []
        for field, detail_value in calculated.items():
            overview_value = decimal(overview.get(field))
            if abs(detail_value - overview_value) > TOLERANCE:
                errors.append(f"{field}: detalhe={detail_value} | overview={overview_value}")

        invalid = [r for r in eligible if r.get("status_analise") != "analisavel"]
        if invalid:
            errors.append(f"{len(invalid)} linhas elegíveis com status inválido.")

        print(f"Snapshot: {ref} / {args.period}")
        print(f"Linhas: {len(rows):,} | Analisáveis: {len(eligible):,}")
        print("Status:", dict(Counter(r.get("status_analise") for r in rows)))
        print(f"Faturamento: R$ {calculated['faturamento_analisavel']:,.2f}")
        print(f"Custo: R$ {calculated['custo_analisavel']:,.2f}")
        print(f"Lucro: R$ {calculated['lucro_bruto']:,.2f}")

        if errors:
            print("\nFALHA NA VALIDAÇÃO:")
            for error in errors:
                print("-", error)
            sys.exit(1)

        print("\nVALIDAÇÃO APROVADA.")
    except Exception as exc:
        print(f"Erro ao validar: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
