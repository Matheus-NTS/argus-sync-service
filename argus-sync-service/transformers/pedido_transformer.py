import re
import unicodedata

import pandas as pd


class PedidoTransformer:

    def __init__(
        self,
        valid_status=None,
        valid_order_types=None,
    ):
        self.valid_status = valid_status or [
            "CONCRETIZADO",
        ]

        self.valid_order_types = valid_order_types or {
            "CT 0",
            "CT 100",
            "SERVICO",
        }

    @staticmethod
    def _normalize_value(value) -> str:
        """
        Normaliza textos para comparação:

        - remove espaços extras;
        - converte para maiúsculas;
        - remove acentos;
        - padroniza múltiplos espaços.
        """
        if pd.isna(value):
            return ""

        normalized = str(value).strip().upper()

        normalized = unicodedata.normalize(
            "NFKD",
            normalized,
        )

        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized

    @classmethod
    def _normalize_series(
        cls,
        series: pd.Series,
    ) -> pd.Series:
        return series.apply(cls._normalize_value)

    @classmethod
    def _normalize_column_name(
        cls,
        column_name,
    ) -> str:
        """
        Normaliza o nome da coluna sem alterar o DataFrame original.

        Exemplos:
        Tipo_Pedido -> tipo_pedido
        TIPO PEDIDO -> tipo_pedido
        Situação -> situacao
        """
        normalized = cls._normalize_value(column_name).lower()

        normalized = re.sub(
            r"[^a-z0-9]+",
            "_",
            normalized,
        )

        return normalized.strip("_")

    @classmethod
    def _find_column(
        cls,
        dataframe: pd.DataFrame,
        expected_names: list[str],
    ) -> str | None:
        """
        Retorna o nome real da coluna no DataFrame,
        comparando nomes normalizados.
        """
        normalized_columns = {
            cls._normalize_column_name(column): column
            for column in dataframe.columns
        }

        for expected_name in expected_names:
            normalized_expected = (
                cls._normalize_column_name(expected_name)
            )

            if normalized_expected in normalized_columns:
                return normalized_columns[normalized_expected]

        return None

    def filter_revenue_orders(
        self,
        pedidos_df: pd.DataFrame,
    ) -> pd.DataFrame:

        pedidos = pedidos_df.copy()

        situacao_column = self._find_column(
            pedidos,
            [
                "situacao",
                "situação",
                "status",
                "situacao_pedido",
            ],
        )

        tipo_pedido_column = self._find_column(
            pedidos,
            [
                "tipo_pedido",
                "tipo pedido",
                "tipopedido",
                "tipo_de_pedido",
            ],
        )

        missing_columns = []

        if situacao_column is None:
            missing_columns.append("situacao")

        if tipo_pedido_column is None:
            missing_columns.append("tipo_pedido")

        if missing_columns:
            available_columns = ", ".join(
                str(column)
                for column in pedidos.columns
            )

            raise KeyError(
                "Colunas obrigatórias não encontradas: "
                + ", ".join(missing_columns)
                + ". Colunas disponíveis: "
                + available_columns
            )

        situacao_normalizada = self._normalize_series(
            pedidos[situacao_column]
        )

        tipo_pedido_normalizado = self._normalize_series(
            pedidos[tipo_pedido_column]
        )

        valid_status = {
            self._normalize_value(status)
            for status in self.valid_status
        }

        valid_order_types = {
            self._normalize_value(order_type)
            for order_type in self.valid_order_types
        }

        valid_status_mask = (
            situacao_normalizada.isin(valid_status)
        )

        valid_exact_type_mask = (
            tipo_pedido_normalizado.isin(
                valid_order_types
            )
        )

        # Inclui qualquer variação comercial iniciada por CT 30.
        valid_ct30_mask = (
            tipo_pedido_normalizado
            .str.startswith("CT 30")
        )

        valid_order_type_mask = (
            valid_exact_type_mask
            | valid_ct30_mask
        )

        filtered_orders = pedidos[
            valid_status_mask
            & valid_order_type_mask
        ].copy()

        print()
        print("Filtro comercial aplicado:")
        print(
            f"  Registros recebidos: "
            f"{len(pedidos):,}"
        )
        print(
            f"  Situação válida: "
            f"{int(valid_status_mask.sum()):,}"
        )
        print(
            f"  Tipo comercial válido: "
            f"{int(valid_order_type_mask.sum()):,}"
        )
        print(
            f"  Vendas concretizadas mantidas: "
            f"{len(filtered_orders):,}"
        )
        print(
            f"  Registros excluídos: "
            f"{len(pedidos) - len(filtered_orders):,}"
        )

        return filtered_orders