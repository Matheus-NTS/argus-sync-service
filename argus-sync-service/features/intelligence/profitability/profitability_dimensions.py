import pandas as pd


class ProfitabilityDimensions:

    DIMENSIONS = {
        "company": [
            "empresa_key",
        ],
        "seller": [
            "vendedor",
        ],
        "customer": [
            "codigo_cliente_normalizado",
            "cliente",
        ],
        "product": [
            "codigo_produto",
            "produto",
            "codigo_fabricante",
            "categoria",
            "curva_abcde",
        ],
        "category": [
            "categoria",
        ],
        "curve": [
            "curva_abcde",
        ],
    }

    @staticmethod
    def _safe_value(value):

        if value is None or pd.isna(value):
            return None

        return str(value)

    def _build_dimension(
        self,
        eligible,
        dimension_type,
        group_columns,
        total_revenue,
        total_profit
    ):

        grouped = (
            eligible
            .groupby(
                group_columns,
                dropna=False
            )
            .agg(
                faturamento=(
                    "faturamento_analisavel",
                    "sum"
                ),
                custo=(
                    "custo_analisavel",
                    "sum"
                ),
                lucro=(
                    "lucro_analisavel",
                    "sum"
                ),
                quantidade=(
                    "quantidade",
                    "sum"
                ),
                pedidos=(
                    "numero_pedido",
                    "nunique"
                ),
                clientes=(
                    "codigo_cliente_normalizado",
                    "nunique"
                ),
                produtos=(
                    "codigo_produto",
                    "nunique"
                ),
                vendedores=(
                    "vendedor",
                    "nunique"
                ),
                data_primeira_venda=(
                    "data_venda",
                    "min"
                ),
                data_ultima_venda=(
                    "data_venda",
                    "max"
                ),
            )
            .reset_index()
        )

        grouped["margem_percentual"] = (
            grouped["lucro"]
            / grouped["faturamento"]
            * 100
        ).where(
            grouped["faturamento"] > 0
        )

        grouped["markup_percentual"] = (
            grouped["lucro"]
            / grouped["custo"]
            * 100
        ).where(
            grouped["custo"] > 0
        )

        grouped["ticket_medio"] = (
            grouped["faturamento"]
            / grouped["pedidos"]
        ).where(
            grouped["pedidos"] > 0
        )

        grouped["ticket_lucro"] = (
            grouped["lucro"]
            / grouped["pedidos"]
        ).where(
            grouped["pedidos"] > 0
        )

        if total_revenue > 0:
            grouped["participacao_faturamento"] = (
                grouped["faturamento"] / total_revenue
            )
        else:
            grouped["participacao_faturamento"] = None

        if total_profit != 0:
            grouped["participacao_lucro"] = (
                grouped["lucro"] / total_profit
            )
        else:
            grouped["participacao_lucro"] = None

        def classify_status(row):

            margem = row["margem_percentual"]
            lucro = row["lucro"]

            if lucro < 0:
                return "prejuizo"

            if pd.isna(margem):
                return "sem_margem"

            if margem < 5:
                return "critico"

            if margem < 10:
                return "margem_baixa"

            if margem < 20:
                return "monitoramento"

            if margem < 30:
                return "saudavel"

            if margem < 40:
                return "alta_rentabilidade"

            return "excelente"

        grouped["status"] = grouped.apply(
            classify_status,
            axis=1
        )

        records = []

        for _, row in grouped.iterrows():

            dimension_values = {
                column: self._safe_value(
                    row.get(column)
                )
                for column in group_columns
            }

            primary_value = (
                dimension_values.get(
                    group_columns[-1]
                )
                or "Não informado"
            )

            if dimension_type == "customer":
                primary_value = (
                    dimension_values.get("cliente")
                    or dimension_values.get(
                        "codigo_cliente_normalizado"
                    )
                    or "Não informado"
                )

            if dimension_type == "product":
                primary_value = (
                    dimension_values.get("produto")
                    or dimension_values.get(
                        "codigo_produto"
                    )
                    or "Não informado"
                )

            records.append({
                "dimension_type": dimension_type,
                "dimension_key": "||".join(
                    [
                        dimension_values.get(column)
                        or ""
                        for column in group_columns
                    ]
                ),
                "dimension_value": primary_value,
                "dimension_data": dimension_values,
                "faturamento": round(
                    float(row["faturamento"]),
                    2
                ),
                "custo": round(
                    float(row["custo"]),
                    2
                ),
                "lucro": round(
                    float(row["lucro"]),
                    2
                ),
                "margem_percentual": (
                    None
                    if pd.isna(
                        row["margem_percentual"]
                    )
                    else round(
                        float(
                            row["margem_percentual"]
                        ),
                        4
                    )
                ),
                "markup_percentual": (
                    None
                    if pd.isna(
                        row["markup_percentual"]
                    )
                    else round(
                        float(
                            row["markup_percentual"]
                        ),
                        4
                    )
                ),
                "quantidade": round(
                    float(row["quantidade"]),
                    2
                ),
                "pedidos": int(row["pedidos"]),
                "clientes": int(row["clientes"]),
                "produtos": int(row["produtos"]),
                "vendedores": int(
                    row["vendedores"]
                ),
                "ticket_medio": (
                    None
                    if pd.isna(row["ticket_medio"])
                    else round(
                        float(row["ticket_medio"]),
                        2
                    )
                ),
                "ticket_lucro": (
                    None
                    if pd.isna(row["ticket_lucro"])
                    else round(
                        float(row["ticket_lucro"]),
                        2
                    )
                ),
                "participacao_faturamento": (
                    None
                    if pd.isna(
                        row[
                            "participacao_faturamento"
                        ]
                    )
                    else round(
                        float(
                            row[
                                "participacao_faturamento"
                            ]
                        ),
                        6
                    )
                ),
                "participacao_lucro": (
                    None
                    if pd.isna(
                        row["participacao_lucro"]
                    )
                    else round(
                        float(
                            row["participacao_lucro"]
                        ),
                        6
                    )
                ),
                "data_primeira_venda": (
                    None
                    if pd.isna(
                        row["data_primeira_venda"]
                    )
                    else row[
                        "data_primeira_venda"
                    ].date().isoformat()
                ),
                "data_ultima_venda": (
                    None
                    if pd.isna(
                        row["data_ultima_venda"]
                    )
                    else row[
                        "data_ultima_venda"
                    ].date().isoformat()
                ),
                "status": row["status"],
            })

        return records

    def build(self, dataset):

        eligible = dataset[
            dataset["elegivel_kpi"]
        ].copy()

        total_revenue = float(
            eligible["faturamento_analisavel"].sum()
        )

        total_profit = float(
            eligible["lucro_analisavel"].sum()
        )

        result = {}

        for (
            dimension_type,
            group_columns
        ) in self.DIMENSIONS.items():

            result[dimension_type] = (
                self._build_dimension(
                    eligible=eligible,
                    dimension_type=dimension_type,
                    group_columns=group_columns,
                    total_revenue=total_revenue,
                    total_profit=total_profit
                )
            )

        return result