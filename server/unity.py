"""Unity Editor / Unity Hub integration: projects, editors, live status, shortcuts, log."""
import glob
import json
import os
import re
import time
import winreg

import psutil

import winapi

HUB_DIR = os.path.join(os.environ.get("APPDATA", ""), "UnityHub")
GLOBAL_LOG = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Unity", "Editor", "Editor.log")
EDITOR_WINDOW_CLASS = "UnityContainerWndClass"

# Editor shortcuts sent to the focused Unity window (default Unity keymap).
COMMANDS = {
    "play": ("Play / Stop", ("ctrl", "p")),
    "pause": ("Pause", ("ctrl", "shift", "p")),
    "step": ("Image suivante", ("ctrl", "alt", "p")),
    "refresh": ("Actualiser les assets", ("ctrl", "r")),
    "save": ("Enregistrer", ("ctrl", "s")),
    "undo": ("Annuler", ("ctrl", "z")),
    "redo": ("Rétablir", ("ctrl", "y")),
    "build_settings": ("Profils de build", ("ctrl", "shift", "b")),
    "build_run": ("Build and Run", ("ctrl", "b")),
    "focus": ("Afficher l'éditeur", None),
}

_cmdline_cache = {}  # pid -> project path


class UnityError(Exception):
    pass


def _read_json(name):
    try:
        with open(os.path.join(HUB_DIR, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def hub_exe():
    for path in (os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Unity Hub", "Unity Hub.exe"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Unity Hub", "Unity Hub.exe")):
        if os.path.exists(path):
            return path
    return None


def editors():
    """Installed editor versions -> Unity.exe path."""
    roots = [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Unity", "Hub", "Editor")]
    secondary = _read_json("secondaryInstallPath.json")
    if isinstance(secondary, str) and secondary:
        roots.append(secondary)
    found = {}
    for root in roots:
        for exe in glob.glob(os.path.join(root, "*", "Editor", "Unity.exe")):
            found[os.path.basename(os.path.dirname(os.path.dirname(exe)))] = exe
    listed = _read_json("editors-v2.json") or {}
    for entry in listed.get("data", []) if isinstance(listed, dict) else []:
        locations = entry.get("location") or []
        for exe in locations if isinstance(locations, list) else [locations]:
            if entry.get("version") and isinstance(exe, str) and os.path.exists(exe):
                found[entry["version"]] = exe
    return found


def project_version(path):
    try:
        with open(os.path.join(path, "ProjectSettings", "ProjectVersion.txt"), "r", encoding="utf-8") as f:
            match = re.search(r"m_EditorVersion:\s*(\S+)", f.read())
            return match.group(1) if match else None
    except OSError:
        return None


def _registry_projects():
    paths = []
    for key_name in (r"Software\Unity Technologies\Unity Editor 5.x",):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
                i = 0
                while True:
                    name, value, _ = winreg.EnumValue(key, i)
                    i += 1
                    if name.startswith("RecentlyUsedProjectPaths") and isinstance(value, bytes):
                        paths.append(value.rstrip(b"\x00").decode("utf-8", "ignore").replace("/", "\\"))
        except OSError:
            pass
    return paths


def projects():
    installed = editors()
    found = {}
    hub = _read_json("projects-v1.json") or {}
    for path, entry in (hub.get("data") or {}).items():
        found[os.path.normcase(path)] = {
            "name": entry.get("title") or os.path.basename(path), "path": path,
            "version": entry.get("version"), "modified": (entry.get("lastModified") or 0) / 1000.0,
            "favorite": bool(entry.get("isFavorite")),
        }
    for path in _registry_projects():
        found.setdefault(os.path.normcase(path), {"name": os.path.basename(path), "path": path,
                                                  "version": None, "modified": 0, "favorite": False})
    result = []
    for project in found.values():
        if not os.path.isdir(os.path.join(project["path"], "Assets")):
            continue
        project["version"] = project_version(project["path"]) or project["version"]
        project["installed"] = project["version"] in installed
        project["exe"] = installed.get(project["version"]) or hub_exe() or ""
        if not project["modified"]:
            try:
                project["modified"] = os.path.getmtime(os.path.join(project["path"], "Assets"))
            except OSError:
                pass
        project["solution"] = bool(_solution(project["path"]))
        result.append(project)
    result.sort(key=lambda p: (not p["favorite"], -p["modified"]))
    return result


def known_project(path):
    for project in projects():
        if os.path.normcase(project["path"]) == os.path.normcase(path or ""):
            return project
    raise UnityError("Ce projet n'est pas dans votre liste Unity Hub.")


def _solution(path):
    found = glob.glob(os.path.join(path, "*.sln")) + glob.glob(os.path.join(path, "*.slnx"))
    return found[0] if found else None


def _project_path_of(pid):
    if pid not in _cmdline_cache:
        path = None
        try:
            args = psutil.Process(pid).cmdline()
            for i, arg in enumerate(args[:-1]):
                if arg.lower() in ("-projectpath", "-createproject"):
                    path = args[i + 1]
        except psutil.Error:
            pass
        _cmdline_cache[pid] = path
    return _cmdline_cache[pid]


def _parse_title(title):
    """'MyGame - SampleScene - Windows, Mac, Linux - Unity 6.5 (6000.5.5f1) <DX12>'"""
    parts = [p.strip() for p in title.split(" - ")]
    info = {"project": parts[0] if parts else "", "scene": "", "platform": "", "version": ""}
    if len(parts) >= 4:
        info["scene"], info["platform"] = parts[1], parts[2]
    match = re.search(r"\((\d+\.\d+\.\d+\w*)\)", title) or re.search(r"Unity (\d{4}\.\d+\.\d+\w*)", title)
    if match:
        info["version"] = match.group(1)
    return info


def editor_windows(windows):
    return [w for w in windows if w["cls"] == EDITOR_WINDOW_CLASS]


def status(windows, names):
    """Live editor/hub state. Called by the monitor every second, so it stays cheap."""
    editor_pids = {pid for pid, name in names.items() if name.lower() == "unity.exe"}
    for pid in [p for p in _cmdline_cache if p not in editor_pids]:
        del _cmdline_cache[pid]
    mains = [w for w in editor_windows(windows) if w["pid"] in editor_pids]
    state = {"running": bool(mains), "starting": False, "hub": any(n.lower() == "unity hub.exe" for n in names.values()),
             "count": len(mains), "project": "", "scene": "", "dirty": False, "version": "", "platform": "",
             "path": ""}
    if mains:
        main = mains[0]
        info = _parse_title(main["title"])
        path = _project_path_of(main["pid"]) or ""
        scene = info["scene"]
        state.update({
            "project": os.path.basename(path.rstrip("\\/")) if path else info["project"],
            "scene": scene.rstrip("*").strip(), "dirty": scene.endswith("*"),
            "version": info["version"], "platform": info["platform"], "path": path,
        })
    elif any(_project_path_of(pid) for pid in editor_pids):
        state["starting"] = True  # process up, main window not created yet
    return state


def run_command(name, windows):
    if name not in COMMANDS:
        raise UnityError("Commande Unity inconnue.")
    mains = editor_windows(windows)
    if not mains:
        raise UnityError("L'éditeur Unity n'est pas ouvert.")
    label, keys = COMMANDS[name]
    if not winapi.focus_window(mains[0]["hwnd"]):
        raise UnityError("Impossible d'afficher Unity au premier plan.")
    if keys:
        time.sleep(0.12)  # let the editor process the activation before the shortcut
        if not winapi.send_keys(*keys):
            raise UnityError("Windows a bloqué la frappe.")
    return label


def open_project(path):
    project = known_project(path)
    exe = editors().get(project["version"])
    if exe:
        if not winapi.shell_open(exe, '-projectPath "%s"' % project["path"]):
            raise UnityError("Impossible de lancer Unity %s." % project["version"])
        return "Ouverture de %s dans Unity %s" % (project["name"], project["version"])
    hub = hub_exe()
    if hub and winapi.shell_open(hub):
        return "Unity %s n'est pas installé : Unity Hub ouvert" % (project["version"] or "")
    raise UnityError("Aucun éditeur Unity correspondant ni Unity Hub trouvé.")


def open_folder(path):
    project = known_project(path)
    if not winapi.shell_open(project["path"]):
        raise UnityError("Impossible d'ouvrir le dossier.")
    return "Dossier %s ouvert" % project["name"]


def open_code(path):
    project = known_project(path)
    solution = _solution(project["path"])
    if solution and winapi.shell_open(solution):
        return "%s ouvert" % os.path.basename(solution)
    code = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Microsoft VS Code", "Code.exe")
    if os.path.exists(code) and winapi.shell_open(code, '"%s"' % project["path"]):
        return "%s ouvert dans VS Code" % project["name"]
    raise UnityError("Pas encore de fichier solution : ouvrez le projet une fois dans Unity.")


def open_hub():
    hub = hub_exe()
    if not hub or not winapi.shell_open(hub):
        raise UnityError("Unity Hub n'est pas installé.")
    return "Unity Hub ouvert"


# --------------------------------------------------------------------- logs

_ERROR = re.compile(r"error CS\d+|Exception|\bError\b|: error|Failed to|NullReference|Assertion failed", re.I)
_WARNING = re.compile(r"warning CS\d+|\bWarning\b|: warning|obsolete", re.I)


def log_path(project_path=""):
    """Unity 6.3+ writes to <project>/Logs/Editor.log and leaves a pointer in the global log."""
    candidates = []
    if project_path:
        candidates.append(os.path.join(project_path, "Logs", "Editor.log"))
    try:
        with open(GLOBAL_LOG, "r", encoding="utf-8", errors="replace") as f:
            tail = f.read()[-4000:]
        match = re.search(r"Logs moved to project-relative Editor\.log file.*?\n(.+Editor\.log)", tail, re.S)
        if match:
            candidates.append(os.path.normpath(match.group(1).strip()))
    except OSError:
        pass
    candidates.append(GLOBAL_LOG)
    existing = [p for p in candidates if os.path.exists(p)]
    return max(existing, key=os.path.getmtime) if existing else None


def read_log(project_path="", lines=300):
    path = log_path(project_path)
    if not path:
        return {"path": "", "lines": [], "modified": 0}
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - 256 * 1024))
        text = f.read().decode("utf-8", "replace")
    rows = []
    for line in text.splitlines()[-lines:]:
        line = line.rstrip()
        if not line:
            continue
        level = "error" if _ERROR.search(line) else "warning" if _WARNING.search(line) else "info"
        rows.append({"t": line[:600], "l": level})
    return {"path": path, "lines": rows, "modified": os.path.getmtime(path)}
