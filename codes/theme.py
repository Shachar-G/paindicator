# PAINDICATOR UI Theme — central design system
# All UI files should import from here instead of hardcoding colors, font
# sizes, or spacing values. Values below are unscaled "design pixels" —
# pass sizes through scale.sc() at the point of use.

# ---------------------------------------------------------------------------
# Core palette
# ---------------------------------------------------------------------------
BACKGROUND    = "#F0F4F8"
SURFACE       = "rgba(255, 255, 255, 0.75)"
SURFACE_SOLID = "#FFFFFF"
PRIMARY       = "#00CED1"
PRIMARY_LIGHT = "rgba(0, 206, 209, 0.15)"
PRIMARY_DARK  = "#0099A8"
BORDER        = "rgba(0, 206, 209, 0.25)"
BORDER_LIGHT  = "rgba(255, 255, 255, 0.9)"

# Text — WCAG-AA compliant on BACKGROUND (#F0F4F8)
TEXT_PRIMARY  = "#0A1628"   # ~16:1 contrast
TEXT_SECOND   = "#3D6472"   # darkened from #5a8a9a (~3:1) to reach >=4.5:1
TEXT_HINT     = "#5A6B82"   # darkened from #8a9ab0 (~2.5:1) to reach >=4.5:1
TEXT_ON_PRIMARY = "#FFFFFF"

# ---------------------------------------------------------------------------
# State colors
# ---------------------------------------------------------------------------
DISABLED_BG   = "#C7CFD9"
DISABLED_TEXT = "#5F6B78"   # readable gray-on-gray (>=4.5:1 on DISABLED_BG)
SUCCESS       = "#2E8B57"
WARNING       = "#B45309"
ERROR         = "#C0392B"
DANGER        = "#C0392B"   # alias for destructive buttons
DANGER_DARK   = "#96281B"

# ---------------------------------------------------------------------------
# Pain severity — SINGLE SOURCE OF TRUTH for UI representations of pain
# levels. Matches the canonical VTK paint colors (yellow / orange / red in
# vtk_interactor_custom.COLORS). Chosen with distinct luminance steps so the
# scale remains readable for color-blind users; severity must ALWAYS also be
# communicated with a text label, never by hue alone.
# ---------------------------------------------------------------------------
PAIN_MILD     = "#F5C842"   # level 1 — yellow  (light)
PAIN_MODERATE = "#E8883A"   # level 2 — orange  (medium)
PAIN_SEVERE   = "#D94040"   # level 3 — red     (dark)

PAIN_LEVEL_COLORS = {1: PAIN_MILD, 2: PAIN_MODERATE, 3: PAIN_SEVERE}
PAIN_LEVEL_NAMES  = {1: "Mild", 2: "Moderate", 3: "Severe"}

# Legacy aliases (kept for compatibility; do not use in new code)
MILD          = PAIN_MILD
MODERATE      = PAIN_MODERATE
SEVERE        = PAIN_SEVERE

# ---------------------------------------------------------------------------
# Typographic scale (pass through scale.sc() before use in px stylesheets)
# One size per semantic role — do not invent new sizes in screens.
# ---------------------------------------------------------------------------
FONT_H1      = 28   # main screen titles
FONT_H2      = 22   # section titles / large buttons
FONT_TITLE   = 20   # emphasized labels, input text
FONT_BODY    = 16   # regular labels and content
FONT_CAPTION = 13   # hints, footnotes, secondary info

# ---------------------------------------------------------------------------
# Spacing scale (pass through scale.sc() before use)
# ---------------------------------------------------------------------------
SPACE_XS = 8
SPACE_SM = 12
SPACE_MD = 20
SPACE_LG = 32
SPACE_XL = 48

# ---------------------------------------------------------------------------
# Shape / component constants
# ---------------------------------------------------------------------------
RADIUS_SM = 8
RADIUS_MD = 10
RADIUS_LG = 16

# Minimum comfortable touch-target edge (design px, before scaling).
# Medical/tablet guideline: 44-48 px.
TOUCH_TARGET_MIN = 48
