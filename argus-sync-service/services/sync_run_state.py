import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter


class SyncRunState:
    def __init__(self, log_file=None, state_path=None):
        base_dir = Path(__file__).resolve().parents[1]
        runtime_dir = base_dir / ".runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        self.state_path = Path(
            state_path or runtime_dir / "argus_sync_state.json"
        )
        self.log_file = (
            str(Path(log_file).resolve()) if log_file else None
        )
        self.started_at = None
        self._started_perf = None

    @staticmethod
    def _now_iso():
        return datetime.now(timezone.utc).isoformat()

    def _write_atomic(self, payload):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        fd, temp_name = tempfile.mkstemp(
            prefix="argus_sync_state_",
            suffix=".tmp",
            dir=str(self.state_path.parent),
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    indent=2,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temp_name, self.state_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def start(self):
        self.started_at = self._now_iso()
        self._started_perf = perf_counter()

        self._write_atomic(
            {
                "status": "running",
                "started_at": self.started_at,
                "finished_at": None,
                "duration_seconds": None,
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "log_file": self.log_file,
                "error_type": None,
                "error_message": None,
            }
        )

        print(
            "[ARGUS STATE] "
            f"status=running | pid={os.getpid()}"
        )
        return self

    def _finish(self, status, error_type=None, error_message=None):
        finished_at = self._now_iso()
        duration_seconds = None

        if self._started_perf is not None:
            duration_seconds = round(
                perf_counter() - self._started_perf,
                3,
            )

        self._write_atomic(
            {
                "status": status,
                "started_at": self.started_at,
                "finished_at": finished_at,
                "duration_seconds": duration_seconds,
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "log_file": self.log_file,
                "error_type": error_type,
                "error_message": error_message,
            }
        )

        print(
            "[ARGUS STATE] "
            f"status={status} | "
            f"duration={duration_seconds}s"
        )

    def success(self):
        self._finish("success")

    def failed(self, exc):
        self._finish(
            "failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.success()
        else:
            self.failed(exc_value)

        return False
