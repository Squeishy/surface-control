"""Win32 helpers built on ctypes only: windows, keyboard, audio, icons, power."""
import contextlib
import ctypes
import os
import struct
import time
import zlib
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32")
shell32 = ctypes.WinDLL("shell32")
dwmapi = ctypes.WinDLL("dwmapi")
version_dll = ctypes.WinDLL("version")
powrprof = ctypes.WinDLL("powrprof")
ole32 = ctypes.OleDLL("ole32")

ULONG_PTR = wintypes.WPARAM
WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
SW_RESTORE = 9
SW_SHOWNORMAL = 1
GW_OWNER = 4
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WM_CLOSE = 0x0010
WM_SYSCOMMAND = 0x0112
SC_MONITORPOWER = 0xF170
HWND_BROADCAST = 0xFFFF
DWMWA_CLOAKED = 14
ASFW_ANY = 0xFFFFFFFF
COINIT_MULTITHREADED = 0x0
COINIT_APARTMENTTHREADED = 0x2
CLSCTX_ALL = 0x17


class GUID(ctypes.Structure):
    _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]


class ICONINFO(ctypes.Structure):
    _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD), ("yHotspot", wintypes.DWORD),
                ("hbmMask", wintypes.HBITMAP), ("hbmColor", wintypes.HBITMAP)]


class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", wintypes.LONG), ("bmWidth", wintypes.LONG), ("bmHeight", wintypes.LONG),
                ("bmWidthBytes", wintypes.LONG), ("bmPlanes", wintypes.WORD),
                ("bmBitsPixel", wintypes.WORD), ("bmBits", ctypes.c_void_p)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD), ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 256)]


class SHFILEINFOW(ctypes.Structure):
    _fields_ = [("hIcon", wintypes.HICON), ("iIcon", ctypes.c_int), ("dwAttributes", wintypes.DWORD),
                ("szDisplayName", wintypes.WCHAR * 260), ("szTypeName", wintypes.WCHAR * 80)]


def _sig(fn, restype, *argtypes):
    fn.restype = restype
    fn.argtypes = argtypes


