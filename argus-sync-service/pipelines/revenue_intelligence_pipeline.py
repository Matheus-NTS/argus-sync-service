from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from extractors.meta_extractor import MetaExtractor
from features.intelligence.revenue.meta_dataset import MetaDataset
from features.intelligence.revenue.revenue_daily import RevenueDaily
from features.intelligence.revenue.revenue_history import RevenueHistory
from features.intelligence.revenue.revenue_overview import RevenueOverview
from features.intelligence.revenue.revenue_projection import (
    RevenueProjection,
)


class RevenueIntelligencePipeline:
    """
    Publica os contratos oficiais do módulo Faturamento.

    Responsabilidades:
    - utilizar os pedidos comerciais já filtrados;
    - extrair e preparar as metas;
    - construir históricos de faturamento;
    - unir realizado e metas;
    - gerar projeções anuais;
    - publicar snapshots no Supabase.

    A pipeline não extrai pedidos novamente.
    """

    TABLE_COLUMNS = {
        "mart_revenue_daily": [
            "reference_date",
            "data",
            "ano",
            "mes",
            "dia",
            "ano_mes",
            "empresa",
            "nivel",
            "faturamento",
            "faturamento_acumulado",
            "meta_mensal",
            "meta_diaria",
            "meta_acumulada",
            "atingimento_meta_acumulada",
            "gap_acumulado",
            "dia_util",
            "dia_util_numero",
            "dias_uteis_mes",
        ],
        "mart_revenue_monthly": [
            "reference_date",
            "ano",
            "mes",
            "mes_nome",
            "ano_mes",
            "trimestre",
            "semestre",
            "empresa",
            "nivel",
            "faturamento",
            "pedidos",
            "ticket_medio",
            "empresas_ativas",
            "vendedores_ativos",
            "tem_movimento",
            "periodo_futuro",
            "mes_em_aberto",
            "faturamento_mes_anterior",
            "crescimento_mom",
            "faturamento_ano_anterior",
            "crescimento_yoy",
            "acumulado_ytd",
            "meta",
            "supermeta",
            "hipermeta",
            "status_meta",
            "meta_valida",
            "atingimento_meta",
            "atingimento_supermeta",
            "atingimento_hipermeta",
            "gap_meta",
            "gap_supermeta",
            "gap_hipermeta",
            "falta_para_meta",
            "falta_para_supermeta",
            "falta_para_hipermeta",
            "faixa_desempenho",
            "empresas_com_meta",
            "vendedores_cadastrados_meta",
            "vendedores_com_meta",
            "vendedores_pendentes",
        ],
        "mart_revenue_company_monthly": [
            "reference_date",
            "ano",
            "mes",
            "ano_mes",
            "empresa",
            "nivel",
            "faturamento",
            "pedidos",
            "vendedores_ativos",
            "ticket_medio",
            "faturamento_total_mes",
            "participacao_mensal",
            "ranking_empresa_mes",
            "meta",
            "supermeta",
            "hipermeta",
            "status_meta",
            "meta_valida",
            "atingimento_meta",
            "atingimento_supermeta",
            "atingimento_hipermeta",
            "gap_meta",
            "gap_supermeta",
            "gap_hipermeta",
            "falta_para_meta",
            "falta_para_supermeta",
            "falta_para_hipermeta",
            "faixa_desempenho",
            "vendedores_cadastrados_meta",
            "vendedores_com_meta",
            "vendedores_pendentes",
        ],
        "mart_revenue_seller_monthly": [
            "reference_date",
            "ano",
            "mes",
            "ano_mes",
            "empresa",
            "vendedor_key",
            "vendedor",
            "seller_identity",
            "nivel",
            "faturamento",
            "pedidos",
            "ticket_medio",
            "faturamento_empresa_mes",
            "participacao_empresa",
            "ranking_vendedor_empresa",
            "ranking_faturamento_empresa",
            "ranking_atingimento_empresa",
            "meta",
            "supermeta",
            "hipermeta",
            "status_meta",
            "meta_valida",
            "meta_configurada",
            "meta_pendente",
            "atingimento_meta",
            "atingimento_supermeta",
            "atingimento_hipermeta",
            "gap_meta",
            "gap_supermeta",
            "gap_hipermeta",
            "falta_para_meta",
            "falta_para_supermeta",
            "falta_para_hipermeta",
            "faixa_desempenho",
        ],
        "mart_revenue_current_summary": [
    "reference_date",
    "empresa",
    "nivel",
    "ano",
    "mes",
    "faturamento",
    "faturamento_dia",
    "meta",
    "meta_diaria",
    "supermeta",
    "hipermeta",
    "atingimento_meta",
    "gap_meta",
    "ritmo_atual",
    "ritmo_necessario",
    "dias_uteis_mes",
    "dias_uteis_decorridos",
    "dias_uteis_restantes",
    "projecao_fechamento",
    "status_meta",
    "faixa_desempenho",
    "empresas_com_faturamento",
    "vendedores_com_faturamento",
    "vendedores_com_meta_valida",
    "vendedores_que_bateram_meta",
    "vendedores_em_supermeta",
    "vendedores_em_hipermeta",
    "status",
],
        "mart_revenue_yearly": [
            "reference_date",
            "empresa",
            "nivel",
            "ano",
            "faturamento",
            "pedidos",
            "meses_com_movimento",
            "ticket_medio",
            "media_mensal",
            "melhor_mes",
            "melhor_mes_nome",
            "melhor_mes_faturamento",
            "pior_mes",
            "pior_mes_nome",
            "pior_mes_faturamento",
            "ano_completo",
            "faturamento_ano_anterior",
            "ano_anterior_completo",
            "crescimento_anual",
        ],
        "mart_revenue_ytd": [
            "reference_date",
            "empresa",
            "nivel",
            "ano",
            "mes_limite",
            "faturamento_ytd",
            "pedidos_ytd",
            "faturamento_ytd_ano_anterior",
            "crescimento_ytd",
        ],
        "mart_revenue_projection_monthly": [
            "reference_date",
            "ano_base",
            "ano_projetado",
            "mes",
            "mes_nome",
            "cenario_percentual",
            "faturamento_base",
            "participacao_ano_base",
            "faturamento_projetado",
            "crescimento_valor",
        ],
        "mart_revenue_projection_summary": [
            "reference_date",
            "ano_base",
            "ano_projetado",
            "cenario_percentual",
            "faturamento_ano_base",
            "faturamento_projetado",
            "crescimento_valor",
            "media_mensal_projetada",
        ],
        "mart_revenue_projection_company_monthly": [
            "reference_date",
            "empresa",
            "nivel",
            "ano_base",
            "ano_projetado",
            "mes",
            "mes_nome",
            "cenario_percentual",
            "faturamento_base",
            "participacao_ano_base",
            "faturamento_projetado",
            "crescimento_valor",
        ],
        "mart_revenue_projection_company_summary": [
            "reference_date",
            "empresa",
            "nivel",
            "ano_base",
            "ano_projetado",
            "cenario_percentual",
            "faturamento_ano_base",
            "faturamento_projetado",
            "crescimento_valor",
            "media_mensal_projetada",
        ],
    }

    COLUMN_ALIASES = {
        "super_meta": "supermeta",
        "hiper_meta": "hipermeta",
        "atingimento_super_meta": "atingimento_supermeta",
        "atingimento_hiper_meta": "atingimento_hipermeta",
        "gap_super_meta": "gap_supermeta",
        "gap_hiper_meta": "gap_hipermeta",
        "falta_para_super_meta": "falta_para_supermeta",
        "falta_para_hiper_meta": "falta_para_hipermeta",
        "vendedores_meta_valida": "vendedores_com_meta_valida",
        "vendedores_bateram_meta": "vendedores_que_bateram_meta",
        "vendedores_supermeta": "vendedores_em_supermeta",
        "vendedores_hipermeta": "vendedores_em_hipermeta",
    }

    INTEGER_COLUMNS = {
        "dias_uteis_mes",
        "dias_uteis_decorridos",
        "dias_uteis_restantes",
        "ano",
        "mes",
        "trimestre",
        "semestre",
        "pedidos",
        "empresas_ativas",
        "vendedores_ativos",
        "empresas_com_meta",
        "vendedores_cadastrados_meta",
        "vendedores_com_meta",
        "vendedores_pendentes",
        "ranking_empresa_mes",
        "ranking_vendedor_empresa",
        "ranking_faturamento_empresa",
        "ranking_atingimento_empresa",
        "empresas_com_faturamento",
        "vendedores_com_faturamento",
        "vendedores_com_meta_valida",
        "vendedores_que_bateram_meta",
        "vendedores_em_supermeta",
        "vendedores_em_hipermeta",
        "meses_com_movimento",
        "melhor_mes",
        "pior_mes",
        "mes_limite",
        "pedidos_ytd",
        "ano_base",
        "ano_projetado",
        "dia",
        "dia_util_numero",
    }

    def __init__(
        self,
        sql_connector,
        supabase_connector,
    ):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    def run(
        self,
        pedidos: pd.DataFrame,
    ) -> dict[str, Any]:
        reference_date = date.today()

        revenue = self._prepare_revenue(
            pedidos
        )

        metas_raw = MetaExtractor(
            self.sql_connector
        ).extract()

        metas = MetaDataset(
            reference_date=reference_date
        ).build(
            metas_raw
        )

        history = RevenueHistory().build(
            revenue
        )

        daily_service = RevenueDaily(
            revenue_df=revenue,
            meta_df=metas.general_monthly,
            company_meta_df=getattr(
                metas,
                "company_monthly",
                None,
            ),
            reference_date=reference_date,
        )

        daily = daily_service.build()
        daily_mart = daily_service.build_mart()

        overview = RevenueOverview(
            reference_date=reference_date,
        ).build(
            history=history,
            metas=metas,
            daily=daily,
        )

        company_monthly_analytics = (
            self._build_company_monthly_analytics(
                company_monthly=overview.company_monthly,
                reference_date=reference_date,
            )
        )

        monthly_mart = pd.concat(
            [
                overview.monthly.assign(
                    empresa="Consolidado",
                    nivel="consolidado",
                ),
                company_monthly_analytics,
            ],
            ignore_index=True,
            sort=False,
        )

        company_yearly = self._build_company_yearly(
            company_monthly=company_monthly_analytics,
            reference_date=reference_date,
        )

        company_ytd = self._build_company_ytd(
            company_monthly=company_monthly_analytics,
            reference_date=reference_date,
        )

        yearly_mart = pd.concat(
            [
                history["yearly"].assign(
                    empresa="Consolidado",
                    nivel="consolidado",
                ),
                company_yearly,
            ],
            ignore_index=True,
            sort=False,
        )

        ytd_mart = pd.concat(
            [
                history["ytd"].assign(
                    empresa="Consolidado",
                    nivel="consolidado",
                ),
                company_ytd,
            ],
            ignore_index=True,
            sort=False,
        )

        company_current_summary = (
            self._build_company_current_summary(
                company_monthly=company_monthly_analytics,
                daily_mart=daily_mart,
                reference_date=reference_date,
            )
        )

        current_summary_mart = pd.concat(
            [
                overview.current_summary.assign(
                    empresa="Consolidado",
                    nivel="consolidado",
                ),
                company_current_summary,
            ],
            ignore_index=True,
            sort=False,
        )

        # O bloco abaixo permanece pronto para a próxima etapa.
        # Ele será alcançado após removermos o SystemExit temporário.
        projection_service = RevenueProjection(
            reference_date=reference_date,
        )

        base_year = self._resolve_projection_base_year(
            history["yearly"],
            reference_date,
        )

        projection_wide = projection_service.build(
            revenue_df=revenue,
            base_year=base_year,
        )

        projection_monthly = (
            projection_service.build_long_format(
                projection_wide
            )
        )

        projection_summary = (
            projection_service.build_summary(
                projection_wide
            )
        )

        projection_company_monthly = (
            projection_service.build_company_monthly(
                revenue_df=revenue,
                base_year=base_year,
            )
        )

        projection_company_summary = (
            projection_service.build_company_summary(
                revenue_df=revenue,
                base_year=base_year,
            )
        )

        datasets = {
            "mart_revenue_daily": daily_mart,
            "mart_revenue_monthly": monthly_mart,
            "mart_revenue_company_monthly": (
                overview.company_monthly
            ),
            "mart_revenue_seller_monthly": (
                overview.seller_monthly
            ),
            "mart_revenue_current_summary": (
                current_summary_mart
            ),
            "mart_revenue_yearly": yearly_mart,
            "mart_revenue_ytd": ytd_mart,
            "mart_revenue_projection_monthly": (
                projection_monthly
            ),
            "mart_revenue_projection_summary": (
                projection_summary
            ),
            "mart_revenue_projection_company_monthly": (
                projection_company_monthly
            ),
            "mart_revenue_projection_company_summary": (
                projection_company_summary
            ),
        }

        result = {
            "revenue_projection_base_year": base_year,
        }

        for table_name, dataframe in datasets.items():
            print(
                f"  Publicando Revenue Intelligence: "
                f"{table_name}"
            )

            records = self._prepare_records(
                dataframe=dataframe,
                table_name=table_name,
                reference_date=reference_date,
            )

            print(
                f"Registros preparados: {len(records):,}"
            )

            self._validate_integer_records(
                table_name=table_name,
                records=records,
            )

            self.supabase.replace_snapshot_batches(
                table_name=table_name,
                filters={
                    "reference_date": reference_date.isoformat()
                },
                data=records,
                batch_size=500,
            )

            result[
                self._result_key(table_name)
            ] = len(records)

        return result

    @staticmethod
    def _prepare_revenue(
        pedidos: pd.DataFrame,
    ) -> pd.DataFrame:
        if pedidos is None or pedidos.empty:
            raise ValueError(
                "A base de pedidos comerciais está vazia."
            )

        revenue = pedidos.copy()

        if "Data" not in revenue.columns:
            raise KeyError(
                "A coluna Data não existe na base de pedidos."
            )

        revenue["Data"] = pd.to_datetime(
            revenue["Data"],
            errors="coerce",
        )

        revenue = revenue[
            revenue["Data"].notna()
        ].copy()

        if revenue.empty:
            raise ValueError(
                "Nenhuma data válida foi encontrada "
                "na base de pedidos."
            )

        if "ano" not in revenue.columns:
            revenue["ano"] = revenue["Data"].dt.year

        if "mes" not in revenue.columns:
            revenue["mes"] = revenue["Data"].dt.month

        revenue["ano"] = pd.to_numeric(
            revenue["ano"],
            errors="coerce",
        )

        revenue["mes"] = pd.to_numeric(
            revenue["mes"],
            errors="coerce",
        )

        revenue = revenue[
            revenue["ano"].notna()
            & revenue["mes"].notna()
        ].copy()

        revenue["ano"] = revenue["ano"].astype(int)
        revenue["mes"] = revenue["mes"].astype(int)

        if "ano_mes" not in revenue.columns:
            revenue["ano_mes"] = (
                revenue["ano"].astype(str)
                + "-"
                + revenue["mes"]
                .astype(str)
                .str.zfill(2)
            )

        return revenue


    @staticmethod
    def _build_company_monthly_analytics(
        company_monthly: pd.DataFrame,
        reference_date: date,
    ) -> pd.DataFrame:
        """
        Enriquece o histórico mensal por empresa com comparações
        MoM, YoY e acumulado YTD. Todos os cálculos permanecem
        no backend.
        """
        if company_monthly is None or company_monthly.empty:
            return pd.DataFrame()

        df = company_monthly.copy()
        required = {"empresa", "ano", "mes", "faturamento", "pedidos"}
        missing = required.difference(df.columns)
        if missing:
            raise KeyError(
                "mart_revenue_company_monthly sem colunas: "
                + ", ".join(sorted(missing))
            )

        df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
        df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
        df["faturamento"] = pd.to_numeric(
            df["faturamento"], errors="coerce"
        ).fillna(0.0)
        df["pedidos"] = pd.to_numeric(
            df["pedidos"], errors="coerce"
        ).fillna(0)

        df = df[df["ano"].notna() & df["mes"].notna()].copy()
        df["ano"] = df["ano"].astype(int)
        df["mes"] = df["mes"].astype(int)
        df["empresa"] = df["empresa"].astype(str).str.strip()
        df["nivel"] = "empresa"
        df["ano_mes"] = (
            df["ano"].astype(str)
            + "-"
            + df["mes"].astype(str).str.zfill(2)
        )

        month_names = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março",
            4: "Abril", 5: "Maio", 6: "Junho",
            7: "Julho", 8: "Agosto", 9: "Setembro",
            10: "Outubro", 11: "Novembro", 12: "Dezembro",
        }
        df["mes_nome"] = df["mes"].map(month_names)
        df["trimestre"] = ((df["mes"] - 1) // 3) + 1
        df["semestre"] = ((df["mes"] - 1) // 6) + 1
        df["tem_movimento"] = df["faturamento"] != 0
        df["periodo_futuro"] = (
            (df["ano"] > reference_date.year)
            | (
                (df["ano"] == reference_date.year)
                & (df["mes"] > reference_date.month)
            )
        )
        df["mes_em_aberto"] = (
            (df["ano"] == reference_date.year)
            & (df["mes"] == reference_date.month)
        )

        df = df.sort_values(
            ["empresa", "ano", "mes"]
        ).reset_index(drop=True)

        df["faturamento_mes_anterior"] = (
            df.groupby("empresa")["faturamento"].shift(1).fillna(0.0)
        )
        previous = df["faturamento_mes_anterior"]
        df["crescimento_mom"] = np.where(
            previous != 0,
            (df["faturamento"] / previous) - 1,
            np.nan,
        )

        previous_year = df[
            ["empresa", "ano", "mes", "faturamento"]
        ].copy()
        previous_year["ano"] = previous_year["ano"] + 1
        previous_year = previous_year.rename(
            columns={"faturamento": "faturamento_ano_anterior"}
        )

        df = df.merge(
            previous_year,
            on=["empresa", "ano", "mes"],
            how="left",
        )
        df["faturamento_ano_anterior"] = (
            pd.to_numeric(
                df["faturamento_ano_anterior"],
                errors="coerce",
            ).fillna(0.0)
        )
        df["crescimento_yoy"] = np.where(
            df["faturamento_ano_anterior"] != 0,
            (
                df["faturamento"]
                / df["faturamento_ano_anterior"]
            ) - 1,
            np.nan,
        )
        df["acumulado_ytd"] = (
            df.groupby(["empresa", "ano"])["faturamento"].cumsum()
        )

        for column, default in {
            "empresas_ativas": 1,
            "empresas_com_meta": 1,
        }.items():
            df[column] = default

        for column in [
            "vendedores_cadastrados_meta",
            "vendedores_com_meta",
            "vendedores_pendentes",
        ]:
            if column not in df.columns:
                df[column] = 0

        return df

    @staticmethod
    def _build_company_yearly(
        company_monthly: pd.DataFrame,
        reference_date: date,
    ) -> pd.DataFrame:
        if company_monthly is None or company_monthly.empty:
            return pd.DataFrame()

        source = company_monthly[
            ~company_monthly["periodo_futuro"].fillna(False)
        ].copy()

        rows: list[dict[str, Any]] = []
        month_names = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março",
            4: "Abril", 5: "Maio", 6: "Junho",
            7: "Julho", 8: "Agosto", 9: "Setembro",
            10: "Outubro", 11: "Novembro", 12: "Dezembro",
        }

        for (empresa, ano), group in source.groupby(
            ["empresa", "ano"], dropna=False
        ):
            group = group.sort_values("mes")
            moving = group[group["tem_movimento"].fillna(False)]
            faturamento = float(group["faturamento"].sum())
            pedidos = int(group["pedidos"].sum())
            ticket = faturamento / pedidos if pedidos else 0.0

            if moving.empty:
                best = worst = group.iloc[0]
            else:
                best = moving.loc[moving["faturamento"].idxmax()]
                worst = moving.loc[moving["faturamento"].idxmin()]

            rows.append({
                "empresa": empresa,
                "nivel": "empresa",
                "ano": int(ano),
                "faturamento": faturamento,
                "pedidos": pedidos,
                "meses_com_movimento": int(
                    moving["mes"].nunique()
                ),
                "ticket_medio": ticket,
                "media_mensal": (
                    faturamento / max(int(group["mes"].nunique()), 1)
                ),
                "melhor_mes": int(best["mes"]),
                "melhor_mes_nome": month_names.get(
                    int(best["mes"]), str(best["mes"])
                ),
                "melhor_mes_faturamento": float(best["faturamento"]),
                "pior_mes": int(worst["mes"]),
                "pior_mes_nome": month_names.get(
                    int(worst["mes"]), str(worst["mes"])
                ),
                "pior_mes_faturamento": float(worst["faturamento"]),
                "ano_completo": (
                    int(ano) < reference_date.year
                    and int(group["mes"].nunique()) >= 12
                ),
            })

        yearly = pd.DataFrame(rows).sort_values(
            ["empresa", "ano"]
        ).reset_index(drop=True)

        previous = yearly[
            ["empresa", "ano", "faturamento", "ano_completo"]
        ].copy()
        previous["ano"] = previous["ano"] + 1
        previous = previous.rename(columns={
            "faturamento": "faturamento_ano_anterior",
            "ano_completo": "ano_anterior_completo",
        })

        yearly = yearly.merge(
            previous,
            on=["empresa", "ano"],
            how="left",
        )
        yearly["faturamento_ano_anterior"] = yearly[
            "faturamento_ano_anterior"
        ].fillna(0.0)
        yearly["ano_anterior_completo"] = yearly[
            "ano_anterior_completo"
        ].fillna(False)
        yearly["crescimento_anual"] = np.where(
            yearly["faturamento_ano_anterior"] != 0,
            (
                yearly["faturamento"]
                / yearly["faturamento_ano_anterior"]
            ) - 1,
            np.nan,
        )
        return yearly

    @staticmethod
    def _build_company_ytd(
        company_monthly: pd.DataFrame,
        reference_date: date,
    ) -> pd.DataFrame:
        if company_monthly is None or company_monthly.empty:
            return pd.DataFrame()

        rows: list[dict[str, Any]] = []
        years = sorted(
            pd.to_numeric(
                company_monthly["ano"], errors="coerce"
            ).dropna().astype(int).unique().tolist()
        )

        for empresa, company_rows in company_monthly.groupby("empresa"):
            for ano in years:
                year_rows = company_rows[company_rows["ano"] == ano]
                if year_rows.empty:
                    continue

                mes_limite = (
                    reference_date.month
                    if ano == reference_date.year
                    else 12
                )
                current = year_rows[
                    year_rows["mes"] <= mes_limite
                ]
                previous = company_rows[
                    (company_rows["ano"] == ano - 1)
                    & (company_rows["mes"] <= mes_limite)
                ]

                current_value = float(current["faturamento"].sum())
                previous_value = float(previous["faturamento"].sum())
                current_orders = int(current["pedidos"].sum())

                rows.append({
                    "empresa": empresa,
                    "nivel": "empresa",
                    "ano": int(ano),
                    "mes_limite": int(mes_limite),
                    "faturamento_ytd": current_value,
                    "pedidos_ytd": current_orders,
                    "faturamento_ytd_ano_anterior": previous_value,
                    "crescimento_ytd": (
                        (current_value / previous_value) - 1
                        if previous_value != 0
                        else np.nan
                    ),
                })

        return pd.DataFrame(rows)

    @staticmethod
    def _build_company_current_summary(
        company_monthly: pd.DataFrame,
        daily_mart: pd.DataFrame,
        reference_date: date,
    ) -> pd.DataFrame:
        if company_monthly is None or company_monthly.empty:
            return pd.DataFrame()

        current = company_monthly[
            (company_monthly["ano"] == reference_date.year)
            & (company_monthly["mes"] == reference_date.month)
        ].copy()

        if current.empty:
            return pd.DataFrame()

        daily = daily_mart.copy() if daily_mart is not None else pd.DataFrame()
        rows: list[dict[str, Any]] = []

        for _, monthly in current.iterrows():
            empresa = str(monthly["empresa"])
            company_daily = (
                daily[
                    (daily["empresa"].astype(str) == empresa)
                    & (daily["ano"] == reference_date.year)
                    & (daily["mes"] == reference_date.month)
                ].sort_values("data")
                if not daily.empty
                else pd.DataFrame()
            )

            faturamento = float(monthly.get("faturamento", 0) or 0)
            meta = float(monthly.get("meta", 0) or 0)
            faturamento_dia = 0.0

            if not company_daily.empty:
                today_rows = company_daily[
                    company_daily["data"].astype(str)
                    == reference_date.isoformat()
                ]
                if not today_rows.empty:
                    faturamento_dia = float(
                        today_rows["faturamento"].sum()
                    )

                latest = company_daily.iloc[-1]
                dias_uteis_mes = int(
                    latest.get("dias_uteis_mes", 0) or 0
                )
                dias_uteis_decorridos = int(
                    latest.get("dia_util_numero", 0) or 0
                )
            else:
                dias_uteis_mes = 0
                dias_uteis_decorridos = 0

            dias_uteis_restantes = max(
                dias_uteis_mes - dias_uteis_decorridos, 0
            )
            ritmo_atual = (
                faturamento / dias_uteis_decorridos
                if dias_uteis_decorridos > 0
                else 0.0
            )
            gap_meta = faturamento - meta if meta > 0 else 0.0
            ritmo_necessario = (
                max(meta - faturamento, 0.0)
                / dias_uteis_restantes
                if dias_uteis_restantes > 0 and meta > 0
                else 0.0
            )
            projecao = (
                faturamento
                + ritmo_atual * dias_uteis_restantes
            )
            atingimento = (
                faturamento / meta if meta > 0 else 0.0
            )

            rows.append({
                "empresa": empresa,
                "nivel": "empresa",
                "ano": reference_date.year,
                "mes": reference_date.month,
                "faturamento": faturamento,
                "faturamento_dia": faturamento_dia,
                "meta": meta,
                "meta_diaria": (
                    meta / dias_uteis_mes
                    if dias_uteis_mes > 0
                    else 0.0
                ),
                "supermeta": float(monthly.get("supermeta", 0) or 0),
                "hipermeta": float(monthly.get("hipermeta", 0) or 0),
                "atingimento_meta": atingimento,
                "gap_meta": gap_meta,
                "ritmo_atual": ritmo_atual,
                "ritmo_necessario": ritmo_necessario,
                "dias_uteis_mes": dias_uteis_mes,
                "dias_uteis_decorridos": dias_uteis_decorridos,
                "dias_uteis_restantes": dias_uteis_restantes,
                "projecao_fechamento": projecao,
                "status_meta": monthly.get("status_meta"),
                "faixa_desempenho": monthly.get("faixa_desempenho"),
                "empresas_com_faturamento": 1 if faturamento else 0,
                "vendedores_com_faturamento": int(
                    monthly.get("vendedores_ativos", 0) or 0
                ),
                "vendedores_com_meta_valida": int(
                    monthly.get("vendedores_com_meta", 0) or 0
                ),
                "vendedores_que_bateram_meta": 0,
                "vendedores_em_supermeta": 0,
                "vendedores_em_hipermeta": 0,
                "status": "available",
            })

        return pd.DataFrame(rows)

    @staticmethod
    def _resolve_projection_base_year(
        yearly: pd.DataFrame,
        reference_date: date,
    ) -> int:
        """
        Utiliza sempre o ano corrente como base da projeção.

        Exemplos:
        - 2026 -> projeta 2027
        - 2027 -> projeta 2028

        O ano corrente precisa existir no histórico anual.
        """

        if yearly is None or yearly.empty:
            raise ValueError(
                "O histórico anual está vazio."
            )

        if "ano" not in yearly.columns:
            raise KeyError(
                "A coluna 'ano' não existe no histórico anual."
            )

        years = (
            pd.to_numeric(
                yearly["ano"],
                errors="coerce",
            )
            .dropna()
            .astype(int)
        )

        if years.empty:
            raise ValueError(
                "Nenhum ano válido foi encontrado "
                "no histórico anual."
            )

        current_year = int(reference_date.year)

        if current_year not in set(years.tolist()):
            raise ValueError(
                f"O ano corrente {current_year} não possui "
                "faturamento no histórico anual."
            )

        return current_year

    def _prepare_records(
        self,
        dataframe: pd.DataFrame,
        table_name: str,
        reference_date: date,
    ) -> list[dict[str, Any]]:
        if dataframe is None:
            return []

        df = dataframe.copy()
        df = df.rename(columns=self.COLUMN_ALIASES)
        df["reference_date"] = reference_date.isoformat()

        expected_columns = self.TABLE_COLUMNS[table_name]

        for column in expected_columns:
            if column not in df.columns:
                df[column] = None

        df = df[expected_columns].copy()

        for column in self.INTEGER_COLUMNS:
            if column not in df.columns:
                continue

            numeric_values = pd.to_numeric(
                df[column],
                errors="coerce",
            )

            df[column] = numeric_values.apply(
                lambda value: (
                    int(value)
                    if pd.notna(value)
                    else None
                )
            )

        records = df.to_dict(orient="records")

        return [
            {
                key: self._prepare_value(
                    column=key,
                    value=value,
                )
                for key, value in record.items()
            }
            for record in records
        ]

    def _prepare_value(
        self,
        column: str,
        value: Any,
    ) -> Any:
        """
        Converte valores conforme o contrato do Supabase.

        A conversão é feita depois do DataFrame virar
        dicionário, evitando que o pandas transforme
        inteiros com valores nulos novamente em float.
        """

        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        if column in self.INTEGER_COLUMNS:
            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Valor inválido para coluna inteira "
                    f"'{column}': {value!r}"
                ) from exc

            if not numeric_value.is_integer():
                raise ValueError(
                    f"Valor decimal encontrado na coluna "
                    f"inteira '{column}': {value!r}"
                )

            return int(numeric_value)

        return self._to_native(value)

    @staticmethod
    def _to_native(
        value: Any,
    ) -> Any:
        if value is None:
            return None

        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        if isinstance(
            value,
            (
                pd.Timestamp,
                datetime,
                date,
            ),
        ):
            return value.isoformat()

        if isinstance(value, np.bool_):
            return bool(value)

        if isinstance(value, np.integer):
            return int(value)

        if isinstance(value, np.floating):
            return float(value)

        if isinstance(value, np.ndarray):
            return value.tolist()

        return value

    def _validate_integer_records(
        self,
        table_name: str,
        records: list[dict[str, Any]],
    ) -> None:
        """
        Impede o envio de strings ou decimais para colunas
        declaradas como inteiras.
        """

        for row_index, record in enumerate(records):
            for column in self.INTEGER_COLUMNS:
                if column not in record:
                    continue

                value = record[column]

                if value is None:
                    continue

                if isinstance(value, bool):
                    raise TypeError(
                        f"{table_name}: coluna inteira "
                        f"'{column}' recebeu booleano "
                        f"na linha {row_index}: {value!r}"
                    )

                if not isinstance(value, int):
                    raise TypeError(
                        f"{table_name}: coluna inteira "
                        f"'{column}' recebeu "
                        f"{type(value).__name__} "
                        f"na linha {row_index}: {value!r}"
                    )

    @staticmethod
    def _result_key(
        table_name: str,
    ) -> str:
        return (
            table_name
            .removeprefix("mart_")
            + "_records"
        )