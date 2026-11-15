"""User settings kept on the server in data/settings.json (git-ignored).

  display_name   shown in the header / profile (else the resume's own name)
  llm_endpoint   the local model's URL, e.g. an ngrok tunnel
                 (https://xxxx.ngrok-free.app/predict). Overrides LLM_ENDPOINT
                 from .env, so a new tunnel URL can be set from the app.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
PATH = ROOT / "data" / "settings.json"
_URL = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.I)


class SettingsError(ValueError):
    pass


def load() -> dict:
    try:
        return json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    PATH.parent.mkdir(exist_ok=True)
    tmp = PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, PATH)


def _load_env() -> None:
    from analyze import load_env   # local import: analyze imports this module
    load_env()


def llm_endpoint() -> str:
    """The local model URL: the one saved in the app, else LLM_ENDPOINT in .env."""
    saved = load().get("llm_endpoint", "").strip()
    if saved:
        return saved
    _load_env()
    return os.getenv("LLM_ENDPOINT", "").strip()


def llm_timeout() -> float:
    _load_env()
    return float(os.getenv("LLM_TIMEOUT", "120"))


def update(display_name: str | None = None, llm_endpoint_: str | None = None) -> dict:
    data = load()
    if display_name is not None:
        name = display_name.strip()
        if len(name) > 60:
            raise SettingsError("Name is too long (60 characters max)")
        data["display_name"] = name
    if llm_endpoint_ is not None:
        url = llm_endpoint_.strip().rstrip("/")
        if url and not _URL.match(url):
            raise SettingsError("Enter a full URL starting with https://")
        data["llm_endpoint"] = url
        _PROBE["at"] = 0.0                 # re-check the new URL right away
    _save(data)
    return data


# ---------------------------------------------------------------- probing
_PROBE: dict = {"at": 0.0, "state": "unset", "url": ""}


def probe(url: str | None = None, force: bool = False) -> dict:
    """Is the local model reachable? A GET on its POST-only route answers
    405/422 when the server is up; ngrok answers 404 when the tunnel is down.
    Cached for a minute unless forced."""
    url = (url if url is not None else llm_endpoint()).strip()
    if not url:
        return {"state": "unset", "detail": "No local model URL set"}
    if not force and _PROBE["url"] == url and time.time() - _PROBE["at"] < 60:
        return {"state": _PROBE["state"], "detail": _PROBE.get("detail", "")}
    state, detail = "offline", ""
    try:
        req = urllib.request.Request(url, headers={"ngrok-skip-browser-warning": "1"})
        with urllib.request.urlopen(req, timeout=5) as r:
            state, detail = "online", f"HTTP {r.status}"
    except urllib.error.HTTPError as e:
        if e.code in (405, 422):
            state, detail = "online", f"HTTP {e.code} (endpoint expects POST: good)"
        elif e.code == 404:
            detail = ("HTTP 404: tunnel is down, or the URL is missing the route "
                      "(e.g. /predict)")
        else:
            detail = f"HTTP {e.code}"
    except Exception as e:
        detail = f"{type(e).__name__}: {e}"
    _PROBE.update(at=time.time(), state=state, url=url, detail=detail)
    return {"state": state, "detail": detail}
