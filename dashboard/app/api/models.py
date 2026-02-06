from fastapi import APIRouter, BackgroundTasks
from pathlib import Path
import json
import shutil

router = APIRouter(prefix="/models", tags=["models"])

AE_BASE = Path("models/autoencoder_cicids2018.h5")
AE_EXPERIMENTS = Path("models/experiments/ae")
STATE_FILE = AE_EXPERIMENTS / "training_state.json"


def read_training_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"status": "idle"}


# @router.get("/ae/status")
# def ae_training_status():
#     from trainer.ae.build_dataset import build_ae_training_set

#     try:
#         data = build_ae_training_set()
#         return {
#             "ready": bool(data.get("ready", False)),
#             "reason": data.get("reason"),
#             "stats": data.get("stats"),
#         }

#     except Exception as e:
#         return {
#             "ready": False,
#             "reason": "status_check_failed",
#             "error": str(e),
#             "stats": None,
#         }

@router.get("/ae/status")
def ae_training_status():
    from trainer.ae.build_dataset import build_ae_training_set
    from pathlib import Path
    import json

    response = {}

    try:
        data = build_ae_training_set()
        response.update({
            "ready": bool(data.get("ready", False)),
            "reason": data.get("reason"),
            "stats": data.get("stats"),
        })
    except Exception as e:
        response.update({
            "ready": False,
            "reason": "status_check_failed",
            "error": str(e),
            "stats": None,
        })

    state_file = Path("models/experiments/ae/training_state.json")
    if state_file.exists():
        try:
            response["training_state"] = json.loads(state_file.read_text())
        except Exception:
            response["training_state"] = {}

    return response


# -------------------------------
# TRAIN
# -------------------------------

@router.post("/ae/train")
def trigger_ae_training(background_tasks: BackgroundTasks):
    try:
        from trainer.ae.build_dataset import build_ae_training_set
        from trainer.ae.train_incremental import train_incremental

        data = build_ae_training_set()

        if not data.get("ready"):
            return {
                "status": "skipped",
                "reason": data.get("reason"),
                "stats": data.get("stats"),
            }

        background_tasks.add_task(train_incremental)

        return {
            "status": "started"
        }

    except Exception as e:
        # FORCE ERROR VISIBILITY
        return {
            "status": "error",
            "ERROR_TYPE": type(e).__name__,
            "ERROR_MSG": str(e)
        }


# -------------------------------
# CANDIDATES
# -------------------------------

@router.get("/ae/candidates")
def list_candidates():
    runs = []

    for run in sorted(AE_EXPERIMENTS.glob("run_*")):
        runs.append({
            "run": run.name,
            "has_model": (run / "autoencoder.h5").exists(),
            "has_metrics": (run / "metrics.json").exists(),
        })

    return runs


@router.get("/ae/candidate/{run_id}/metrics")
def get_candidate_metrics(run_id: str):
    path = AE_EXPERIMENTS / run_id / "metrics.json"
    if not path.exists():
        return {"error": "metrics_not_found"}
    return json.loads(path.read_text())


@router.get("/ae/compare/{run_id}")
def compare_candidate(run_id: str):
    from trainer.ae.compare_models import compare_candidate
    from pathlib import Path

    candidate = Path(f"models/experiments/ae/{run_id}/autoencoder.h5")
    if not candidate.exists():
        return {"error": "candidate_not_found"}

    return compare_candidate(str(candidate))



# -------------------------------
# PROMOTE / ROLLBACK
# -------------------------------

@router.post("/ae/promote/{run_id}")
def promote_candidate(run_id: str):
    from trainer.ae.promote_model import promote
    from trainer.ae.compare_models import compare_candidate
    from pathlib import Path

    candidate = Path(f"models/experiments/ae/{run_id}/autoencoder.h5")
    if not candidate.exists():
        return {"status": "error", "reason": "candidate_not_found"}

    comparison = compare_candidate(str(candidate))
    if comparison.get("verdict") != "BETTER":
        return {
            "status": "blocked",
            "reason": "candidate_worse_than_base",
            "comparison": comparison,
        }

    promote(candidate)
    return {
        "status": "promoted",
        "run": run_id,
        "comparison": comparison,
    }


@router.post("/ae/rollback")
def rollback():
    state = read_training_state()
    if state.get("status") == "running":
        return {"status": "error", "reason": "training_in_progress"}

    backups = sorted(Path("models/backups").glob("autoencoder_*.h5"))
    if not backups:
        return {"status": "error", "reason": "no_backups"}

    last = backups[-1]
    shutil.copy(last, AE_BASE)
    return {"status": "rolled_back", "backup": last.name}

@router.get("/ae/report/{run_id}")
def promotion_report(run_id: str):
    from trainer.ae.promotion_report import build_promotion_report
    return build_promotion_report(run_id)