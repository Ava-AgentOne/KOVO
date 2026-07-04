"""
Metrics history for the Mission Control sparklines (v2.1).

A background task samples CPU/RAM/disk every SAMPLE_SECONDS and keeps a
rolling 24h window, persisted as JSON so restarts don't blank the charts.
Deliberately tiny: no database, no chart library — the frontend draws
inline SVG polylines from these numbers.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from src.utils.platform import data_path

log = logging.getLogger(__name__)

SAMPLE_SECONDS = 300          # one sample every 5 minutes
WINDOW_SECONDS = 24 * 3600    # keep 24 hours (288 samples)


class MetricsHistory:
    def __init__(self, path=None):
        self.path = path or (data_path() / "metrics_history.json")
        self._samples: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            if self.path.exists():
                self._samples = json.loads(self.path.read_text())
                self._prune()
        except Exception as e:
            log.warning("Metrics history load failed: %s", e)
            self._samples = []

    def _prune(self) -> None:
        cutoff = time.time() - WINDOW_SECONDS
        self._samples = [s for s in self._samples if s.get("t", 0) >= cutoff]

    def add_sample(self, cpu: float, ram: float, disk: float) -> None:
        self._samples.append({
            "t": int(time.time()),
            "cpu": round(cpu, 1),
            "ram": round(ram, 1),
            "disk": round(disk, 1),
        })
        self._prune()
        try:
            self.path.write_text(json.dumps(self._samples))
        except Exception as e:
            log.warning("Metrics history save failed: %s", e)

    def samples(self) -> list[dict]:
        self._prune()
        return list(self._samples)


history = MetricsHistory()


async def run_sampler() -> None:
    """Background loop started from the gateway lifespan."""
    import psutil
    while True:
        try:
            history.add_sample(
                cpu=psutil.cpu_percent(interval=1),
                ram=psutil.virtual_memory().percent,
                disk=psutil.disk_usage("/").percent,
            )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("Metrics sample failed: %s", e)
        await asyncio.sleep(SAMPLE_SECONDS)
