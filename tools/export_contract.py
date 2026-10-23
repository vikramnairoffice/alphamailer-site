"""Run from the orchestrator root: python -m tools.export_contract."""
import json
from pathlib import Path

from app import fleet_schemas as schemas


def export():
    target = Path(__file__).resolve().parents[1] / "contracts" / "v1"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("WorkerCreate", "JobCreate", "CampaignCreate", "Heartbeat", "Claim", "Report",
                 "GoogleOAuthStart", "GoogleOAuthSession", "GoogleOAuthRefresh"):
        (target / f"{name}.schema.json").write_text(
            json.dumps(getattr(schemas, name).model_json_schema(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    export()
