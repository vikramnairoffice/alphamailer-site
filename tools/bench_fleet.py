"""Synthetic local SQLite fleet submission/claim timing; no workers or email."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import time
import tracemalloc

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.fleet_models import Worker  # register fleet tables
from app import campaign_service, fleet_service
from app.fleet_schemas import CampaignCreate, Claim, Heartbeat, WorkerCreate


def run(total=500):
    if not 1 <= total <= 500:
        raise ValueError("Benchmark accepts one to 500 synthetic leads")
    with tempfile.TemporaryDirectory(prefix="alphamailer-fleet-bench-") as directory:
        db_path = Path(directory) / "fleet.sqlite3"
        engine = create_engine("sqlite:///" + db_path.as_posix())
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            workers = []
            for i in range(5):
                worker = fleet_service.pair(db, WorkerCreate(name=f"Fixture {i}",
                    platform="test", capabilities=["gmail.compose"],
                    accounts=[f"account{i}@example.test"]))
                fleet_service.heartbeat(db, worker["id"], Heartbeat(session_id=f"benchmark-session-{i}"))
                workers.append(worker)
            manifest = CampaignCreate(idempotency_key="benchmark-manifest", assignments=[{
                "lead_id": f"lead-{i:04}", "worker_id": workers[i % 5]["id"],
                "account_email": f"account{i % 5}@example.test", "operation": "gmail.compose",
                "message": {"to": [f"recipient{i}@example.test"],
                            "subject": "Synthetic benchmark", "body": "Fixture only"},
            } for i in range(total)])
            tracemalloc.start()
            start = time.perf_counter()
            campaign = campaign_service.submit(db, manifest)
            submit_seconds = time.perf_counter() - start
            peak_bytes = tracemalloc.get_traced_memory()[1]
            tracemalloc.stop()
            start = time.perf_counter()
            claims = [fleet_service.claim(db, worker["id"], Claim(
                session_id=f"benchmark-session-{i}", slot_id=f"slot-{i}",
                account_email=f"account{i}@example.test")) for i, worker in enumerate(workers)]
            claim_seconds = time.perf_counter() - start
            if campaign["total"] != total or any(value["job"] is None for value in claims):
                raise AssertionError("Synthetic campaign did not retain every assignment")
        engine.dispose()
        return {"leads": total, "workers": 5, "submit_seconds": round(submit_seconds, 4),
                "five_claims_seconds": round(claim_seconds, 4),
                "python_peak_bytes_during_submit": peak_bytes,
                "sqlite_bytes": db_path.stat().st_size,
                "scope": "synthetic local SQLite; no renderer, provider, network or email"}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
