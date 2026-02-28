from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

from dashboard.app.api.portal import router as portal_router
from dashboard.app.api.dashboard import router as dashboard_router
from dashboard.app.api.agent import router as agent_router
import time
from dashboard.app.api.state import router as state_router
from dashboard.app.api.predictions import router as predictions_router
from dashboard.app.api.prediction_state import router as prediction_state_router
from dashboard.app.api.topology import router as topology_router
from dashboard.app.api import models as models_api
from dashboard.app.api import devices
from dashboard.app.api.debug import router as debug_router
from dashboard.app.api.auth import router as auth_router, get_current_user







app = FastAPI(title="SwarmSec Dashboard Backend")

app.include_router(portal_router)
app.include_router(dashboard_router)
app.include_router(agent_router)
app.include_router(state_router)
app.include_router(predictions_router)
app.include_router(prediction_state_router)
app.include_router(topology_router)
app.include_router(models_api.router)
app.include_router(devices.router)
app.include_router(debug_router)
app.include_router(auth_router)


app.mount(
    "/static",
    StaticFiles(directory="dashboard/app/static"),
    name="static"
)

@app.get("/_init")
def _init():
    pass

from fastapi.templating import Jinja2Templates
templates = Jinja2Templates(directory="dashboard/app/templates")

templates.env.filters["humantime"] = lambda ts: time.strftime(
    "%Y-%m-%d %H:%M:%S", time.localtime(ts)
)