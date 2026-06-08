"""Single shared Jinja2Templates instance — globals set by main.py at startup."""
import os
from datetime import datetime
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
# Make now() callable in every template so we can do match_date comparisons
templates.env.globals["utcnow"] = datetime.utcnow
