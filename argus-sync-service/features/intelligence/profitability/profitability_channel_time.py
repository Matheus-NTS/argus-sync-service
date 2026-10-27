"""Referencia temporal do PostgreSQL para o canal Atacado x Varejo."""

from datetime import datetime, timedelta, timezone


SAFETY_MARGIN = timedelta(seconds=5)


def get_channel_source_as_of(supabase_connector) -> datetime:
    """Obtem horario do PostgreSQL e aplica margem operacional."""

    response = supabase_connector.client.rpc(
        "argus_channel_server_time",
        {},
    ).execute()

    value = response.data

    if not isinstance(value, str):
        raise ValueError(
            "ARGUS_CHANNEL_SERVER_TIME_INVALID: "
            "RPC nao retornou timestamp textual."
        )

    try:
        server_time = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError(
            "ARGUS_CHANNEL_SERVER_TIME_INVALID: "
            "Timestamp retornado e invalido."
        ) from exc

    if (
        server_time.tzinfo is None
        or server_time.utcoffset() is None
    ):
        raise ValueError(
            "ARGUS_CHANNEL_SERVER_TIME_INVALID: "
            "Timestamp sem timezone."
        )

    source_as_of = (
        server_time.astimezone(timezone.utc)
        - SAFETY_MARGIN
    )

    if source_as_of > datetime.now(timezone.utc):
        raise ValueError(
            "ARGUS_CHANNEL_CLOCK_MISMATCH: "
            "Referencia do PostgreSQL esta no futuro "
            "em relacao ao processo Python. "
            "Nenhuma publicacao deve ser iniciada."
        )

    return source_as_of
