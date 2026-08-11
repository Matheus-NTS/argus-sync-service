from datetime import datetime, timezone


PIPELINE_STATE_TABLE = "argus_pipeline_state"


def mark_pipeline_success(
    supabase_connector,
    pipeline_key: str,
):
    now = datetime.now(timezone.utc)

    supabase_connector.upsert(
        PIPELINE_STATE_TABLE,
        {
            "pipeline_key": pipeline_key,
            "reference_date": now.date().isoformat(),
            "last_success_at": now.isoformat(),
        },
        "pipeline_key",
    )