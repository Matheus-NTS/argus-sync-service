from connectors.sql_server import SQLServerConnector
from connectors.supabase_connector import SupabaseConnector

from pipelines.executive_pipeline import ExecutivePipeline
from pipelines.sales_pipeline import SalesPipeline


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    sql_connector = SQLServerConnector()
    supabase_connector = SupabaseConnector()

    # ==========================
    # Executive
    # ==========================

    executive = ExecutivePipeline(
        sql_connector,
        supabase_connector
    )

    executive_result = executive.run()

    # ==========================
    # Sales
    # ==========================

    sales = SalesPipeline(
        sql_connector,
        supabase_connector
    )

    sales_result = sales.run()

    # ==========================
    # LOG
    # ==========================

    print()

    print("✓ Executive Pipeline finalizada")
    print(f"  Insights: {executive_result['insights_count']}")

    print()

    print("✓ Sales Pipeline finalizada")
    print(f"  Ranking: {sales_result['seller_ranking']} vendedores")
    print(f"  Empresas: {sales_result['companies']}")

    print()

    print("=" * 60)
    print("ARGUS SYNC FINALIZADO")
    print("=" * 60)


if __name__ == "__main__":
    main()