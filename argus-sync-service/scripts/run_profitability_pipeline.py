import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from connectors.sql_server import (
    SQLServerConnector,
)
from connectors.supabase_connector import (
    SupabaseConnector,
)
from pipelines.profitability_pipeline import (
    ProfitabilityPipeline,
)


def format_currency(value):

    formatted = f"{float(value or 0):,.2f}"

    return (
        "R$ "
        + formatted
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def main():

    print("=" * 80)
    print("ARGUS — CARGA DE RENTABILIDADE")
    print("=" * 80)

    sql_connector = SQLServerConnector()
    supabase_connector = (
        SupabaseConnector()
    )

    pipeline = ProfitabilityPipeline(
        sql_connector,
        supabase_connector
    )

    result = pipeline.run()

    print()
    print(
        f"Períodos gerados: "
        f"{result['periods_generated']}"
    )
    print(
        f"Linhas YTD na origem: "
        f"{result['ytd_source_rows']:,}"
    )
    print(
        f"Linhas YTD analisáveis: "
        f"{result['ytd_analyzable_rows']:,}"
    )
    print(
        f"Dimensões YTD: "
        f"{result['ytd_dimensions']:,}"
    )
    print(
        f"Riscos YTD: "
        f"{result['ytd_risks']:,}"
    )
    print(
        f"Recomendações YTD: "
        f"{result['ytd_recommendations']:,}"
    )

    print()
    print(
        f"Faturamento YTD: "
        f"{format_currency(result['ytd_revenue'])}"
    )
    print(
        f"Lucro bruto YTD: "
        f"{format_currency(result['ytd_profit'])}"
    )
    print(
        f"Margem YTD: "
        f"{result['ytd_margin']:.2f}%"
    )
    print(
        f"Markup YTD: "
        f"{result['ytd_markup']:.2f}%"
    )
    print(
        f"Cobertura YTD: "
        f"{result['ytd_coverage'] * 100:.2f}%"
    )
    print(
        f"Status YTD: "
        f"{result['ytd_status']}"
    )

    print()
    print("=" * 80)
    print("CARGA FINALIZADA")
    print("=" * 80)


if __name__ == "__main__":
    main()