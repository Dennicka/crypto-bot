from typing import Any, Dict, List
from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request):
    # Простой HTML — данные подгружаются из API fetch'ем на стороне браузера
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.post("/api/ui/config/validate")
async def validate_config(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []

    def add(path: str, msg: str) -> None:
        errors.append({"path": path, "msg": msg})

    # safe_mode
    if "safe_mode" in payload:
        sm = payload["safe_mode"]
        if not isinstance(sm, dict):
            add("safe_mode", "must be object")
        else:
            if "enabled" in sm and not isinstance(sm["enabled"], bool):
                add("safe_mode.enabled", "must be boolean")
            if "require_double_confirmation" in sm and not isinstance(sm["require_double_confirmation"], bool):
                add("safe_mode.require_double_confirmation", "must be boolean")

    # engine
    if "engine" in payload:
        eng = payload["engine"]
        if not isinstance(eng, dict):
            add("engine", "must be object")
        else:
            if "auto_trade" in eng and not isinstance(eng["auto_trade"], bool):
                add("engine.auto_trade", "must be boolean")

            def check_num(name: str, *, gt: float = None, ge: float = None, integer: bool = False) -> None:
                if name not in eng:
                    return
                v = eng[name]
                if integer:
                    if not isinstance(v, int):
                        add(f"engine.{name}", "must be integer")
                        return
                else:
                    if not isinstance(v, (int, float)):
                        add(f"engine.{name}", "must be number")
                        return
                if gt is not None and not (v > gt):
                    add(f"engine.{name}", f"must be > {gt}")
                if ge is not None and not (v >= ge):
                    add(f"engine.{name}", f"must be ≥ {ge}")

            check_num("min_spread_bps", ge=0)
            check_num("cooldown_s", gt=0)
            check_num("notional", gt=0)
            check_num("max_open_trades", ge=0, integer=True)

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}
