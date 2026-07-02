from connectors.sql_server import SQLServerConnector
from extractors.produto_extractor import ProdutoExtractor
from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer


sql = SQLServerConnector()

estoque = ProdutoExtractor(sql).extract()
vendas_raw = PedidoExtractor(sql).extract()

vendas = PedidoTransformer().filter_revenue_orders(vendas_raw)

codigo = "000693"

print("\n=== ESTOQUE 000693 ===")
print(
    estoque[
        estoque["Codigo_Supra"].astype(str).str.strip() == codigo
    ][["Codigo_Supra", "Descricao", "Empresa", "Quantidade_Estoque", "preco_custo"]]
)

print("\n=== VENDAS RAW 000693 ===")
print(
    vendas_raw[
        vendas_raw["prod_codigo"].astype(str).str.strip() == codigo
    ][["Data", "prod_codigo", "produto", "Empresa", "Quantidade", "Valor_total_Unitario", "situacao", "Tipo_Pedido"]]
    .sort_values("Data", ascending=False)
    .head(50)
)

print("\n=== VENDAS APÓS TRANSFORMER 000693 ===")
print(
    vendas[
        vendas["prod_codigo"].astype(str).str.strip() == codigo
    ][["Data", "prod_codigo", "produto", "Empresa", "Quantidade", "Valor_total_Unitario", "situacao", "Tipo_Pedido"]]
    .sort_values("Data", ascending=False)
    .head(50)
)

print("\n=== AGRUPADO RAW POR EMPRESA ===")
print(
    vendas_raw[
        vendas_raw["prod_codigo"].astype(str).str.strip() == codigo
    ]
    .groupby(["Empresa", "situacao", "Tipo_Pedido"], dropna=False)
    .agg(
        qtd=("Quantidade", "sum"),
        faturamento=("Valor_total_Unitario", "sum"),
        ultima_venda=("Data", "max")
    )
    .reset_index()
)

print("\n=== AGRUPADO APÓS TRANSFORMER POR EMPRESA ===")
print(
    vendas[
        vendas["prod_codigo"].astype(str).str.strip() == codigo
    ]
    .groupby(["Empresa"], dropna=False)
    .agg(
        qtd=("Quantidade", "sum"),
        faturamento=("Valor_total_Unitario", "sum"),
        ultima_venda=("Data", "max")
    )
    .reset_index()
)