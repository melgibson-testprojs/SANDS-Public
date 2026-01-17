from fastapi import APIRouter

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/ae/status")
def ae_training_status():
    try:
        # IMPORT INSIDE FUNCTION (IMPORTANT)
        from trainer.ae.build_dataset import build_ae_training_set

        data = build_ae_training_set()

        if not data.get("ready"):
            return {
                "ready": False,
                "reason": data.get("reason"),
                "stats": data.get("stats"),
            }

        return {
            "ready": True,
            "stats": data.get("stats"),
        }

    except Exception as e:
        # TEMPORARY: surface error clearly
        return {
            "ready": False,
            "error": str(e),
        }
