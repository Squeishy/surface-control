"""Background sampler that keeps a fresh snapshot of the PC's state for the API."""
import logging
import os
import platform
import socket
import threading
import time
import winreg

import psutil

import winapi

log = logging.getLogger("monitor")

# Ending these takes Windows down with them; the Task Manager page refuses to.
PROTECTED = {
    "system", "system idle process", "registry", "secure system", "memory compression", "memcompression", "smss.exe",
    "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe", "lsaiso.exe",
    "svchost.exe", "fontdrvhost.exe", "dwm.exe",
}


def pc_info():
    info = {"name": os.environ.get("COMPUTERNAME") or socket.gethostname(), "os": "Windows",
            "cpu": platform.processor(), "ram": psutil.virtual_memory().total,
            "cores": psutil.cpu_count() or 1}
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            product = winreg.QueryValueEx(key, "ProductName")[0]
            build = int(winreg.QueryValueEx(key, "CurrentBuild")[0])
            try:
                release = winreg.QueryValueEx(key, "DisplayVersion")[0]
            except OSError:
                release = ""
            if build >= 22000:  # the registry still says "Windows 10" on 11
                product = product.replace("Windows 10", "Windows 11")
            info["os"] = ("%s %s" % (product, release)).strip()
    except OSError:
        pass
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            info["cpu"] = " ".join(winreg.QueryValueEx(key, "ProcessorNameString")[0].split())
    except OSError:
        pass
    return info


def lan_addresses():
    stats = psutil.net_if_stats()
    found = []
    for iface, addrs in psutil.net_if_addrs().items():
        if iface in stats and not stats[iface].isup:
            continue
        for addr in addrs:
            if addr.family == socket.AF_INET and not addr.address.startswith(("127.", "169.254.")):
                found.append({"iface": iface, "ip": addr.address})
    return found


