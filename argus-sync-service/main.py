from connectors.sql_server import SQLServerConnector
from connectors.supabase_connector import SupabaseConnector
from connectors.google_sheets_connector import GoogleSheetsConnector

from pipelines.executive_pipeline import ExecutivePipeline
from pipelines.sales_pipeline import SalesPipeline
from pipelines.stock_pipeline import StockPipeline
from pipelines.customer_geo_pipeline import CustomerGeoPipeline
from pipelines.lost_sales_pipeline import LostSalesPipeline


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    sql_connector = SQLServerConnector()
    supabase_connector = SupabaseConnector()
    google_sheets_connector = GoogleSheetsConnector()

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

    customer_geo = CustomerGeoPipeline(
        sql_connector,
        supabase_connector
    )
    customer_geo_result = customer_geo.run()

    stock = StockPipeline(
        sql_connector,
        supabase_connector
    )
    stock_result = stock.run()

    lost_sales = LostSalesPipeline(
        google_sheets_connector,
        supabase_connector
    )
    lost_sales_result = lost_sales.run()

    print()
    print("✓ Executive Pipeline finalizada")
    print(
        f"  Insights: "
        f"{executive_result['insights_count']}"
    )

    print()
    print("✓ Sales Pipeline finalizada")
    print(
        f"  Períodos gerados: "
        f"{sales_result['periods_generated']}"
    )
    print(
        f"  Ranking: "
        f"{sales_result['seller_ranking']} vendedores"
    )
    print(f"  Empresas: {sales_result['companies']}")
    print(f"  Produtos: {sales_result['products']}")
    print(f"  Clientes: {sales_result['customers']}")
    print(f"  Categorias: {sales_result['categories']}")
    print(
        f"  Commercial Facts: "
        f"{sales_result['commercial_facts']}"
    )
    print(
        f"  Commercial Summary: "
        f"{sales_result['commercial_summary']}"
    )
    print(
        f"  Commercial Recommendations: "
        f"{sales_result['commercial_recommendations']}"
    )
    print(
        f"  Commercial Alerts: "
        f"{sales_result['commercial_alerts']}"
    )
    print(
        f"  ABC Produtos: "
        f"{sales_result['abc_products']}"
    )
    print(
        f"  ABC Clientes: "
        f"{sales_result['abc_customers']}"
    )
    print(
        f"  Commercial Concentration: "
        f"{sales_result['commercial_concentration']}"
    )
    print(
        f"  Customer Risks: "
        f"{sales_result['customer_risks']}"
    )
    print(
        f"  Product Risks: "
        f"{sales_result['product_risks']}"
    )
    print(
        f"  Commercial Overview: "
        f"{sales_result['commercial_overview']}"
    )
    print(
        f"  Commercial Scorecards: "
        f"{sales_result['commercial_scorecards']}"
    )
    print(
        f"  Product Overview: "
        f"{sales_result['product_overview']}"
    )
    print(
        f"  Product Scorecards: "
        f"{sales_result['product_scorecards']}"
    )
    print(
        f"  Customer Overview: "
        f"{sales_result['customer_overview']}"
    )
    print(
        f"  Customer Scorecards: "
        f"{sales_result['customer_scorecards']}"
    )
    print(
        f"  Category Overview: "
        f"{sales_result['category_overview']}"
    )
    print(
        f"  Category Scorecards: "
        f"{sales_result['category_scorecards']}"
    )
    print(
        f"  Commercial Status: "
        f"{sales_result['commercial_status']}"
    )
    print(
        f"  Product Status: "
        f"{sales_result['product_status']}"
    )
    print(
        f"  Customer Status: "
        f"{sales_result['customer_status']}"
    )
    print(
        f"  Category Status: "
        f"{sales_result['category_status']}"
    )

    print()
    print("✓ Customer Geo Pipeline finalizada")
    print(
        f"  Registros geográficos: "
        f"{customer_geo_result['geo_records']}"
    )
    print(
        f"  Pendentes de geocodificação: "
        f"{customer_geo_result['geo_pending']}"
    )
    print(
        f"  Coordenadas reutilizadas: "
        f"{customer_geo_result['geo_cached']}"
    )
    print(
        f"  Endereços inválidos: "
        f"{customer_geo_result['geo_invalid']}"
    )

    print()
    print("✓ Stock Pipeline finalizada")
    print(
        f"  Produtos em estoque analisados: "
        f"{stock_result['stock_products']}"
    )
    print(
        f"  Críticos: "
        f"{stock_result['stock_critical']}"
    )
    print(
        f"  Atenção: "
        f"{stock_result['stock_attention']}"
    )
    print(
        f"  Saudáveis: "
        f"{stock_result['stock_healthy']}"
    )
    print(
        f"  Stock Overview: "
        f"{stock_result['stock_overview']}"
    )
    print(
        f"  Stock Scorecards: "
        f"{stock_result['stock_scorecards']}"
    )
    print(
        f"  Stock Risks: "
        f"{stock_result['stock_risks']}"
    )
    print(
        f"  Stock by Company: "
        f"{stock_result['stock_company']}"
    )
    print(
        f"  Stock Status: "
        f"{stock_result['stock_status']}"
    )

    print()
    print("✓ Lost Sales Pipeline finalizada")
    print(
        f"  Registros na origem: "
        f"{lost_sales_result['source_records']}"
    )
    print(
        f"  Registros carregados: "
        f"{lost_sales_result['lost_sales_records']}"
    )
    print(
        f"  Registros válidos: "
        f"{lost_sales_result['lost_sales_valid']}"
    )
    print(
        f"  Registros em atenção: "
        f"{lost_sales_result['lost_sales_attention']}"
    )
    print(
        f"  Registros inválidos: "
        f"{lost_sales_result['lost_sales_invalid']}"
    )
    print(
        f"  Valor perdido total: R$ "
        f"{lost_sales_result['lost_sales_value']:,.2f}"
    )

    print()
    print("=" * 60)
    print("ARGUS SYNC FINALIZADO")
    print("=" * 60)


if __name__ == "__main__":
    main()