import pandas as pd


class ProfitabilityOverview:

    @staticmethod
    def _weighted_metrics(df):

        eligible = df[
            df["elegivel_kpi"]
        ].copy()

        faturamento = float(
            eligible["faturamento_analisavel"].sum()
        )

        custo = float(
            eligible["custo_analisavel"].sum()
        )

        lucro = float(
            eligible["lucro_analisavel"].sum()
        )

        margem = (
            lucro / faturamento * 100
            if faturamento > 0
            else 0
        )

        markup = (
            lucro / custo * 100
            if custo > 0
            else 0
        )

        return {
            "faturamento": faturamento,
            "custo": custo,
            "lucro": lucro,
            "margem": margem,
            "markup": markup,
        }

    @staticmethod
    def _classify_status(
        participacao_faturamento_critico,
        participacao_faturamento_prejuizo,
        impacto_prejuizo_sobre_faturamento,
        produtos_prejuizo,
    ):

        # Status baseado em materialidade financeira.
        # A quantidade absoluta de produtos não define sozinha
        # que toda a operação está crítica.

        if (
            participacao_faturamento_critico >= 0.20
            or impacto_prejuizo_sobre_faturamento >= 0.02
        ):
            return "critical"

        if (
            participacao_faturamento_critico >= 0.10
            or participacao_faturamento_prejuizo >= 0.05
            or impacto_prejuizo_sobre_faturamento >= 0.005
        ):
            return "attention"

        if (
            produtos_prejuizo > 0
            or participacao_faturamento_critico > 0
        ):
            return "monitoring"

        return "healthy"

    def build(self, dataset):

        total_rows = len(dataset)

        eligible = dataset[
            dataset["elegivel_kpi"]
        ].copy()

        metrics = self._weighted_metrics(dataset)

        pedidos = int(
            eligible["numero_pedido"].nunique()
        )

        produtos = int(
            eligible["codigo_produto"].nunique()
        )

        clientes = int(
            eligible[
                "codigo_cliente_normalizado"
            ].nunique()
        )

        vendedores = int(
            eligible["vendedor"].nunique()
        )

        empresas = int(
            eligible["empresa_key"].nunique()
        )

        quantidade = float(
            eligible["quantidade"].sum()
        )

        ticket_medio = (
            metrics["faturamento"] / pedidos
            if pedidos > 0
            else 0
        )

        ticket_lucro = (
            metrics["lucro"] / pedidos
            if pedidos > 0
            else 0
        )

        product_summary = (
            eligible
            .groupby(
                [
                    "codigo_produto",
                    "produto",
                ],
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
            )
            .reset_index()
        )

        product_summary["margem"] = (
            product_summary["lucro"]
            / product_summary["faturamento"]
            * 100
        ).where(
            product_summary["faturamento"] > 0
        )

        produtos_rentaveis = int(
            (
                product_summary["lucro"] > 0
            ).sum()
        )

        produtos_prejuizo = int(
            (
                product_summary["lucro"] < 0
            ).sum()
        )

        produtos_margem_critica = int(
            (
                product_summary["margem"] < 5
            ).sum()
        )

        produtos_margem_baixa = int(
            (
                (product_summary["margem"] >= 5)
                & (product_summary["margem"] < 10)
            ).sum()
        )

        faturamento_margem_critica = float(
            product_summary.loc[
                product_summary["margem"] < 10,
                "faturamento"
            ].sum()
        )

        faturamento_produtos_prejuizo = float(
            product_summary.loc[
                product_summary["lucro"] < 0,
                "faturamento"
            ].sum()
        )

        prejuizo_bruto_total = abs(
            float(
                product_summary.loc[
                    product_summary["lucro"] < 0,
                    "lucro"
                ].sum()
            )
        )

        participacao_faturamento_critico = (
            faturamento_margem_critica
            / metrics["faturamento"]
            if metrics["faturamento"] > 0
            else 0
        )

        participacao_faturamento_prejuizo = (
            faturamento_produtos_prejuizo
            / metrics["faturamento"]
            if metrics["faturamento"] > 0
            else 0
        )

        impacto_prejuizo_sobre_faturamento = (
            prejuizo_bruto_total
            / metrics["faturamento"]
            if metrics["faturamento"] > 0
            else 0
        )

        top_product = None

        if not product_summary.empty:

            top_row = (
                product_summary
                .sort_values(
                    "lucro",
                    ascending=False
                )
                .iloc[0]
            )

            top_product = {
                "codigo_produto": top_row[
                    "codigo_produto"
                ],
                "produto": top_row["produto"],
                "lucro": float(top_row["lucro"]),
                "faturamento": float(
                    top_row["faturamento"]
                ),
                "margem": (
                    None
                    if pd.isna(top_row["margem"])
                    else float(top_row["margem"])
                ),
                "participacao_faturamento": (
                    float(top_row["faturamento"])
                    / metrics["faturamento"]
                    if metrics["faturamento"] > 0
                    else 0
                ),
                "participacao_lucro": (
                    float(top_row["lucro"])
                    / metrics["lucro"]
                    if metrics["lucro"] != 0
                    else 0
                ),
    "participacao_lucro": (
        float(top_row["lucro"])
        / metrics["lucro"]
        if metrics["lucro"] != 0
        else 0
    ),
}

        faturamento_total_origem = float(
            dataset.loc[
                dataset["empresa_oficial"],
                "faturamento"
            ].sum()
        )

        cobertura_financeira = (
            metrics["faturamento"]
            / faturamento_total_origem
            if faturamento_total_origem > 0
            else 0
        )

        linhas_analisaveis = int(
            dataset["elegivel_kpi"].sum()
        )

        linhas_sem_custo = int(
            (
                dataset["status_analise"]
                == "sem_custo_valido"
            ).sum()
        )

        linhas_suspeitas = int(
            (
                dataset["status_analise"]
                == "dado_suspeito"
            ).sum()
        )

        linhas_fora_escopo = int(
            dataset["status_analise"].isin(
                [
                    "produto_fora_escopo",
                    "empresa_fora_escopo",
                ]
            ).sum()
        )

        status = self._classify_status(
            participacao_faturamento_critico=(
                participacao_faturamento_critico
            ),
            participacao_faturamento_prejuizo=(
                participacao_faturamento_prejuizo
            ),
            impacto_prejuizo_sobre_faturamento=(
                impacto_prejuizo_sobre_faturamento
            ),
            produtos_prejuizo=produtos_prejuizo,
        )

        headline = (
            f"A operação gerou "
            f"R$ {metrics['lucro']:,.2f} de lucro bruto estimado, "
            f"com margem ponderada de "
            f"{metrics['margem']:.2f}% e markup de "
            f"{metrics['markup']:.2f}%. "
            f"Produtos abaixo de 10% de margem representam "
            f"{participacao_faturamento_critico * 100:.2f}% "
            f"do faturamento analisável."
        )

        return {
            "faturamento_analisavel": round(
                metrics["faturamento"],
                2
            ),
            "custo_analisavel": round(
                metrics["custo"],
                2
            ),
            "lucro_bruto": round(
                metrics["lucro"],
                2
            ),
            "margem_percentual": round(
                metrics["margem"],
                4
            ),
            "markup_percentual": round(
                metrics["markup"],
                4
            ),
            "pedidos": pedidos,
            "produtos": produtos,
            "clientes": clientes,
            "vendedores": vendedores,
            "empresas": empresas,
            "quantidade": round(
                quantidade,
                2
            ),
            "ticket_medio": round(
                ticket_medio,
                2
            ),
            "ticket_lucro": round(
                ticket_lucro,
                2
            ),
            "produtos_rentaveis": produtos_rentaveis,
            "produtos_prejuizo": produtos_prejuizo,
            "produtos_margem_critica": (
                produtos_margem_critica
            ),
            "produtos_margem_baixa": (
                produtos_margem_baixa
            ),
            "faturamento_margem_critica": round(
                faturamento_margem_critica,
                2
            ),
            "faturamento_produtos_prejuizo": round(
                faturamento_produtos_prejuizo,
                2
            ),
            "prejuizo_bruto_total": round(
                prejuizo_bruto_total,
                2
            ),
            "participacao_faturamento_critico": round(
                participacao_faturamento_critico,
                6
            ),
            "participacao_faturamento_prejuizo": round(
                participacao_faturamento_prejuizo,
                6
            ),
            "impacto_prejuizo_sobre_faturamento": round(
                impacto_prejuizo_sobre_faturamento,
                6
            ),
            "cobertura_financeira": round(
                cobertura_financeira,
                6
            ),
            "linhas_total": total_rows,
            "linhas_analisaveis": linhas_analisaveis,
            "linhas_sem_custo": linhas_sem_custo,
            "linhas_suspeitas": linhas_suspeitas,
            "linhas_fora_escopo": linhas_fora_escopo,
            "top_product": top_product,
            "headline": headline,
            "status": status,
        }