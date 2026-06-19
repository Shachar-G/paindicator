# codes/vtk_interactor_custom.py
# NOTE: All comments are in English only (as requested).

from __future__ import annotations
from typing import Dict, Tuple, Optional, List
import logging
import math
import time

import vtk


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
COLORS: Dict[int, Tuple[int, int, int]] = {
    0: (200, 200, 200),  # base gray (no pain)
    1: (255, 255, 0),    # yellow
    2: (255, 165, 0),    # orange
    3: (255, 0, 0),      # red
}

VALID_MODES = ("NONE", "VIEW", "MARK", "ERASE")

# Screen-space interpolation step in pixels.
# Picks are fired every N pixels between consecutive mouse events.
# Smaller = smoother strokes; 2px gives finer stylus strokes.
_SCREEN_INTERP_STEP_PX = 2

# Undo granularity: after this many pixels of drag, the current stroke chunk
# is pushed to the undo stack and a new chunk begins.
# This prevents a single long drag from being one monolithic undo entry.
# 30px ≈ 20 undo steps across a full-body stroke — fine enough to feel responsive.
_UNDO_GRANULARITY_PX = 30

# Zoom clamp: view angle limits in degrees (perspective camera, default 30°).
# 10° = ~3× zoom in from default; 60° = ~0.5× zoom out from default.
_VIEW_ANGLE_MIN = 10.0
_VIEW_ANGLE_MAX = 60.0

# Pan limit: focal point may drift up to this fraction of the model diagonal
# from model centre. 0.35 ≈ 35% of body height — enough to navigate any region
# while keeping the model from disappearing off-screen.
_PAN_LIMIT_FACTOR = 0.35


# ------------------------------------------------------------
# Input diagnostics (TEMPORARY)
# ------------------------------------------------------------
# Logs the Qt(logical) -> VTK(physical) coordinate conversion so picking
# accuracy under Windows display scaling can be verified on the target tablet.
# Writes to input_diag.log in the working directory (shared logger name with
# codes/screens/show_model.py). Changes NO behavior. Set False to disable.
# Disabled for production now that touch interaction is solved.
_INPUT_DIAG = False

_diag_logger_cache = None


def _diag_log(msg: str):
    """Append a line to input_diag.log. No-op if disabled or if logging fails."""
    if not _INPUT_DIAG:
        return
    global _diag_logger_cache
    try:
        if _diag_logger_cache is None:
            import os
            lg = logging.getLogger("input_diag")
            lg.setLevel(logging.DEBUG)
            lg.propagate = False  # keep diagnostics out of the root/basicConfig logs
            if not lg.handlers:
                fh = logging.FileHandler(
                    os.path.join(os.getcwd(), "input_diag.log"), encoding="utf-8"
                )
                fh.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
                lg.addHandler(fh)
            _diag_logger_cache = lg
        _diag_logger_cache.debug(msg)
    except Exception:
        pass


