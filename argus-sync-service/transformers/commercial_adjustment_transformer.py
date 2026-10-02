from decimal import Decimal, ROUND_HALF_UP

import pandas as pd


class CommercialAdjustmentTransformer:

    ADJUSTMENTS = {
        40324: {
            "expected_original_total": Decimal("96831.89"),
            "adjusted_total": Decimal("41425.00"),
            "reason": (
                "Desconto comercial excepcional geral "
                "nao refletido no sistema de origem."
            ),
        },
    }

    MONEY_QUANT = Decimal("0.01")

    @classmethod
    def _money(cls, value) -> Decimal:
        return Decimal(str(value)).quantize(
            cls.MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def _apply_order_adjustment(
        cls,
        pedidos: pd.DataFrame,
        order_number: int,
        adjustment: dict,
    ) -> None:
        order_mask = (
            pd.to_numeric(
                pedidos["numero_pedido"],
                errors="coerce",
            )
            == order_number
        )

        indexes = pedidos.index[order_mask].tolist()

        if not indexes:
            return

        original_values = [
            cls._money(
                pedidos.at[index, "Valor_total_Unitario"]
            )
            for index in indexes
        ]

        original_total = sum(
            original_values,
            Decimal("0.00"),
        )

        expected_original_total = adjustment[
            "expected_original_total"
        ]

        adjusted_total = adjustment[
            "adjusted_total"
        ]

        if original_total != expected_original_total:
            raise ValueError(
                "Ajuste comercial abortado para pedido "
                f"{order_number}: total original encontrado "
                f"R$ {original_total} difere do esperado "
                f"R$ {expected_original_total}."
            )

        factor = (
            adjusted_total
            / expected_original_total
        )

        adjusted_values = []

        for value in original_values:
            adjusted_values.append(
                (value * factor).quantize(
                    cls.MONEY_QUANT,
                    rounding=ROUND_HALF_UP,
                )
            )

        rounding_difference = (
            adjusted_total
            - sum(
                adjusted_values,
                Decimal("0.00"),
            )
        )

        if rounding_difference:
            adjusted_values[-1] += rounding_difference

        final_total = sum(
            adjusted_values,
            Decimal("0.00"),
        )

        if final_total != adjusted_total:
            raise ValueError(
                "Ajuste comercial abortado para pedido "
                f"{order_number}: rateio final nao fecha "
                f"em R$ {adjusted_total}."
            )

        for index, adjusted_value in zip(
            indexes,
            adjusted_values,
        ):
            quantity = Decimal(
                str(
                    pedidos.at[
                        index,
                        "Quantidade",
                    ]
                )
            )

            if quantity <= 0:
                raise ValueError(
                    "Ajuste comercial abortado para pedido "
                    f"{order_number}: quantidade invalida "
                    f"na linha {index}."
                )

            adjusted_unit_value = (
                adjusted_value / quantity
            )

            pedidos.at[
                index,
                "Valor_total_Unitario",
            ] = float(adjusted_value)

            pedidos.at[
                index,
                "valor_unitario",
            ] = float(adjusted_unit_value)

        validation_total = cls._money(
            pd.to_numeric(
                pedidos.loc[
                    order_mask,
                    "Valor_total_Unitario",
                ],
                errors="coerce",
            ).sum()
        )

        if validation_total != adjusted_total:
            raise ValueError(
                "Ajuste comercial abortado para pedido "
                f"{order_number}: validacao apos escrita "
                f"resultou em R$ {validation_total}."
            )

        discount = (
            expected_original_total
            - adjusted_total
        )

        print()
        print(
            "[COMMERCIAL ADJUSTMENT] "
            f"Pedido {order_number}"
        )
        print(
            "  Motivo: "
            f"{adjustment['reason']}"
        )
        print(
            "  Valor original: "
            f"R$ {expected_original_total}"
        )
        print(
            "  Ajuste: "
            f"-R$ {discount}"
        )
        print(
            "  Valor final: "
            f"R$ {validation_total}"
        )

    def apply(
        self,
        pedidos_df: pd.DataFrame,
    ) -> pd.DataFrame:
        pedidos = pedidos_df.copy()

        required_columns = {
            "numero_pedido",
            "Quantidade",
            "valor_unitario",
            "Valor_total_Unitario",
        }

        missing_columns = (
            required_columns
            - set(pedidos.columns)
        )

        if missing_columns:
            raise KeyError(
                "Colunas obrigatorias para ajustes "
                "comerciais nao encontradas: "
                + ", ".join(
                    sorted(missing_columns)
                )
            )

        for order_number, adjustment in (
            self.ADJUSTMENTS.items()
        ):
            self._apply_order_adjustment(
                pedidos,
                order_number,
                adjustment,
            )

        return pedidos
