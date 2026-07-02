from connectors.sql_server import SQLServerConnector
from extractors.produto_extractor import ProdutoExtractor
from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer
from features.intelligence.stock.stock_snapshot import StockSnapshot

sql = SQLServerConnector()

estoque = ProdutoExtractor(sql).extract()
vendas = PedidoTransformer().filter_revenue_orders(
    PedidoExtractor(sql).extract()
)

stock_df = StockSnapshot().build(estoque, vendas)

print(
    stock_df[
        stock_df["codigo_produto"].astype(str).str.strip() == "000693"
    ][[
        "codigo_produto",
        "Descricao",
        "Empresa",
        "empresa_key",
        "Quantidade_Estoque",
        "qtd_vendida_30d",
        "qtd_vendida_90d",
        "ultima_venda",
        "media_venda_mensal",
        "cobertura_estoque",
        "risk_type",
        "status"
    ]]
)