# ------------------------------------------------------------
# CustomInteractorStyle (Paint V2)
# ------------------------------------------------------------
class CustomInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):
    """
    Paint V2 interactor:
      - Per-vertex brush painting (radius-based) with drag support
      - Screen-space interpolation between cursor samples (no gaps when painting fast)
      - Prevent painting "through" the body using point normals + camera direction
      - Undo is per-stroke (true undo)
      - Keeps Trackball camera behavior for VIEW/NONE modes
      - Keyboard: R reset, arrow keys orientation
    """

    def __init__(
        self,
        renderer: vtk.vtkRenderer,
        render_window: vtk.vtkRenderWindow,
        interactor: vtk.vtkRenderWindowInteractor,
        actor: vtk.vtkActor,
        polydata: vtk.vtkPolyData,
        logger: Optional[logging.Logger] = None,
    ):
        super().__init__()

        self.renderer = renderer
        self.render_window = render_window
        self.interactor = interactor
        self.actor = actor
        self.polydata = polydata
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # -----------------------------
        # Mode / brush state
        # -----------------------------
        self.mode: str = "NONE"
        self.current_mark_level: int = 1

        self.n_points: int = int(self.polydata.GetNumberOfPoints())
        self.point_levels: List[int] = [0] * self.n_points

        self.undo_stack: List[Dict[int, int]] = []
        self._current_stroke: Optional[Dict[int, int]] = None

        self._left_button_down: bool = False
        self._right_button_down: bool = False
        self._is_injected_stroke: bool = False  # True when paint is driven by stylus/touch

        # Qt widget reference — used ONLY to read devicePixelRatioF() so that
        # injected (stylus/touch) coordinates, which arrive in Qt LOGICAL pixels,
        # can be converted to the PHYSICAL pixels VTK's render window expects.
        # Set by RendererScene right after construction. Mirrors how
        # renderer_scene.py reads devicePixelRatioF() for the L/R labels.
        self._qt_widget = None

        # Render throttling for paint strokes: cap render rate so that the
        # high-frequency touch digitiser does not force one full Render() of the
        # ~200k-vertex model per event. Picks/paints still happen every event;
        # only the (expensive) Render() is rate-limited, with a guaranteed flush
        # on stroke end so the last paint is never lost.
        self._RENDER_MIN_INTERVAL: float = 1.0 / 60.0  # ~60 fps cap during strokes
        self._last_render_time: float = 0.0
        self._pending_render: bool = False

        # Sampler for coordinate-conversion diagnostics (see _set_event_position_from_qt).
        self._diag_coord_count: int = 0

        # Optional callback — called after any wheel zoom so nav panel can sync its slider
        self._on_zoom_changed = None

        # Last screen-space position where a paint event was processed.
        # Stored as (x, y) in VTK display coordinates (origin = bottom-left).
        # Used for screen-space interpolation to prevent gaps on fast strokes.
        self._last_screen_pos: Optional[Tuple[int, int]] = None

        # Accumulated drag distance (pixels) within the current undo sub-stroke.
        # When this reaches _UNDO_GRANULARITY_PX, the sub-stroke is pushed to
        # the undo stack and a new one starts. Keeps undo steps manageable.
        self._stroke_distance_px: float = 0.0

        # -----------------------------
        # Ensure normals exist (needed to prevent painting through)
        # -----------------------------
        self._ensure_point_normals()

        # -----------------------------
        # Locator & picker
        # -----------------------------
        self.point_locator = vtk.vtkPointLocator()
        self.point_locator.SetDataSet(self.polydata)
        self.point_locator.BuildLocator()

        self.picker = vtk.vtkPointPicker()
        self.picker.SetTolerance(0.005)

        # -----------------------------
        # Adaptive brush radius (stable across model scale)
        # -----------------------------
        self.brush_radius = self._default_brush_radius()

        # Normal gating threshold: keep points whose normal faces camera enough.
        # Lower value = more permissive (0.05 lets near-edge vertices be painted,
        # improving stylus responsiveness at model edges).
        self._normal_gate_threshold = 0.05

        # -----------------------------
        # Camera baseline (make sure not sideways)
        # -----------------------------
        self._set_standard_camera_front()
        self._snapshot_initial_camera()

        # -----------------------------
        # Pan limit (derived from model bounds)
        # -----------------------------
        bounds = self.polydata.GetBounds()  # (xmin,xmax, ymin,ymax, zmin,zmax)
        self._model_center = (
            (bounds[0] + bounds[1]) * 0.5,
            (bounds[2] + bounds[3]) * 0.5,
            (bounds[4] + bounds[5]) * 0.5,
        )
        self._pan_limit = self.polydata.GetLength() * _PAN_LIMIT_FACTOR

        # -----------------------------
        # Initialize per-point colors
        # -----------------------------
        self._initialize_colors()

        # Attach this style
        self.interactor.SetInteractorStyle(self)

        # Observers
        self.AddObserver("LeftButtonPressEvent", self.OnLeftButtonDown)
        self.AddObserver("LeftButtonReleaseEvent", self.OnLeftButtonUp)
        self.AddObserver("MouseMoveEvent", self.OnMouseMove)
        self.AddObserver("KeyPressEvent", self._on_key_press)
        self.AddObserver("MouseWheelForwardEvent", self.OnMouseWheelForward)
        self.AddObserver("MouseWheelBackwardEvent", self.OnMouseWheelBackward)
        self.AddObserver("RightButtonPressEvent", self.OnRightButtonDown)
        self.AddObserver("RightButtonReleaseEvent", self.OnRightButtonUp)

        self.logger.info("[VTK] CustomInteractorStyle initialized (PaintV2).")

    # ------------------------------------------------------------
    # Normals
    # ------------------------------------------------------------
    def _ensure_point_normals(self):
        """Ensure polydata has point normals; compute if missing."""
        pd = self.polydata
        if pd is None:
            return

        normals = pd.GetPointData().GetNormals()
        if normals is not None and normals.GetNumberOfTuples() == pd.GetNumberOfPoints():
            return

        # Compute normals
        n = vtk.vtkPolyDataNormals()
        n.SetInputData(pd)
        n.ComputePointNormalsOn()
        n.ComputeCellNormalsOff()
        n.SplittingOff()
        n.ConsistencyOn()
        n.AutoOrientNormalsOn()
        n.Update()

        self.polydata = n.GetOutput()

    # ------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------
    def _snapshot_initial_camera(self):
        cam = self.renderer.GetActiveCamera()
        self._initial_camera_pos = cam.GetPosition()
        self._initial_camera_fp = cam.GetFocalPoint()
        self._initial_camera_vup = cam.GetViewUp()
        self._initial_view_angle = cam.GetViewAngle()

    def _set_standard_camera_front(self):
        """
        Force a stable 'front' camera so the model is not sideways.
        Z axis is treated as up.
        """
        if self.polydata is None:
            return

        bounds = self.polydata.GetBounds()
        cx = 0.5 * (bounds[0] + bounds[1])
        cy = 0.5 * (bounds[2] + bounds[3])
        cz = 0.5 * (bounds[4] + bounds[5])

        dx = bounds[1] - bounds[0]
        dy = bounds[3] - bounds[2]
        dz = bounds[5] - bounds[4]
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)

        cam = self.renderer.GetActiveCamera()
        cam.SetFocalPoint(cx, cy, cz)
        cam.SetViewUp(0.0, 0.0, 1.0)  # Z-up

        # Place camera along -Y looking at center (front view assumption)
        cam.SetPosition(cx - 2.2 * diag, cy, cz)
        cam.OrthogonalizeViewUp()

        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()

    def reset_camera(self):
        cam = self.renderer.GetActiveCamera()
        cam.SetPosition(*self._initial_camera_pos)
        cam.SetFocalPoint(*self._initial_camera_fp)
        cam.SetViewUp(*self._initial_camera_vup)
        cam.SetViewAngle(self._initial_view_angle)
        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        if self._on_zoom_changed:
            self._on_zoom_changed()

    def _clamp_zoom(self):
        """Clamp camera view angle to [_VIEW_ANGLE_MIN, _VIEW_ANGLE_MAX]."""
        cam = self.renderer.GetActiveCamera()
        angle = cam.GetViewAngle()
        clamped = max(_VIEW_ANGLE_MIN, min(_VIEW_ANGLE_MAX, angle))
        if clamped != angle:
            cam.SetViewAngle(clamped)

    def _clamp_camera_pan(self):
        """
        Prevent the model from being panned off-screen.
        Clamps the focal point to a sphere of radius _pan_limit around the
        model center. Camera position shifts by the same correction vector.
        """
        cam = self.renderer.GetActiveCamera()
        fp = cam.GetFocalPoint()
        pos = cam.GetPosition()
        mc = self._model_center

        offset = (fp[0] - mc[0], fp[1] - mc[1], fp[2] - mc[2])
        dist = math.sqrt(offset[0]**2 + offset[1]**2 + offset[2]**2)

        if dist <= self._pan_limit:
            return

        scale = self._pan_limit / dist
        new_fp = (mc[0] + offset[0] * scale,
                  mc[1] + offset[1] * scale,
                  mc[2] + offset[2] * scale)
        correction = (new_fp[0] - fp[0], new_fp[1] - fp[1], new_fp[2] - fp[2])
        cam.SetFocalPoint(*new_fp)
        cam.SetPosition(pos[0] + correction[0],
                        pos[1] + correction[1],
                        pos[2] + correction[2])

    def _apply_arrow_orientation(self, key_lower: str, cam: vtk.vtkCamera):
        """Arrow keys replicate legacy: left/right azimuth, up/down elevation."""
        step = 90
        if key_lower == "left":
            cam.Azimuth(-step)
        elif key_lower == "right":
            cam.Azimuth(step)
        elif key_lower == "up":
            cam.Elevation(step)
        elif key_lower == "down":
            cam.Elevation(-step)

        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()

    # ------------------------------------------------------------
    # Brush sizing
    # ------------------------------------------------------------
    def _default_brush_radius(self) -> float:
        if self.polydata is None:
            return 2.0
        b = self.polydata.GetBounds()
        dx = b[1] - b[0]
        dy = b[3] - b[2]
        dz = b[5] - b[4]
        diag = math.sqrt(dx * dx + dy * dy + dz * dz)
        return max(diag * 0.009, 1e-3)  # ~0.9% diag — slightly larger for stylus responsiveness

    # ------------------------------------------------------------
    # Colors
    # ------------------------------------------------------------
    def _initialize_colors(self):
        n = int(self.polydata.GetNumberOfPoints())
        colors = vtk.vtkUnsignedCharArray()
        colors.SetNumberOfComponents(3)
        colors.SetName("Colors")
        colors.SetNumberOfTuples(n)

        r, g, b = COLORS[0]
        for i in range(n):
            colors.SetTuple3(i, r, g, b)

        self.polydata.GetPointData().SetScalars(colors)
        self.colors = colors

        # Re-enable per-vertex coloring now that grey colors are set.
        # (ScalarVisibilityOff was set in RendererScene._initialize_scene to prevent
        #  the PLY's baked dermatome colors from flashing on screen.)
        if self.actor and self.actor.GetMapper():
            m = self.actor.GetMapper()
            m.ScalarVisibilityOn()
            m.SetColorModeToDirectScalars()

        self.polydata.Modified()
        self.render_window.Render()

    # ------------------------------------------------------------
    # Public API (Toolbar-compatible)
    # ------------------------------------------------------------
    def set_mode(self, mode: str):
        mode = (mode or "NONE").upper()
        if mode not in VALID_MODES:
            mode = "NONE"
        self.mode = mode
        self.logger.info(f"[VTK] Mode set to: {self.mode}")

    def toggle_mode(self, mode: str):
        mode = (mode or "NONE").upper()
        if self.mode == mode:
            return
        self.set_mode(mode)

    def set_mark_level(self, level: int):
        level = int(level)
        if 1 <= level <= 3:
            self.current_mark_level = level

    def clear_all(self):
        self.point_levels = [0] * int(self.polydata.GetNumberOfPoints())
        r, g, b = COLORS[0]
        for i in range(len(self.point_levels)):
            self.colors.SetTuple3(i, r, g, b)
        self.polydata.Modified()
        self.render_window.Render()
        self.undo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return
        last_stroke = self.undo_stack.pop()
        for pid, old_level in last_stroke.items():
            self._apply_point_level(pid, old_level, record=False)
        self.polydata.Modified()
        self.render_window.Render()

    # ------------------------------------------------------------
    # Inject API — called by stylus/touch (bypasses VTK mouse events)
    # ------------------------------------------------------------
    def _dpr(self) -> float:
        """Device-pixel ratio of the Qt widget (logical → physical px). 1.0 if unknown."""
        try:
            if self._qt_widget is not None:
                return float(self._qt_widget.devicePixelRatioF())
        except Exception:
            pass
        return 1.0

    def _set_event_position_from_qt(self, qt_x: int, qt_y: int):
        """
        Set the VTK interactor event position from Qt LOGICAL widget coordinates.

        Qt reports stylus/touch positions in logical pixels (top-left origin),
        while the VTK render window works in physical pixels (bottom-left origin).
        Apply the device-pixel ratio and flip Y so injected picks land exactly
        under the fingertip/pen on high-DPI displays.
        """
        dpr = self._dpr()
        phys_x = int(round(qt_x * dpr))
        phys_y = int(round(qt_y * dpr))
        vtk_y = self.render_window.GetSize()[1] - phys_y - 1
        self.interactor.SetEventPosition(phys_x, vtk_y)

        # Diagnostics only — log full at stroke start, sample during the stroke.
        if _INPUT_DIAG:
            self._diag_coord_count += 1
            if self._last_screen_pos is None or self._diag_coord_count % 10 == 0:
                _diag_log(
                    f"COORD qt=({qt_x},{qt_y}) dpr={dpr:.3f} "
                    f"phys=({phys_x},{phys_y}) vtk_y={vtk_y} "
                    f"win={tuple(self.render_window.GetSize())}"
                )

    def inject_paint_begin(self, qt_x: int, qt_y: int):
        """Start a paint stroke at Qt widget coordinates (stylus/touch → always MARK)."""
        self._is_injected_stroke = True
        self._left_button_down = True
        self._current_stroke = {}
        self._last_screen_pos = None
        self._stroke_distance_px = 0.0
        self._last_render_time = 0.0  # ensure the first dab renders immediately
        self._set_event_position_from_qt(qt_x, qt_y)
        self._paint_at_cursor_with_interpolation()

    def inject_paint_move(self, qt_x: int, qt_y: int):
        """Continue an active injected paint stroke."""
        if not self._left_button_down:
            return
        self._set_event_position_from_qt(qt_x, qt_y)
        self._paint_at_cursor_with_interpolation()

    def inject_paint_end(self):
        """End the injected paint stroke and push to undo stack."""
        if self._left_button_down and self._current_stroke:
            self.undo_stack.append(self._current_stroke)
        self._left_button_down = False
        self._is_injected_stroke = False
        self._current_stroke = None
        self._last_screen_pos = None
        self._stroke_distance_px = 0.0
        self._flush_pending_render()  # show the final segment of the stroke

    # ------------------------------------------------------------
    # Mouse wheel zoom (kept)
    # ------------------------------------------------------------
    def OnMouseWheelForward(self, obj=None, event=None):
        cam = self.renderer.GetActiveCamera()
        cam.Zoom(1.05)
        self._clamp_zoom()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        if self._on_zoom_changed:
            self._on_zoom_changed()

    def OnMouseWheelBackward(self, obj=None, event=None):
        cam = self.renderer.GetActiveCamera()
        cam.Zoom(0.95)
        self._clamp_zoom()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        if self._on_zoom_changed:
            self._on_zoom_changed()

    # ------------------------------------------------------------
    # Events
    # ------------------------------------------------------------
    def OnLeftButtonDown(self, obj=None, event=None):
        if self.mode not in ("MARK", "ERASE"):
            super().OnLeftButtonDown()
            return

        self._left_button_down = True
        self._current_stroke = {}
        self._last_screen_pos = None
        self._stroke_distance_px = 0.0
        self._last_render_time = 0.0  # ensure the first dab renders immediately
        self._paint_at_cursor_with_interpolation()

    def OnMouseMove(self, obj=None, event=None):
        # Right-drag always rotates
        if self._right_button_down:
            self.Rotate()
            self.render_window.Render()
            return

        if not self._left_button_down:
            super().OnMouseMove()
            self._clamp_camera_pan()
            return

        if self.mode not in ("MARK", "ERASE"):
            return

        self._paint_at_cursor_with_interpolation()

    def OnLeftButtonUp(self, obj=None, event=None):
        # Push any remaining sub-stroke that hasn't been flushed yet.
        if self._left_button_down and self._current_stroke:
            self.undo_stack.append(self._current_stroke)

        self._left_button_down = False
        self._current_stroke = None
        self._last_screen_pos = None
        self._stroke_distance_px = 0.0

        self._flush_pending_render()  # show the final segment of the stroke

        # IMPORTANT: release VTK internal mouse state
        super().OnLeftButtonUp()

    def OnMiddleButtonDown(self, obj=None, event=None):
        # Middle-button pan — standard 3D tool behavior
        super().OnMiddleButtonDown()

    def OnMiddleButtonUp(self, obj=None, event=None):
        super().OnMiddleButtonUp()

    def OnRightButtonDown(self, obj=None, event=None):
        # Right button always rotates (never zooms)
        self._right_button_down = True
        self.StartRotate()

    def OnRightButtonUp(self, obj=None, event=None):
        self._right_button_down = False
        self.EndRotate()

    # ------------------------------------------------------------
    # Core painting
    # ------------------------------------------------------------
    def _throttled_render(self):
        """
        Render at most once per _RENDER_MIN_INTERVAL.

        Decouples the render rate from the touch event rate so a fast finger
        stroke does not queue up one full-model Render() per digitiser report.
        If a render is skipped, _pending_render is set so the stroke-end handler
        flushes a final frame and the last paint is always shown.
        """
        now = time.monotonic()
        if now - self._last_render_time >= self._RENDER_MIN_INTERVAL:
            self.render_window.Render()
            self._last_render_time = now
            self._pending_render = False
        else:
            self._pending_render = True

    def _flush_pending_render(self):
        """Force a final render if one was throttled during the stroke."""
        if self._pending_render:
            self.render_window.Render()
            self._pending_render = False

    def _pick_world_point_at(self, x: int, y: int) -> Optional[Tuple[float, float, float]]:
        """Pick the nearest surface vertex at screen position (x, y)."""
        self.picker.Pick(x, y, 0, self.renderer)
        pid = self.picker.GetPointId()
        if pid < 0:
            return None
        return self.polydata.GetPoint(pid)

    def _pick_world_point(self) -> Optional[Tuple[float, float, float]]:
        """Pick the nearest surface vertex at the current cursor position."""
        x, y = self.interactor.GetEventPosition()
        return self._pick_world_point_at(x, y)

    def _paint_at_cursor_with_interpolation(self):
        """
        Paint at the current cursor, interpolating in screen space from the
        last painted position.

        Screen-space interpolation guarantees that every intermediate sample
        is a real surface pick — unlike world-space interpolation which can
        pass through the model interior and miss vertices entirely.
        """
        cx, cy = self.interactor.GetEventPosition()

        # First sample of this stroke: paint once and remember position.
        if self._last_screen_pos is None:
            world = self._pick_world_point_at(cx, cy)
            if world is not None:
                self._paint_at_world(world)
                self.polydata.Modified()
                self._throttled_render()
            self._last_screen_pos = (cx, cy)
            return

        ax, ay = self._last_screen_pos
        dx = cx - ax
        dy = cy - ay
        pixel_dist = math.sqrt(dx * dx + dy * dy)

        # No meaningful movement — just paint at current position.
        if pixel_dist < _SCREEN_INTERP_STEP_PX:
            world = self._pick_world_point_at(cx, cy)
            if world is not None:
                self._paint_at_world(world)
                self.polydata.Modified()
                self._throttled_render()
            self._last_screen_pos = (cx, cy)
            return

        # Interpolate along the screen-space segment and pick at each step.
        # Each pick lands on the visible surface, so the brush never cuts
        # through the body interior.
        painted_any = False
        steps = int(pixel_dist / _SCREEN_INTERP_STEP_PX) + 1
        for s in range(1, steps + 1):
            t = s / steps
            ix = int(ax + t * dx)
            iy = int(ay + t * dy)
            world = self._pick_world_point_at(ix, iy)
            if world is not None:
                self._paint_at_world(world)
                painted_any = True

        if painted_any:
            self.polydata.Modified()
            self._throttled_render()

        self._last_screen_pos = (cx, cy)

        # Undo granularity: after enough drag distance, flush the current
        # sub-stroke to the undo stack and start a fresh one.
        # This ensures one long drag produces several undo steps, not one.
        self._stroke_distance_px += pixel_dist
        if self._stroke_distance_px >= _UNDO_GRANULARITY_PX and self._current_stroke:
            self.undo_stack.append(self._current_stroke)
            self._current_stroke = {}
            self._stroke_distance_px = 0.0

    def _paint_at_world(self, world_pos: Tuple[float, float, float]):
        """
        Apply brush at a 3D world position.
        Finds all vertices within brush_radius and paints the ones facing the camera.
        Does NOT call Render — the caller is responsible for batching the render.
        """
        ids = vtk.vtkIdList()
        self.point_locator.FindPointsWithinRadius(self.brush_radius, world_pos, ids)
        if ids.GetNumberOfIds() <= 0:
            return

        cam = self.renderer.GetActiveCamera()
        cam_pos = cam.GetPosition()

        normals = self.polydata.GetPointData().GetNormals()

        for i in range(ids.GetNumberOfIds()):
            pid = ids.GetId(i)

            # Prevent painting through body: normal must face camera
            if normals is not None:
                nx, ny, nz = normals.GetTuple(pid)
                px, py, pz = self.polydata.GetPoint(pid)

                tx = cam_pos[0] - px
                ty = cam_pos[1] - py
                tz = cam_pos[2] - pz
                tlen = math.sqrt(tx * tx + ty * ty + tz * tz)
                if tlen > 1e-9:
                    tx /= tlen
                    ty /= tlen
                    tz /= tlen

                dot = nx * tx + ny * ty + nz * tz
                if dot < self._normal_gate_threshold:
                    continue

            # Erase (level 0) whenever ERASE mode is active — for mouse, finger,
            # AND stylus alike. Previously injected strokes (finger/stylus) were
            # forced to always mark, which made the Erase button do nothing under
            # touch. Mode is the single source of truth for paint vs. erase.
            level = 0 if self.mode == "ERASE" else self.current_mark_level
            self._apply_point_level(pid, level, record=True)

    def _apply_point_level(self, pid: int, level: int, record: bool = True):
        old = int(self.point_levels[pid])
        if old == level:
            return

        if record and self._current_stroke is not None and pid not in self._current_stroke:
            self._current_stroke[pid] = old

        self.point_levels[pid] = level
        r, g, b = COLORS[level]
        self.colors.SetTuple3(pid, r, g, b)

    # ------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------
    def _on_key_press(self, obj, event):
        """Keyboard shortcuts: R reset camera; arrows orientation."""
        key = self.interactor.GetKeySym()
        key_lower = key.lower() if key else ""

        if key_lower == "r":
            self.reset_camera()
            return

        cam = self.renderer.GetActiveCamera()
        if key_lower in ("left", "right", "up", "down"):
            self._apply_arrow_orientation(key_lower, cam)
            return
