import os
import sys


def get_base_icons_path():
    """Returns the correct path to the 'files/icons' directory."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "files", "icons")
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "files", "icons")
    )


def get_base_models_path():
    """
    Returns the correct path to the 'files/models' directory,
    both for development and PyInstaller EXE.
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "files", "models")
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "files", "models")
    )


def get_male_model_info() -> dict:
    """
    Returns file paths for the male model and its dermatome mapping.

    Keys
    ----
    model_path      : PLY used for patient painting (and clinician replay)
    derm_swap_ply   : PLY loaded as the dermatome toggle actor
    derm_bin        : .u8 per-vertex dermatome-ID file
    derm_meta       : dermatome meta JSON
    swap_show_pain  : whether to overlay pain marks on the dermatome toggle view
    """
    root = get_base_models_path()
    male_dir = os.path.join(root, "male model")
    return {
        "model_path":      os.path.join(male_dir, "male_derm_vertex_colors.ply"),
        "derm_swap_ply":   os.path.join(male_dir, "male_derm_vertex_colors.ply"),
        "derm_bin":        os.path.join(male_dir, "male_derm_vertex_id.u8"),
        "derm_meta":       os.path.join(male_dir, "male_derm_meta.json"),
        "swap_show_pain":  True,
        "initial_azimuth": 90,
    }


def get_female_model_info() -> dict:
    """
    Returns file paths for the female model and its dermatome mapping.

    Keys
    ----
    model_path      : PLY used for patient painting (and clinician replay)
    derm_swap_ply   : PLY loaded as the dermatome toggle actor
    derm_bin        : .u8 per-vertex dermatome-ID file
    derm_meta       : dermatome meta JSON
    swap_show_pain  : whether to overlay pain marks on the dermatome toggle view
    """
    root = get_base_models_path()
    female_dir = os.path.join(root, "female model")
    return {
        "model_path":      os.path.join(female_dir, "female_derm_vertex_colors.ply"),
        "derm_swap_ply":   os.path.join(female_dir, "female_derm_vertex_colors_fixed.ply"),
        "derm_bin":        os.path.join(female_dir, "female_derm_vertex_id.u8"),
        "derm_meta":       os.path.join(female_dir, "female_derm_meta.json"),
        "swap_show_pain":  True,
        "initial_azimuth": 90,
    }
