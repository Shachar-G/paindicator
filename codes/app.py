# codes/app.py
import sys
import os
import subprocess
import time
from PyQt6.QtWidgets import QApplication, QLineEdit, QTextEdit, QAbstractSpinBox
from PyQt6.QtCore import QObject, QEvent, QTimer
from PyQt6.QtGui import QIcon
from codes.ui_main import MainWindow
from codes.session_manager import SessionManager  # ← הוספנו שורה זו


def _get_app_icon() -> QIcon:
    if hasattr(sys, "_MEIPASS"):
        base = os.path.join(sys._MEIPASS, "files", "pictures")
    else:
        base = os.path.join(os.path.dirname(__file__), "..", "files", "pictures")
    path = os.path.join(base, "HD Logo.png")

    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt
    px = QPixmap(path)
    if px.isNull():
        return QIcon()
    # Center the rectangular logo on a transparent square canvas
    side = max(px.width(), px.height())
    square = QPixmap(side, side)
    square.fill(Qt.GlobalColor.transparent)
    from PyQt6.QtGui import QPainter
    p = QPainter(square)
    p.drawPixmap((side - px.width()) // 2, (side - px.height()) // 2, px)
    p.end()
    return QIcon(square)


_last_kb_show_time: float = 0.0  # module-level debounce timestamp


def _show_touch_keyboard():
    """
    Open the Windows touch keyboard for tablet use (Chuwi and similar devices).

    Strategy (Windows 10/11):
    1. ITipInvocation COM interface — the correct Win10/11 mechanism (pure ctypes).
    2. Try Qt's built-in input method — works when the platform plugin supports it.
    3. Find the TabTip window by its known class names and show it.
    4. If not found, launch TabTip.exe (Windows 10 path) and then show it.
    5. Fallback to OSK.
    """
    if sys.platform != "win32":
        return

    # Debounce: ignore rapid successive calls within 500 ms.
    # This prevents a double-toggle when FocusIn + MouseButtonPress both fire
    # on the same tap (which would open then immediately close the keyboard).
    global _last_kb_show_time
    now = time.monotonic()
    if now - _last_kb_show_time < 0.5:
        return
    _last_kb_show_time = now

    _NO_WINDOW = 0x08000000  # CREATE_NO_WINDOW — hides the console flash

    # --- Strategy 1: ITipInvocation COM interface (Windows 10/11 primary path) ---
    # This is the documented API for invoking the touch keyboard programmatically.
    # CLSID_UIHostNoLaunch = {4CE576FA-83DC-4F88-951C-9D0782B4E376}
    # IID_ITipInvocation  = {37C994E7-432B-4834-A2F7-DCE1F13B834B}
    # The interface has one method beyond IUnknown: Toggle(hwndDesktop).
    try:
        import ctypes

        class _GUID(ctypes.Structure):
            _fields_ = [
                ("Data1", ctypes.c_ulong),
                ("Data2", ctypes.c_ushort),
                ("Data3", ctypes.c_ushort),
                ("Data4", ctypes.c_ubyte * 8),
            ]

        ole32 = ctypes.windll.ole32
        user32 = ctypes.windll.user32

        clsid, iid = _GUID(), _GUID()
        ole32.CLSIDFromString("{4CE576FA-83DC-4F88-951C-9D0782B4E376}", ctypes.byref(clsid))
        ole32.CLSIDFromString("{37C994E7-432B-4834-A2F7-DCE1F13B834B}", ctypes.byref(iid))

        ppv = ctypes.c_void_p(0)
        hr = ole32.CoCreateInstance(
            ctypes.byref(clsid), None, 4,  # CLSCTX_LOCAL_SERVER = 4
            ctypes.byref(iid), ctypes.byref(ppv)
        )
        if hr >= 0 and ppv.value:
            # Navigate COM vtable: [0]=QueryInterface, [1]=AddRef, [2]=Release, [3]=Toggle
            vtbl_addr = ctypes.c_void_p.from_address(ppv.value).value
            vtbl = (ctypes.c_void_p * 4).from_address(vtbl_addr)
            Toggle = ctypes.WINFUNCTYPE(
                ctypes.HRESULT, ctypes.c_void_p, ctypes.c_void_p
            )(vtbl[3])
            Toggle(ppv.value, user32.GetDesktopWindow())
            Release = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
            Release(ppv.value)
            return  # success — no further strategies needed
    except Exception:
        pass

    # --- Strategy 2: Qt-native path (works on some Windows tablet configurations) ---
    try:
        from PyQt6.QtCore import QCoreApplication
        im = QCoreApplication.instance().inputMethod()
        if im:
            im.show()
    except Exception:
        pass

    # --- Strategy 3: Win32 path: find or launch TabTip ---
    try:
        import ctypes
        user32 = ctypes.windll.user32

        # Class names for the touch keyboard on different Windows versions
        _KB_CLASSES = [
            "IPTIP_Main_Window",        # Windows 10 (most devices)
            "IPTip_Main_Window",        # alternative spelling seen on some OEMs
            "TF_FloatyWnd_Class",       # Windows 11 touch keyboard floating mode
        ]

        def _find_kb_window():
            for cls in _KB_CLASSES:
                hwnd = user32.FindWindowW(cls, None)
                if hwnd:
                    return hwnd
            return 0

        hwnd = _find_kb_window()
        if hwnd:
            # Show and bring to front
            SW_SHOW, SW_RESTORE = 5, 9
            user32.ShowWindow(hwnd, SW_RESTORE)
            user32.SetForegroundWindow(hwnd)
            return

        # Windows 10 fallback: launch TabTip.exe (common locations)
        # NOTE: the explorer.exe shell:AppsFolder URI for Windows 11 touch keyboard
        # was removed — it silently falls back to opening Documents when the URI
        # isn't recognised, causing Explorer windows to open on every text focus.
        _tabtip_paths = [
            r"C:\Program Files\Common Files\Microsoft Shared\ink\TabTip.exe",
            r"C:\Program Files (x86)\Common Files\Microsoft Shared\ink\TabTip.exe",
        ]
        launched = False
        for p in _tabtip_paths:
            if os.path.exists(p):
                subprocess.Popen([p], creationflags=_NO_WINDOW)
                launched = True
                break

        if not launched:
            # Last resort: on-screen keyboard
            subprocess.Popen("osk.exe", shell=True, creationflags=_NO_WINDOW)
    except Exception:
        pass


def _hide_touch_keyboard():
    """Close the touch keyboard by sending WM_CLOSE to the known keyboard window."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        user32 = ctypes.windll.user32
        WM_CLOSE = 0x0010
        for cls in ["IPTIP_Main_Window", "IPTip_Main_Window", "TF_FloatyWnd_Class"]:
            hwnd = user32.FindWindowW(cls, None)
            if hwnd and user32.IsWindowVisible(hwnd):
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
                return
    except Exception:
        pass


class TouchKeyboardFilter(QObject):
    """
    Application-level event filter: opens/closes the Windows touch keyboard
    based on text-widget focus and tap events.
    """
    _TEXT_TYPES = (QLineEdit, QTextEdit, QAbstractSpinBox)

    def eventFilter(self, obj, event):
        etype = event.type()

        # Show keyboard: on first focus (FocusIn) OR re-tap when already focused (MouseButtonPress).
        # The 500ms debounce in _show_touch_keyboard prevents the double-call that would
        # otherwise happen when both events fire together on the same tap.
        if etype in (QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress):
            if isinstance(obj, self._TEXT_TYPES):
                if not getattr(obj, 'isReadOnly', lambda: False)():
                    _show_touch_keyboard()

        # Hide keyboard when focus leaves all text inputs
        elif etype == QEvent.Type.FocusOut and isinstance(obj, self._TEXT_TYPES):
            def _check_hide():
                from PyQt6.QtWidgets import QApplication as _App
                fw = _App.focusWidget()
                if not isinstance(fw, self._TEXT_TYPES):
                    _hide_touch_keyboard()
            QTimer.singleShot(50, _check_hide)

        return False  # never consume events


def main():
    """
    Initializes and runs the QApplication. This is the sole entry point.
    """
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # ensures border-radius in stylesheets works on Windows
    app.setWindowIcon(_get_app_icon())

    # Show platform touch keyboard on text-widget focus (touchscreen support)
    _kb_filter = TouchKeyboardFilter()
    app.installEventFilter(_kb_filter)

    # --- Create the global SessionManager instance ---
    session_manager = SessionManager()

    # --- Init responsive scale factor based on primary screen size ---
    from PyQt6.QtGui import QGuiApplication
    from codes import scale as _scale_mod
    _primary = QGuiApplication.primaryScreen()
    if _primary:
        _scale_mod.init_scale(_primary.availableGeometry())

    # --- Create Main Window ---
    window = MainWindow(session_manager=session_manager)

    # Use maximized window instead of delayed timer/start()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
