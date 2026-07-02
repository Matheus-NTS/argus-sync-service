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

    executive = ExecutivePipeline(sql_connector, supabase_connector)
    executive_result = executive.run()

    sales = SalesPipeline(sql_connector, supabase_connector)
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
    print(f"  Commercial Facts: {sales_result['commercial_facts']}")
    print(f"  Commercial Summary: {sales_result['commercial_summary']}")
    print(f"  Commercial Recommendations: {sales_result['commercial_recommendations']}")
    print(f"  Commercial Alerts: {sales_result['commercial_alerts']}")
    print(f"  ABC Produtos: {sales_result['abc_products']}")
    print(f"  ABC Clientes: {sales_result['abc_customers']}")
    print(f"  Commercial Concentration: {sales_result['commercial_concentration']}")
    print(f"  Customer Risks: {sales_result['customer_risks']}")
    print(f"  Product Risks: {sales_result['product_risks']}")
    print(f"  Commercial Overview: {sales_result['commercial_overview']}")
    print(f"  Commercial Scorecards: {sales_result['commercial_scorecards']}")
    print(f"  Product Overview: {sales_result['product_overview']}")
    print(f"  Product Scorecards: {sales_result['product_scorecards']}")
    print(f"  Customer Overview: {sales_result['customer_overview']}")
    print(f"  Customer Scorecards: {sales_result['customer_scorecards']}")
    print(f"  Category Overview: {sales_result['category_overview']}")
    print(f"  Commercial Status: {sales_result['commercial_status']}")
    print(f"  Product Status: {sales_result['product_status']}")
    print(f"  Customer Status: {sales_result['customer_status']}")
    print(f"  Category Status: {sales_result['category_status']}")

    print()
    print("=" * 60)
    print("ARGUS SYNC FINALIZADO")
    print("=" * 60)


if __name__ == "__main__":
    main()