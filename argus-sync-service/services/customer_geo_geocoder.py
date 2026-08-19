import os
import re
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from geopy.exc import (
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable,
)
from geopy.geocoders import Nominatim


class CustomerGeoGeocoder:

    DEFAULT_BATCH_SIZE = 5
    MIN_DELAY_SECONDS = 1.1

    def __init__(self, supabase_connector):
        self.supabase = supabase_connector

        load_dotenv("config/.env")

        self.user_agent = os.getenv(
            "GEOCODER_USER_AGENT"
        )

        self.batch_size = int(
            os.getenv(
                "GEOCODER_SYNC_BATCH_SIZE",
                self.DEFAULT_BATCH_SIZE,
            )
        )

        if self.batch_size < 0:
            raise ValueError(
                "GEOCODER_SYNC_BATCH_SIZE deve ser maior ou igual a zero."
            )

    @staticmethod
    def _now_iso():
        return datetime.now(
            timezone.utc
        ).isoformat()

    @staticmethod
    def _clean(value):
        if value is None:
            return ""

        text = str(value).strip()

        if text.lower() in {
            "nan",
            "none",
            "null",
        }:
            return ""

        if text.endswith(".0"):
            text = text[:-2]

        return text.strip()

    @classmethod
    def _normalize_cep(cls, value):
        text = cls._clean(value)
        digits = re.sub(
            r"\D",
            "",
            text,
        )

        if len(digits) == 8:
            return digits

        return digits or ""

    @classmethod
    def _normalize_number(cls, value):
        text = cls._clean(value)

        if text.upper() in {
            "",
            "0",
            "00",
            "S/N",
            "SN",
        }:
            return ""

        return text

    @classmethod
    def _build_queries(cls, row):
        tipo = cls._clean(
            row.get("tipo_logradouro")
        )
        logradouro = cls._clean(
            row.get("logradouro")
        )
        numero = cls._normalize_number(
            row.get("numero")
        )
        bairro = cls._clean(
            row.get("bairro")
        )
        cidade = cls._clean(
            row.get("cidade")
        )
        cep = cls._normalize_cep(
            row.get("cep")
        )

        street = " ".join(
            item
            for item in [tipo, logradouro]
            if item
        ).strip()

        queries = []

        if street and numero and cidade:
            parts = [
                f"{street}, {numero}",
                bairro,
                cidade,
                cep,
                "Brasil",
            ]
            queries.append(
                ", ".join(
                    part
                    for part in parts
                    if part
                )
            )

        if street and numero and cidade:
            parts = [
                f"{street}, {numero}",
                bairro,
                cidade,
                "Brasil",
            ]
            queries.append(
                ", ".join(
                    part
                    for part in parts
                    if part
                )
            )

        if street and cidade:
            parts = [
                street,
                bairro,
                cidade,
                "Brasil",
            ]
            queries.append(
                ", ".join(
                    part
                    for part in parts
                    if part
                )
            )

        if cidade and cep:
            queries.append(
                f"{cidade}, {cep}, Brasil"
            )

        return list(
            dict.fromkeys(queries)
        )

    def _load_pending(
        self,
        candidate_hashes=None,
    ):
        if self.batch_size == 0:
            return []

        columns = (
            "endereco_hash,endereco_completo,"
            "tipo_logradouro,logradouro,numero,"
            "bairro,cidade,cep,geo_status,"
            "attempt_count,first_checked_at,"
            "created_at"
        )

        if candidate_hashes is None:
            return self.supabase.select_rows(
                "customer_geo_cache",
                columns=columns,
                filters={
                    "geo_status": "pending"
                },
                order_by="created_at",
                descending=False,
                limit=self.batch_size,
            )

        candidate_hashes = set(
            candidate_hashes
        )

        if not candidate_hashes:
            return []

        pending = self.supabase.select_rows_paginated(
            "customer_geo_cache",
            columns=columns,
            filters={
                "geo_status": "pending"
            },
            order_by="created_at",
            descending=False,
            page_size=1000,
        )

        selected = [
            row
            for row in pending
            if row.get("endereco_hash")
            in candidate_hashes
        ]

        return selected[:self.batch_size]

    def _update_hash(
        self,
        endereco_hash,
        payload,
    ):
        (
            self.supabase.client
            .table("customer_geo_cache")
            .update(payload)
            .eq(
                "endereco_hash",
                endereco_hash,
            )
            .execute()
        )

    def run(
        self,
        candidate_hashes=None,
    ):
        result = {
            "processed": 0,
            "success": 0,
            "not_found": 0,
            "errors": 0,
        }

        if self.batch_size == 0:
            return result

        if not self.user_agent:
            raise RuntimeError(
                "GEOCODER_USER_AGENT não foi configurado em config/.env."
            )

        pending = self._load_pending(
            candidate_hashes=candidate_hashes,
        )

        if not pending:
            return result

        geolocator = Nominatim(
            user_agent=self.user_agent,
            timeout=15,
        )

        print(
            f"  Geo automático: processando "
            f"{len(pending)} hash(es) pending"
        )

        for row in pending:
            checked_at = self._now_iso()
            attempts_before = int(
                row.get("attempt_count") or 0
            )

            try:
                location = None
                queries = self._build_queries(
                    row
                )

                for query in queries:
                    location = geolocator.geocode(
                        query,
                        addressdetails=True,
                        country_codes="br",
                        exactly_one=True,
                    )

                    if location:
                        break

                    time.sleep(
                        self.MIN_DELAY_SECONDS
                    )

                if location:
                    raw_address = (
                        location.raw.get(
                            "address",
                            {},
                        )
                        if location.raw
                        else {}
                    )

                    state = (
                        raw_address.get("state")
                        or raw_address.get("region")
                    )

                    self._update_hash(
                        row["endereco_hash"],
                        {
                            "latitude": float(
                                location.latitude
                            ),
                            "longitude": float(
                                location.longitude
                            ),
                            "estado": state,
                            "geo_status": "success",
                            "geo_provider": "nominatim_osm",
                            "geo_display_name": location.address,
                            "attempt_count": attempts_before + 1,
                            "first_checked_at": (
                                row.get("first_checked_at")
                                or checked_at
                            ),
                            "last_checked_at": checked_at,
                            "next_retry_at": None,
                            "last_error": None,
                            "updated_at": checked_at,
                        },
                    )

                    result["success"] += 1

                else:
                    self._update_hash(
                        row["endereco_hash"],
                        {
                            "geo_status": "not_found",
                            "geo_provider": "nominatim_osm",
                            "attempt_count": attempts_before + 1,
                            "first_checked_at": (
                                row.get("first_checked_at")
                                or checked_at
                            ),
                            "last_checked_at": checked_at,
                            "next_retry_at": None,
                            "last_error": None,
                            "updated_at": checked_at,
                        },
                    )

                    result["not_found"] += 1

            except (
                GeocoderTimedOut,
                GeocoderUnavailable,
                GeocoderServiceError,
            ) as exc:
                self._update_hash(
                    row["endereco_hash"],
                    {
                        "geo_status": "error",
                        "geo_provider": "nominatim_osm",
                        "attempt_count": attempts_before + 1,
                        "first_checked_at": (
                            row.get("first_checked_at")
                            or checked_at
                        ),
                        "last_checked_at": checked_at,
                        "next_retry_at": None,
                        "last_error": str(exc)[:1000],
                        "updated_at": checked_at,
                    },
                )

                result["errors"] += 1

            result["processed"] += 1

            time.sleep(
                self.MIN_DELAY_SECONDS
            )

        print(
            f"  Geo automático concluído: "
            f"{result['success']} success | "
            f"{result['not_found']} not_found | "
            f"{result['errors']} error"
        )

        return result
