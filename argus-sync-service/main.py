from connectors.sql_server import SQLServerConnector
from connectors.supabase_connector import SupabaseConnector
from pipelines.executive_pipeline import ExecutivePipeline


def main():

    print("=" * 60)
    print("ARGUS SYNC SERVICE")
    print("=" * 60)

    sql_connector = SQLServerConnector()
    supabase_connector = SupabaseConnector()

    executive_pipeline = ExecutivePipeline(
        sql_connector,
        supabase_connector
    )

    result = executive_pipeline.run()

    print()
    print("Pipeline executada com sucesso.")
    print(f"Ranking atualizado: {result['seller_ranking_count']} vendedores.")
    print(f"Insights gerados: {result['insights_count']}.")
    print()
    print("ARGUS Sync finalizado com sucesso.")


if __name__ == "__main__":
    main()