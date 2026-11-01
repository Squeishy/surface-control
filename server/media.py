"""What's playing on the PC, via the Windows media controls: title, progress, seeking."""
import asyncio
import logging
import threading
import time

import winapi

try:
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
except ImportError:  # pip install winrt-runtime winrt-Windows.Media.Control winrt-Windows.Foundation
    SessionManager = None

log = logging.getLogger("media")
PLAYING, PAUSED = 4, 5


def _app_name(app_id):
    """'SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify' -> 'Spotify', 'brave.exe' -> 'brave'."""
    name = (app_id or "").split("!")[-1]
    return name[:-4] if name.lower().endswith(".exe") else name


class Media:
    def __init__(self):
        self.state = None
        self.loop = None
        self._manager = None
        self._props = {"title": "", "artist": ""}
        self._props_key = None
        self._props_at = 0

    @property
    def available(self):
        return SessionManager is not None

    def start(self):
        if not self.available:
            log.info("winrt not installed: no now-playing bar")
            return
        threading.Thread(target=self._run, name="media", daemon=True).start()

    def _run(self):
        with winapi.com_apartment(winapi.COINIT_MULTITHREADED):
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._watch())

    async def _watch(self):
        while True:
            try:
                if self._manager is None:
                    self._manager = await SessionManager.request_async()
                self.state = await self._read()
            except Exception:
                log.exception("reading the media session failed")
                self.state, self._manager = None, None
                await asyncio.sleep(4)
            await asyncio.sleep(1)

    async def _read(self):
        session = self._manager.get_current_session()
        if session is None:
            return None
        info = session.get_playback_info()
        status = int(info.playback_status)
        if status not in (PLAYING, PAUSED):
            return None
        timeline = session.get_timeline_properties()
        start = timeline.start_time.total_seconds()
        duration = timeline.end_time.total_seconds() - start
        now = time.time()
        # Titles are an async call: refresh on a new track/app, otherwise every few seconds.
        key = (session.source_app_user_model_id, round(duration))
        if key != self._props_key or now - self._props_at > 3:
            props = await session.try_get_media_properties_async()
            self._props = {"title": props.title or "", "artist": props.artist or ""}
            self._props_key, self._props_at = key, now
        # Apps only report the position when it changes state; extrapolate while playing.
        position = timeline.position.total_seconds() - start
        if status == PLAYING and timeline.last_updated_time is not None:
            elapsed = now - timeline.last_updated_time.timestamp()
            if 0 < elapsed < 86400:
                position += elapsed * (info.playback_rate or 1.0)
        if duration > 0:
            position = max(0.0, min(duration, position))
        return {"title": self._props["title"], "artist": self._props["artist"],
                "app": _app_name(session.source_app_user_model_id), "playing": status == PLAYING,
                "position": round(position, 1), "duration": round(max(0.0, duration), 1),
                "seekable": bool(info.controls.is_playback_position_enabled) and duration > 0,
                "at": round(now, 2)}  # when `position` was true; the tablet advances it locally

    def seek(self, seconds):
        if not self.loop or not self._manager:
            return False
        return asyncio.run_coroutine_threadsafe(self._seek(seconds), self.loop).result(timeout=5)

    async def _seek(self, seconds):
        session = self._manager.get_current_session()
        if session is None:
            return False
        start = session.get_timeline_properties().start_time.total_seconds()
        ok = await session.try_change_playback_position_async(int((start + max(0.0, seconds)) * 10000000))
        self.state = await self._read()
        return bool(ok)
