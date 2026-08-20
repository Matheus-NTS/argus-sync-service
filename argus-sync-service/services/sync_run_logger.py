import atexit
import os
import sys
from datetime import datetime
from pathlib import Path


class _TeeStream:
    def __init__(self, console_stream, log_file):
        self.console_stream = console_stream
        self.log_file = log_file

    def write(self, data):
        self.console_stream.write(data)
        self.log_file.write(data)
        return len(data)

    def flush(self):
        self.console_stream.flush()
        self.log_file.flush()

    def isatty(self):
        return self.console_stream.isatty()

    @property
    def encoding(self):
        return getattr(self.console_stream, "encoding", "utf-8")

    @property
    def errors(self):
        return getattr(self.console_stream, "errors", None)

    def fileno(self):
        return self.console_stream.fileno()


class SyncRunLogger:
    def __init__(self, logs_dir=None):
        base_dir = Path(__file__).resolve().parents[1]
        self.logs_dir = Path(logs_dir or base_dir / "logs")
        self.log_path = None
        self._file = None
        self._stdout = None
        self._stderr = None
        self._closed = False

    def start(self):
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now().astimezone()
        filename = f"argus_sync_{now:%Y%m%d_%H%M%S}_{os.getpid()}.log"
        self.log_path = self.logs_dir / filename
        self._file = open(self.log_path, "a", encoding="utf-8", buffering=1)

        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = _TeeStream(self._stdout, self._file)
        sys.stderr = _TeeStream(self._stderr, self._file)

        atexit.register(self.close)

        print(f"[ARGUS LOG] Arquivo: {self.log_path}")
        return self

    def close(self):
        if self._closed:
            return

        self._closed = True

        try:
            if self._file is not None:
                self._file.flush()
        finally:
            if self._stdout is not None and sys.stdout is not self._stdout:
                sys.stdout = self._stdout
            if self._stderr is not None and sys.stderr is not self._stderr:
                sys.stderr = self._stderr
            if self._file is not None:
                self._file.close()

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.close()
        else:
            self._file.flush()

        return False
