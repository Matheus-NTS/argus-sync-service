"""Construcao isolada do dataset Atacado x Varejo.

Reutiliza os componentes oficiais de Rentabilidade.
Nao executa ProfitabilityPipeline.run() nem escreve em bancos.
"""

from datetime import datetime, timezone

from extractors.pedido_extractor import PedidoExtractor
from extractors.produto_extractor import ProdutoExtractor
from transformers.pedido_transformer import PedidoTransformer
from transformers.commercial_adjustment_transformer import (
    CommercialAdjustmentTransformer,
)
from transformers.produto_transformer import ProdutoTransformer
from features.intelligence.profitability.profitability_dataset import (
    ProfitabilityDataset,
)
from features.intelligence.profitability.profitability_channel import (
    build_channel_daily,
    read_customer_classifications,
)

from features.intelligence.profitability.profitability_channel_detail import build_channel_detail


def build_profitability_channel_snapshot(sql_connector):
    """Retorna (dados_por_canal, inicio_da_extracao_utc).

    Executa apenas leituras e transformacoes.
    Nao publica resultados.
    """
    source_as_of = datetime.now(timezone.utc)

    orders_raw = PedidoExtractor(sql_connector).extract()
    products_raw = ProdutoExtractor(sql_connector).extract()

    orders = (
        PedidoTransformer()
        .filter_revenue_orders(orders_raw)
    )

    orders = (
        CommercialAdjustmentTransformer()
        .apply(orders)
    )

    products = (
        ProdutoTransformer()
        .prepare(products_raw)
    )

    dataset = (
        ProfitabilityDataset()
        .build(orders, products)
    )

    dataset = dataset[
        dataset["data_venda"].notna()
    ].copy()

    customers = read_customer_classifications(sql_connector)

    channel_daily = build_channel_daily(dataset, customers)

    return channel_daily, source_as_of


def build_profitability_channel_full_snapshot(sql_connector):
    """Constroi agregado e detalhe em uma unica extracao, sem publicar."""
    source_as_of = datetime.now(timezone.utc)

    orders_raw = PedidoExtractor(sql_connector).extract()
    products_raw = ProdutoExtractor(sql_connector).extract()

    orders = PedidoTransformer().filter_revenue_orders(orders_raw)
    orders = CommercialAdjustmentTransformer().apply(orders)
    products = ProdutoTransformer().prepare(products_raw)

    dataset = ProfitabilityDataset().build(orders, products)
    dataset = dataset.loc[dataset["data_venda"].notna()].copy()

    customers = read_customer_classifications(sql_connector)

    channel_daily = build_channel_daily(dataset, customers)
    channel_detail = build_channel_detail(dataset, customers)

    return channel_daily, channel_detail, source_as_of
