"""
RendererScene: robust, modular VTK scene manager for PAINDICATOR.
Handles 3D model rendering, camera control, painting/erasing, and toolbar interaction
through the CustomInteractorStyle class.
"""
import os
import sys
import math
import json
import logging
import datetime

import vtk
from vtkmodules.vtkIOPLY import vtkPLYReader
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkActor, vtkPolyDataMapper
from codes.vtk_interactor_custom import CustomInteractorStyle
from codes.dermatome_mapper import DermatomeMapper

log_path = os.path.join(os.getcwd(), "paindicator_debug.log")
logging.basicConfig(
    filename=log_path,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger(__name__)


def compute_pan_motion(renderer, camera, dx_phys, dy_phys):
    """
    Convert a screen-pixel pan delta into a world-space motion vector for the
    camera focal point, evaluated at the focal-point depth.

    dx_phys, dy_phys are in PHYSICAL pixels (device-pixel-ratio already applied),
    with dy following the Qt convention (y increases downward).

    Mirrors vtkInteractorStyleTrackballCamera::Pan: it uses the renderer's
    display<->world transform, so the result is automatically scale-correct for
    any model size and zoom level (no hard-coded distance constant). Pure function
    of (renderer, camera) — kept module-level so it can be unit-tested headlessly.
    """
    fp = list(camera.GetFocalPoint())

    # Focal point in display coordinates (preserve its depth/Z).
    renderer.SetWorldPoint(fp[0], fp[1], fp[2], 1.0)
    renderer.WorldToDisplay()
    disp = renderer.GetDisplayPoint()

    # Where the focal point should map to after the drag. Subtracting the finger
    # delta makes the scene follow the fingers (drag up -> view moves up). Qt y is
    # top-left/down while VTK display y is bottom-left/up, hence the +dy_phys.
    renderer.SetDisplayPoint(disp[0] - dx_phys, disp[1] + dy_phys, disp[2])
    renderer.DisplayToWorld()
    w = list(renderer.GetWorldPoint())
    if w[3] != 0.0:
        w = [w[0] / w[3], w[1] / w[3], w[2] / w[3]]

    return (w[0] - fp[0], w[1] - fp[1], w[2] - fp[2])


class RendererScene:
    """
    Core VTK rendering environment for the PAINDICATOR application.
    Handles model loading, renderer setup, interactor behavior, and toolbar API.

    All interactive behavior (painting, erasing, camera reset, etc.)
    is implemented in CustomInteractorStyle.
    """

    def __init__(self, parent, model_path, session_manager=None, initial_azimuth=0):
        super().__init__()
        print("[DEBUG] RendererScene __init__ started")
        self.session_manager = session_manager

        self.logger = logging.getLogger(self.__class__.__name__)
        self.vtk_widget = parent
        self.model_path = self._resolve_model_path(model_path)

        # Base VTK components
        self.renderer = None
        self.render_window = None
        self.interactor = None
        self.mapper = None
        self.actor = None
        self.polydata = None
        self.interactor_style = None
        # Dermatome mapping (loaded only when needed, e.g., clinician view)
        self.dermatome_mapper = None
        # Explicit dermatome map file paths (override default models-dir lookup)
        self._derm_map_bin = None
        self._derm_map_meta = None
        # Dermatome overlay (optional second actor)
        self._derm_overlay_path = None
        self._derm_actor = None
        self._derm_visible = False
        # Dermatome swap actor: second actor used to toggle between
        # plain-model view and dermatome-region view (clinician only).
        self._derm_swap_actor = None
        self._point_locator = None      # built lazily, cached for dermatome picking
        self._comparison_actor = None   # transparent overlay for session comparison
        self._lr_vtk_actors = {}        # vtkTextActor badges for L/R orientation labels

        # Initialize full VTK pipeline
        self._initialize_scene()

        # Apply per-model initial camera rotation (e.g. female model faces a different axis)
        if initial_azimuth != 0:
            self._apply_initial_azimuth(initial_azimuth)

        self.logger.info("[RendererScene] Initialized successfully.")

    # ------------------------------------------------------------------
    # Scene setup and initialization
    # ------------------------------------------------------------------
    from codes.config import get_base_models_path

    def _resolve_model_path(self, path: str) -> str:
        """
        Resolve full path to the model file using the centralized config.
        Only the filename is expected; the base directory is determined by config.
        """
        # If the incoming path is absolute and exists → use it as-is.
        if os.path.isabs(path) and os.path.exists(path):
            return path

        # Otherwise assume a filename and attach to the model base directory
        base_dir = get_base_models_path()
        filename = os.path.basename(path)
        resolved = os.path.join(base_dir, filename)

        return resolved

    def _initialize_scene(self):
        """Build the entire VTK rendering environment."""
        self.logger.info(f"[RendererScene] Loading model: {self.model_path}")
        print(f"[DEBUG] MODEL PATH REQUESTED: {self.model_path}")
        print(f"[DEBUG] FILE EXISTS? {os.path.exists(self.model_path)}")

        # --- Renderer ---
        self.renderer = vtkRenderer()
        # Gradient background: pale blue top → slate gray bottom (depth effect)
        self.renderer.GradientBackgroundOn()
        self.renderer.SetBackground(0.541, 0.600, 0.671)   # bottom/corners: slate #8A99AB
        self.renderer.SetBackground2(0.749, 0.831, 0.902)  # top/center: pale blue #BFD4E6

        # --- Render Window (from QVTK widget) ---
        self.render_window = self.vtk_widget.GetRenderWindow()
        self.render_window.AddRenderer(self.renderer)

        # --- Interactor ---
        self.interactor = self.render_window.GetInteractor()

        # --- Model Loading ---
        if not os.path.exists(self.model_path):
            self.logger.error(f"[RendererScene] Model not found: {self.model_path}")
            return
        print("[DEBUG] Loading model from:", self.model_path)

        reader = vtkPLYReader()
        reader.SetFileName(self.model_path)
        reader.Update()
        print("[DEBUG] Model loaded, building mapper…")

        self.polydata = reader.GetOutput()

        # Strip any baked vertex colors from the PLY before the mapper is created.
        # This prevents the dermatome color scheme from ever being shown to the patient
        # or as the clinician's default view. The interactor will write grey scalars.
        _active = self.polydata.GetPointData().GetScalars()
        if _active is not None:
            self.polydata.GetPointData().RemoveArray(_active.GetName())

        # --- Mapper ---
        self.mapper = vtkPolyDataMapper()
        self.mapper.SetInputData(self.polydata)
        # ScalarVisibilityOff until _initialize_colors() sets the grey base scalars.
        self.mapper.ScalarVisibilityOff()

        # --- Actor ---
        self.actor = vtkActor()
        self.actor.SetMapper(self.mapper)
        # Grey property color shown during the brief window before scalars are set.
        self.actor.GetProperty().SetColor(200/255.0, 200/255.0, 200/255.0)
        self.renderer.AddActor(self.actor)

        # --- Camera ---
        self.renderer.ResetCamera()
        cam = self.renderer.GetActiveCamera()
        cam.Zoom(1)
        self.camera = cam
        self.logger.debug("[RendererScene] Camera initialized.")

        # --- Interactor Style ---
        self.interactor_style = CustomInteractorStyle(
            renderer=self.renderer,
            render_window=self.render_window,
            interactor=self.interactor,
            actor=self.actor,
            polydata=self.polydata,
            logger=self.logger,
        )

        # Give the style a handle to the Qt widget so injected (stylus/touch)
        # coordinates can be device-pixel-ratio corrected (logical → physical px).
        self.interactor_style._qt_widget = self.vtk_widget

        # _ensure_point_normals() inside CustomInteractorStyle may have produced a NEW
        # polydata object (vtkPolyDataNormals output). If so, the mapper must be updated
        # to point at the same object the interactor paints on — otherwise paint strokes
        # and apply_saved_marks() are invisible in the render.
        if self.interactor_style.polydata is not self.polydata:
            self.polydata = self.interactor_style.polydata
            self.mapper.SetInputData(self.polydata)
            self.mapper.Modified()
            self.logger.debug("[RendererScene] Mapper resynced to interactor polydata after normals pass.")

        # Ensure stable camera orientation (not sideways)
        if hasattr(self.interactor_style, "reset_camera"):
            self.interactor_style.reset_camera()

        # Attach interactor style
        self.interactor.SetInteractorStyle(self.interactor_style)
        self.interactor.Initialize()

        # --- Compute L/R world positions for Qt overlay labels ---
        self._setup_lr_marker_positions()

        # Ensure initial render
        self.render_window.Render()
        self.logger.info("[RendererScene] Scene setup complete.")

    # ------------------------------------------------------------------
    # L/R side marker badges — rendered as VTK 2D actors (no Qt compositing)
    # ------------------------------------------------------------------
    def _setup_lr_marker_positions(self):
        """
        Compute fixed 3D world positions for the L/R side labels.

        Both models use initial_azimuth=90: after that rotation the camera sits
        at the -Y side of the model looking in +Y.  Screen-right = +X.
        The patient faces the camera (-Y direction), so:
          patient's right = -X  → R label at the -X (minimum-X) extreme
          patient's left  = +X  → L label at the +X (maximum-X) extreme

        project_lr_to_screen() uses a dot-product test to hide whichever label
        is currently on the far side of the model (behind it from the camera).
        """
        if self.polydata is None:
            self._lr_world = {}
            self._lr_center = None
            return
        try:
            b = self.polydata.GetBounds()   # (xmin,xmax, ymin,ymax, zmin,zmax)
            cx = (b[0] + b[1]) * 0.5
            cy = (b[2] + b[3]) * 0.5
            cz = (b[4] + b[5]) * 0.5 + (b[5] - b[4]) * 0.12   # slightly above mid-height
            diag = math.sqrt((b[1]-b[0])**2 + (b[3]-b[2])**2 + (b[5]-b[4])**2)
            dx_pad = (b[1] - b[0]) * 0.08                        # 8 % of body width — stays close

            self._lr_center = (cx, cy, cz)
            self._lr_world = {
                "R": (b[0] - dx_pad, cy, cz),   # patient's right = -X = screen-left in front view
                "L": (b[1] + dx_pad, cy, cz),   # patient's left  = +X = screen-right in front view
            }
        except Exception as e:
            self.logger.warning(f"[RendererScene] LR setup failed: {e}")
            self._lr_world = {}
            self._lr_center = None
            return

        self._create_lr_vtk_actors()

    def _create_lr_vtk_actors(self):
        """Create vtkTextActor badges for L/R orientation labels and attach a
        StartEvent observer so they reproject themselves before every render.
        Using VTK actors sidesteps all Qt/OpenGL compositing issues entirely."""
        configs = [
            ("L", (1.00, 0.60, 0.267)),   # #FF9944 orange
            ("R", (0.40, 0.67, 1.00)),    # #66AAFF blue
        ]
        self._lr_vtk_actors = {}
        for name, color in configs:
            actor = vtk.vtkTextActor()
            actor.SetInput(f" {name} ")   # spaces on each side make width ≈ height → square badge
            tp = actor.GetTextProperty()
            tp.SetFontSize(20)
            tp.SetBold(True)
            tp.SetColor(*color)
            tp.SetBackgroundColor(0.051, 0.067, 0.090)   # #0D1117
            tp.SetBackgroundOpacity(1.0)
            tp.SetFrame(True)
            tp.SetFrameColor(*color)
            tp.SetFrameWidth(2)
            tp.SetJustificationToCentered()
            tp.SetVerticalJustificationToBottom()
            actor.GetPositionCoordinate().SetCoordinateSystemToDisplay()
            actor.SetDisplayPosition(0, 0)
            actor.VisibilityOff()
            self.renderer.AddActor2D(actor)
            self._lr_vtk_actors[name] = actor

        # Update badge positions before every frame — fired synchronously
        # inside VTK's render pipeline so positions are always current.
        self.renderer.AddObserver("StartEvent", self._update_lr_vtk_actors)

    def _update_lr_vtk_actors(self, obj=None, event=None):
        """Reproject L/R badge positions to display space before each VTK render."""
        if not self._lr_world or not self._lr_center or not self.renderer or not self.render_window:
            return
        try:
            win_w, win_h = self.render_window.GetSize()
            if win_w < 1 or win_h < 1:
                return

            cam = self.renderer.GetActiveCamera()
            vd = cam.GetDirectionOfProjection()
            cx, cy, cz = self._lr_center

            coord = vtk.vtkCoordinate()
            coord.SetCoordinateSystemToWorld()

            for label, pos in self._lr_world.items():
                actor = self._lr_vtk_actors.get(label)
                if actor is None:
                    continue
                # Dot > 0.15 → this side faces away from camera → hide
                vec = (pos[0] - cx, pos[1] - cy, pos[2] - cz)
                mag = math.sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)
                if mag > 1e-8:
                    dot = (vec[0]*vd[0] + vec[1]*vd[1] + vec[2]*vd[2]) / mag
                    if dot > 0.15:
                        actor.VisibilityOff()
                        continue
                # Project world coords → display coords (VTK origin: bottom-left)
                coord.SetValue(*pos)
                dp = coord.GetComputedDisplayValue(self.renderer)
                x = max(20, min(win_w - 20, int(dp[0])))
                y = max(20, min(win_h - 20, int(dp[1]) + 44))  # raise badge on screen
                actor.SetDisplayPosition(x, y)
                actor.VisibilityOn()
        except Exception as e:
            self.logger.warning(f"[RendererScene] _update_lr_vtk_actors failed: {e}")

    def project_lr_to_screen(self):
        """
        Project L/R anchor points to screen, but constrain both labels to a
        single fixed horizontal track (the projected Y of the model centre).

        Behaviour as the camera rotates in azimuth:
          - Each label's screen X = projected X of its fixed 3D anchor point.
          - Both labels share the same screen Y (projected centre height).
          - Result: labels glide left/right along one horizontal line, like two
            points on a flat ellipse — perfect depth-rotation synchronisation.

        Depth ordering / visibility:
          dot( (anchor - model_centre).normalised, view_dir ) > 0.15
          → anchor is facing away from camera → label is "behind" → hidden.
        """
        if not self._lr_world or not self.renderer or not self.render_window:
            return {}
        try:
            win_w, win_h = self.render_window.GetSize()
            if win_w < 1 or win_h < 1:
                return {}

            # DPI correction: VTK returns physical pixels; Qt lbl.move() uses logical pixels.
            try:
                dpr = float(self.vtk_widget.devicePixelRatioF())
            except Exception:
                dpr = 1.0

            # Fixed horizontal track: vertical centre of the Qt widget (logical pixels).
            try:
                fixed_screen_y = self.vtk_widget.height() // 2
            except Exception:
                fixed_screen_y = int(win_h / dpr) // 2

            qt_w = int(win_w / dpr)   # logical widget width for bounds check

            cam = self.renderer.GetActiveCamera()
            vd = cam.GetDirectionOfProjection()   # unit vector into scene
            cx, cy, cz = self._lr_center

            coord = vtk.vtkCoordinate()
            coord.SetCoordinateSystemToWorld()

            result = {}
            best_front_dot = float("inf")
            front_label = None

            for label, pos in self._lr_world.items():
                # Project anchor to screen; convert physical → logical; X only
                coord.SetValue(*pos)
                dp = coord.GetComputedDisplayValue(self.renderer)
                sx = int(dp[0] / dpr)
                sx = max(10, min(qt_w - 10, sx))
                result[label] = (sx, fixed_screen_y)

                # Track which label is facing the camera (smallest dot = most front)
                vec = (pos[0] - cx, pos[1] - cy, pos[2] - cz)
                mag = math.sqrt(vec[0]**2 + vec[1]**2 + vec[2]**2)
                if mag > 1e-8:
                    dot = (vec[0]*vd[0] + vec[1]*vd[1] + vec[2]*vd[2]) / mag
                    if dot < best_front_dot:
                        best_front_dot = dot
                        front_label = label

            result["_front"] = front_label   # caller uses this for raise_()
            return result
        except Exception:
            return {}

    # ------------------------------------------------------------------
    # Toolbar-facing API (to be called from show_model.py)
    # ------------------------------------------------------------------
    def set_mode(self, mode: str):
        """Activate a paint/erase/none mode."""
        if self.interactor_style:
            self.interactor_style.set_mode(mode)
            self.logger.debug(f"[RendererScene] set_mode({mode})")

    def toggle_mode(self, mode: str):
        """Toggle mode MARK/ERASE from toolbar buttons."""
        if self.interactor_style:
            self.interactor_style.toggle_mode(mode)
            self.logger.debug(f"[RendererScene] toggle_mode({mode})")

    def reset_camera(self):
        """Reset camera to initial orientation."""
        if self.interactor_style:
            self.interactor_style.reset_camera()
        else:
            cam = self.renderer.GetActiveCamera()
            cam.SetPosition(0, 0, 1)
            cam.SetFocalPoint(0, 0, 0)
            self.renderer.ResetCamera()
            camera = self.renderer.GetActiveCamera()
            camera.Zoom(0.8)  # Zoom out slightly
            self.render_window.Render()
        self.logger.debug("[RendererScene] reset_camera() called.")

    def _apply_initial_azimuth(self, degrees: float):
        """
        Rotate the camera around the focal point by `degrees` azimuth and
        re-snapshot the initial camera so that reset_camera() returns here.
        Called once during __init__ after _initialize_scene().
        """
        cam = self.renderer.GetActiveCamera()
        cam.Azimuth(degrees)
        cam.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        # Update the stored initial position so reset_camera() returns to this view
        if self.interactor_style and hasattr(self.interactor_style, "_snapshot_initial_camera"):
            self.interactor_style._snapshot_initial_camera()

    def apply_zoom(self, scale: float):
        """
        Apply zoom based on pinch gesture.
        scale > 1 → zoom in
        scale < 1 → zoom out
        """
        if not self.camera:
            return

        try:
            # Prevent extreme jumps
            scale = max(0.5, min(scale, 1.5))
            self.camera.Zoom(scale)
            # Clamp view angle to same limits as wheel zoom
            angle = self.camera.GetViewAngle()
            self.camera.SetViewAngle(max(10.0, min(60.0, angle)))
            self.render_window.Render()
        except Exception as e:
            print(f"[RendererScene] Zoom error: {e}")

    def apply_rotation(self, delta_degrees: float):
        """
        Rotate the camera based on a two-finger twist gesture.
        Horizontal rotation = Azimuth
        Vertical rotation   = limited Elevation
        """
        if not self.camera:
            return

        try:
            # Limit per-frame rotation to prevent jumps
            delta_degrees = max(-10, min(10, delta_degrees))

            # --- HORIZONTAL ROTATION ---
            self.camera.Azimuth(delta_degrees)

            # --- VERTICAL ROTATION LIMITER ---
            # Read current elevation angle indirectly using view up vector
            # (VTK has no direct getElevation)
            up = self.camera.GetViewUp()
            vertical_angle = math.degrees(math.atan2(up[2], up[1]))

            # Limit tilt between -60° and +60°
            if vertical_angle > 60:
                self.camera.SetViewUp(0, 1, 0)
            elif vertical_angle < -60:
                self.camera.SetViewUp(0, 1, 0)

            self.render_window.Render()

        except Exception as e:
            print(f"[RendererScene] Rotate error: {e}")

    def apply_pan(self, dx: float, dy: float):
        """
        Pan the camera so the scene follows a two-finger drag.

        dx, dy are the finger midpoint movement in Qt LOGICAL screen pixels
        (top-left origin, y increasing downward).

        Implementation mirrors vtkInteractorStyleTrackballCamera::Pan: convert
        the pixel delta to a world-space delta at the focal-point depth using the
        renderer's display<->world transform. This is automatically correct for
        any model scale and zoom level (no hard-coded distance constant), which
        is why the previous fixed-factor version barely moved the camera.
        """
        if not self.camera or not self.renderer or not self.render_window:
            return

        try:
            # Finger deltas are logical pixels; the renderer display transform
            # works in physical pixels, so apply the device-pixel ratio.
            try:
                dpr = float(self.vtk_widget.devicePixelRatioF())
            except Exception:
                dpr = 1.0

            cam = self.camera
            mx, my, mz = compute_pan_motion(self.renderer, cam, dx * dpr, dy * dpr)

            fp = list(cam.GetFocalPoint())
            pos = list(cam.GetPosition())
            cam.SetFocalPoint(fp[0] + mx, fp[1] + my, fp[2] + mz)
            cam.SetPosition(pos[0] + mx, pos[1] + my, pos[2] + mz)

            # Reuse the existing clamp so a now-working pan can't push the model
            # off-screen (the interactor style owns the pan-limit logic).
            if self.interactor_style and hasattr(self.interactor_style, "_clamp_camera_pan"):
                self.interactor_style._clamp_camera_pan()

            self.renderer.ResetCameraClippingRange()
            self.render_window.Render()

        except Exception as e:
            print(f"[RendererScene] Pan error: {e}")

    def rotate_azimuth_step(self, degrees: float = 0.5):
        """Rotate camera by one small azimuth increment. Called by the auto-rotate timer."""
        if not self.camera or not self.renderer or not self.render_window:
            return
        self.camera.Azimuth(degrees)
        self.camera.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()

    def rotate_direction(self, direction: str):
        """90° camera rotation from D-pad buttons (matches keyboard arrow behavior)."""
        if not self.camera:
            return
        step = 90
        d = direction.lower()
        if d == "left":
            self.camera.Azimuth(-step)
        elif d == "right":
            self.camera.Azimuth(step)
        elif d == "up":
            self.camera.Elevation(step)
        elif d == "down":
            self.camera.Elevation(-step)
        self.camera.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()

    def apply_touch_rotation(self, dx_pixels: float, dy_pixels: float):
        """
        Rotate camera from a finger drag (1-finger) or 2-finger midpoint translate.
        dx_pixels: horizontal screen delta  → azimuth
        dy_pixels: vertical screen delta    → elevation
        """
        if not self.camera:
            return
        sensitivity = 0.3  # degrees per pixel
        # Invert BOTH axes so the model follows the finger ("grab and drag"):
        # dragging right spins the model right, dragging up tilts it up. Without
        # the X inversion, Azimuth() turns the camera the same way as the finger,
        # which makes the model appear to rotate the opposite way (unintuitive).
        az = max(-15.0, min(15.0, -dx_pixels * sensitivity))
        el = max(-10.0, min(10.0, -dy_pixels * sensitivity))  # invert Y
        self.camera.Azimuth(az)
        self.camera.Elevation(el)
        self.camera.OrthogonalizeViewUp()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()

    def clear_all(self):
        """Clear all painted regions."""
        if self.interactor_style:
            self.interactor_style.clear_all()
        self.logger.debug("[RendererScene] clear_all() called.")

    def undo(self):
        """Undo last marking action."""
        if self.interactor_style:
            self.interactor_style.undo()
        self.logger.debug("[RendererScene] undo() called.")

    def apply_saved_marks(self, model_data: dict):
        """
        Apply saved marks onto the current model.
        Supports Paint V2 (per-vertex) and ignores legacy cell-based marks.
        """
        if not self.interactor_style or not model_data:
            return

        try:
            paint_v2 = model_data.get("paint_v2") or {}
            point_levels = paint_v2.get("point_level")

            if not point_levels:
                # Nothing to apply (either empty session or legacy file)
                self.logger.info("[RendererScene] No PaintV2 marks found to apply.")
                return

            style = self.interactor_style
            n_points = int(self.polydata.GetNumberOfPoints()) if self.polydata else 0
            usable_len = min(len(point_levels), n_points)

            applied = 0
            for pid in range(usable_len):
                lvl = int(point_levels[pid])
                if lvl > 0:
                    # PaintV2 internal method (no undo recording during load)
                    style._apply_point_level(pid, lvl, record=False)
                    applied += 1

            style.polydata.Modified()
            style.render_window.Render()

            self.logger.info(f"[RendererScene] Applied PaintV2 marks: {applied} points (usable_len={usable_len})")

        except Exception as e:
            self.logger.error(f"[RendererScene] Failed to apply PaintV2 marks: {e}")

    # ------------------------------------------------------------------
    # Dermatome mapping API (clinician-side utilities)
    # ------------------------------------------------------------------
    def set_dermatome_map_paths(self, bin_path: str, meta_path: str):
        """
        Store explicit paths for the dermatome map files.
        When set, load_dermatome_mapper() and compute_dermatome_coverage_result()
        will use these instead of looking in the default models directory.
        """
        self._derm_map_bin = bin_path
        self._derm_map_meta = meta_path

    def load_dermatome_mapper(self, bin_filename: str = None, meta_filename: str = None) -> bool:
        """
        Load dermatome mapper files.

        Path resolution order (per file):
          1. Explicit argument (if provided and not None)
          2. Stored path set via set_dermatome_map_paths()
          3. Default: filename resolved against get_base_models_path()

        Absolute paths are used directly; bare filenames are joined to the
        appropriate base directory.  Returns False on failure without crashing.
        """
        try:
            from codes.config import get_base_models_path

            def _resolve(arg, stored):
                p = arg if arg is not None else stored
                if p is None:
                    return None
                # Absolute path that exists → use directly
                if os.path.isabs(p) and os.path.exists(p):
                    return p
                # Bare filename → join to default models dir
                return os.path.join(get_base_models_path(), os.path.basename(p))

            bin_path  = _resolve(bin_filename,  self._derm_map_bin)
            meta_path = _resolve(meta_filename, self._derm_map_meta)

            if bin_path is None or not os.path.exists(bin_path):
                self.logger.error(f"[RendererScene] Dermatome BIN not found: {bin_path}")
                return False
            if meta_path is None or not os.path.exists(meta_path):
                self.logger.error(f"[RendererScene] Dermatome META not found: {meta_path}")
                return False
            if self.polydata is None:
                self.logger.error("[RendererScene] Cannot load dermatome mapper: polydata is None.")
                return False

            self.dermatome_mapper = DermatomeMapper(bin_path=bin_path, meta_path=meta_path)

            # --- Fix small vertex-map truncation (e.g., missing last 1-10 points) ---
            n_points = int(self.polydata.GetNumberOfPoints())
            dm = self.dermatome_mapper.derm_map

            if dm is not None:
                n_map = int(len(dm))
                diff = n_points - n_map

                # If slightly short, pad with UNASSIGNED (0) to match points count
                if 0 < diff <= 10:
                    import numpy as np
                    self.dermatome_mapper.derm_map = np.pad(dm, (0, diff), mode="constant", constant_values=0)
                    self.logger.warning(
                        f"[RendererScene] Padded dermatome map with {diff} UNASSIGNED entries to match points."
                    )

            # Soft validation: map length should be close to point count (per-vertex mapping expected)
            n_points = int(self.polydata.GetNumberOfPoints())
            n_map = int(len(self.dermatome_mapper.derm_map)) if self.dermatome_mapper.derm_map is not None else 0
            diff = abs(n_map - n_points)

            if diff == 0:
                self.logger.info(f"[RendererScene] Dermatome mapper loaded (per-vertex). points={n_points}, map={n_map}")
            elif diff <= 10:
                self.logger.warning(
                    f"[RendererScene] Dermatome mapper loaded but length mismatch is small. "
                    f"points={n_points}, map={n_map}, diff={diff}. Out-of-range points -> UNASSIGNED."
                )
            else:
                self.logger.warning(
                    f"[RendererScene] Dermatome mapper loaded but length mismatch is large. "
                    f"points={n_points}, map={n_map}, diff={diff}. Verify export pipeline."
                )

            return True

        except Exception as e:
            self.logger.error(f"[RendererScene] Failed to load dermatome mapper: {e}")
            self.dermatome_mapper = None
            return False

    def get_dermatome_for_cell(self, cell_id: int):
        """
        Return DermatomeHit for a given cell_id based on the loaded mapper.
        If mapper is not loaded -> returns UNASSIGNED.
        """
        if not self.dermatome_mapper or self.polydata is None:
            return None
        try:
            return self.dermatome_mapper.get_dermatome_for_cell(self.polydata, int(cell_id))
        except Exception as e:
            self.logger.error(f"[RendererScene] get_dermatome_for_cell failed: {e}")
            return None

    def get_dermatome_name_at(self, display_x: int, display_y: int) -> str | None:
        """
        Pick the model at VTK display coordinates (display_x, display_y) and return
        the dermatome name for the nearest surface vertex.

        Coordinates must already be in VTK display space (Y=0 at bottom).
        Caller converts Qt Y: vtk_y = widget_height - qt_y - 1.

        Returns None when mapper not loaded, nothing hit, or dermatome is UNASSIGNED.
        Uses vtkPointPicker so the picked point_id maps directly into derm_map[point_id].
        """
        if not self.dermatome_mapper or self.render_window is None or self.renderer is None:
            return None

        # vtkCellPicker does a proper ray-triangle intersection — never misses
        # a visible surface the way a point-proximity picker can.
        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.0001)
        hit = picker.Pick(display_x, display_y, 0, self.renderer)
        if not hit:
            return None

        px, py, pz = picker.GetPickPosition()

        # Find the nearest vertex on the base polydata to the hit world position.
        # Building the locator once and caching it avoids rebuilding on every click.
        if self.polydata is None:
            return None
        if self._point_locator is None:
            self._point_locator = vtk.vtkPointLocator()
            self._point_locator.SetDataSet(self.polydata)
            self._point_locator.BuildLocator()

        point_id = self._point_locator.FindClosestPoint([px, py, pz])
        if point_id < 0:
            return None

        derm_hit = self.dermatome_mapper.get_dermatome_for_point(point_id)
        if derm_hit is None or derm_hit.derm_id == 0:
            return None

        return derm_hit.derm_name

    def compute_marked_dermatomes(self):
        """
        Aggregate current painted marks (PaintV2 point_levels) into dermatome stats.
        Requires mapper to be loaded (per-vertex derm_map).
        Returns: {derm_id: {"cells": count_points, "level_sum": sum_levels}}
        """
        if not self.dermatome_mapper or self.polydata is None or self.interactor_style is None:
            return {}

        try:
            levels = getattr(self.interactor_style, "point_levels", None)
            dm = getattr(self.dermatome_mapper, "derm_map", None)

            if levels is None or dm is None:
                return {}

            usable_len = min(len(levels), len(dm), int(self.polydata.GetNumberOfPoints()))

            stats = {}
            for pid in range(usable_len):
                lvl = int(levels[pid])
                if lvl <= 0:
                    continue
                derm_id = int(dm[pid])  # per-vertex dermatome id
                if derm_id not in stats:
                    stats[derm_id] = {"vertices": 0, "level_sum": 0}
                stats[derm_id]["vertices"] += 1
                stats[derm_id]["level_sum"] += lvl

            return stats

        except Exception as e:
            self.logger.error(f"[RendererScene] compute_marked_dermatomes failed: {e}")
            return {}

    # ------------------------------------------------------------------
    # Dermatome overlay API (Clinician)
    # ------------------------------------------------------------------
    def set_dermatomes_overlay_path(self, path: str):
        """Set the expected dermatome overlay model path (PLY)."""
        self._derm_overlay_path = path

    def toggle_dermatomes_overlay(self, opacity: float = 0.45):
        """
        Toggle a dermatome overlay actor on top of the patient-painted model.
        The overlay is expected as a PLY with colors (vertex/cell). Easiest export from Blender.
        """
        if not self._derm_overlay_path:
            self.logger.warning("[RendererScene] No dermatome overlay path set.")
            return

        if not os.path.exists(self._derm_overlay_path):
            self.logger.warning(f"[RendererScene] Dermatome overlay file not found: {self._derm_overlay_path}")
            return

        # If actor not created yet -> create it
        if self._derm_actor is None:
            try:
                reader = vtkPLYReader()
                reader.SetFileName(self._derm_overlay_path)
                reader.Update()

                poly = reader.GetOutput()

                derm_mapper = vtkPolyDataMapper()
                derm_mapper.SetInputData(poly)
                derm_mapper.ScalarVisibilityOn()
                derm_mapper.SetColorModeToDirectScalars()

                derm_actor = vtkActor()
                derm_actor.SetMapper(derm_mapper)
                derm_actor.GetProperty().SetOpacity(opacity)

                # Add on top of base actor
                self.renderer.AddActor(derm_actor)
                self._derm_actor = derm_actor
                self._derm_visible = True

                self.render_window.Render()
                return
            except Exception as e:
                self.logger.error(f"[RendererScene] Failed to create dermatome overlay: {e}")
                return

        # Toggle visibility
        self._derm_visible = not self._derm_visible
        self._derm_actor.SetVisibility(1 if self._derm_visible else 0)
        self.render_window.Render()

    # ------------------------------------------------------------------
    # Dermatome swap view (Clinician toggle: regular ↔ dermatome colors)
    # ------------------------------------------------------------------
    def build_dermatome_swap_actor(self, derm_ply_path: str, show_pain_overlay: bool = True) -> bool:
        """
        Build a second read-only actor that shows the PLY's baked vertex colors.

        show_pain_overlay=True  (original behaviour):
            Painted vertices override the dermatome color with the pain-level color.
            Must be called AFTER apply_saved_marks() so point_levels are populated.

        show_pain_overlay=False (new claudeV concept):
            Show pure baked vertex colors exactly as exported — no pain marks on top.
            The toggle becomes a clean dermatome reference map.

        The actor starts hidden.  Call toggle_model_view() to switch between the
        regular painted model and this dermatome view.
        """
        _PAIN_COLORS = {1: (255, 255, 0), 2: (255, 165, 0), 3: (255, 0, 0)}

        try:
            if not os.path.exists(derm_ply_path):
                self.logger.error(f"[RendererScene] Dermatome PLY not found: {derm_ply_path}")
                return False

            reader = vtkPLYReader()
            reader.SetFileName(derm_ply_path)
            reader.Update()
            derm_poly = reader.GetOutput()

            # Get the baked vertex colors from the PLY.
            orig_scalars = derm_poly.GetPointData().GetScalars()
            if orig_scalars is None:
                self.logger.warning("[RendererScene] Dermatome PLY has no vertex colors.")
                return False

            # Optionally overlay pain marks on top of the dermatome colors.
            if show_pain_overlay:
                n_comp = orig_scalars.GetNumberOfComponents()
                point_levels = getattr(self.interactor_style, "point_levels", None)
                if point_levels is not None:
                    n = min(orig_scalars.GetNumberOfTuples(), len(point_levels))
                    for pid in range(n):
                        lvl = int(point_levels[pid])
                        if lvl > 0 and lvl in _PAIN_COLORS:
                            r, g, b = _PAIN_COLORS[lvl]
                            if n_comp == 4:
                                orig_scalars.SetTuple4(pid, r, g, b, 255)
                            else:
                                orig_scalars.SetTuple3(pid, r, g, b)
                    derm_poly.Modified()

            derm_mapper = vtkPolyDataMapper()
            derm_mapper.SetInputData(derm_poly)
            derm_mapper.ScalarVisibilityOn()
            derm_mapper.SetColorModeToDirectScalars()

            derm_actor = vtkActor()
            derm_actor.SetMapper(derm_mapper)
            derm_actor.SetVisibility(0)  # hidden until toggled

            self.renderer.AddActor(derm_actor)
            self._derm_swap_actor = derm_actor
            self.render_window.Render()

            self.logger.info("[RendererScene] Dermatome swap actor built successfully.")
            return True

        except Exception as e:
            self.logger.error(f"[RendererScene] Failed to build dermatome swap actor: {e}")
            return False

    def toggle_model_view(self):
        """
        Toggle between the regular painted model (gray base + pain colors)
        and the dermatome-region model (Blender colors + pain marks on top).
        """
        if self._derm_swap_actor is None:
            self.logger.warning("[RendererScene] toggle_model_view: dermatome actor not built yet.")
            return

        showing_derm = bool(self._derm_swap_actor.GetVisibility())

        # Swap the two actors
        self._derm_swap_actor.SetVisibility(0 if showing_derm else 1)
        if self.actor:
            self.actor.SetVisibility(1 if showing_derm else 0)

        self.render_window.Render()
        self.logger.debug(
            f"[RendererScene] toggle_model_view → {'regular' if showing_derm else 'dermatome'}"
        )

    # ------------------------------------------------------------------
    # Session comparison overlay (clinician view)
    # ------------------------------------------------------------------
    def add_comparison_overlay(self, point_levels: list, opacity: float = 0.35) -> bool:
        """
        Add a transparent actor showing a previous session's pain marks.

        Uses cool tones (blue/violet) so the overlay is visually distinct from
        the current session's warm pain colors (yellow/orange/red).
        Polygon offset pushes the overlay slightly in front of the base model
        to eliminate z-fighting artefacts on identical geometry.

        Calling this again replaces any existing overlay.
        """
        # RGBA: unpainted = fully transparent, painted = cool-tone semi-transparent
        _OVERLAY_COLORS = {
            1: (100, 200, 255, 180),   # light blue  — mild
            2: (50,  100, 255, 210),   # medium blue — moderate
            3: (150,  50, 255, 230),   # violet      — severe
        }

        try:
            self.remove_comparison_overlay()

            if self.polydata is None:
                return False

            n_points = int(self.polydata.GetNumberOfPoints())

            # Shallow-copy geometry (points + cells) — no scalars
            overlay_poly = vtk.vtkPolyData()
            overlay_poly.CopyStructure(self.polydata)

            # RGBA array: unpainted vertices are fully transparent (alpha=0),
            # so only pain markings are visible — no ghost body underneath.
            # Built with numpy (pre-zeroed + vectorized level mapping) instead
            # of two O(n) Python SetTuple4 loops.
            import numpy as np
            from vtk.util import numpy_support

            rgba = np.zeros((n_points, 4), dtype=np.uint8)  # transparent by default
            usable = min(len(point_levels), n_points)
            if usable > 0:
                levels = np.asarray(point_levels[:usable], dtype=np.int64)
                for lvl, color in _OVERLAY_COLORS.items():
                    rgba[:usable][levels == lvl] = color

            colors = numpy_support.numpy_to_vtk(rgba, deep=True,
                                                array_type=vtk.VTK_UNSIGNED_CHAR)
            colors.SetNumberOfComponents(4)
            colors.SetName("OverlayColors")

            overlay_poly.GetPointData().SetScalars(colors)

            mapper = vtkPolyDataMapper()
            mapper.SetInputData(overlay_poly)
            mapper.ScalarVisibilityOn()
            mapper.SetColorModeToDirectScalars()
            # Pull overlay toward camera to prevent z-fighting on identical geometry
            mapper.SetResolveCoincidentTopologyToPolygonOffset()
            mapper.SetResolveCoincidentTopologyPolygonOffsetParameters(-1.0, -1.0)

            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetOpacity(1.0)   # alpha handled per-vertex

            self.renderer.AddActor(actor)
            self._comparison_actor = actor
            self.render_window.Render()

            self.logger.info("[RendererScene] Comparison overlay added (markings only).")
            return True

        except Exception as e:
            self.logger.error(f"[RendererScene] add_comparison_overlay failed: {e}")
            return False

    def remove_comparison_overlay(self):
        """Remove the comparison overlay actor if one is present."""
        if self._comparison_actor is not None:
            try:
                self.renderer.RemoveActor(self._comparison_actor)
                self._comparison_actor = None
                if self.render_window:
                    self.render_window.Render()
                self.logger.info("[RendererScene] Comparison overlay removed.")
            except Exception as e:
                self.logger.error(f"[RendererScene] remove_comparison_overlay failed: {e}")

    # ------------------------------------------------------------------
    # Future: session persistence (save/load)
    # ------------------------------------------------------------------
    def save_annotations(self, output_path: str):
        """Save current markings to disk (future implementation)."""
        self.logger.info(f"[RendererScene] save_annotations() → {output_path}")

    def load_annotations(self, input_path: str):
        """Load previous markings (future implementation)."""
        self.logger.info(f"[RendererScene] load_annotations() ← {input_path}")


    def save_session(self, subject_id: str, gender: str, comments=None, connected_comments=None, color_map=None):
        """
        Save current session data to:
        Data/Subjects/<subject_id>/session_<timestamp>/session_data.json
        """
        try:
            # --- Step 1: Build base path ---
            base_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "Data", "Subjects", subject_id
            )
            os.makedirs(base_dir, exist_ok=True)

            # --- Step 2: Create timestamped folder ---
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            session_dir = os.path.join(base_dir, f"session_{timestamp}")
            os.makedirs(session_dir, exist_ok=True)

            # --- Step 3: Build data structure ---
            session_data = {
                "subject_id": subject_id,
                "gender": gender,
                "datetime": datetime.datetime.now().isoformat(),
                "comments": comments or [],
                "color_map": color_map or [],
            }

            # --- Step 4: Save to JSON ---
            json_path = os.path.join(session_dir, "session_data.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=4)

            self.logger.info(f"[RendererScene] ✅ Session saved successfully: {json_path}")

        except Exception as e:
            self.logger.error(f"[RendererScene] ❌ Failed to save session: {e}")

    def set_brush_scale(self, factor: float):
        """Forward user brush-size adjustment to the interactor style."""
        if self.interactor_style:
            try:
                self.interactor_style.set_brush_scale(factor)
            except Exception as e:
                self.logger.warning(f"[RendererScene] set_brush_scale failed: {e}")

    def get_brush_scale(self) -> float:
        """Current brush scale (1.0 default) — safe when style is missing."""
        try:
            return self.interactor_style.get_brush_scale()
        except Exception:
            return 1.0

    def set_mark_level(self, level: int):
        """Set current paint intensity level (1..3)."""
        if self.interactor_style:
            try:
                self.interactor_style.set_mark_level(level)
                self.logger.debug(f"[RendererScene] set_mark_level({level})")
            except Exception as e:
                self.logger.error(f"[RendererScene] Failed to set mark level: {e}")

    # ------------------------------------------------------------------
    # Session saving (integrated with SessionManager)
    # ------------------------------------------------------------------
    def compute_dermatome_coverage_result(self, session_manager=None) -> dict:
        """
        Run the centralized dermatome coverage engine on the current point_levels.

        Loads the mapper when not already loaded (male model only).
        Returns the full coverage result dict from dermatome_coverage.py.
        Safe to call even when the mapper is not loaded — returns analysis_type="unavailable".
        """
        from codes.dermatome_coverage import compute_dermatome_coverage

        def _unavailable(reason: str) -> dict:
            return {
                "analysis_type": "unavailable",
                "reason": reason,
                "overall": {},
                "dermatomes": [],
            }

        # Load mapper if not already present
        if not self.dermatome_mapper:
            # If explicit paths are not already stored, derive them from gender
            if not self._derm_map_bin:
                gender = ""
                if session_manager:
                    subject_info = (session_manager.data or {}).get("subject_info") or {}
                    gender = (subject_info.get("gender") or "").lower()
                if gender == "female":
                    from codes.config import get_female_model_info
                    info = get_female_model_info()
                else:
                    from codes.config import get_male_model_info
                    info = get_male_model_info()
                self._derm_map_bin = info["derm_bin"]
                self._derm_map_meta = info["derm_meta"]
            ok = self.load_dermatome_mapper()
            if not ok:
                return _unavailable("Failed to load dermatome map files.")

        if self.interactor_style is None:
            return _unavailable("Interactor not initialized.")

        point_levels = getattr(self.interactor_style, "point_levels", None) or []
        derm_map = getattr(self.dermatome_mapper, "derm_map", None)

        return compute_dermatome_coverage(
            point_levels=point_levels,
            derm_map=derm_map,
            total_vertices_per_dermatome=self.dermatome_mapper.total_vertices_per_dermatome,
            id_to_name=self.dermatome_mapper.id_to_name,
            dermatome_order=self.dermatome_mapper.get_dermatome_order(),
        )

    def _compute_dermatome_stats_for_save(self, session_manager) -> dict:
        """
        Run the coverage engine and return a serialized dict for model_data["dermatome_coverage"].
        Returns {} when analysis is unavailable (female model, missing files, etc.).
        """
        from codes.dermatome_coverage import serialize_dermatome_coverage
        try:
            result = self.compute_dermatome_coverage_result(session_manager)
            if result.get("analysis_type") != "anatomical_mapping_only":
                return {}
            return serialize_dermatome_coverage(result)
        except Exception as e:
            self.logger.error(f"[RendererScene] _compute_dermatome_stats_for_save failed: {e}")
            return {}

    def save_full_session(self, session_manager, comments=None):
        """
        Save the current PAINDICATOR session (model state + screenshots + metadata).
        Automatically creates folder by ID/date in Israeli format.
        """
        import json
        from datetime import datetime
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtGui import QImage, QPixmap

        try:
            # --- Validate manager ---
            if not session_manager:
                raise ValueError("SessionManager not provided")

            # --- 1. Create folder ---
            session_dir = session_manager.get_session_folder()
            print(f"[RendererScene] Saving full session to {session_dir}")

            # --- Save current camera state so we can restore it after screenshots ---
            cam = self.renderer.GetActiveCamera()
            original_position    = cam.GetPosition()
            original_focal_point = cam.GetFocalPoint()
            original_view_up     = cam.GetViewUp()
            original_view_angle  = cam.GetViewAngle()

            # --- Move camera to the initial "open" position for consistent screenshots ---
            # We read the stored initial values from the interactor style — these are set
            # once when the model loads and represent exactly what the user saw on first open.
            # This avoids the "tiny model" problem of hardcoded world coords and ensures
            # screenshots always match the default view regardless of user rotation.
            style = self.interactor_style
            init_pos = getattr(style, "_initial_camera_pos", None)
            init_fp  = getattr(style, "_initial_camera_fp",  None)
            init_vup = getattr(style, "_initial_camera_vup", None)

            # Restore front-view orientation from the stored initial values, then call
            # ResetCamera() to fit the whole model in frame.  This handles zoom (which
            # changes ViewAngle, not position) and pan — the user could have done either
            # during the session and the screenshot should still show the full body.
            if init_pos and init_fp and init_vup:
                cam.SetPosition(*init_pos)
                cam.SetFocalPoint(*init_fp)
                cam.SetViewUp(*init_vup)
                cam.OrthogonalizeViewUp()
            cam.SetViewAngle(30.0)          # reset any Zoom() that changed the view angle
            self.renderer.ResetCamera()     # fit whole model in view (adjusts distance)
            self.renderer.ResetCameraClippingRange()
            self.render_window.Render()

            # --- 2. Capture front screenshot ---
            front_path = os.path.join(session_dir, "front.png")
            self._capture_screenshot(front_path)

            # --- 3. Capture back screenshot (rotate 180° around the up axis) ---
            back_path = os.path.join(session_dir, "back.png")
            cam.Azimuth(180)
            self.renderer.ResetCamera()     # re-fit after rotation
            self.renderer.ResetCameraClippingRange()
            self.render_window.Render()
            self._capture_screenshot(back_path)

            # --- Restore original camera state ---
            cam.SetPosition(*original_position)
            cam.SetFocalPoint(*original_focal_point)
            cam.SetViewUp(*original_view_up)
            cam.SetViewAngle(original_view_angle)
            self.renderer.ResetCameraClippingRange()
            self.render_window.Render()

            # --- 4. Update session manager ---
            session_manager.set_screenshots(front_path, back_path)

            # --- PaintV2 save (per-vertex) ---
            levels = getattr(self.interactor_style, "point_levels", None)
            if levels is None:
                levels = []

            model_data = {
                "paint_v2": {
                    "point_level": levels
                },
                "mode": getattr(self.interactor_style, "mode", None),
            }

            # Attach comments from toolbar if provided
            if comments:
                try:
                    model_data["comments"] = list(comments)
                except Exception:
                    pass

            # Attach dermatome coverage result (male model only).
            # Saves alongside raw point_level for the summary file and external tools.
            derm_coverage = self._compute_dermatome_stats_for_save(session_manager)
            if derm_coverage:
                model_data["dermatome_coverage"] = derm_coverage

            session_manager.set_model_data(model_data)

            # --- 5. Save JSON (technical data) ---
            session_manager.save_to_file(session_dir)

            # --- 6. Save human-readable summary ---
            try:
                session_manager.save_to_human_readable_file(session_dir)
            except Exception as e:
                # Summary is secondary to session.json — warn but don't fail the save
                self.logger.exception("Failed to save human-readable summary")
                try:
                    QMessageBox.warning(
                        None, "Partial Save",
                        "Session data was saved, but the text summary could not be written.\n"
                        f"Details: {e}"
                    )
                except Exception:
                    pass

            self.logger.info("Session fully saved in %s", session_dir)

            # --- 6. Notify user ---
            try:
                QMessageBox.information(None, "Session Saved", "Session saved successfully!")
            except Exception:
                pass

        except Exception as e:
            # Surface the failure to the user — silent data loss is unacceptable
            self.logger.exception("Failed to save full session")
            try:
                QMessageBox.critical(
                    None, "Save Failed",
                    "The session could NOT be saved.\n"
                    f"Details: {e}\n\n"
                    "Please check disk space/permissions and try again."
                )
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Helper: capture current render window as PNG
    # ------------------------------------------------------------------
    def _capture_screenshot(self, output_path: str):
        """Capture the current render window to a PNG file."""
        w2if = vtk.vtkWindowToImageFilter()
        w2if.SetInput(self.render_window)
        w2if.Update()

        writer = vtk.vtkPNGWriter()
        writer.SetFileName(output_path)
        writer.SetInputConnection(w2if.GetOutputPort())
        writer.Write()
        print(f"[RendererScene] Screenshot saved → {output_path}")

    def capture_consistent_screenshot(self, output_path: str, width=1080, height=1080):
        """
        Capture screenshot with fixed camera, ensuring consistent framing.
        """
        renderer = self.renderer
        camera = renderer.GetActiveCamera()

        # --- FIXED CAMERA SETTINGS ---
        camera.SetPosition(0, 0, 180)
        camera.SetFocalPoint(0, 0, 0)
        camera.SetViewUp(0, 1, 0)
        camera.SetViewAngle(20)

        renderer.ResetCameraClippingRange()
        self.render_window.SetSize(width, height)
        self.render_window.Render()

        w2if = vtk.vtkWindowToImageFilter()
        w2if.SetInput(self.render_window)
        w2if.SetScale(1)
        w2if.ReadFrontBufferOff()
        w2if.Update()

        writer = vtk.vtkPNGWriter()
        writer.SetFileName(output_path)
        writer.SetInputConnection(w2if.GetOutputPort())
        writer.Write()

        print(f"[RendererScene] Consistent screenshot saved → {output_path}")