class Monitor:
    def __init__(self, unity_status=None):
        self.info = pc_info()
        self.snapshot = {}
        self.windows = []
        self.names = {}            # pid -> process name
        self.processes = {"ts": 0, "groups": [], "count": 0}
        self._unity_status = unity_status
        self._lock = threading.Lock()
        self._want_processes_until = 0
        self._cpu_prev = ({}, 0)   # ({(pid, created): cpu time}, sampled at)
        self._exe_cache = {}       # pid -> exe path
        self._desc_cache = {}      # exe path -> friendly name
        self._net = None
        self._drives, self._drives_at = [], 0
        self._ncpu = psutil.cpu_count() or 1
        self._boot = psutil.boot_time()
        self._tick = 0

    def start(self):
        threading.Thread(target=self._run, name="monitor", daemon=True).start()

    def want_processes(self):
        """Per-process CPU/memory is only sampled while someone has Task Manager open."""
        if time.time() > self._want_processes_until + 5:
            self.processes = {"ts": 0, "groups": [], "count": 0}  # don't show a stale list
        self._want_processes_until = time.time() + 6

    def state(self):
        with self._lock:
            return self.snapshot, self.windows, self.names

    # ------------------------------------------------------------ sampling

    def _run(self):
        psutil.cpu_percent(None)
        with winapi.com_apartment(winapi.COINIT_MULTITHREADED):
            while True:
                started = time.time()
                try:
                    self._sample()
                except Exception:
                    log.exception("sample failed")
                self._tick += 1
                time.sleep(max(0.1, 1.0 - (time.time() - started)))

    def _sample(self):
        now = time.time()
        windows = winapi.list_windows()
        detailed = now < self._want_processes_until
        names = self._scan(windows, detailed) if (detailed or self._tick % 2 == 0 or not self.names) else self.names
        vm = psutil.virtual_memory()
        snap = {
            "time": now,
            "cpu": {"percent": round(psutil.cpu_percent(None), 1), "cores": self._ncpu},
            "ram": {"percent": round(vm.percent, 1), "used": vm.total - vm.available, "total": vm.total},
            "uptime": int(now - self._boot),
            "active": self._active(names),
            "net": self._net_rates(now),
            "drives": self._drive_usage(now),
            "volume": self._volume(),
            "processes": len(names),
        }
        if self._unity_status:
            snap["unity"] = self._unity_status(windows, names)
        with self._lock:
            self.windows, self.names, self.snapshot = windows, names, snap

    def _scan(self, windows, detailed):
        now = time.time()
        procs = winapi.process_snapshot()
        names = {pid: name for pid, name, _, _, _ in procs if pid}
        if detailed:
            self._group(procs, windows, now)
        for pid in [p for p in self._exe_cache if p not in names]:
            del self._exe_cache[pid]
        return names

    def _group(self, procs, windows, now):
        """Task Manager rows: processes grouped by program, CPU from the delta since the last scan."""
        prev, prev_at = self._cpu_prev
        elapsed = now - prev_at
        valid = 0 < elapsed < 5
        titles, groups, times = {}, {}, {}
        for w in windows:
            titles.setdefault(w["pid"], w["title"])
        for pid, name, created, cpu_time, mem in procs:
            if pid == 0:
                continue
            times[(pid, created)] = cpu_time
            before = prev.get((pid, created))
            cpu = (cpu_time - before) / (elapsed * 1e5 * self._ncpu) if valid and before is not None else 0.0
            key = name.lower()
            group = groups.get(key)
            if group is None:
                exe = self.exe_of(pid)
                group = groups[key] = {"name": name, "display": self.describe(exe, name), "exe": exe,
                                       "count": 0, "cpu": 0.0, "mem": 0, "app": False, "title": "",
                                       "protected": key in PROTECTED}
            group["count"] += 1
            group["cpu"] += max(0.0, cpu)
            group["mem"] += mem
            if pid in titles:
                group["app"] = True
                group["title"] = group["title"] or titles[pid]
        self._cpu_prev = (times, now)
        if valid:  # the first scan only primes the CPU counters
            rows = sorted(groups.values(), key=lambda g: -g["cpu"])
            for g in rows:
                g["cpu"] = round(min(100.0, g["cpu"]), 1)
            self.processes = {"ts": now, "groups": rows, "count": sum(g["count"] for g in rows)}

    def exe_of(self, pid, proc=None):
        exe = self._exe_cache.get(pid)
        if exe is None:
            try:
                exe = (proc or psutil.Process(pid)).exe()
            except (psutil.Error, OSError):
                exe = ""
            self._exe_cache[pid] = exe
        return exe

    def describe(self, exe, name):
        fallback = name[:-4] if name.lower().endswith(".exe") else name
        if not exe:
            return fallback
        if exe not in self._desc_cache:
            self._desc_cache[exe] = winapi.file_description(exe)
        return self._desc_cache[exe] or fallback

    def _active(self, names):
        fg = winapi.foreground_window()
        if not fg:
            return None
        pid = fg["pid"]
        name = names.get(pid, "")
        if not name:
            try:
                name = psutil.Process(pid).name()
            except psutil.Error:
                name = ""
        exe = self.exe_of(pid)
        title = fg["title"]
        lname = name.lower()
        if lname == "explorer.exe" and fg["cls"] in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd"):
            display, title = "Desktop", ""
        elif lname == "applicationframehost.exe":
            display = title or "Windows app"
        elif lname == "lockapp.exe":
            display, title = "Lock screen", ""
        else:
            display = self.describe(exe, name)
        return {"name": display, "process": name, "title": title if title != display else "", "exe": exe}

    def _net_rates(self, now):
        io = psutil.net_io_counters()
        rates = {"down": 0, "up": 0}
        if self._net:
            then, prev = self._net
            dt = max(0.001, now - then)
            rates = {"down": max(0, int((io.bytes_recv - prev.bytes_recv) / dt)),
                     "up": max(0, int((io.bytes_sent - prev.bytes_sent) / dt))}
        self._net = (now, io)
        return rates

    def _drive_usage(self, now):
        if now - self._drives_at > 15:
            drives = []
            for part in psutil.disk_partitions(all=False):
                if "fixed" not in part.opts:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                except OSError:
                    continue
                drives.append({"mount": part.mountpoint.rstrip("\\"), "total": usage.total,
                               "used": usage.used, "percent": usage.percent})
            self._drives, self._drives_at = drives, now
        return self._drives

    def _volume(self):
        try:
            return winapi.get_volume()
        except OSError:
            return None
