# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules

# IMPORTANT: __file__ does NOT exist when running spec → use working directory
project_root = os.getcwd()

# Collect all vtk hidden modules automatically
vtk_hidden = collect_submodules('vtk')
vtkmodules_hidden = collect_submodules('vtkmodules')

a = Analysis(
    ['codes/app.py'],     # Entry point
    pathex=[project_root],
    binaries=[],
    datas=[
        # Fonts
        (os.path.join(project_root, 'files', 'fonts'), 'files/fonts'),

        # Icons
        (os.path.join(project_root, 'files', 'icons'), 'files/icons'),

        # Pictures (used by role_selection and ui_main)
        (os.path.join(project_root, 'files', 'pictures'), 'files/pictures'),

        # Male model — only runtime files, no .blend
        (os.path.join(project_root, 'files', 'models', 'male model', 'male_derm_vertex_colors.ply'), 'files/models/male model'),
        (os.path.join(project_root, 'files', 'models', 'male model', 'male_derm_preview_flat.ply'), 'files/models/male model'),
        (os.path.join(project_root, 'files', 'models', 'male model', 'male_derm_vertex_id.u8'), 'files/models/male model'),
        (os.path.join(project_root, 'files', 'models', 'male model', 'male_derm_meta.json'), 'files/models/male model'),

        # Female model — only runtime files, no .blend
        (os.path.join(project_root, 'files', 'models', 'female model', 'female_derm_vertex_colors.ply'), 'files/models/female model'),
        (os.path.join(project_root, 'files', 'models', 'female model', 'female_derm_vertex_colors_fixed.ply'), 'files/models/female model'),
        (os.path.join(project_root, 'files', 'models', 'female model', 'female_derm_vertex_id.u8'), 'files/models/female model'),
        (os.path.join(project_root, 'files', 'models', 'female model', 'female_derm_meta.json'), 'files/models/female model'),

        # Data — empty sessions folder so the path exists on first run
        (os.path.join(project_root, 'data', 'sessions'), 'data/sessions'),
    ],
    hiddenimports=[
        # Dynamically-loaded screens (not detected by static analysis)
        'codes.screens.role_selection',
        'codes.screens.clinician_name',
        'codes.screens.clinician_patients',
        'codes.screens.clinician_session_selection',
        'codes.screens.clinician_view_session',
        'codes.screens.patient_id',
        'codes.screens.gender_selection',
        'codes.screens.questionnaire',
        'codes.screens.show_model',
        'codes.screens.info',
        # VTK
        'vtk',
        'vtkmodules',
        'vtkmodules.vtkRenderingCore',
        'vtkmodules.vtkRenderingOpenGL2',
        'vtkmodules.vtkInteractionStyle',
        'vtkmodules.vtkFiltersCore',
        'vtkmodules.vtkCommonCore',
        'vtkmodules.vtkCommonDataModel',
        'vtkmodules.vtkRenderingUI',
        'vtkmodules.vtkIOGeometry',
        'vtkmodules.vtkIOPLY',
        'vtkmodules.vtkIOImport',
        'vtkmodules.vtkFiltersSources',
    ] + vtk_hidden + vtkmodules_hidden  ,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='PAINDICATOR',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(project_root, 'files', 'pictures', 'logo.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='PAINDICATOR'
)
