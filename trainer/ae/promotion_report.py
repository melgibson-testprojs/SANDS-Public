import json
from pathlib import Path
from trainer.ae.compare_models import compare_candidate

def build_promotion_report(run_id):
    run_dir = Path(f"models/experiments/ae/{run_id}")
    metrics_path = run_dir / "metrics.json"

    if not metrics_path.exists():
        return {"error": "metrics_not_found"}

    metrics = json.loads(metrics_path.read_text())
    comparison = compare_candidate(str(run_dir / "autoencoder.h5"))

    verdict = comparison.get("verdict")
    recommendation = "PROMOTE" if verdict == "BETTER" else "REJECT"

    return {
        "run": run_id,
        "training": metrics,
        "comparison": comparison,
        "recommendation": recommendation,
    }
