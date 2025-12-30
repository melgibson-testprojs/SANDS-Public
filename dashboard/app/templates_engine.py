import time
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="dashboard/app/templates")

# ✅ Global filter
def humantime(ts: float):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

templates.env.filters["humantime"] = humantime
