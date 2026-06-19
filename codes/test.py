import vtk

# =====================================
# Load your OBJ model
# =====================================
filename = r"C:\Users\GuttmanShachar\Documents\PAINDICATOR\files\models\untitled.obj"
reader = vtk.vtkOBJReader()
reader.SetFileName(filename)
reader.Update()

polydata = reader.GetOutput()

# =====================================
# Renderer + Actor
# =====================================
mapper = vtk.vtkPolyDataMapper()
mapper.SetInputData(polydata)

actor = vtk.vtkActor()
actor.SetMapper(mapper)

renderer = vtk.vtkRenderer()
renderer.AddActor(actor)
renderer.SetBackground(0.1, 0.1, 0.1)

render_window = vtk.vtkRenderWindow()
render_window.AddRenderer(renderer)
render_window.SetSize(1000, 800)

interactor = vtk.vtkRenderWindowInteractor()
interactor.SetRenderWindow(render_window)

# =====================================
# Painting logic
# =====================================
# ניצור מערך צבעים מותאם לכל Face
num_cells = polydata.GetNumberOfCells()
colors = vtk.vtkUnsignedCharArray()
colors.SetName("CellColors")
colors.SetNumberOfComponents(3)
colors.SetNumberOfTuples(num_cells)

# צבע ברירת מחדל לכל הפאות (אפור)
for i in range(num_cells):
    colors.SetTuple(i, (180, 180, 180))

polydata.GetCellData().SetScalars(colors)


class PaintCallback(vtk.vtkInteractorStyleTrackballCamera):
    def __init__(self, parent=None):
        super().__init__()
        self.AddObserver("LeftButtonPressEvent", self.left_click)

    def left_click(self, obj, event):
        click_pos = self.GetInteractor().GetEventPosition()

        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.0005)
        picker.Pick(click_pos[0], click_pos[1], 0, renderer)

        cell_id = picker.GetCellId()
        if cell_id != -1:
            print("Painting cell:", cell_id)
            colors.SetTuple(cell_id, (255, 0, 0))  # צבע אדום
            colors.Modified()
            polydata.Modified()
            render_window.Render()

        self.OnLeftButtonDown()


style = PaintCallback()
interactor.SetInteractorStyle(style)

# =====================================
# Run
# =====================================
render_window.Render()
interactor.Initialize()
interactor.Start()
