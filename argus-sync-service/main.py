from time import perf_counter
from connectors.sql_server import SQLServerConnector
from connectors.supabase_connector import SupabaseConnector
from connectors.google_sheets_connector import GoogleSheetsConnector

from pipelines.executive_pipeline import ExecutivePipeline
from pipelines.sales_pipeline import SalesPipeline
from pipelines.stock_pipeline import StockPipeline
from pipelines.customer_geo_pipeline import CustomerGeoPipeline
from pipelines.lost_sales_pipeline import LostSalesPipeline
from pipelines.profitability_pipeline import ProfitabilityPipeline
from services.pipeline_state import mark_pipeline_success
from services.sync_run_lock import (
    SyncAlreadyRunningError,
    SyncRunLock,
)
from services.sync_run_logger import SyncRunLogger

def run_timed(label, callback):
    started_at = perf_counter()

    print()
    print(f"[TIMING] Iniciando {label}...")

    result = callback()

    elapsed = perf_counter() - started_at

    print(
        f"[TIMING] {label} concluída em "
        f"{elapsed:.2f}s "
        f"({elapsed / 60:.2f} min)"
    )

    return result, elapsed

def main():
    main_started_at = perf_counter()

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    sql_connector = SQLServerConnector()
    supabase_connector = SupabaseConnector()
    google_sheets_connector = GoogleSheetsConnector()

    sales = SalesPipeline(
        sql_connector,
        supabase_connector
    )
    sales_result, sales_elapsed = run_timed(
        "Sales Pipeline",
        sales.run,
    )

    mark_pipeline_success(
    supabase_connector,
    "sales",
    )

    customer_geo = CustomerGeoPipeline(
        sql_connector,
        supabase_connector
    )
    customer_geo_result, customer_geo_elapsed = run_timed(
        "Customer Geo Pipeline",
        customer_geo.run,
    )

    mark_pipeline_success(
    supabase_connector,
    "customer_geo",
    )

    stock = StockPipeline(
        sql_connector,
        supabase_connector
    )
    stock_result, stock_elapsed = run_timed(
        "Stock Pipeline",
        stock.run,
    )

    mark_pipeline_success(
    supabase_connector,
    "stock",
    )

    profitability = ProfitabilityPipeline(
        sql_connector,
        supabase_connector
    )
    profitability_result, profitability_elapsed = run_timed(
        "Profitability Pipeline",
        profitability.run,
    )

    mark_pipeline_success(
    supabase_connector,
    "profitability",
    )

    lost_sales = LostSalesPipeline(
        google_sheets_connector,
        supabase_connector
    )
    lost_sales_result, lost_sales_elapsed = run_timed(
        "Lost Sales Pipeline",
        lost_sales.run,
    )

    mark_pipeline_success(
    supabase_connector,
    "lost_sales",
    )

    # A IA ARGUS depende das marts publicadas pelos pipelines anteriores.
    # Por isso, o Executive Pipeline deve ser executado por último.
    executive = ExecutivePipeline(
        sql_connector,
        supabase_connector
    )
    executive_result, executive_elapsed = run_timed(
        "Executive Pipeline",
        executive.run,
    )

    mark_pipeline_success(
    supabase_connector,
    "executive",
    )

    total_elapsed = (
        sales_elapsed
        + customer_geo_elapsed
        + stock_elapsed
        + profitability_elapsed
        + lost_sales_elapsed
        + executive_elapsed
    )

    print()
    print("=" * 60)
    print("TEMPO DAS PIPELINES")
    print("=" * 60)
    print(
        f"Sales:          {sales_elapsed:8.2f}s "
        f"({sales_elapsed / 60:.2f} min)"
    )
    print(
        f"Customer Geo:   {customer_geo_elapsed:8.2f}s "
        f"({customer_geo_elapsed / 60:.2f} min)"
    )
    print(
        f"Stock:          {stock_elapsed:8.2f}s "
        f"({stock_elapsed / 60:.2f} min)"
    )
    print(
        f"Profitability:  {profitability_elapsed:8.2f}s "
        f"({profitability_elapsed / 60:.2f} min)"
    )
    print(
        f"Lost Sales:     {lost_sales_elapsed:8.2f}s "
        f"({lost_sales_elapsed / 60:.2f} min)"
    )
    print(
        f"Executive:      {executive_elapsed:8.2f}s "
        f"({executive_elapsed / 60:.2f} min)"
    )
    print("-" * 60)
    print(
        f"TOTAL:          {total_elapsed:8.2f}s "
        f"({total_elapsed / 60:.2f} min)"
    )

    print()
    print("Executive Pipeline finalizada")
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
    print(
        f"  Seller Intelligence: "
        f"{sales_result['commercial_sellers']} vendedores"
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
    print("✓ Revenue Intelligence finalizada")
    print(
        f"  Histórico mensal: "
        f"{sales_result['revenue_monthly_records']}"
    )
    print(
        f"  Empresas mensais: "
        f"{sales_result['revenue_company_monthly_records']}"
    )
    print(
        f"  Vendedores mensais: "
        f"{sales_result['revenue_seller_monthly_records']}"
    )
    print(
        f"  Resumo atual: "
        f"{sales_result['revenue_current_summary_records']}"
    )
    print(
        f"  Histórico anual: "
        f"{sales_result['revenue_yearly_records']}"
    )
    print(
        f"  Comparativos YTD: "
        f"{sales_result['revenue_ytd_records']}"
    )
    print(
        f"  Projeções mensais: "
        f"{sales_result['revenue_projection_monthly_records']}"
    )
    print(
        f"  Resumo de projeções: "
        f"{sales_result['revenue_projection_summary_records']}"
    )
    print(
        f"  Ano-base da projeção: "
        f"{sales_result['revenue_projection_base_year']}"
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
    print("✓ Profitability Pipeline finalizada")
    print(
        f"  Períodos gerados: "
        f"{profitability_result['periods_generated']}"
    )
    print(
        f"  Linhas YTD na origem: "
        f"{profitability_result['ytd_source_rows']:,}"
    )
    print(
        f"  Linhas YTD analisáveis: "
        f"{profitability_result['ytd_analyzable_rows']:,}"
    )
    print(
        f"  Dimensões YTD: "
        f"{profitability_result['ytd_dimensions']:,}"
    )
    print(
        f"  Riscos YTD: "
        f"{profitability_result['ytd_risks']:,}"
    )
    print(
        f"  Recomendações YTD: "
        f"{profitability_result['ytd_recommendations']:,}"
    )
    print(
        f"  Faturamento analisável YTD: R$ "
        f"{profitability_result['ytd_revenue']:,.2f}"
    )
    print(
        f"  Lucro bruto estimado YTD: R$ "
        f"{profitability_result['ytd_profit']:,.2f}"
    )
    print(
        f"  Margem ponderada YTD: "
        f"{profitability_result['ytd_margin']:.2f}%"
    )
    print(
        f"  Markup ponderado YTD: "
        f"{profitability_result['ytd_markup']:.2f}%"
    )
    print(
        f"  Cobertura financeira YTD: "
        f"{profitability_result['ytd_coverage'] * 100:.2f}%"
    )
    print(
        f"  Status YTD: "
        f"{profitability_result['ytd_status']}"
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
    print("✓ IA ARGUS finalizada")
    print(
        f"  Briefing: "
        f"{executive_result['argus_ai_briefing']}"
    )
    print(
        f"  Mudanças: "
        f"{executive_result['argus_ai_changes']}"
    )
    print(
        f"  Atenções: "
        f"{executive_result['argus_ai_attention']}"
    )
    print(
        f"  Oportunidades: "
        f"{executive_result['argus_ai_opportunities']}"
    )
    print(
        f"  Ações: "
        f"{executive_result['argus_ai_actions']}"
    )
    print(
        f"  Eventos: "
        f"{executive_result['argus_ai_events']}"
    )
    print(
        f"  Insights legados preservados: "
        f"{executive_result['insights_count']}"
    )

    print()
    print("=" * 60)
    print("ARGUS SYNC FINALIZADO")
    print("=" * 60)

    main_elapsed = perf_counter() - main_started_at
    pipeline_overhead = main_elapsed - total_elapsed

    print()
    print("=" * 60)
    print("TEMPO TOTAL DO SYNC")
    print("=" * 60)
    print(
        f"Pipelines medidas: {total_elapsed:.2f}s "
        f"({total_elapsed / 60:.2f} min)"
    )
    print(
        f"Overhead restante: {pipeline_overhead:.2f}s "
        f"({pipeline_overhead / 60:.2f} min)"
    )
    print(
        f"MAIN COMPLETO:     {main_elapsed:.2f}s "
        f"({main_elapsed / 60:.2f} min)"
    )

if __name__ == "__main__":
    with SyncRunLogger():
        try:
            with SyncRunLock():
                main()
        except SyncAlreadyRunningError as exc:
            print()
            print("=" * 60)
            print("ARGUS SYNC NAO INICIADO")
            print("=" * 60)
            print(str(exc))
            print(
                "A execucao atual permanece protegida; "
                "nenhuma pipeline foi iniciada."
            )
            raise SystemExit(75)