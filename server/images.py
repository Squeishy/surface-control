"""Images the dashboard shows: background wallpapers and website logos for Quick Links."""
import base64
import hashlib
import html
import os
import re
import time
import urllib.parse
import urllib.request
import winreg

import config

CUSTOM_WALLPAPER = os.path.join(config.DATA_DIR, "wallpaper.img")
ICON_DIR = os.path.join(config.DATA_DIR, "icons")
MAX_UPLOAD = 15 * 1024 * 1024
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
_LINK_TAG = re.compile(r"<link\b[^>]*>", re.I)
_memory = {}  # icon key -> (bytes, content type) or None


def sniff(data):
    """Content type from magic bytes (the files we serve have no trustworthy extension)."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:2] == b"BM":
        return "image/bmp"
    if data[:4] == b"\x00\x00\x01\x00":
        return "image/x-icon"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    head = data[:1024].lstrip().lower()
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return "image/svg+xml"
    return None


# --------------------------------------------------------------- wallpapers

def pc_wallpaper_path():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop") as key:
            path = winreg.QueryValueEx(key, "WallPaper")[0]
        if path and os.path.isfile(path):
            return path
    except OSError:
        pass
    path = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Themes", "TranscodedWallpaper")
    return path if os.path.isfile(path) else None


def _version(path):
    try:
        return int(os.path.getmtime(path)) if path else 0
    except OSError:
        return 0


def versions():
    """Change stamps the UI puts in the image URL so a new wallpaper isn't served from cache."""
    return {"pc": _version(pc_wallpaper_path()), "custom": _version(CUSTOM_WALLPAPER)}


def read_wallpaper(source):
    path = pc_wallpaper_path() if source == "pc" else CUSTOM_WALLPAPER
    if not path or not os.path.isfile(path):
        return None, None
    with open(path, "rb") as f:
        data = f.read()
    ctype = sniff(data)
    return (data, ctype) if ctype in ("image/jpeg", "image/png", "image/gif", "image/bmp") else (None, None)


def save_wallpaper(data_url):
    match = re.match(r"^data:[\w/+.-]*;base64,(.*)$", data_url or "", re.S)
    if not match:
        raise ValueError("Ce fichier ne ressemble pas à une image.")
    raw = base64.b64decode(match.group(1))
    if len(raw) > MAX_UPLOAD:
        raise ValueError("Cette image dépasse 15 Mo.")
    if sniff(raw) not in ("image/jpeg", "image/png", "image/gif", "image/bmp"):
        raise ValueError("Utilisez une image JPEG ou PNG.")
    tmp = CUSTOM_WALLPAPER + ".tmp"
    with open(tmp, "wb") as f:
        f.write(raw)
    os.replace(tmp, CUSTOM_WALLPAPER)


# -------------------------------------------------------------- link icons

def _fetch(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    with urllib.request.urlopen(request, timeout=6) as response:
        return response.geturl(), response.read(limit)


def _attr(tag, name):
    match = re.search(r"""\b%s\s*=\s*("([^"]*)"|'([^']*)'|([^\s>]+))""" % name, tag, re.I)
    return html.unescape(match.group(2) or match.group(3) or match.group(4) or "") if match else ""


def _icon_candidates(page_url, page):
    """Icon URLs declared by a page, largest first (apple-touch-icon and SVG look best on big tiles)."""
    found = []
    for tag in _LINK_TAG.findall(page.decode("utf-8", "replace")):
        rel, href = _attr(tag, "rel").lower(), _attr(tag, "href")
        if not href or "icon" not in rel or "mask-icon" in rel:
            continue
        size = max([int(n) for n in re.findall(r"(\d+)x\d+", _attr(tag, "sizes"))] or [0])
        if "apple-touch-icon" in rel:
            size = max(size, 180)
        if href.split("?")[0].lower().endswith(".svg") or "svg" in _attr(tag, "type"):
            size = max(size, 256)
        found.append((size, urllib.parse.urljoin(page_url, href)))
    found.sort(key=lambda c: -c[0])
    return [url for _, url in found]


def link_icon(target):
    """Best logo for a web link, fetched once from the site and cached in data/icons."""
    if not re.match(r"^https?://", target or "", re.I):
        return None
    key = hashlib.sha1(target.encode("utf-8")).hexdigest()[:16]
    if key in _memory:
        return _memory[key]
    os.makedirs(ICON_DIR, exist_ok=True)
    path, miss = os.path.join(ICON_DIR, key + ".img"), os.path.join(ICON_DIR, key + ".none")
    if os.path.isfile(path):
        with open(path, "rb") as f:
            data = f.read()
        _memory[key] = (data, sniff(data))
        return _memory[key]
    if os.path.isfile(miss) and time.time() - os.path.getmtime(miss) < 86400:
        return None

    candidates, page_url = [], target
    try:
        page_url, page = _fetch(target, 512 * 1024)
        candidates = _icon_candidates(page_url, page)
    except Exception:
        pass
    for url in (page_url, target):
        parts = urllib.parse.urlsplit(url)
        candidates.append("%s://%s/favicon.ico" % (parts.scheme, parts.netloc))
    # Last resort for sites that block scripts (e.g. behind Cloudflare): Google's favicon service.
    candidates = candidates[:6] + ["https://www.google.com/s2/favicons?sz=128&domain=" +
                                   urllib.parse.urlsplit(target).netloc]
    for url in candidates:
        try:
            _, data = _fetch(url, 2 * 1024 * 1024)
        except Exception:
            continue
        ctype = sniff(data)
        if ctype and ctype != "image/webp":  # IE11 can't show WebP
            with open(path, "wb") as f:
                f.write(data)
            _memory[key] = (data, ctype)
            return _memory[key]
    open(miss, "w").close()
    _memory[key] = None
    return None
