from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dashboard.app.api.portal import router as portal_router
from dashboard.app.api.dashboard import router as dashboard_router
from dashboard.app.api.agent import router as agent_router


app = FastAPI(title="SwarmSec Dashboard Backend")

app.include_router(portal_router)
app.include_router(dashboard_router)
app.include_router(agent_router)

app.mount(
    "/static",
    StaticFiles(directory="dashboard/app/static"),
    name="static"
)
