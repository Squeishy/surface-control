"""Built-in commands the dashboard can trigger, and the shared command history."""
import subprocess
import threading
import time
from collections import deque

import winapi


class ActionError(Exception):
    pass


def _keys(*names):
    def run():
        if not winapi.send_keys(*names):
            raise ActionError("Windows a bloqué la frappe (le PC est-il verrouillé ?).")
    return run


def _later(fn, delay=0.8):
    """Run after the HTTP response has gone out (sleep, power)."""
    def run():
        threading.Timer(delay, fn).start()
    return run


def _shutdown(*args):
    def run():
        subprocess.Popen(["shutdown"] + list(args), creationflags=subprocess.CREATE_NO_WINDOW)
    return run


def _check(fn, message):
    def run():
        if not fn():
            raise ActionError(message)
    return run


# id: (label, icon, group, needs confirmation, handler)
CATALOG = [
    ("media.prev", "Précédent", "prev", "Média", False, _keys("media_prev")),
    ("media.playpause", "Lecture / Pause", "playpause", "Média", False, _keys("media_playpause")),
    ("media.next", "Suivant", "next", "Média", False, _keys("media_next")),
    ("volume.down", "Volume −", "voldown", "Média", False, _keys("volume_down")),
    ("volume.up", "Volume +", "volup", "Média", False, _keys("volume_up")),
    ("volume.mute", "Muet", "mute", "Média", False, _keys("volume_mute")),
    ("system.show_desktop", "Afficher le bureau", "desktop", "Windows", False, _keys("win", "d")),
    ("system.task_view", "Vue des tâches", "taskview", "Windows", False, _keys("win", "tab")),
    ("system.screenshot", "Capture d'écran", "camera", "Windows", False, _keys("win", "printscreen")),
    ("system.snip", "Capture de zone", "scissors", "Windows", False, _keys("win", "shift", "s")),
    ("system.explorer", "Explorateur", "folder", "Windows", False, _keys("win", "e")),
    ("system.taskmgr", "Gestionnaire des tâches", "activity", "Windows", False, _keys("ctrl", "shift", "esc")),
    ("system.settings", "Paramètres Windows", "settings", "Windows", False,
     _check(lambda: winapi.shell_open("ms-settings:"), "Impossible d'ouvrir les Paramètres.")),
    ("system.lock", "Verrouiller", "lock", "Alimentation", False,
     _check(winapi.lock_workstation, "Windows a refusé le verrouillage.")),
    ("system.monitor_off", "Éteindre les écrans", "monitoroff", "Alimentation", False,
     _check(winapi.monitors_off, "Impossible d'éteindre les écrans.")),
    ("system.sleep", "Veille", "moon", "Alimentation", True, _later(winapi.suspend)),
    ("system.restart", "Redémarrer", "restart", "Alimentation", True, _shutdown("/r", "/t", "5")),
    ("system.shutdown", "Éteindre", "power", "Alimentation", True, _shutdown("/s", "/t", "5")),
    ("system.abort", "Annuler l'arrêt", "x", "Alimentation", False, _shutdown("/a")),
]
BY_ID = {a[0]: a for a in CATALOG}


def catalog(unity_commands):
    items = [{"id": a[0], "label": a[1], "icon": a[2], "group": a[3], "confirm": a[4]} for a in CATALOG]
    icons = {"play": "play", "pause": "pause", "step": "step", "refresh": "refresh", "save": "save",
             "undo": "undo", "redo": "redo", "build_settings": "hammer", "build_run": "buildrun", "focus": "focus"}
    for key, (label, _) in unity_commands.items():
        items.append({"id": "unity." + key, "label": label, "icon": icons.get(key, "unity"),
                      "group": "Unity", "confirm": False})
    return items


def run(action_id):
    action = BY_ID.get(action_id)
    if not action:
        raise ActionError("Commande inconnue.")
    action[5]()
    return action[1], action[2]


# ------------------------------------------------------------------ history

_history = deque(maxlen=40)
_history_lock = threading.Lock()
_seq = [0]


def record(label, icon, ok=True, detail=""):
    with _history_lock:
        _seq[0] += 1
        _history.appendleft({"id": _seq[0], "ts": time.time(), "label": label, "icon": icon,
                             "ok": ok, "detail": detail})


def history(limit=12):
    with _history_lock:
        return list(_history)[:limit]
