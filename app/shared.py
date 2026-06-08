"""Single shared Jinja2Templates instance — globals set by main.py at startup."""
import os, json as _json
from datetime import datetime
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))
templates.env.globals["utcnow"] = datetime.utcnow

def _tojson(v, default=None):
    if hasattr(v, "__iter__") and not isinstance(v, str):
        out = []
        for t in v:
            if hasattr(t, "id"):
                out.append({"id": t.id, "name": t.name, "code": t.code, "group_letter": t.group_letter})
            else:
                out.append(t)
        return _json.dumps(out)
    return _json.dumps(v)

templates.env.filters["tojson"] = _tojson
