import os
from pathlib import Path


class SyncAlreadyRunningError(RuntimeError):
    pass


class SyncRunLock:
    """
    Cross-platform non-blocking process lock.

    The lock is held by the operating system while the process is alive.
    If the process crashes, the OS releases the lock automatically.
    The lock file itself may remain on disk; that does not block future runs.
    """

    def __init__(self, lock_path=None):
        base_dir = Path(__file__).resolve().parents[1]
        runtime_dir = base_dir / ".runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)

        self.lock_path = Path(
            lock_path or runtime_dir / "argus_sync.lock"
        )
        self._handle = None

    def acquire(self):
        self._handle = open(
            self.lock_path,
            "a+b",
            buffering=0,
        )

        self._handle.seek(0, os.SEEK_END)

        if self._handle.tell() == 0:
            self._handle.write(b"0")
            self._handle.flush()

        self._handle.seek(0)

        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(
                    self._handle.fileno(),
                    msvcrt.LK_NBLCK,
                    1,
                )
            else:
                import fcntl

                fcntl.flock(
                    self._handle.fileno(),
                    fcntl.LOCK_EX | fcntl.LOCK_NB,
                )
        except (OSError, IOError) as exc:
            self._handle.close()
            self._handle = None

            raise SyncAlreadyRunningError(
                "Outra execução do ARGUS Sync já está em andamento."
            ) from exc

        return self

    def release(self):
        if self._handle is None:
            return

        try:
            self._handle.seek(0)

            if os.name == "nt":
                import msvcrt

                msvcrt.locking(
                    self._handle.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                import fcntl

                fcntl.flock(
                    self._handle.fileno(),
                    fcntl.LOCK_UN,
                )
        finally:
            self._handle.close()
            self._handle = None

    def __enter__(self):
        return self.acquire()

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.release()
        return False
