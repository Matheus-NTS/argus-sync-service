import os
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from geopy.geocoders import Nominatim
from geopy.exc import (
    GeocoderServiceError,
    GeocoderTimedOut,
    GeocoderUnavailable
)

from connectors.supabase_connector import SupabaseConnector


PAGE_SIZE = 100
MIN_DELAY_SECONDS = 1.1


def build_queries(row):
    tipo = (row.get("tipo_logradouro") or "").strip()
    logradouro = (row.get("logradouro") or "").strip()
    numero = (row.get("numero") or "").strip()
    bairro = (row.get("bairro") or "").strip()
    cidade = (row.get("cidade") or "").strip()
    cep = (row.get("cep") or "").strip()

    street = " ".join(
        item for item in [tipo, logradouro]
        if item
    ).strip()

    valid_number = (
        numero
        and numero.upper() not in {
            "0",
            "00",
            "S/N",
            "SN"
        }
    )

    queries = []

    if street and valid_number:
        queries.append(
            f"{street}, {numero}, {bairro}, "
            f"{cidade}, {cep}, Brasil"
        )

    if street:
        queries.append(
            f"{street}, {bairro}, "
            f"{cidade}, {cep}, Brasil"
        )

    if bairro and cidade:
        queries.append(
            f"{bairro}, {cidade}, {cep}, Brasil"
        )

    if cidade and cep:
        queries.append(
            f"{cidade}, {cep}, Brasil"
        )

    # Remove tentativas duplicadas preservando a ordem.
    return list(dict.fromkeys(queries))


def fetch_pending(client, batch_size):
    response = (
        client
        .table("mart_customer_geo_snapshot")
        .select(
            "id,tipo_logradouro,logradouro,numero,"
            "bairro,cidade,cep,endereco_completo"
        )
        .eq("geo_status", "pending")
        .order("id")
        .limit(batch_size)
        .execute()
    )

    return response.data or []


def update_geo(client, record_id, payload):
    (
        client
        .table("mart_customer_geo_snapshot")
        .update(payload)
        .eq("id", record_id)
        .execute()
    )


def main():
    load_dotenv("config/.env")

    user_agent = os.getenv("GEOCODER_USER_AGENT")
    batch_size = int(
        os.getenv("GEOCODER_BATCH_SIZE", PAGE_SIZE)
    )

    if not user_agent:
        raise RuntimeError(
            "Defina GEOCODER_USER_AGENT em config/.env "
            "com o nome do ARGUS e um contato válido."
        )

    supabase = SupabaseConnector()

    geolocator = Nominatim(
        user_agent=user_agent,
        timeout=15
    )

    pending = fetch_pending(
        supabase.client,
        batch_size
    )

    if not pending:
        print("Nenhum endereço pendente para geocodificar.")
        return

    success = 0
    not_found = 0
    errors = 0

    print(
        f"Geocodificando {len(pending)} endereços "
        f"(máximo {batch_size} nesta execução)."
    )

    for index, row in enumerate(pending, start=1):
        checked_at = datetime.now().isoformat()

        try:
            location = None

            for query in build_queries(row):
                location = geolocator.geocode(
                    query,
                    addressdetails=True,
                    country_codes="br",
                    exactly_one=True
                )

                if location:
                    break

                time.sleep(MIN_DELAY_SECONDS)

            if location:
                raw_address = (
                    location.raw.get("address", {})
                    if location.raw
                    else {}
                )

                state = (
                    raw_address.get("state")
                    or raw_address.get("region")
                )

                update_geo(
                    supabase.client,
                    row["id"],
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
                        "geo_last_checked_at": checked_at,
                        "updated_at": checked_at
                    }
                )

                success += 1
                result = "OK"

            else:
                update_geo(
                    supabase.client,
                    row["id"],
                    {
                        "geo_status": "not_found",
                        "geo_provider": "nominatim_osm",
                        "geo_last_checked_at": checked_at,
                        "updated_at": checked_at
                    }
                )

                not_found += 1
                result = "NÃO ENCONTRADO"

        except (
            GeocoderTimedOut,
            GeocoderUnavailable,
            GeocoderServiceError
        ) as exc:
            update_geo(
                supabase.client,
                row["id"],
                {
                    "geo_status": "error",
                    "geo_provider": "nominatim_osm",
                    "geo_last_checked_at": checked_at,
                    "updated_at": checked_at
                }
            )

            errors += 1
            result = f"ERRO: {exc}"

        print(
            f"[{index}/{len(pending)}] "
            f"{row.get('cidade') or '-'} — {result}"
        )

        time.sleep(MIN_DELAY_SECONDS)

    print()
    print("=" * 50)
    print("GEOCODIFICAÇÃO FINALIZADA")
    print(f"Sucesso: {success}")
    print(f"Não encontrados: {not_found}")
    print(f"Erros: {errors}")
    print("=" * 50)


if __name__ == "__main__":
    main()