from datetime import datetime
import pandas as pd

from features.sales.seller_ranking import SellerRanking
from features.sales.company_performance import CompanyPerformance
from features.sales.product_performance import ProductPerformance
from features.sales.customer_performance import CustomerPerformance
from features.sales.category_performance import CategoryPerformance


class SalesMartPipeline:

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

    def run(self, pedidos, period_type="current_month"):

        hoje = datetime.today()

        filters = {
            "reference_date": hoje.date().isoformat(),
            "period_type": period_type
        }

        seller_df = SellerRanking().build(pedidos)
        company_df = CompanyPerformance().build(pedidos)

        product_df_all = self._normalize_products(ProductPerformance().build(pedidos))
        customer_df_all = self._normalize_customers(CustomerPerformance().build(pedidos))
        category_df_all = self._normalize_categories(CategoryPerformance().build(pedidos))

        self._save_sellers(seller_df, filters)
        self._save_companies(company_df, filters)
        self._save_products(product_df_all, filters)
        self._save_customers(customer_df_all, filters)
        self._save_categories(category_df_all, filters)

        product_df_total = product_df_all[product_df_all["Empresa"] == "TOTAL"].copy()
        customer_df_total = customer_df_all[customer_df_all["Empresa"] == "TOTAL"].copy()
        category_df_total = category_df_all[category_df_all["Empresa"] == "TOTAL"].copy()

        return {
            "seller_df": seller_df,
            "company_df": company_df,
            "product_df": product_df_total,
            "customer_df": customer_df_total,
            "category_df": category_df_total,
            "product_df_all": product_df_all,
            "customer_df_all": customer_df_all,
            "category_df_all": category_df_all
        }

    def _normalize_products(self, product_df):

        if product_df is None or product_df.empty:
            return product_df

        df = product_df.copy()

        return (
            df.groupby(["Empresa", "prod_codigo"], as_index=False)
            .agg({
                "produto": "first",
                "Classificacao": "first",
                "unidade": "first",
                "faturamento_total": "sum",
                "quantidade": "sum",
                "pedidos": "sum",
                "clientes": "sum",
                "ticket_medio": "mean"
            })
        )

    def _normalize_customers(self, customer_df):

        if customer_df is None or customer_df.empty:
            return customer_df

        df = customer_df.copy()

        agg = {
            "Cliente": "first",
            "faturamento_total": "sum",
            "faturamento_90d": "sum",
            "faturamento_180d": "sum",
            "faturamento_90d_anterior": "sum",
            "pedidos": "sum",
            "itens_vendidos": "sum",
            "mix_produtos": "max",
            "ultima_compra": "max",
            "ticket_medio": "mean",
            "produtos_comprados": "first",
            "evolution_status": "first",
            "fidelidade_score": "max",
            "customer_tier": "first",
            "cliente_status": "first"
        }

        agg = {k: v for k, v in agg.items() if k in df.columns}

        result = (
            df.groupby(["Empresa", "codigo_cliente"], as_index=False)
            .agg(agg)
        )

        if "dias_sem_compra" in df.columns:
            result["dias_sem_compra"] = result["ultima_compra"].apply(
                lambda x: (pd.Timestamp(datetime.today().date()) - pd.to_datetime(x)).days
                if pd.notnull(x) else None
            )

        if "faturamento_90d" in result.columns and "faturamento_90d_anterior" in result.columns:
            result["variacao_faturamento_90d"] = result.apply(
                lambda row: (
                    (row["faturamento_90d"] - row["faturamento_90d_anterior"]) /
                    row["faturamento_90d_anterior"]
                    if row["faturamento_90d_anterior"] > 0
                    else 0
                ),
                axis=1
            )

        return result

    def _normalize_categories(self, category_df):

        if category_df is None or category_df.empty:
            return category_df

        df = category_df.copy()

        return (
            df.groupby(["Empresa", "Categoria"], as_index=False)
            .agg({
                "faturamento_total": "sum",
                "pedidos": "sum",
                "itens_vendidos": "sum",
                "clientes": "sum",
                "produtos": "sum",
                "ticket_medio": "mean"
            })
        )

    def _save_sellers(self, seller_df, filters):

        seller_records = []

        for _, row in seller_df.iterrows():
            seller_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "vendedor": row["Vendedor"],
                "empresa": "TOTAL",
                "empresa_breakdown": row["empresa_breakdown"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("sales_seller_ranking_snapshot", filters, seller_records)

    def _save_companies(self, company_df, filters):

        company_records = []

        for _, row in company_df.iterrows():
            company_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("mart_sales_company_snapshot", filters, company_records)

    def _save_products(self, product_df, filters):

        product_records = []

        for _, row in product_df.iterrows():
            product_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "prod_codigo": row["prod_codigo"],
                "produto": row["produto"],
                "classificacao": row["Classificacao"],
                "unidade": row["unidade"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "quantidade": float(row["quantidade"]),
                "pedidos": int(row["pedidos"]),
                "clientes": int(row["clientes"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("mart_sales_product_snapshot", filters, product_records)

    def _save_customers(self, customer_df, filters):

        customer_records = []

        for _, row in customer_df.iterrows():

            ultima_compra = None
            if pd.notnull(row["ultima_compra"]):
                try:
                    ultima_compra = pd.to_datetime(row["ultima_compra"]).date().isoformat()
                except Exception:
                    ultima_compra = None

            dias_sem_compra = row.get("dias_sem_compra")
            if pd.isna(dias_sem_compra):
                dias_sem_compra = None

            customer_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "codigo_cliente": str(row["codigo_cliente"]),
                "cliente": row["Cliente"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "faturamento_90d": round(float(row.get("faturamento_90d", 0)), 2),
                "faturamento_180d": round(float(row.get("faturamento_180d", 0)), 2),
                "faturamento_90d_anterior": round(float(row.get("faturamento_90d_anterior", 0)), 2),
                "variacao_faturamento_90d": round(float(row.get("variacao_faturamento_90d", 0)), 4),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "mix_produtos": int(row["mix_produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2),
                "ultima_compra": ultima_compra,
                "dias_sem_compra": None if dias_sem_compra is None else int(dias_sem_compra),
                "produtos_comprados": row.get("produtos_comprados"),
                "evolution_status": row.get("evolution_status"),
                "fidelidade_score": round(float(row.get("fidelidade_score", 0)), 2),
                "customer_tier": row.get("customer_tier"),
                "cliente_status": row.get("cliente_status")
            })

        self.supabase.replace_snapshot("mart_sales_customer_snapshot", filters, customer_records)

    def _save_categories(self, category_df, filters):

        category_records = []

        for _, row in category_df.iterrows():
            category_records.append({
                "reference_date": filters["reference_date"],
                "period_type": filters["period_type"],
                "empresa": row["Empresa"],
                "categoria": row["Categoria"],
                "faturamento_total": round(float(row["faturamento_total"]), 2),
                "pedidos": int(row["pedidos"]),
                "itens_vendidos": int(row["itens_vendidos"]),
                "clientes": int(row["clientes"]),
                "produtos": int(row["produtos"]),
                "ticket_medio": round(float(row["ticket_medio"]), 2)
            })

        self.supabase.replace_snapshot("mart_sales_category_snapshot", filters, category_records)