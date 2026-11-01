"""Surface Control server: serves the tablet UI and the control API on your local network."""
import argparse
import ipaddress
import json
import logging
import os
import re
import secrets
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import psutil  # noqa: E402

import actions  # noqa: E402
import config  # noqa: E402
import images  # noqa: E402
import media  # noqa: E402
import monitor  # noqa: E402
import unity  # noqa: E402
import winapi  # noqa: E402

VERSION = "1.0.0"
WEB_DIR = os.path.join(config.ROOT, "web")
MIME = {".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}
URI = re.compile(r"^[a-z][a-z0-9+.-]+:", re.I)  # steam://, ms-settings:, https:// (but not C:\)
BACKGROUNDS = ("aurora", "sunset", "ocean", "grape", "mint", "ember", "midnight", "pc", "custom")
UNITY_ICONS = {"play": "play", "pause": "pause", "step": "step", "refresh": "refresh", "save": "save",
               "undo": "undo", "redo": "redo", "build_settings": "hammer", "build_run": "buildrun", "focus": "focus"}

log = logging.getLogger("server")
MON = None
MEDIA = media.Media()
PORT = 8765
_pin_failures = {}   # ip -> {"count", "until"}
_icon_cache = {}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Raw:
    def __init__(self, body, ctype, cache=0):
        self.body, self.ctype, self.cache = body, ctype, cache


class Ctx:
    def __init__(self, ip, local, device, authorized, query, body):
        self.ip, self.local, self.device, self.authorized = ip, local, device, authorized
        self.query, self.body = query, body


ROUTES = {}


def route(method, path, auth=True):
    def register(fn):
        ROUTES[(method, path)] = (fn, auth)
        return fn
    return register


def perform(label, icon, fn):
    """Run a command, log it in the history and turn failures into a readable API error."""
    try:
        message = fn()
    except (actions.ActionError, unity.UnityError) as e:
        actions.record(label, icon, False, str(e))
        raise ApiError(409, str(e))
    actions.record(label, icon, True, message or "")
    return {"ok": True, "message": message or label}


# ------------------------------------------------------------------ pairing

@route("GET", "/api/ping", auth=False)
def ping(ctx):
    return {"ok": True, "name": MON.info["name"], "version": VERSION, "paired": ctx.authorized,
            "local": ctx.local, "pin_length": len(str(config.get("pin")))}


@route("POST", "/api/pair", auth=False)
def pair(ctx):
    entry = _pin_failures.get(ctx.ip)
    if entry and entry["until"] > time.time():
        raise ApiError(429, "Trop de codes erronés. Réessayez dans %d secondes." % (entry["until"] - time.time()))
    if not secrets.compare_digest(str(ctx.body.get("pin", "")), str(config.get("pin"))):
        entry = _pin_failures.setdefault(ctx.ip, {"count": 0, "until": 0})
        entry["count"] += 1
        if entry["count"] >= 5:
            entry.update(count=0, until=time.time() + 60)
        raise ApiError(403, "Code PIN incorrect.")
    _pin_failures.pop(ctx.ip, None)
    name = str(ctx.body.get("device") or "Tablet")
    device_id, token = config.add_device(name)
    actions.record("Appairé : " + name, "tablet")
    return {"token": token, "device": device_id}


@route("POST", "/api/unpair")
def unpair(ctx):
    if ctx.device:
        config.remove_device(ctx.device)
    return {"ok": True}


@route("GET", "/api/security")
def security(ctx):
    devices = [{"id": k, "name": d["name"], "paired": d["paired"], "seen": d["seen"], "current": k == ctx.device}
               for k, d in config.get("devices").items()]
    devices.sort(key=lambda d: -d["seen"])
    return {"devices": devices, "pin": config.get("pin") if ctx.local else None,
            "trust_localhost": config.get("trust_localhost")}


@route("POST", "/api/security/pin")
def change_pin(ctx):
    pin = str(ctx.body.get("pin", ""))
    if not re.match(r"^\d{4,8}$", pin):
        raise ApiError(400, "Le code doit contenir 4 à 8 chiffres.")
    config.put("pin", pin)
    actions.record("Code PIN modifié", "key")
    return {"ok": True}


@route("POST", "/api/security/revoke")
def revoke(ctx):
    if not config.remove_device(str(ctx.body.get("id", ""))):
        raise ApiError(404, "Appareil introuvable.")
    return {"ok": True}


# -------------------------------------------------------------- state/config

def _pids_by_name(names):
    index = {}
    for pid, name in names.items():
        index.setdefault(name.lower(), []).append(pid)
    return index


@route("GET", "/api/state")
def state(ctx):
    snap, windows, names = MON.state()
    by_name = _pids_by_name(names)
    window_count = {}
    for w in windows:
        window_count[w["pid"]] = window_count.get(w["pid"], 0) + 1
    running = {}
    for app in config.get("apps"):
        pids = by_name.get((app.get("process") or "").lower(), [])
        if pids:
            running[app["id"]] = {"count": len(pids), "windows": sum(window_count.get(p, 0) for p in pids)}
    out = dict(snap)
    out.update({"pc": MON.info, "apps": running, "history": actions.history(), "time": time.time(),
                "utc_offset": time.localtime().tm_gmtoff, "media": MEDIA.state})
    return out


@route("GET", "/api/config")
def get_config(ctx):
    device = config.get("devices").get(ctx.device or "", {})
    return {"apps": config.get("apps"), "links": config.get("links"), "quick_actions": config.get("quick_actions"),
            "catalog": actions.catalog(unity.COMMANDS), "pc": MON.info, "version": VERSION, "port": PORT,
            "addresses": monitor.lan_addresses(), "device": {"id": ctx.device, "name": device.get("name"),
                                                             "paired": device.get("paired")},
            "local": ctx.local, "theme": theme_info()}


@route("POST", "/api/quick_actions")
def save_quick_actions(ctx):
    items = [str(x) for x in ctx.body.get("items", []) if isinstance(x, str)][:18]
    config.put("quick_actions", items)
    return {"quick_actions": items}


# -------------------------------------------------------------- appearance

def theme_info():
    theme = dict(config.DEFAULT_THEME, **(config.get("theme") or {}))
    theme["versions"] = images.versions()
    return theme


@route("POST", "/api/theme")
def save_theme(ctx):
    theme = dict(config.DEFAULT_THEME, **(config.get("theme") or {}))
    body = ctx.body
    if "bg" in body:
        if body["bg"] not in BACKGROUNDS:
            raise ApiError(400, "Fond inconnu.")
        if body["bg"] != "custom" or images.versions()["custom"]:
            theme["bg"] = body["bg"]
        else:
            raise ApiError(400, "Importez d'abord une image.")
    if "dim" in body:
        theme["dim"] = max(0, min(70, int(body["dim"])))
    if "labels" in body:
        theme["labels"] = bool(body["labels"])
    config.put("theme", theme)
    return theme_info()


@route("GET", "/api/wallpaper")
def wallpaper(ctx):
    data, ctype = images.read_wallpaper(ctx.query.get("src", "pc"))
    if not data:
        raise ApiError(404, "Aucun fond d'écran trouvé.")
    return Raw(data, ctype, cache=86400 * 30)  # the URL carries a version stamp


@route("POST", "/api/wallpaper")
def upload_wallpaper(ctx):
    try:
        images.save_wallpaper(ctx.body.get("data"))
    except (ValueError, TypeError) as e:
        raise ApiError(400, str(e))
    config.put("theme", dict(config.DEFAULT_THEME, **dict(config.get("theme") or {}, bg="custom")))
    return theme_info()


@route("GET", "/api/linkicon")
def link_icon(ctx):
    link = _get("links", ctx.query.get("id"))
    found = images.link_icon(link["target"])
    if not found:
        raise ApiError(404, "Pas d'icône.")
    return Raw(found[0], found[1], cache=86400 * 7)


# ------------------------------------------------------------------ actions

@route("POST", "/api/action")
def run_action(ctx):
    action_id = str(ctx.body.get("id", ""))
    if action_id.startswith("unity."):
        return unity_command_by_name(action_id[6:])
    if action_id.startswith("app:"):
        return launch_app(action_id[4:], "auto")
    if action_id.startswith("link:"):
        return open_link(action_id[5:])
    entry = actions.BY_ID.get(action_id)
    if not entry:
        raise ApiError(404, "Commande inconnue.")
    return perform(entry[1], entry[2], lambda: actions.run(action_id) and None)


@route("POST", "/api/volume")
def volume(ctx):
    level, muted = ctx.body.get("level"), ctx.body.get("muted")
    try:
        if ctx.body.get("delta"):  # the - / + buttons
            level = winapi.get_volume()["level"] + int(ctx.body["delta"])
        winapi.set_volume(level=None if level is None else int(level), muted=None if muted is None else bool(muted))
        current = winapi.get_volume()
    except OSError as e:
        raise ApiError(409, "Impossible d'accéder au périphérique audio (%s)." % e)
    if muted is not None:
        actions.record("Son coupé" if current["muted"] else "Son rétabli", "mute" if current["muted"] else "volume")
    elif ctx.body.get("final") or ctx.body.get("delta"):
        actions.record("Volume %d%%" % current["level"], "volume")
    return current


@route("POST", "/api/media/seek")
def media_seek(ctx):
    try:
        ok = MEDIA.seek(float(ctx.body.get("position", 0)))
    except Exception as e:
        raise ApiError(409, "Impossible de changer la position (%s)." % e)
    if not ok:
        raise ApiError(409, "Cette appli ne permet pas de changer la position.")
    return {"ok": True, "media": MEDIA.state}


# --------------------------------------------------------------------- apps

def _get(kind, item_id):
    item = config.find(kind, str(item_id or ""))
    if not item:
        raise ApiError(404, "Cet élément n'existe plus.")
    return item


def _app_pids(app):
    _, _, names = MON.state()
    return _pids_by_name(names).get((app.get("process") or "").lower(), [])


def _windows_of(pids):
    _, windows, _ = MON.state()
    pids = set(pids)
    return [w for w in windows if w["pid"] in pids]


def launch_app(app_id, mode):
    app = _get("apps", app_id)

    def go():
        if mode != "new":
            windows = _windows_of(_app_pids(app))
            if windows and winapi.focus_window(windows[0]["hwnd"]):
                return "Basculé vers " + app["name"]
        cwd = os.path.dirname(app["path"]) if os.path.isfile(app["path"]) else None
        if not winapi.shell_open(app["path"], app.get("args"), cwd):
            raise actions.ActionError("Impossible de lancer %s." % app["name"])
        return app["name"] + " lancé"

    return perform(app["name"], "app:" + app["id"], go)


@route("POST", "/api/apps/launch")
def app_launch(ctx):
    return launch_app(ctx.body.get("id"), ctx.body.get("mode", "auto"))


@route("POST", "/api/apps/close")
def app_close(ctx):
    app = _get("apps", ctx.body.get("id"))

    def go():
        windows = _windows_of(_app_pids(app))
        if not windows:
            raise actions.ActionError("%s n'a aucune fenêtre ouverte." % app["name"])
        for w in windows:
            winapi.close_window(w["hwnd"])
        return "Fermeture de %s demandée" % app["name"]

    return perform("Fermer " + app["name"], "app:" + app["id"], go)


@route("POST", "/api/apps/kill")
def app_kill(ctx):
    app = _get("apps", ctx.body.get("id"))
    return perform("Forcer l'arrêt : " + app["name"], "app:" + app["id"], lambda: _kill_by_name(app.get("process")))


def _clean_app(body):
    name = str(body.get("name", "")).strip()[:40]
    path = str(body.get("path", "")).strip().strip('"')
    if not name or not path:
        raise ApiError(400, "Le nom et le chemin sont obligatoires.")
    expanded = os.path.expandvars(path)
    if not URI.match(path) and not os.path.exists(expanded):
        raise ApiError(400, "Ce chemin n'existe pas sur le PC.")
    target = expanded
    if expanded.lower().endswith(".lnk"):
        target = config.resolve_shortcut(expanded) or expanded
    existing = config.find("apps", str(body.get("id") or "")) or {}
    same_path = existing.get("path") == expanded
    process = str(body.get("process") or "").strip().lower()
    if not same_path and process == existing.get("process"):
        process = ""  # path changed: re-derive the process name from the new target
    if not process and target.lower().endswith(".exe"):
        process = os.path.basename(target).lower()
    icon = existing.get("icon") if same_path else target
    return {"id": existing.get("id"), "name": name, "path": expanded, "args": str(body.get("args", ""))[:300],
            "process": process, "icon": icon or target}


@route("POST", "/api/apps/save")
def app_save(ctx):
    return config.upsert("apps", _clean_app(ctx.body))


@route("POST", "/api/apps/delete")
def app_delete(ctx):
    if not config.remove("apps", str(ctx.body.get("id", ""))):
        raise ApiError(404, "Application introuvable.")
    return {"ok": True}


@route("GET", "/api/apps/discover")
def app_discover(ctx):
    return {"items": config.start_menu_apps()}


# -------------------------------------------------------------------- links

def open_link(link_id):
    link = _get("links", link_id)

    def go():
        if not winapi.shell_open(os.path.expandvars(link["target"])):
            raise actions.ActionError("Windows n'a pas pu ouvrir %s." % link["target"])
        return link["name"] + " ouvert"

    return perform(link["name"], "link:" + link["id"], go)


@route("POST", "/api/links/open")
def link_open(ctx):
    return open_link(ctx.body.get("id"))


@route("POST", "/api/links/save")
def link_save(ctx):
    name = str(ctx.body.get("name", "")).strip()[:40]
    target = str(ctx.body.get("target", "")).strip().strip('"')
    if not name or not target:
        raise ApiError(400, "Le nom et la cible sont obligatoires.")
    if "://" not in target and not URI.match(target) and not os.path.exists(os.path.expandvars(target)):
        if re.match(r"^[\w-]+(\.[\w-]+)+(/.*)?$", target):
            target = "https://" + target  # "github.com" -> https://github.com
        else:
            raise ApiError(400, "Indiquez une adresse web, ou un dossier ou fichier qui existe sur le PC.")
    group = str(ctx.body.get("group", "")).strip()[:24] or ("Web" if URI.match(target) else "Dossiers")
    return config.upsert("links", {"id": ctx.body.get("id") or None, "name": name, "target": target, "group": group})


@route("POST", "/api/links/delete")
def link_delete(ctx):
    if not config.remove("links", str(ctx.body.get("id", ""))):
        raise ApiError(404, "Lien introuvable.")
    return {"ok": True}


# ---------------------------------------------------------------- processes

@route("GET", "/api/processes")
def processes(ctx):
    MON.want_processes()
    data = MON.processes
    return {"ready": data["ts"] > 0, "ts": data["ts"], "count": data["count"], "groups": data["groups"]}


def _kill_by_name(name):
    name = (name or "").lower()
    if not name:
        raise actions.ActionError("Processus inconnu.")
    if name in monitor.PROTECTED:
        raise actions.ActionError("%s est un processus essentiel de Windows." % name)
    own, killed, denied = os.getpid(), 0, 0
    for proc in psutil.process_iter(["name"]):
        if (proc.info["name"] or "").lower() == name and proc.pid != own:
            try:
                proc.kill()
                killed += 1
            except psutil.NoSuchProcess:
                pass
            except psutil.AccessDenied:
                denied += 1
    if not killed:
        raise actions.ActionError("Impossible d'arrêter %s%s." % (name, " (accès refusé)" if denied else ""))
    return "%d processus arrêté%s" % (killed, "" if killed == 1 else "s")


@route("POST", "/api/processes/end")
def process_end(ctx):
    name = str(ctx.body.get("name", ""))
    return perform("Fin de tâche : " + (ctx.body.get("label") or name), "x", lambda: _kill_by_name(name))


@route("POST", "/api/processes/close")
def process_close(ctx):
    name = str(ctx.body.get("name", "")).lower()
    _, _, names = MON.state()

    def go():
        windows = _windows_of(_pids_by_name(names).get(name, []))
        if not windows:
            raise actions.ActionError("Aucune fenêtre à fermer.")
        for w in windows:
            winapi.close_window(w["hwnd"])
        return "%d fenêtre(s) fermée(s)" % len(windows)

    return perform("Fermer : " + (ctx.body.get("label") or name), "x", go)


@route("POST", "/api/processes/focus")
def process_focus(ctx):
    name = str(ctx.body.get("name", "")).lower()
    _, _, names = MON.state()

    def go():
        windows = _windows_of(_pids_by_name(names).get(name, []))
        if not windows or not winapi.focus_window(windows[0]["hwnd"]):
            raise actions.ActionError("Impossible d'afficher cette fenêtre au premier plan.")
        return None

    return perform("Basculer vers " + (ctx.body.get("label") or name), "focus", go)


# -------------------------------------------------------------------- unity

def unity_command_by_name(cmd):
    label = unity.COMMANDS.get(cmd, ("Unity",))[0]
    _, windows, _ = MON.state()
    return perform("Unity: " + label, UNITY_ICONS.get(cmd, "unity"), lambda: unity.run_command(cmd, windows) and None)


@route("GET", "/api/unity")
def unity_info(ctx):
    snap, _, _ = MON.state()
    return {"status": snap.get("unity"), "projects": unity.projects(), "editors": sorted(unity.editors()),
            "hub_installed": bool(unity.hub_exe())}


@route("POST", "/api/unity/command")
def unity_command(ctx):
    return unity_command_by_name(str(ctx.body.get("cmd", "")))


@route("POST", "/api/unity/open")
def unity_open(ctx):
    path = ctx.body.get("path")
    return perform("Ouvrir un projet Unity", "unity", lambda: unity.open_project(path))


@route("POST", "/api/unity/folder")
def unity_folder(ctx):
    path = ctx.body.get("path")
    return perform("Ouvrir le dossier du projet", "folder", lambda: unity.open_folder(path))


@route("POST", "/api/unity/code")
def unity_code(ctx):
    path = ctx.body.get("path")
    return perform("Ouvrir les scripts", "code", lambda: unity.open_code(path))


@route("POST", "/api/unity/hub")
def unity_hub(ctx):
    return perform("Ouvrir Unity Hub", "unity", unity.open_hub)


@route("GET", "/api/unity/log")
def unity_log(ctx):
    snap, _, _ = MON.state()
    project = (snap.get("unity") or {}).get("path", "")
    path = unity.log_path(project)
    if path and ctx.query.get("since") == repr(os.path.getmtime(path)):
        return {"unchanged": True}
    data = unity.read_log(project, min(1000, max(50, int(ctx.query.get("lines") or 300))))
    data["modified"] = repr(data["modified"])
    return data


# -------------------------------------------------------------------- icons

@route("GET", "/api/icon")
def icon(ctx):
    if ctx.query.get("app"):
        app = _get("apps", ctx.query["app"])
        path = app.get("icon") or app["path"]
    else:
        path = ctx.query.get("exe", "")
        if not path.lower().endswith(".exe"):
            raise ApiError(400, "Seules les icônes .exe sont servies.")
    size = int(ctx.query.get("s") or 64)
    size = size if size in (32, 48, 64, 96, 128, 256) else 64
    key = "%s|%d" % (path.lower(), size)
    if key not in _icon_cache:
        if len(_icon_cache) > 600:
            _icon_cache.clear()
        try:
            _icon_cache[key] = winapi.icon_png(path, size) or b""
        except OSError:
            _icon_cache[key] = b""
    if not _icon_cache[key]:
        raise ApiError(404, "No icon.")
    return Raw(_icon_cache[key], "image/png", cache=86400)


# ------------------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):
    server_version = "SurfaceControl/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # the dashboard polls every second or two; don't flood the console

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def _handle(self, method):
        ip = self.client_address[0]
        try:
            addr = ipaddress.ip_address(ip)
        except ValueError:
            return self._json(403, {"error": "Adresse client inconnue."})
        if not (addr.is_private or addr.is_loopback or addr.is_link_local):
            return self._json(403, {"error": "Surface Control n'accepte que les appareils de votre réseau local."})
        parts = urllib.parse.urlsplit(self.path)
        if not parts.path.startswith("/api/"):
            return self._static(urllib.parse.unquote(parts.path)) if method == "GET" else self._json(405, {})
        entry = ROUTES.get((method, parts.path))
        if not entry:
            return self._json(404, {"error": "Introuvable."})
        handler, needs_auth = entry
        local = addr.is_loopback
        query = dict(urllib.parse.parse_qsl(parts.query))
        device = config.find_device(self.headers.get("X-SC-Token") or query.get("t"))
        authorized = bool(device) or (local and bool(config.get("trust_localhost")))
        try:
            limit = 22000000 if parts.path == "/api/wallpaper" else 1000000  # base64 of a 15 MB image
            body = self._body(limit) if method == "POST" else {}
            if needs_auth and not authorized:
                return self._json(401, {"error": "pairing_required"})
            if device:
                config.touch_device(device)
            result = handler(Ctx(ip, local, device, authorized, query, body))
        except ApiError as e:
            return self._json(e.status, {"error": e.message})
        except Exception as e:  # keep the server alive whatever happens in a handler
            log.exception("%s %s failed", method, parts.path)
            return self._json(500, {"error": "Erreur du serveur : %s" % e})
        if isinstance(result, Raw):
            return self._send(200, result.body, result.ctype, result.cache)
        return self._json(200, result)

    def _body(self, limit):
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise ApiError(413, "Requête trop volumineuse.")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise ApiError(400, "JSON invalide.")
        if not isinstance(data, dict):
            raise ApiError(400, "Objet JSON attendu.")
        return data

    def _static(self, path):
        if path in ("", "/"):
            path = "/index.html"
        full = os.path.normpath(os.path.join(WEB_DIR, path.lstrip("/")))
        if not full.startswith(WEB_DIR + os.sep) or not os.path.isfile(full):
            return self._json(404, {"error": "Not found."})
        with open(full, "rb") as f:
            body = f.read()
        self._send(200, body, MIME.get(os.path.splitext(full)[1].lower(), "application/octet-stream"))

    def _json(self, status, payload):
        self._send(status, json.dumps(payload, separators=(",", ":")).encode("utf-8"), "application/json; charset=utf-8")

    def _send(self, status, body, ctype, cache=0):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if cache:
            self.send_header("Cache-Control", "private, max-age=%d" % cache)
        else:
            # IE11 caches XHR GETs aggressively unless told not to.
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        self.send_header("X-UA-Compatible", "IE=edge")  # never let IE fall back to Compatibility View
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            log.exception("Request from %s failed", client_address[0])


def _setup_logging():
    handlers = [logging.FileHandler(os.path.join(config.DATA_DIR, "server.log"), encoding="utf-8")]
    if sys.stderr is not None:  # pythonw has no console
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s", handlers=handlers)


def _say(text=""):
    if sys.stdout is not None:
        print(text, flush=True)


def main():
    global MON, PORT
    parser = argparse.ArgumentParser(description="Surface Control server")
    parser.add_argument("--host", default="0.0.0.0", help="address to listen on (default: all interfaces)")
    parser.add_argument("--port", type=int, help="port (default: from data/config.json, 8765)")
    args = parser.parse_args()
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    os.makedirs(config.DATA_DIR, exist_ok=True)
    _setup_logging()
    config.load()
    PORT = args.port or int(config.get("port") or 8765)
    MON = monitor.Monitor(unity_status=unity.status)
    MON.start()
    MEDIA.start()
    try:
        server = Server((args.host, PORT), Handler)
    except OSError:
        _say("Le port %d est déjà utilisé : Surface Control tourne peut-être déjà." % PORT)
        sys.exit(1)

    _say()
    _say("  Surface Control %s  |  %s" % (VERSION, MON.info["name"]))
    _say("  " + "-" * 52)
    _say("  Ouvrez cette adresse sur la Surface (Internet Explorer) :")
    if args.host in ("0.0.0.0", ""):
        for entry in monitor.lan_addresses():
            _say("     http://%s:%d     (%s)" % (entry["ip"], PORT, entry["iface"]))
    else:
        _say("     http://%s:%d" % (args.host, PORT))
    _say()
    _say("  Code PIN d'appairage :  %s" % config.get("pin"))
    _say()
    _say("  Laissez cette fenêtre ouverte. Ctrl+C pour arrêter.")
    _say()
    log.info("listening on %s:%d", args.host, PORT)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        _say("Arrêté.")


if __name__ == "__main__":
    main()
