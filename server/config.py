"""Persistent configuration (data/config.json): pairing, apps, links, quick actions."""
import glob
import json
import os
import secrets
import subprocess
import threading
import time

import winapi

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

DEFAULT_QUICK_ACTIONS = [
    "system.lock", "system.screenshot", "system.snip", "system.show_desktop", "system.task_view",
    "system.monitor_off", "unity.play", "unity.refresh", "system.explorer", "system.sleep",
]
DEFAULT_THEME = {"bg": "aurora", "dim": 10, "labels": True}

_lock = threading.RLock()
_data = {}


def _new_id(prefix):
    return prefix + secrets.token_hex(4)


def _first_existing(patterns):
    for pattern in patterns:
        matches = sorted(glob.glob(pattern), reverse=True)  # newest version folder first
        if matches:
            return matches[0]
    return None


def _detect_apps():
    """Seed the Applications page with well-known apps installed on this PC."""
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    known = [
        ("Chrome", [pf + r"\Google\Chrome\Application\chrome.exe", pf86 + r"\Google\Chrome\Application\chrome.exe",
                    local + r"\Google\Chrome\Application\chrome.exe"], {}),
        ("Brave", [pf + r"\BraveSoftware\Brave-Browser\Application\brave.exe"], {}),
        ("Firefox", [pf + r"\Mozilla Firefox\firefox.exe"], {}),
        ("Edge", [pf86 + r"\Microsoft\Edge\Application\msedge.exe", pf + r"\Microsoft\Edge\Application\msedge.exe"], {}),
        ("VS Code", [local + r"\Programs\Microsoft VS Code\Code.exe", pf + r"\Microsoft VS Code\Code.exe"], {}),
        ("Visual Studio", [pf + r"\Microsoft Visual Studio\*\*\Common7\IDE\devenv.exe"], {}),
        ("Rider", [pf + r"\JetBrains\JetBrains Rider*\bin\rider64.exe", local + r"\Programs\Rider\bin\rider64.exe"], {}),
        ("Unity Hub", [pf + r"\Unity Hub\Unity Hub.exe"], {}),
        ("Blender", [pf + r"\Blender Foundation\Blender*\blender.exe"], {}),
        ("GitHub Desktop", [local + r"\GitHubDesktop\GitHubDesktop.exe"], {}),
        ("Figma", [local + r"\Figma\Figma.exe"], {}),
        ("Discord", [local + r"\Discord\Update.exe"],
         {"args": "--processStart Discord.exe", "process": "discord.exe",
          "icon": _first_existing([local + r"\Discord\app-*\Discord.exe"])}),
        ("Spotify", [roaming + r"\Spotify\Spotify.exe"], {}),
        ("Steam", [pf86 + r"\Steam\steam.exe"], {}),
        ("OBS Studio", [pf + r"\obs-studio\bin\64bit\obs64.exe"], {}),
        ("Notepad++", [pf + r"\Notepad++\notepad++.exe"], {}),
    ]
    apps = []
    for name, patterns, extra in known:
        path = _first_existing(patterns)
        if not path:
            continue
        app = {"id": _new_id("a"), "name": name, "path": path, "args": "",
               "process": os.path.basename(path).lower(), "icon": path}
        app.update({k: v for k, v in extra.items() if v})
        apps.append(app)
    return apps


def _default_links():
    links = [
        ("GitHub", "https://github.com", "Web"),
        ("YouTube", "https://www.youtube.com", "Web"),
        ("Claude", "https://claude.ai", "Web"),
        ("Manuel Unity", "https://docs.unity3d.com/Manual/index.html", "Unity"),
        ("API de script", "https://docs.unity3d.com/ScriptReference/index.html", "Unity"),
        ("Asset Store", "https://assetstore.unity.com", "Unity"),
        ("Unity Cloud", "https://cloud.unity.com", "Unity"),
    ]
    for name, key in (("Bureau", "desktop"), ("Documents", "documents"), ("Téléchargements", "downloads"),
                      ("Captures d'écran", "screenshots")):
        path = winapi.known_folder(key)
        if path and os.path.isdir(path):
            links.append((name, path, "Dossiers"))
    return [{"id": _new_id("l"), "name": n, "target": t, "group": g} for n, t, g in links]


