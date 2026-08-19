from datetime import datetime
import hashlib
import re
import unicodedata

import pandas as pd

from extractors.pedido_extractor import PedidoExtractor
from transformers.pedido_transformer import PedidoTransformer


class CustomerGeoPipeline:

    PERIOD_TYPE = "historico"

    def __init__(self, sql_connector, supabase_connector):
        self.sql_connector = sql_connector
        self.supabase = supabase_connector

    @staticmethod
    def _clean_text(value) -> str:
        if pd.isna(value):
            return ""

        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)

        return text

    @staticmethod
    def _normalize_code(value) -> str:
        if pd.isna(value):
            return ""

        text = str(value).strip()

        if text.endswith(".0"):
            text = text[:-2]

        return text

    @staticmethod
    def _normalize_for_hash(value: str) -> str:
        text = unicodedata.normalize("NFKD", value)
        text = "".join(
            char for char in text
            if not unicodedata.combining(char)
        )
        text = text.upper().strip()
        text = re.sub(r"\s+", " ", text)

        return text

    def _build_address(self, row) -> str:
        tipo = self._clean_text(row.get("tipo_logradouro"))
        logradouro = self._clean_text(row.get("logradouro_entrega"))
        numero = self._clean_text(row.get("numero_entrega"))
        bairro = self._clean_text(row.get("bairro_entrega"))
        cidade = self._clean_text(row.get("cidade"))
        cep = self._clean_text(row.get("cep_entrega"))

        street = " ".join(
            item for item in [tipo, logradouro]
            if item
        ).strip()

        parts = []

        if street:
            if numero and numero not in {"0", "00", "S/N", "SN"}:
                parts.append(f"{street}, {numero}")
            else:
                parts.append(street)

        if bairro:
            parts.append(bairro)

        if cidade:
            parts.append(cidade)

        if cep:
            parts.append(cep)

        parts.append("Brasil")

        return ", ".join(parts)

    def _build_hash(self, address: str) -> str:
        normalized = self._normalize_for_hash(address)

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    def _fetch_all(self, table_name, columns="*", filters=None):
        filters = filters or {}
        page_size = 1000
        start = 0
        records = []

        while True:
            query = (
                self.supabase.client
                .table(table_name)
                .select(columns)
            )

            for column, value in filters.items():
                query = query.eq(column, value)

            response = query.range(
                start,
                start + page_size - 1
            ).execute()

            batch = response.data or []
            records.extend(batch)

            if len(batch) < page_size:
                break

            start += page_size

        return records

    def _load_geo_cache_hashes(self) -> set:
        records = self._fetch_all(
            "customer_geo_cache",
            columns="endereco_hash"
        )

        return {
            item.get("endereco_hash")
            for item in records
            if item.get("endereco_hash")
        }

    def _register_new_geo_hashes(
        self,
        latest_addresses: pd.DataFrame
    ) -> int:
        existing_hashes = self._load_geo_cache_hashes()
        pending_by_hash = {}

        for _, row in latest_addresses.iterrows():
            city = self._clean_text(
                row.get("cidade")
            )
            street = self._clean_text(
                row.get("logradouro_entrega")
            )

            if not city or not street:
                continue

            address = self._build_address(row)
            address_hash = self._build_hash(address)

            if (
                address_hash in existing_hashes
                or address_hash in pending_by_hash
            ):
                continue

            pending_by_hash[address_hash] = {
                "endereco_hash": address_hash,
                "endereco_completo": address,
                "tipo_logradouro": self._clean_text(
                    row.get("tipo_logradouro")
                ),
                "logradouro": street,
                "numero": self._clean_text(
                    row.get("numero_entrega")
                ),
                "bairro": self._clean_text(
                    row.get("bairro_entrega")
                ),
                "cidade": city,
                "cep": self._clean_text(
                    row.get("cep_entrega")
                ),
                "geo_status": "pending",
            }

        records = list(
            pending_by_hash.values()
        )

        if records:
            self.supabase.insert_batches(
                "customer_geo_cache",
                records,
                batch_size=500
            )

        return len(records)

    def _load_geo_cache(self) -> dict:
        records = self._fetch_all(
            "customer_geo_cache",
            columns=(
                "endereco_hash,latitude,longitude,geo_status,"
                "geo_provider,geo_display_name,estado,"
                "last_checked_at"
            ),
            filters={"geo_status": "success"}
        )

        cache = {}

        for item in records:
            address_hash = item.get("endereco_hash")

            if not address_hash:
                continue

            if item.get("latitude") is None or item.get("longitude") is None:
                continue

            cache[address_hash] = {
                **item,
                "geo_last_checked_at": item.get(
                    "last_checked_at"
                ),
            }

        return cache

    def _load_customer_metrics(self, reference_date: str) -> pd.DataFrame:
        records = self._fetch_all(
            "mart_sales_customer_snapshot",
            columns=(
                "empresa,codigo_cliente,cliente,faturamento_total,"
                "customer_tier,cliente_status,evolution_status,"
                "dias_sem_compra"
            ),
            filters={
                "reference_date": reference_date,
                "period_type": self.PERIOD_TYPE
            }
        )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        df["codigo_cliente"] = (
            df["codigo_cliente"]
            .apply(self._normalize_code)
        )

        df = (
            df.sort_values(
                ["empresa", "codigo_cliente", "faturamento_total"],
                ascending=[True, True, False]
            )
            .drop_duplicates(
                subset=["empresa", "codigo_cliente"],
                keep="first"
            )
        )

        return df

    def _build_latest_addresses(self, pedidos: pd.DataFrame) -> pd.DataFrame:
        required_columns = [
            "Data",
            "Empresa",
            "codigo_cliente",
            "Cliente",
            "tipo_logradouro",
            "logradouro_entrega",
            "numero_entrega",
            "bairro_entrega",
            "cidade",
            "cep_entrega"
        ]

        missing = [
            column
            for column in required_columns
            if column not in pedidos.columns
        ]

        if missing:
            raise KeyError(
                "Colunas ausentes para geolocalização: "
                + ", ".join(missing)
            )

        df = pedidos[required_columns].copy()

        df["Data"] = pd.to_datetime(
            df["Data"],
            errors="coerce"
        )

        df["codigo_cliente"] = (
            df["codigo_cliente"]
            .apply(self._normalize_code)
        )

        df = df[
            df["Data"].notna()
            & df["codigo_cliente"].ne("")
        ].copy()

        # Endereço mais recente por cliente e empresa
        by_company = (
            df.sort_values("Data", ascending=False)
            .drop_duplicates(
                subset=["Empresa", "codigo_cliente"],
                keep="first"
            )
        )

        # Endereço mais recente do cliente no consolidado NTS
        total = (
            df.sort_values("Data", ascending=False)
            .drop_duplicates(
                subset=["codigo_cliente"],
                keep="first"
            )
            .copy()
        )

        total["Empresa"] = "TOTAL"

        result = pd.concat(
            [total, by_company],
            ignore_index=True
        )

        return result

    def run(self):
        today = datetime.today()
        reference_date = today.date().isoformat()

        pedidos = PedidoExtractor(
            self.sql_connector
        ).extract()

        pedidos = PedidoTransformer().filter_revenue_orders(
            pedidos
        )

        latest_addresses = self._build_latest_addresses(
            pedidos
        )

        customer_metrics = self._load_customer_metrics(
            reference_date
        )

        if not customer_metrics.empty:
            latest_addresses = latest_addresses.merge(
                customer_metrics,
                left_on=["Empresa", "codigo_cliente"],
                right_on=["empresa", "codigo_cliente"],
                how="left",
                suffixes=("", "_metric")
            )

        new_geo_hashes = self._register_new_geo_hashes(
            latest_addresses
        )

        if new_geo_hashes:
            print(
                f"  Novos hashes geográficos registrados: "
                f"{new_geo_hashes}"
            )

        geo_cache = self._load_geo_cache()

        records = []
        pending_count = 0
        cached_count = 0
        invalid_count = 0

        for _, row in latest_addresses.iterrows():
            address = self._build_address(row)

            city = self._clean_text(row.get("cidade"))
            street = self._clean_text(
                row.get("logradouro_entrega")
            )

            is_valid = bool(city and street)

            address_hash = (
                self._build_hash(address)
                if is_valid
                else None
            )

            cached = (
                geo_cache.get(address_hash)
                if address_hash
                else None
            )

            if cached:
                geo_status = "success"
                latitude = cached.get("latitude")
                longitude = cached.get("longitude")
                geo_provider = cached.get("geo_provider")
                geo_display_name = cached.get(
                    "geo_display_name"
                )
                estado = cached.get("estado")
                geo_last_checked_at = cached.get(
                    "geo_last_checked_at"
                )
                cached_count += 1

            elif is_valid:
                geo_status = "pending"
                latitude = None
                longitude = None
                geo_provider = None
                geo_display_name = None
                estado = None
                geo_last_checked_at = None
                pending_count += 1

            else:
                geo_status = "invalid_address"
                latitude = None
                longitude = None
                geo_provider = None
                geo_display_name = None
                estado = None
                geo_last_checked_at = (
                    today.isoformat()
                )
                invalid_count += 1

            cliente = row.get("cliente")

            if pd.isna(cliente) or not cliente:
                cliente = row.get("Cliente")

            empresa = row.get("Empresa")

            faturamento_total = row.get(
                "faturamento_total",
                0
            )

            if pd.isna(faturamento_total):
                faturamento_total = 0

            dias_sem_compra = row.get(
                "dias_sem_compra"
            )

            if pd.isna(dias_sem_compra):
                dias_sem_compra = None

            records.append({
                "reference_date": reference_date,
                "period_type": self.PERIOD_TYPE,
                "empresa": self._clean_text(empresa),
                "codigo_cliente": self._normalize_code(
                    row.get("codigo_cliente")
                ),
                "cliente": self._clean_text(cliente),
                "tipo_logradouro": self._clean_text(
                    row.get("tipo_logradouro")
                ),
                "logradouro": street,
                "numero": self._clean_text(
                    row.get("numero_entrega")
                ),
                "bairro": self._clean_text(
                    row.get("bairro_entrega")
                ),
                "cidade": city,
                "estado": estado,
                "cep": self._clean_text(
                    row.get("cep_entrega")
                ),
                "endereco_completo": address,
                "endereco_hash": address_hash,
                "latitude": latitude,
                "longitude": longitude,
                "geo_status": geo_status,
                "geo_provider": geo_provider,
                "geo_display_name": geo_display_name,
                "geo_last_checked_at": geo_last_checked_at,
                "faturamento_total": round(
                    float(faturamento_total),
                    2
                ),
                "customer_tier": (
                    None
                    if pd.isna(row.get("customer_tier"))
                    else str(row.get("customer_tier")).strip()
                ),
                "cliente_status": (
                    None
                    if pd.isna(row.get("cliente_status"))
                    else str(row.get("cliente_status")).strip()
                ),

                "evolution_status": (
                    None
                    if pd.isna(row.get("evolution_status"))
                    else str(row.get("evolution_status")).strip()
                ),
                "dias_sem_compra": (
                    None
                    if dias_sem_compra is None
                    else int(dias_sem_compra)
                ),
                "updated_at": today.isoformat()
            })

        self.supabase.replace_snapshot(
            "mart_customer_geo_snapshot",
            {
                "reference_date": reference_date,
                "period_type": self.PERIOD_TYPE
            },
            records
        )

        return {
            "geo_records": len(records),
            "geo_pending": pending_count,
            "geo_cached": cached_count,
            "geo_invalid": invalid_count
        }