_sig(user32.GetForegroundWindow, wintypes.HWND)
_sig(user32.GetWindowTextLengthW, ctypes.c_int, wintypes.HWND)
_sig(user32.GetWindowTextW, ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
_sig(user32.GetClassNameW, ctypes.c_int, wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
_sig(user32.GetWindowThreadProcessId, wintypes.DWORD, wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
_sig(user32.IsWindowVisible, wintypes.BOOL, wintypes.HWND)
_sig(user32.IsIconic, wintypes.BOOL, wintypes.HWND)
_sig(user32.ShowWindow, wintypes.BOOL, wintypes.HWND, ctypes.c_int)
_sig(user32.SetForegroundWindow, wintypes.BOOL, wintypes.HWND)
_sig(user32.BringWindowToTop, wintypes.BOOL, wintypes.HWND)
_sig(user32.AttachThreadInput, wintypes.BOOL, wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
_sig(user32.AllowSetForegroundWindow, wintypes.BOOL, wintypes.DWORD)
_sig(user32.EnumWindows, wintypes.BOOL, WNDENUMPROC, wintypes.LPARAM)
_sig(user32.GetWindow, wintypes.HWND, wintypes.HWND, wintypes.UINT)
_sig(user32.GetWindowLongW, wintypes.LONG, wintypes.HWND, ctypes.c_int)
_sig(user32.PostMessageW, wintypes.BOOL, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
_sig(user32.SendInput, wintypes.UINT, wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
_sig(user32.MapVirtualKeyW, wintypes.UINT, wintypes.UINT, wintypes.UINT)
_sig(user32.keybd_event, None, wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ULONG_PTR)
_sig(user32.LockWorkStation, wintypes.BOOL)
_sig(user32.PrivateExtractIconsW, wintypes.UINT, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_int, ctypes.c_int,
     ctypes.POINTER(wintypes.HICON), ctypes.POINTER(wintypes.UINT), wintypes.UINT, wintypes.UINT)
_sig(user32.GetIconInfo, wintypes.BOOL, wintypes.HICON, ctypes.POINTER(ICONINFO))
_sig(user32.DestroyIcon, wintypes.BOOL, wintypes.HICON)
_sig(user32.GetDC, wintypes.HDC, wintypes.HWND)
_sig(user32.ReleaseDC, ctypes.c_int, wintypes.HWND, wintypes.HDC)
_sig(kernel32.GetCurrentThreadId, wintypes.DWORD)
_sig(gdi32.GetObjectW, ctypes.c_int, wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p)
_sig(gdi32.GetDIBits, ctypes.c_int, wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
     ctypes.c_void_p, ctypes.POINTER(BITMAPINFO), wintypes.UINT)
_sig(gdi32.DeleteObject, wintypes.BOOL, wintypes.HANDLE)
_sig(shell32.ShellExecuteW, wintypes.HINSTANCE, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR,
     wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_int)
_sig(shell32.SHGetFileInfoW, ULONG_PTR, wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(SHFILEINFOW),
     wintypes.UINT, wintypes.UINT)
_sig(shell32.SHGetKnownFolderPath, ctypes.HRESULT, ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE,
     ctypes.POINTER(ctypes.c_wchar_p))
_sig(dwmapi.DwmGetWindowAttribute, ctypes.c_long, wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)
_sig(version_dll.GetFileVersionInfoSizeW, wintypes.DWORD, wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD))
_sig(version_dll.GetFileVersionInfoW, wintypes.BOOL, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p)
_sig(version_dll.VerQueryValueW, wintypes.BOOL, ctypes.c_void_p, wintypes.LPCWSTR,
     ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT))
_sig(powrprof.SetSuspendState, wintypes.BOOLEAN, wintypes.BOOLEAN, wintypes.BOOLEAN, wintypes.BOOLEAN)
_sig(ole32.CLSIDFromString, ctypes.HRESULT, wintypes.LPCOLESTR, ctypes.POINTER(GUID))
_sig(ole32.CoInitializeEx, ctypes.HRESULT, ctypes.c_void_p, wintypes.DWORD)
_sig(ole32.CoUninitialize, None)
_sig(ole32.CoTaskMemFree, None, ctypes.c_void_p)
_sig(ole32.CoCreateInstance, ctypes.HRESULT, ctypes.POINTER(GUID), ctypes.c_void_p, wintypes.DWORD,
     ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_void_p))


def _guid(text):
    g = GUID()
    ole32.CLSIDFromString(text, ctypes.byref(g))
    return g


@contextlib.contextmanager
def com_apartment(mode=COINIT_APARTMENTTHREADED):
    """Initialise COM for the calling thread if it isn't already."""
    try:
        ole32.CoInitializeEx(None, mode)
        owned = True
    except OSError:  # already initialised in another mode: still usable
        owned = False
    try:
        yield
    finally:
        if owned:
            ole32.CoUninitialize()


# ------------------------------------------------------------------ windows

def window_text(hwnd):
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_pid(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _is_cloaked(hwnd):
    cloaked = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    return cloaked.value != 0


def list_windows():
    """Top-level windows a user would see in the taskbar, in z-order (front first)."""
    found = []

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd) or user32.GetWindow(hwnd, GW_OWNER):
            return True
        if user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & WS_EX_TOOLWINDOW or _is_cloaked(hwnd):
            return True
        title = window_text(hwnd)
        if title:
            found.append({"hwnd": hwnd, "pid": window_pid(hwnd), "title": title, "cls": window_class(hwnd)})
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return found


def foreground_window():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
    return {"hwnd": hwnd, "pid": window_pid(hwnd), "title": window_text(hwnd), "cls": window_class(hwnd)}


def focus_window(hwnd):
    """Bring a window to the front even though this server is a background process."""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    if user32.GetForegroundWindow() == hwnd:
        return True
    current = kernel32.GetCurrentThreadId()
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(fg_thread and fg_thread != current and user32.AttachThreadInput(current, fg_thread, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        if user32.GetForegroundWindow() != hwnd:
            # A synthetic Alt tap lifts the foreground lock Windows puts on background processes.
            user32.keybd_event(0x12, 0, KEYEVENTF_EXTENDEDKEY, 0)
            user32.keybd_event(0x12, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            user32.AttachThreadInput(current, fg_thread, False)
    for _ in range(10):
        if user32.GetForegroundWindow() == hwnd:
            return True
        time.sleep(0.02)
    return False


def close_window(hwnd):
    return bool(user32.PostMessageW(hwnd, WM_CLOSE, 0, 0))


# ----------------------------------------------------------------- keyboard

VK = {
    "ctrl": 0x11, "shift": 0x10, "alt": 0x12, "win": 0x5B, "tab": 0x09, "enter": 0x0D,
    "esc": 0x1B, "space": 0x20, "printscreen": 0x2C, "delete": 0x2E,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "volume_mute": 0xAD, "volume_down": 0xAE, "volume_up": 0xAF,
    "media_next": 0xB0, "media_prev": 0xB1, "media_stop": 0xB2, "media_playpause": 0xB3,
}
_EXTENDED = {0x5B, 0x5C, 0x2C, 0x2D, 0x2E, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
             0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3}


def _vk(name):
    if name in VK:
        return VK[name]
    if len(name) > 1 and name[0] == "f" and name[1:].isdigit():
        return 0x6F + int(name[1:])
    if len(name) == 1:
        return ord(name.upper())
    raise ValueError("Unknown key: %s" % name)


def _key(vk, up):
    flags = (KEYEVENTF_EXTENDEDKEY if vk in _EXTENDED else 0) | (KEYEVENTF_KEYUP if up else 0)
    ki = KEYBDINPUT(wVk=vk, wScan=user32.MapVirtualKeyW(vk, 0), dwFlags=flags)
    return INPUT(type=INPUT_KEYBOARD, u=_INPUTUNION(ki=ki))


def send_keys(*names):
    """Press a chord such as send_keys("ctrl", "shift", "p") on whatever window has focus."""
    codes = [_vk(n) for n in names]
    events = [_key(c, False) for c in codes] + [_key(c, True) for c in reversed(codes)]
    batch = (INPUT * len(events))(*events)
    return user32.SendInput(len(events), batch, ctypes.sizeof(INPUT)) == len(events)


# -------------------------------------------------------------------- audio

CLSID_MMDeviceEnumerator = _guid("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = _guid("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IAudioEndpointVolume = _guid("{5CDF2C82-841E-4546-9722-0CF74078229A}")


def _vcall(obj, index, argtypes, *args):
    vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    return ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, *argtypes)(vtable[index])(obj, *args)


def _release(obj):
    if obj and obj.value:
        vtable = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtable[2])(obj)


@contextlib.contextmanager
def _endpoint_volume():
    """IAudioEndpointVolume of the default playback device (raw COM vtable calls)."""
    with com_apartment(COINIT_MULTITHREADED):
        enum, dev, vol = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        try:
            ole32.CoCreateInstance(ctypes.byref(CLSID_MMDeviceEnumerator), None, CLSCTX_ALL,
                                   ctypes.byref(IID_IMMDeviceEnumerator), ctypes.byref(enum))
            # IMMDeviceEnumerator::GetDefaultAudioEndpoint(eRender, eMultimedia)
            _vcall(enum, 4, (ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)), 0, 1, ctypes.byref(dev))
            # IMMDevice::Activate
            _vcall(dev, 3, (ctypes.POINTER(GUID), wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)),
                   ctypes.byref(IID_IAudioEndpointVolume), CLSCTX_ALL, None, ctypes.byref(vol))
            yield vol
        finally:
            _release(vol)
            _release(dev)
            _release(enum)


def get_volume():
    with _endpoint_volume() as vol:
        level, muted = ctypes.c_float(), wintypes.BOOL()
        _vcall(vol, 9, (ctypes.POINTER(ctypes.c_float),), ctypes.byref(level))   # GetMasterVolumeLevelScalar
        _vcall(vol, 15, (ctypes.POINTER(wintypes.BOOL),), ctypes.byref(muted))   # GetMute
        return {"level": int(round(level.value * 100)), "muted": bool(muted.value)}


def set_volume(level=None, muted=None):
    with _endpoint_volume() as vol:
        if level is not None:
            level = max(0, min(100, int(level)))
            _vcall(vol, 7, (ctypes.c_float, ctypes.c_void_p), level / 100.0, None)  # SetMasterVolumeLevelScalar
            if muted is None and level > 0:
                muted = False
        if muted is not None:
            _vcall(vol, 14, (wintypes.BOOL, ctypes.c_void_p), bool(muted), None)     # SetMute


# -------------------------------------------------------------------- icons

def _png(width, height, rgba):
    stride = width * 4
    raw = b"".join(b"\x00" + bytes(rgba[y * stride:(y + 1) * stride]) for y in range(height))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _bitmap_bits(hdc, hbitmap, width, height):
    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = width
    info.bmiHeader.biHeight = -height  # top-down rows
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    buf = (ctypes.c_ubyte * (width * height * 4))()
    if not gdi32.GetDIBits(hdc, hbitmap, 0, height, buf, ctypes.byref(info), 0):
        return None
    return bytearray(buf)


def _hicon_to_png(hicon):
    info = ICONINFO()
    if not user32.GetIconInfo(hicon, ctypes.byref(info)):
        return None
    hdc = user32.GetDC(None)
    try:
        if not info.hbmColor:
            return None
        bm = BITMAP()
        gdi32.GetObjectW(info.hbmColor, ctypes.sizeof(bm), ctypes.byref(bm))
        w, h = bm.bmWidth, abs(bm.bmHeight)
        bgra = _bitmap_bits(hdc, info.hbmColor, w, h)
        if bgra is None:
            return None
        if not any(bgra[3::4]):  # legacy icon without alpha: derive it from the AND mask
            mask = _bitmap_bits(hdc, info.hbmMask, w, h) or bytearray(len(bgra))
            bgra[3::4] = bytes(0 if m else 255 for m in mask[0::4])
        rgba = bytearray(bgra)
        rgba[0::4], rgba[2::4] = bgra[2::4], bgra[0::4]
        return _png(w, h, rgba)
    finally:
        user32.ReleaseDC(None, hdc)
        if info.hbmColor:
            gdi32.DeleteObject(info.hbmColor)
        if info.hbmMask:
            gdi32.DeleteObject(info.hbmMask)


def icon_png(path, size=64):
    """PNG bytes of the icon for an exe/dll/ico (any size) or any other file/folder (32px)."""
    if not path or not os.path.exists(path):
        return None
    hicon = wintypes.HICON()
    if os.path.splitext(path)[1].lower() in (".exe", ".dll", ".ico"):
        icon_id = wintypes.UINT()
        if user32.PrivateExtractIconsW(path, 0, size, size, ctypes.byref(hicon), ctypes.byref(icon_id), 1, 0) != 1:
            hicon = wintypes.HICON()
    if not hicon:
        sfi = SHFILEINFOW()
        with com_apartment():
            shell32.SHGetFileInfoW(path, 0, ctypes.byref(sfi), ctypes.sizeof(sfi), 0x100)  # SHGFI_ICON | LARGEICON
        hicon = wintypes.HICON(sfi.hIcon)
    if not hicon:
        return None
    try:
        return _hicon_to_png(hicon)
    finally:
        user32.DestroyIcon(hicon)


def file_description(path):
    """The 'FileDescription' from an exe's version resource, e.g. 'Google Chrome'."""
    try:
        size = version_dll.GetFileVersionInfoSizeW(path, None)
        if not size:
            return None
        buf = ctypes.create_string_buffer(size)
        if not version_dll.GetFileVersionInfoW(path, 0, size, buf):
            return None
        ptr, length = ctypes.c_void_p(), wintypes.UINT()
        langs = []
        if version_dll.VerQueryValueW(buf, "\\VarFileInfo\\Translation", ctypes.byref(ptr), ctypes.byref(length)) \
                and length.value >= 4:
            langs.append(struct.unpack("<HH", ctypes.string_at(ptr.value, 4)))
        langs += [(0x0409, 0x04B0), (0x0409, 0x04E4), (0x0000, 0x04B0)]
        for lang, codepage in langs:
            key = "\\StringFileInfo\\%04x%04x\\FileDescription" % (lang, codepage)
            if version_dll.VerQueryValueW(buf, key, ctypes.byref(ptr), ctypes.byref(length)) and length.value > 1:
                text = ctypes.wstring_at(ptr.value, length.value - 1).strip()
                if text:
                    return text
    except OSError:
        pass
    return None


# --------------------------------------------------------------- processes

ntdll = ctypes.WinDLL("ntdll")
_sig(ntdll.NtQuerySystemInformation, ctypes.c_long, wintypes.ULONG, ctypes.c_void_p, wintypes.ULONG,
     ctypes.POINTER(wintypes.ULONG))
STATUS_INFO_LENGTH_MISMATCH = ctypes.c_long(0xC0000004).value


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", wintypes.USHORT), ("MaximumLength", wintypes.USHORT), ("Buffer", ctypes.c_void_p)]


class SYSTEM_PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("NextEntryOffset", wintypes.ULONG), ("NumberOfThreads", wintypes.ULONG),
        ("WorkingSetPrivateSize", ctypes.c_longlong), ("HardFaultCount", wintypes.ULONG),
        ("NumberOfThreadsHighWatermark", wintypes.ULONG), ("CycleTime", ctypes.c_ulonglong),
        ("CreateTime", ctypes.c_longlong), ("UserTime", ctypes.c_longlong), ("KernelTime", ctypes.c_longlong),
        ("ImageName", UNICODE_STRING), ("BasePriority", ctypes.c_long),
        ("UniqueProcessId", ctypes.c_void_p), ("InheritedFromUniqueProcessId", ctypes.c_void_p),
        ("HandleCount", wintypes.ULONG), ("SessionId", wintypes.ULONG), ("UniqueProcessKey", ctypes.c_size_t),
        ("PeakVirtualSize", ctypes.c_size_t), ("VirtualSize", ctypes.c_size_t), ("PageFaultCount", wintypes.ULONG),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
    ]


_snapshot_size = [512 * 1024]


def process_snapshot():
    """Every process in one syscall, like Task Manager does.

    Returns (pid, name, create_time, cpu_time_100ns, private_working_set) tuples. Much cheaper
    than psutil here, which falls back to a full system query per protected process.
    """
    while True:
        buf = ctypes.create_string_buffer(_snapshot_size[0])
        needed = wintypes.ULONG()
        status = ntdll.NtQuerySystemInformation(5, buf, len(buf), ctypes.byref(needed))  # SystemProcessInformation
        if status == STATUS_INFO_LENGTH_MISMATCH:
            _snapshot_size[0] = max(needed.value + 64 * 1024, _snapshot_size[0] * 2)
            continue
        if status < 0:
            raise OSError("NtQuerySystemInformation failed: 0x%08X" % (status & 0xFFFFFFFF))
        break
    found, offset = [], 0
    while True:
        info = SYSTEM_PROCESS_INFORMATION.from_buffer(buf, offset)
        pid = info.UniqueProcessId or 0
        if info.ImageName.Buffer:
            name = ctypes.wstring_at(info.ImageName.Buffer, info.ImageName.Length // 2)
        else:
            name = "System Idle Process" if pid == 0 else "System"
        found.append((pid, name, info.CreateTime, info.UserTime + info.KernelTime, info.WorkingSetPrivateSize))
        if not info.NextEntryOffset:
            return found
        offset += info.NextEntryOffset


# ------------------------------------------------------------------- shell

KNOWN_FOLDERS = {
    "desktop": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "documents": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "pictures": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "screenshots": "{B7BEDE81-DF94-4682-A7D8-57A52620B86F}",
}


def known_folder(name):
    out = ctypes.c_wchar_p()
    try:
        shell32.SHGetKnownFolderPath(ctypes.byref(_guid(KNOWN_FOLDERS[name])), 0, None, ctypes.byref(out))
        return out.value
    except OSError:
        return None
    finally:
        if out:
            ole32.CoTaskMemFree(out)


def shell_open(target, args=None, cwd=None):
    """Open anything Explorer could: exe, shortcut, folder, document or URL."""
    user32.AllowSetForegroundWindow(ASFW_ANY)
    with com_apartment():
        result = shell32.ShellExecuteW(None, "open", target, args or None, cwd or None, SW_SHOWNORMAL)
    return (result or 0) > 32


# -------------------------------------------------------------------- power

def lock_workstation():
    return bool(user32.LockWorkStation())


def suspend():
    return bool(powrprof.SetSuspendState(False, False, False))


def monitors_off():
    return bool(user32.PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2))
