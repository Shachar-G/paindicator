"""
Quick preview for the v2 coordinate-based dermatome mapping.
Run: venv311\Scripts\python.exe preview_v2.py

Controls:
  Left-drag = rotate   |   Scroll = zoom
"""

import os, sys
import numpy as np

ROOT = os.path.dirname(__file__)
PLY   = os.path.join(ROOT, "files", "models", "male_derm_vertex_colors_v2.ply")
U8    = os.path.join(ROOT, "files", "models", "male_derm_vertex_id_v2.u8")

import vtk

derm_map = np.fromfile(U8, dtype=np.uint8)
print(f"Loaded u8: {len(derm_map)} vertices")

reader = vtk.vtkPLYReader()
reader.SetFileName(PLY)
reader.Update()
pd = reader.GetOutput()
print(f"Vertices: {pd.GetNumberOfPoints()}  Faces: {pd.GetNumberOfCells()}")

mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(reader.GetOutputPort())
mapper.ScalarVisibilityOn()
mapper.SetColorModeToDirectScalars()

actor = vtk.vtkActor()
actor.SetMapper(mapper)

renderer = vtk.vtkRenderer()
renderer.AddActor(actor)
renderer.SetBackground(0.18, 0.22, 0.26)
renderer.ResetCamera()

win = vtk.vtkRenderWindow()
win.SetWindowName("PAINDICATOR — Dermatome v2 preview")
win.SetSize(900, 750)
win.AddRenderer(renderer)

iren = vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(win)
iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

renderer.ResetCamera()
win.Render()
print("Window open. Rotate to inspect. Close to exit.")
iren.Initialize()
iren.Start()
