"""Give the running window our own icon in the Windows taskbar and title bar.

`flet run` launches a prebuilt client executable, so the window inherits that executable's
icon. A built release picks up `assets/icon.png` instead, but during development — and for
anyone running from source — the icon has to be applied to the live window handle.

This is cosmetic and entirely optional: every call is guarded, and a failure leaves the
default icon in place rather than affecting the app.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

WM_SETICON = 0x0080
ICON_SMALL = 0
ICON_BIG = 1
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x00000010
LR_DEFAULTSIZE = 0x00000040
# Must match the --org passed to `flet build`, or Windows groups the built
# application under a different taskbar identity than the one running from source.
APP_MODEL_ID = "org.transcriptionlab.TranscriptionLab"


def set_app_model_id(app_id: str = APP_MODEL_ID) -> bool:
    """Group the window under our own taskbar identity rather than the host executable's."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        return True
    except Exception:
        return False


def apply_icon(title: str, ico_path: str | Path, attempts: int = 40, delay: float = 0.5,
               log=None) -> bool:
    """Find the window by title and attach the icon. Returns True once it is applied."""
    note = log or (lambda message: None)
    path = Path(ico_path)
    if not path.is_file():
        note(f"[icon] {path} not found; leaving the default icon")
        return False
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return False

    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = wintypes.HWND
    user32.LoadImageW.restype = wintypes.HANDLE

    for _ in range(attempts):
        handle = user32.FindWindowW(None, title)
        if handle:
            applied = False
            for size, flag in ((16, ICON_SMALL), (32, ICON_BIG)):
                image = user32.LoadImageW(None, str(path.resolve()), IMAGE_ICON, size, size,
                                          LR_LOADFROMFILE)
                if not image:
                    image = user32.LoadImageW(None, str(path.resolve()), IMAGE_ICON, 0, 0,
                                              LR_LOADFROMFILE | LR_DEFAULTSIZE)
                if image:
                    user32.SendMessageW(handle, WM_SETICON, flag, image)
                    applied = True
            note(f"[icon] applied to window '{title}'" if applied else "[icon] could not load the image")
            return applied
        time.sleep(delay)
    note(f"[icon] window '{title}' never appeared; leaving the default icon")
    return False


def apply_in_background(title: str, ico_path: str | Path, log=None) -> None:
    """The window does not exist yet at startup, so wait for it off the UI thread."""
    set_app_model_id()
    threading.Thread(target=apply_icon, args=(title, ico_path), kwargs={"log": log},
                     daemon=True).start()
