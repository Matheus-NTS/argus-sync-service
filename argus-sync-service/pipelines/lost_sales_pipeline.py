from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd


class LostSalesPipeline:

    REQUIRED_FIELDS = [
        "id",
        "data",
        "vendedor",
        "cliente",
        "produto",
        "qtd",
        "valor_un",
        "valor_total",
        "motivo"
    ]

    def __init__(self, sheets_connector, supabase_connector):
        self.sheets = sheets_connector
        self.supabase = supabase_connector

    @staticmethod
    def _clean_text(value: Any) -> str | None:

        if value is None:
            return None

        cleaned = " ".join(str(value).strip().split())

        return cleaned or None

    @staticmethod
    def _parse_currency(value: Any) -> float:

        if value is None:
            return 0.0

        if isinstance(value, (int, float, Decimal)):
            return round(float(value), 2)

        raw = str(value).strip()

        if not raw:
            return 0.0

        raw = (
            raw
            .replace("R$", "")
            .replace("\u00a0", "")
            .replace(" ", "")
            .replace(".", "")
            .replace(",", ".")
        )

        try:
            return round(float(Decimal(raw)), 2)
        except (InvalidOperation, ValueError):
            return 0.0

    @staticmethod
    def _parse_number(value: Any) -> float:

        if value is None:
            return 0.0

        if isinstance(value, (int, float, Decimal)):
            return float(value)

        raw = str(value).strip()

        if not raw:
            return 0.0

        raw = raw.replace(".", "").replace(",", ".")

        try:
            return float(Decimal(raw))
        except (InvalidOperation, ValueError):
            return 0.0

    @staticmethod
    def _parse_date(value: Any):

        parsed = pd.to_datetime(
            value,
            errors="coerce",
            dayfirst=False
        )

        if pd.isna(parsed):
            return None

        return parsed.date()

    def _validate_required_fields(self, records: list[dict]):

        if not records:
            return

        available = set(records[0].keys())
        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if field not in available
        ]

        if missing:
            raise KeyError(
                "Campos obrigatórios ausentes no Google Sheets: "
                + ", ".join(missing)
            )

    def _build_quality_result(
        self,
        row: dict,
        quantidade: float,
        valor_unitario: float,
        valor_total: float,
        sale_date
    ) -> tuple[str, str | None]:

        notes = []

        if sale_date is None:
            notes.append("Data inválida")

        if quantidade <= 0:
            notes.append("Quantidade igual ou menor que zero")

        if valor_unitario <= 0:
            notes.append("Valor unitário igual a zero")

        if valor_total <= 0:
            notes.append("Valor total igual a zero")

        expected_total = round(
            quantidade * valor_unitario,
            2
        )

        difference = abs(expected_total - valor_total)

        tolerance = max(1.0, abs(expected_total) * 0.02)

        if (
            quantidade > 0
            and valor_unitario > 0
            and valor_total > 0
            and difference > tolerance
        ):
            notes.append(
                "Valor total diverge de quantidade × valor unitário"
            )

        if not self._clean_text(row.get("vendedor")):
            notes.append("Vendedor não informado")

        if not self._clean_text(row.get("cliente")):
            notes.append("Cliente não informado")

        if not self._clean_text(row.get("produto")):
            notes.append("Produto não informado")

        if not self._clean_text(row.get("motivo")):
            notes.append("Motivo não informado")

        if not notes:
            return "valid", None

        if sale_date is None or not self._clean_text(row.get("produto")):
            return "invalid", "; ".join(notes)

        return "attention", "; ".join(notes)

    def run(self):

        hoje = datetime.today().date()

        payload = self.sheets.fetch_lost_sales()
        source_updated_at = payload.get("updated_at")
        raw_records = payload.get("data", [])

        self._validate_required_fields(raw_records)

        records_by_id = {}
        invalid_without_id = 0

        for row in raw_records:

            raw_id = row.get("id")

            try:
                record_id = int(raw_id)
            except (TypeError, ValueError):
                invalid_without_id += 1
                continue

            sale_date = self._parse_date(row.get("data"))

            quantidade = self._parse_number(
                row.get("qtd")
            )

            valor_unitario = self._parse_currency(
                row.get("valor_un")
            )

            valor_total = self._parse_currency(
                row.get("valor_total")
            )

            quality_status, quality_notes = (
                self._build_quality_result(
                    row=row,
                    quantidade=quantidade,
                    valor_unitario=valor_unitario,
                    valor_total=valor_total,
                    sale_date=sale_date
                )
            )

            if sale_date is None:
                continue

            record = {
                "id": record_id,
                "reference_date": hoje.isoformat(),
                "source_updated_at": source_updated_at,
                "sale_date": sale_date.isoformat(),
                "vendedor": (
                    self._clean_text(row.get("vendedor"))
                    or "Não informado"
                ),
                "cliente": (
                    self._clean_text(row.get("cliente"))
                    or "Não informado"
                ),
                "cod_supra": self._clean_text(
                    row.get("cod_supra")
                ),
                "produto": (
                    self._clean_text(row.get("produto"))
                    or "Não informado"
                ),
                "quantidade": round(float(quantidade), 2),
                "valor_unitario": round(
                    float(valor_unitario),
                    2
                ),
                "valor_total": round(
                    float(valor_total),
                    2
                ),
                "motivo": (
                    self._clean_text(row.get("motivo"))
                    or "Não informado"
                ),
                "observacao": self._clean_text(
                    row.get("observacao")
                ),
                "data_quality_status": quality_status,
                "data_quality_notes": quality_notes,
                "updated_at": datetime.now().isoformat()
            }

            # Se houver ID repetido, prevalece a última linha
            # existente na planilha.
            records_by_id[record_id] = record

        clean_records = list(records_by_id.values())

        clean_records.sort(
            key=lambda item: (
                item["sale_date"],
                item["id"]
            )
        )

        # O snapshot da planilha é substituído integralmente.
        # Assim, exclusões feitas no Sheets também são refletidas.
        self.supabase.delete_all(
            "mart_lost_sales_snapshot"
        )

        if clean_records:
            batch_size = 500

            for start in range(0, len(clean_records), batch_size):

                batch = clean_records[
                    start:start + batch_size
                ]

                self.supabase.insert(
                    "mart_lost_sales_snapshot",
                    batch
                )

        valid_count = sum(
            1
            for item in clean_records
            if item["data_quality_status"] == "valid"
        )

        attention_count = sum(
            1
            for item in clean_records
            if item["data_quality_status"] == "attention"
        )

        invalid_count = (
            invalid_without_id
            + sum(
                1
                for item in clean_records
                if item["data_quality_status"] == "invalid"
            )
        )

        total_value = sum(
            float(item["valor_total"])
            for item in clean_records
        )

        return {
            "source_records": len(raw_records),
            "lost_sales_records": len(clean_records),
            "lost_sales_valid": valid_count,
            "lost_sales_attention": attention_count,
            "lost_sales_invalid": invalid_count,
            "lost_sales_value": round(total_value, 2),
            "source_updated_at": source_updated_at
        }