def _defaults():
    return {
        "port": 8765,
        "pin": "%06d" % secrets.randbelow(1000000),
        "trust_localhost": True,
        "devices": {},
        "quick_actions": list(DEFAULT_QUICK_ACTIONS),
        "theme": dict(DEFAULT_THEME),
        "apps": _detect_apps(),
        "links": _default_links(),
    }


def load():
    global _data
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _data = json.load(f)
            for key, value in _defaults().items():
                _data.setdefault(key, value)
        else:
            _data = _defaults()
        save()
        return _data


def save():
    with _lock:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_data, f, indent=2)
        os.replace(tmp, CONFIG_PATH)


def get(key):
    with _lock:
        return _data.get(key)


def put(key, value):
    with _lock:
        _data[key] = value
        save()


# ------------------------------------------------------------------ devices

def find_device(token):
    if not token:
        return None
    with _lock:
        for device_id, device in _data["devices"].items():
            if secrets.compare_digest(device["token"], token):
                return device_id
    return None


def add_device(name):
    with _lock:
        device_id = _new_id("d")
        token = secrets.token_hex(24)
        _data["devices"][device_id] = {"token": token, "name": name[:60] or "Tablet",
                                       "paired": time.time(), "seen": time.time()}
        save()
        return device_id, token


def touch_device(device_id):
    with _lock:
        device = _data["devices"].get(device_id)
        if device and time.time() - device.get("seen", 0) > 60:
            device["seen"] = time.time()
            save()


def remove_device(device_id):
    with _lock:
        if _data["devices"].pop(device_id, None) is not None:
            save()
            return True
    return False


# --------------------------------------------------------------- apps/links

def resolve_shortcut(path):
    """Target exe of a .lnk file (via WScript.Shell; only called when an app is added)."""
    script = "(New-Object -ComObject WScript.Shell).CreateShortcut('%s').TargetPath" % path.replace("'", "''")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, timeout=10,
                             creationflags=subprocess.CREATE_NO_WINDOW)
        target = out.stdout.strip()
        return target if target and os.path.exists(target) else None
    except (OSError, subprocess.SubprocessError):
        return None


def upsert(kind, item):
    """Insert or replace an entry of 'apps' or 'links' (matched by id)."""
    with _lock:
        items = _data[kind]
        if not item.get("id"):
            item["id"] = _new_id(kind[0])
            items.append(item)
        else:
            for i, existing in enumerate(items):
                if existing["id"] == item["id"]:
                    items[i] = item
                    break
            else:
                items.append(item)
        save()
        return item


def remove(kind, item_id):
    with _lock:
        before = len(_data[kind])
        _data[kind] = [x for x in _data[kind] if x["id"] != item_id]
        _data["quick_actions"] = [q for q in _data["quick_actions"] if q != "%s:%s" % (kind[:-1], item_id)]
        save()
        return len(_data[kind]) != before


def find(kind, item_id):
    with _lock:
        for item in _data[kind]:
            if item["id"] == item_id:
                return dict(item)
    return None


def start_menu_apps():
    """Every shortcut in the Start menu, for the 'Add application' picker."""
    roots = [os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
             os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")]
    skip = ("uninstall", "readme", "help", "website", "documentation", "release notes", "license", "manual")
    seen, found = set(), []
    for root in roots:
        for folder, _, files in os.walk(root):
            for name in files:
                if not name.lower().endswith(".lnk"):
                    continue
                title = name[:-4]
                if any(s in title.lower() for s in skip) or title.lower() in seen:
                    continue
                seen.add(title.lower())
                found.append({"name": title, "path": os.path.join(folder, name)})
    found.sort(key=lambda x: x["name"].lower())
    return found
