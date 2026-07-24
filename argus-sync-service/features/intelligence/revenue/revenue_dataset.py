import pandas as pd

from features.shared.commercial_dimensions import (
    CommercialDimensions,
)
from transformers.pedido_transformer import PedidoTransformer


class RevenueDataset:
    """
    Prepara a base oficial de faturamento do ARGUS.

    Regras aplicadas:
    - apenas pedidos comerciais válidos;
    - apenas situação CONCRETIZADO;
    - padronização de datas e valores;
    - normalização das dimensões de empresa e vendedor;
    - remoção de linhas sem data ou faturamento válido.

    Observações:
    - o produto 999999 compõe o faturamento oficial
      e não deve ser excluído deste módulo;
    - o campo Vendedor permanece com o nome completo
      normalizado, pois será usado como chave interna;
    - o nome resumido do vendedor será criado apenas
      nas camadas de apresentação.
    """

    REQUIRED_COLUMNS = [
        "Data",
        "Valor_total_Unitario",
        "Empresa",
        "Vendedor",
        "numero_pedido",
        "prod_codigo",
    ]

    def build(
        self,
        pedidos_df: pd.DataFrame,
    ) -> pd.DataFrame:
        if pedidos_df is None:
            raise ValueError(
                "A base de pedidos não pode ser None."
            )

        pedidos = pedidos_df.copy()

        self._validate_columns(pedidos)

        pedidos = PedidoTransformer().filter_revenue_orders(
            pedidos
        )

        pedidos["Data"] = pd.to_datetime(
            pedidos["Data"],
            errors="coerce",
        )

        pedidos["Valor_total_Unitario"] = pd.to_numeric(
            pedidos["Valor_total_Unitario"],
            errors="coerce",
        )

        valid_date_mask = pedidos[
            "Data"
        ].notna()

        valid_revenue_mask = pedidos[
            "Valor_total_Unitario"
        ].notna()

        pedidos = pedidos[
            valid_date_mask
            & valid_revenue_mask
        ].copy()

        pedidos["ano"] = (
            pedidos["Data"]
            .dt.year
            .astype(int)
        )

        pedidos["mes"] = (
            pedidos["Data"]
            .dt.month
            .astype(int)
        )

        pedidos["ano_mes"] = (
            pedidos["Data"]
            .dt.to_period("M")
            .astype(str)
        )

        pedidos["Empresa"] = (
            pedidos["Empresa"]
            .apply(
                CommercialDimensions.normalize_company
            )
        )

        pedidos["Vendedor"] = (
            pedidos["Vendedor"]
            .apply(
                CommercialDimensions.normalize_seller
            )
        )

        print()
        print(
            "Base oficial de faturamento preparada:"
        )

        print(
            f"  Registros finais: {len(pedidos):,}"
        )

        print(
            "  Data inicial: "
            f"{pedidos['Data'].min()}"
        )

        print(
            "  Data final: "
            f"{pedidos['Data'].max()}"
        )

        print(
            "  Faturamento total da base: R$ "
            f"{pedidos['Valor_total_Unitario'].sum():,.2f}"
        )

        return pedidos

    def _validate_columns(
        self,
        pedidos_df: pd.DataFrame,
    ) -> None:
        missing_columns = [
            column
            for column in self.REQUIRED_COLUMNS
            if column not in pedidos_df.columns
        ]

        if missing_columns:
            raise KeyError(
                "Colunas obrigatórias ausentes "
                "na base de pedidos: "
                + ", ".join(missing_columns)
            )