from fastapi import APIRouter, Body
from typing import Any, Dict, List, Tuple

router = APIRouter()

def _err(path: str, msg: str) -> Dict[str, Any]:
    return {"path": path, "message": msg}

def _validate_engine(engine: Dict[str, Any]) -> List[Dict[str, Any]]:
    errs: List[Dict[str, Any]] = []

    if not isinstance(engine, dict):
        return [_err("engine", "must be object")]

    if "auto_trade" in engine and not isinstance(engine["auto_trade"], bool):
        errs.append(_err("engine.auto_trade", "must be boolean"))

    if "min_spread_bps" in engine:
        v = engine["min_spread_bps"]
        if not isinstance(v, (int, float)):
            errs.append(_err("engine.min_spread_bps", "must be number"))
        elif v <= 0:
            errs.append(_err("engine.min_spread_bps", "must be > 0"))

    if "cooldown_s" in engine:
        v = engine["cooldown_s"]
        if not isinstance(v, (int, float)):
            errs.append(_err("engine.cooldown_s", "must be number"))
        elif v <= 0:
            errs.append(_err("engine.cooldown_s", "must be > 0"))

    if "notional" in engine:
        v = engine["notional"]
        if not isinstance(v, (int, float)):
            errs.append(_err("engine.notional", "must be number"))
        elif v <= 0:
            errs.append(_err("engine.notional", "must be > 0"))

    if "max_open_trades" in engine:
        v = engine["max_open_trades"]
        if not isinstance(v, int):
            errs.append(_err("engine.max_open_trades", "must be integer"))
        elif v < 1:
            errs.append(_err("engine.max_open_trades", "must be >= 1"))

    return errs

def _validate_safe_mode(safe_mode: Dict[str, Any]) -> List[Dict[str, Any]]:
    errs: List[Dict[str, Any]] = []
    if not isinstance(safe_mode, dict):
        return [_err("safe_mode", "must be object")]
    if "enabled" in safe_mode and not isinstance(safe_mode["enabled"], bool):
        errs.append(_err("safe_mode.enabled", "must be boolean"))
    if "require_double_confirmation" in safe_mode and not isinstance(safe_mode["require_double_confirmation"], bool):
        errs.append(_err("safe_mode.require_double_confirmation", "must be boolean"))
    return errs

@router.post("/api/ui/config/validate")
def validate_config(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Проверяем только поля, что пришли (partial-validate).
    Возвращаем:
      { "valid": bool, "errors": [ {path, message}, ... ] }
    """
    errors: List[Dict[str, Any]] = []

    if not isinstance(payload, dict):
        return {"valid": False, "errors": [_err("$", "payload must be object")]}

    eng = payload.get("engine")
    if eng is not None:
        errors.extend(_validate_engine(eng))

    sm = payload.get("safe_mode")
    if sm is not None:
        errors.extend(_validate_safe_mode(sm))

    return {"valid": len(errors) == 0, "errors": errors}
