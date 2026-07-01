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

    executive = ExecutivePipeline(
        sql_connector,
        supabase_connector
    )

    executive_result = executive.run()

    sales = SalesPipeline(
        sql_connector,
        supabase_connector
    )

    sales_result = sales.run()

    print()
    print("✓ Executive Pipeline finalizada")
    print(f"  Insights: {executive_result['insights_count']}")

    print()
    print("✓ Sales Pipeline finalizada")
    print(f"  Ranking: {sales_result['seller_ranking']} vendedores")
    print(f"  Empresas: {sales_result['companies']}")
    print(f"  Produtos: {sales_result['products']}")
    print(f"  Clientes: {sales_result['customers']}")
    print(f"  Categorias: {sales_result['categories']}")

    print()
    print("=" * 60)
    print("ARGUS SYNC FINALIZADO")
    print("=" * 60)


if __name__ == "__main__":
    main()