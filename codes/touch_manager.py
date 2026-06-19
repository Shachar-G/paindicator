from PyQt6.QtCore import QObject
import math

# Dead-zone thresholds — filter out sub-threshold noise from tablet digitiser jitter.
# Chuwi UBook XPro 13 (Windows 11) has ~4-5 px of high-frequency touch noise,
# so dead zones must be larger than typical to prevent visible shaking.
_ROT_DEAD_PX  = 5.0   # ignore rotation if pixel-space magnitude is below this
_SCALE_DEAD   = 0.04  # ignore pinch scale if within 1 ± this fraction
_PAN_DEAD_PX  = 5.0   # ignore pan if total displacement is below this

# EMA (Exponential Moving Average) smoothing for rotation.
# Lower alpha = more smoothing, less responsive to frame-to-frame noise.
# 0 = completely frozen (no motion passes through), 1 = raw unfiltered
_EMA_ALPHA = 0.3
_TWIST_DEAD_DEG = 2.0  # ignore twist if angular change is below this (degrees)


class TouchManager(QObject):
    """
    Handles multi-touch gestures for the VTK widget.

    Rules:
    - 1 finger: rotate (azimuth + elevation from dx/dy)
    - 2 fingers: pinch = zoom, midpoint translate = pan, twist = azimuth rotation
    - Fingers NEVER paint (painting is stylus/mouse only)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # Output values read by show_model.py after each TouchUpdate
        self.last_rotation_dx: float = 0.0
        self.last_rotation_dy: float = 0.0
        self.last_pinch_scale: float = 1.0
        self.last_pan_dx: float = 0.0
        self.last_pan_dy: float = 0.0
        self.last_twist_deg: float = 0.0
        # Manual position tracking — avoids unreliable lastPosition() on some tablet drivers
        self._prev_positions: dict = {}  # touch_id → (x, y)
        # EMA carry-over state for rotation smoothing
        self._smooth_rot_dx: float = 0.0
        self._smooth_rot_dy: float = 0.0
        # Previous inter-finger angle for twist computation
        self._prev_angle: float | None = None
        # Pan accumulator — sub-threshold per-frame motion is summed here instead of
        # being discarded, so slow drags (or fast digitisers reporting tiny per-frame
        # deltas) still pan once the running total crosses _PAN_DEAD_PX.
        self._pan_accum_x: float = 0.0
        self._pan_accum_y: float = 0.0

    def handle_touch_begin(self, event):
        self._reset()
        self._prev_angle = None
        self._pan_accum_x = 0.0
        self._pan_accum_y = 0.0
        self._prev_positions = {
            p.id(): (p.position().x(), p.position().y())
            for p in event.points()
        }

    def handle_touch_update(self, event):
        self._reset()
        points = event.points()
        curr = {p.id(): (p.position().x(), p.position().y()) for p in points}

        if len(points) == 1:
            p = points[0]
            pid = p.id()
            prev = self._prev_positions.get(pid, curr[pid])
            raw_dx = curr[pid][0] - prev[0]
            raw_dy = curr[pid][1] - prev[1]

            if math.hypot(raw_dx, raw_dy) >= _ROT_DEAD_PX:
                # EMA smoothing: blend raw delta with previous smoothed value
                self._smooth_rot_dx = _EMA_ALPHA * raw_dx + (1 - _EMA_ALPHA) * self._smooth_rot_dx
                self._smooth_rot_dy = _EMA_ALPHA * raw_dy + (1 - _EMA_ALPHA) * self._smooth_rot_dy
                self.last_rotation_dx = self._smooth_rot_dx
                self.last_rotation_dy = self._smooth_rot_dy
            else:
                # Below dead zone: decay EMA toward zero so it doesn't accumulate
                self._smooth_rot_dx *= (1 - _EMA_ALPHA)
                self._smooth_rot_dy *= (1 - _EMA_ALPHA)

        elif len(points) == 2:
            p1, p2 = points[0], points[1]
            id1, id2 = p1.id(), p2.id()

            # Zoom: ratio of current to previous finger distance
            curr_dist = math.hypot(
                curr[id1][0] - curr[id2][0],
                curr[id1][1] - curr[id2][1]
            )
            prev1 = self._prev_positions.get(id1, curr[id1])
            prev2 = self._prev_positions.get(id2, curr[id2])
            prev_dist = math.hypot(prev1[0] - prev2[0], prev1[1] - prev2[1])
            if prev_dist > 5.0:
                scale = curr_dist / prev_dist
                if abs(scale - 1.0) >= _SCALE_DEAD:
                    self.last_pinch_scale = scale

            # Pan: midpoint movement
            mx = (curr[id1][0] + curr[id2][0]) / 2
            my = (curr[id1][1] + curr[id2][1]) / 2
            pm_x = (prev1[0] + prev2[0]) / 2
            pm_y = (prev1[1] + prev2[1]) / 2
            pan_dx = mx - pm_x
            pan_dy = my - pm_y
            # Accumulate so sub-threshold per-frame motion is not lost (see __init__).
            self._pan_accum_x += pan_dx
            self._pan_accum_y += pan_dy
            if math.hypot(self._pan_accum_x, self._pan_accum_y) >= _PAN_DEAD_PX:
                self.last_pan_dx = self._pan_accum_x
                self.last_pan_dy = self._pan_accum_y
                self._pan_accum_x = 0.0
                self._pan_accum_y = 0.0

            # Twist: angular change between the two fingers.
            # Only reliable when fingers are far enough apart (≥30 px).
            if curr_dist > 30.0:
                curr_angle = math.degrees(math.atan2(
                    curr[id2][1] - curr[id1][1],
                    curr[id2][0] - curr[id1][0]
                ))
                if self._prev_angle is not None:
                    twist = curr_angle - self._prev_angle
                    # Normalize to [-180, 180] to handle angle wrap-around
                    if twist > 180:
                        twist -= 360
                    elif twist < -180:
                        twist += 360
                    if abs(twist) >= _TWIST_DEAD_DEG:
                        self.last_twist_deg = twist
                self._prev_angle = curr_angle

        self._prev_positions = curr

    def handle_touch_end(self, event):
        self._reset()
        self._prev_positions.clear()
        self._smooth_rot_dx = 0.0
        self._smooth_rot_dy = 0.0
        self._prev_angle = None
        self._pan_accum_x = 0.0
        self._pan_accum_y = 0.0

    def _reset(self):
        self.last_rotation_dx = 0.0
        self.last_rotation_dy = 0.0
        self.last_pinch_scale = 1.0
        self.last_pan_dx = 0.0
        self.last_pan_dy = 0.0
        self.last_twist_deg = 0.0
