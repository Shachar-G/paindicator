# codes/scale.py
# Global UI scale factor — computed once at startup based on primary screen size.
# Reference resolution: 1366x768 (small laptop / tablet target).
# On the reference screen scale == 1.0, so all sc() calls return the original values.
# On larger screens the scale grows proportionally (clamped to 2.0 max).

_REF_W: int = 1366
_REF_H: int = 768
_CLAMP_MIN: float = 0.85
_CLAMP_MAX: float = 2.0

_scale: float = 1.0


def init_scale(available_geometry) -> None:
    """
    Call once before MainWindow is created, passing
    QGuiApplication.primaryScreen().availableGeometry().
    Uses the minimum of the two axis ratios (letterbox strategy) so neither
    axis exceeds its proportional share.
    """
    global _scale
    w = available_geometry.width()
    h = available_geometry.height()
    raw = min(w / _REF_W, h / _REF_H)
    _scale = max(_CLAMP_MIN, min(_CLAMP_MAX, raw))


def get() -> float:
    """Return the current scale factor."""
    return _scale


def sc(value: int) -> int:
    """Scale an integer pixel/point value. Always returns at least 1."""
    return max(1, round(value * _scale))


def scf(value: float) -> float:
    """Scale a float value."""
    return value * _scale
