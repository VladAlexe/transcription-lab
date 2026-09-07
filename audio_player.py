"""One persistent player for the original recording.

Verified against the installed packages: audio lives in `flet-audio` 0.86.1, not in `flet`
itself. `Audio` is a **Service** (attached through `page.services`, not `page.controls`) and
every transport method is a coroutine — `play(position)`, `pause()`, `resume()`, `seek(position)`
— so each one is dispatched through `page.run_task`.

The player holds no Flet imports of its own: the audio object and the task runner are injected,
which keeps seek arithmetic testable without a window.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

# Seeking must land on the real timestamp. Any pre-roll is a deliberate, small concession and
# is off by default; the guard below stops it ever creeping back up to the old one-second lead.
PRE_ROLL_SECONDS = 0.0
MAX_PRE_ROLL_SECONDS = 0.25

Runner = Callable[..., Any]


def to_milliseconds(seconds: float) -> int:
    """Absolute seconds from the transcript to the integer milliseconds the player expects."""
    return max(0, int(round(float(seconds) * 1000)))


def duration_to_ms(value: Any) -> int:
    """Flet reports positions as `Duration`; tests and older paths may pass a number."""
    if value is None:
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    total = (getattr(value, "days", 0) * 86400 + getattr(value, "hours", 0) * 3600
             + getattr(value, "minutes", 0) * 60 + getattr(value, "seconds", 0))
    return int(total * 1000 + getattr(value, "milliseconds", 0) + getattr(value, "microseconds", 0) / 1000)


def format_position(milliseconds: int) -> str:
    total = max(0, int(milliseconds // 1000))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"


class AudioPlayer:
    """Transport state plus the seek arithmetic. Rendering lives in components/audio_transport."""

    def __init__(self, audio: Any, runner: Runner, log: Callable[[str], None] | None = None,
                 pre_roll: float = PRE_ROLL_SECONDS,
                 factory: Callable[[str], Any] | None = None,
                 attach: Callable[[Any], None] | None = None,
                 detach: Callable[[Any], None] | None = None) -> None:
        self.audio = audio
        self.runner = runner
        # Assigning `src` to an already-attached Audio service never reaches the Flutter side:
        # the backend keeps no source, so on_loaded and on_duration_change never fire and the
        # first play() waits forever. With a factory the service is REPLACED per source, which
        # is the only form the backend actually loads. Measured, not assumed.
        self.factory = factory
        self.attach = attach
        self.detach = detach
        self.log = log or (lambda message: None)
        self.pre_roll = min(max(0.0, pre_roll), MAX_PRE_ROLL_SECONDS)
        self.path: str | None = None
        self.duration_ms = 0
        self.position_ms = 0
        self.playing = False
        self.on_change: Callable[[], None] | None = None
        self.on_position: Callable[[int], None] | None = None
        # Seconds to step back when pausing, so resuming catches the start of the word.
        # Inert by default; the application sets it from the researcher's preference.
        self.auto_rewind = 0.0
        # Set when pausing, spent when playback starts again. See `_take_owed_rewind`.
        self._rewind_owed = False
        self._started = False
        # Transport calls sent before the backend has opened the source block for ten seconds
        # and then raise. Requests made too early are remembered and replayed on on_loaded.
        # Without a factory (tests, legacy path) there is nothing to wait for.
        self.loaded = True
        self.speed = 1.0
        self._pending_ms: int | None = None
        self._pending_play = False
        self._wire(self.audio)
        self.log(f"[audio] player created (pre-roll {self.pre_roll:.3f}s, "
                 f"{'recreating' if factory else 'mutating'} the service per source)")

    # ── binding ──────────────────────────────────────────────────────────────
    @property
    def ready(self) -> bool:
        return self.path is not None

    def bind(self, path: str | None) -> bool:
        """Point the player at a recording. Returns False when the file is not there."""
        if not path:
            return False
        candidate = Path(path)
        if not candidate.is_file():
            return False
        resolved = str(candidate.resolve())
        self.log(f"[audio] loading src={resolved} ({candidate.stat().st_size} bytes)")
        if self.factory is not None:
            previous = self.audio
            fresh = self.factory(resolved)
            fresh.playback_rate = self.speed
            self._wire(fresh)
            if self.detach is not None and previous is not None:
                self.detach(previous)
            if self.attach is not None:
                self.attach(fresh)
            self.audio = fresh
            self.log("[audio] service rebuilt with the source set at construction")
        else:
            self.audio.src = resolved
            self._push()
        self.path = resolved
        self.duration_ms = 0
        self.position_ms = 0
        self.playing = False
        self._started = False
        self.loaded = self.factory is None
        self._pending_ms = None
        self._pending_play = False
        self.log("[audio] waiting for on_loaded / on_duration_change")
        self._changed()
        return True

    def unbind(self) -> None:
        if self.factory is not None and self.detach is not None and self.audio is not None:
            self.detach(self.audio)
        self.path = None
        self.playing = False
        self._started = False
        self.duration_ms = 0
        self.position_ms = 0

    # ── transport ────────────────────────────────────────────────────────────
    def seek(self, seconds: float, play: bool = True) -> int | None:
        """Move to an absolute position in the recording. Returns the milliseconds requested."""
        if not self.ready:
            return None
        target = max(0.0, float(seconds) - self.pre_roll)
        milliseconds = to_milliseconds(target)
        self.position_ms = milliseconds
        self.log(f"[audio] seek -> {milliseconds} ms (requested {seconds:.3f}s, pre-roll {self.pre_roll:.3f}s)")
        if not self.loaded:
            self._pending_ms = milliseconds
            self._pending_play = play
            self.log("[audio] source not open yet — queued until on_loaded")
            self._changed()
            return milliseconds
        self._rewind_owed = False
        if not self._started:
            # audioplayers needs a first play() to open the source; it takes the start position.
            self._started = True
            self.playing = play
            self.log(f"[audio] first play() issued at {milliseconds} ms")
            self.runner(self.audio.play, milliseconds)
            # ...which also starts it. Seeking while paused — skipping back to check a word,
            # clicking a turn to hear it — has to stay paused, and it did not: the
            # backend was playing while the interface said it was not, so the next play/pause
            # press appeared to do nothing at all.
            if not play:
                self.log("[audio] paused straight after opening the source")
                self.runner(self.audio.pause)
        else:
            self.log(f"[audio] seek() issued at {milliseconds} ms")
            self.runner(self.audio.seek, milliseconds)
            if play and not self.playing:
                self.playing = True
                self.runner(self.audio.resume)
        self._changed()
        return milliseconds

    def skip(self, delta_seconds: float) -> int | None:
        """Jump relative to where playback is now, clamped to the recording.

        The pre-roll is added back before seeking, so a ten second jump moves exactly ten
        seconds rather than ten minus the pre-roll. Playback state is preserved: skipping
        while paused leaves it paused, which is what a researcher checking a word expects.
        """
        if not self.ready:
            return None
        target = self.position_ms / 1000.0 + float(delta_seconds) + self.pre_roll
        if self.duration_ms:
            target = min(target, max(0.0, self.duration_ms / 1000.0 - .05))
        return self.seek(max(0.0, target), play=self.playing)

    def toggle(self) -> None:
        if not self.ready:
            return
        if not self.loaded:
            self._pending_ms = self.position_ms
            self._pending_play = True
            self.playing = True
            self.log("[audio] play queued until the source is open")
            self._changed()
            return
        if self.playing:
            self.playing = False
            self.runner(self.audio.pause)
            # The rewind is owed, not taken. Seeking backwards at the moment of pausing sent
            # a lower position to the interface, which followed it — so Ctrl+W sometimes
            # jumped to the previous turn instead of stopping, and always looked as though
            # the audio had run on for another second before it stopped. Pause stops here;
            # the step back happens when playback starts again, which is the only moment it
            # was ever for.
            self._rewind_owed = self.auto_rewind > 0 and self._started
        else:
            self._take_owed_rewind()
            self.playing = True
            if not self._started:
                self._started = True
                self.runner(self.audio.play, self.position_ms)
            else:
                self.runner(self.audio.resume)
        self._changed()

    def set_speed(self, rate: float) -> None:
        """Change the rate on the live service. Nothing reloads, nothing is lost.

        `src` genuinely has to be set at construction — that was established by bisection —
        and the rebuild that fact forced was wrongly applied to speed as well. Changing the
        rate therefore tore down the service and reloaded the recording: on a hundred-and-
        thirty-megabyte file, playback stopped, the position was restored by guesswork and
        the audio stuttered back to life. `playback_rate` is an ordinary property; it takes
        an update like any other.
        """
        rate = max(0.25, min(float(rate), 3.0))
        if rate == self.speed:
            return
        self.speed = rate
        if not self.ready or self.audio is None:
            return
        try:
            self.audio.playback_rate = rate
            self.audio.update()
            self.log(f"[audio] speed {rate:g}x applied in place at {self.position_ms} ms")
        except Exception as exc:
            # A rebuild is the fallback, not the plan: it costs the load and the position.
            self.log(f"[audio] speed {rate:g}x needs a rebuild ({exc})")
            position, playing, path = self.position_ms, self.playing, self.path
            self.unbind()
            if path and self.bind(path):
                self._pending_ms = position
                self._pending_play = playing
        self._changed()

    def _take_owed_rewind(self) -> None:
        """Step back the pre-roll owed from the last pause, just before resuming.

        Nothing is owed after a deliberate move — skipping, scrubbing, or clicking a turn
        already put the cursor where the researcher meant it to be, and stepping back from
        there would take the audio somewhere neither of them asked for.
        """
        from playback_sync import rewind_target
        if not self._rewind_owed:
            return
        self._rewind_owed = False
        if self.auto_rewind <= 0 or not self._started:
            return
        target = rewind_target(self.position_ms, self.auto_rewind)
        if target == self.position_ms:
            return
        self.position_ms = target
        self.log(f"[audio] auto-rewind {self.auto_rewind:g}s -> {target} ms on resume")
        self.runner(self.audio.seek, target)

    def scrub(self, milliseconds: int) -> None:
        """Dragging the scrubber: move without changing whether we are playing."""
        self.seek(max(0, int(milliseconds)) / 1000.0, play=self.playing)

    # ── events from the control ──────────────────────────────────────────────
    def handle_loaded(self, event: Any) -> None:
        self.log("[audio] on_loaded — the backend opened the source")
        self._release_pending()
        self._changed()

    def _release_pending(self) -> None:
        """The backend is ready: replay whatever the researcher asked for while it was loading."""
        first_time, self.loaded = not self.loaded, True
        if self._pending_ms is None:
            return
        milliseconds, play = self._pending_ms, self._pending_play
        self._pending_ms = None
        self.log(f"[audio] replaying queued request at {milliseconds} ms")
        self._started = True
        self.playing = play
        self.runner(self.audio.play, milliseconds)

    def handle_duration(self, event: Any) -> None:
        # Duration is the other proof the source opened; either event unblocks the transport.
        self._release_pending()
        self.duration_ms = duration_to_ms(getattr(event, "duration", None))
        self.log(f"[audio] on_duration_change -> {self.duration_ms} ms "
                 f"({format_position(self.duration_ms)})")
        self._changed()

    def handle_position(self, event: Any) -> None:
        self.position_ms = duration_to_ms(getattr(event, "position", None))
        if self.on_position:
            self.on_position(self.position_ms)
        self._changed()

    def handle_state(self, event: Any) -> None:
        state = str(getattr(event, "data", "") or getattr(event, "state", "")).lower()
        self.log(f"[audio] on_state_change -> {state or 'none'}")
        if "playing" in state:
            self.playing = True
        elif any(word in state for word in ("paused", "stopped", "completed", "disposed")):
            self.playing = False
        self._changed()

    # ── internals ────────────────────────────────────────────────────────────
    def _wire(self, audio: Any) -> None:
        """Every service the player owns reports back to the player, however it was created."""
        if audio is None:
            return
        audio.on_loaded = self.handle_loaded
        audio.on_duration_change = self.handle_duration
        audio.on_position_change = self.handle_position
        audio.on_state_change = self.handle_state

    def _push(self) -> None:
        try:
            self.audio.update()
        except Exception:
            # Not attached to a page yet (or under test); the value is already set on the control.
            pass

    def _changed(self) -> None:
        if self.on_change:
            self.on_change()
