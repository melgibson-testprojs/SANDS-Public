from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dashboard.app.api.portal import router as portal_router
from dashboard.app.api.dashboard import router as dashboard_router
from dashboard.app.api.agent import router as agent_router
import time
from dashboard.app.api.state import router as state_router



app = FastAPI(title="SwarmSec Dashboard Backend")

app.include_router(portal_router)
app.include_router(dashboard_router)
app.include_router(agent_router)
app.include_router(state_router)

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