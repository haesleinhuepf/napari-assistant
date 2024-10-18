from __future__ import annotations

from pathlib import Path
from typing import Callable
from warnings import warn
from qtpy.QtWidgets import QFileDialog, QLineEdit, QVBoxLayout, QHBoxLayout, QWidget, QMenu, QLabel
from qtpy.QtGui import QCursor
from typing import Union
from .._categories import CATEGORIES, Category, filter_categories, find_function, get_category_of_function
from ._button_grid import ButtonGrid, _get_highlight_brush, _get_background_brush
from ._category_widget import make_gui_for_category
from napari.viewer import Viewer

class Assistant(QWidget):
    """The main Assistant widget.

    The widget holds buttons with icons to create widgets for the various
    cel operation categories.  It tracks which layers are connected to which
    widgets, and can export the state of the task graph to a dask graph
    or to jython code.

    Parameters
    ----------
    napari_viewer : Viewer
        This viewer instance will be provided by napari when it gets added
        as a plugin dock widget.
    """

    def __init__(self, napari_viewer: Viewer):

        super().__init__()
        self._viewer = napari_viewer
        napari_viewer.layers.events.removed.connect(self._on_layer_removed)
        napari_viewer.layers.selection.events.changed.connect(self._on_selection)
        self._layers = {}

        # visualize intermediate results human-readable from top-left to bottom-right
        self._viewer.grid.stride = -1

        CATEGORIES["Generate code..."] = self._code_menu
        CATEGORIES["Save and load workflows"] = self._workflow_menu
        CATEGORIES["Undo"] = self.undo_action
        # CATEGORIES["Redo"] = self.redo_action

        CATEGORIES["Search napari hub"] = self.search_napari_hub
        CATEGORIES["Search image.sc"] = self.search_image_sc
        CATEGORIES["Search BIII"] = self.search_biii

        # build GUI
        self.icon_grid = ButtonGrid(self)
        self.icon_grid.addItems(CATEGORIES)
        self.icon_grid.itemClicked.connect(self._on_item_clicked)

        self.seach_field = QLineEdit("")
        self.seach_field.setPlaceholderText("Enter operation or plugin name to search")

        def text_changed(*args, **kwargs):
            search_string = self.seach_field.text().lower()
            self.icon_grid.clear()
            self.icon_grid.addItems(filter_categories(search_string))

        self.seach_field.textChanged.connect(text_changed)
        text_changed()

        # create menu
        self.actions = [
            ("Export Python script to file", self.to_python),
            ("Export Jupyter Notebook", self.to_notebook),
            ("Export Jupyter Notebook using Napari", self.to_notebook_using_napari),
            ("Copy Python code to clipboard", self.to_clipboard),
        ]

        # create workflow menu
        self.workflow_actions = [
            ("Export workflow to file", self.to_file),
            ("Load workflow from file", self.load_workflow),
        ]

        # add Send to script editor menu in case it's installed
        try:
            import napari_script_editor
            self.actions.append(("Send to Script Editor", self.to_script_editor))
        except ImportError:
            pass
        # add plugin generator menu in case it's installed
        try:
            import napari_assistant_plugin_generator
            self.actions.append(("Generate Napari plugin", self.to_napari_plugin))
        except ImportError:
            pass

        self.setLayout(QVBoxLayout())
        search_and_help = QWidget()
        search_and_help.setLayout(QHBoxLayout())
        from ._button_grid import _get_icon
        help = QLabel("?")
        help.setToolTip(
            '<html>'
            'Use the search field on the left to enter a term describing the function you would like to apply to your image.\n'
            'Searching will limit the number of shown categories and listed operations.\n'
            '<br><br>The icons in the buttons below denote the processed image types:\n'
            '<br><img src="' + _get_icon("intensity_image") + '" width="24" heigth="24"> In <b>intensity images</b> the pixel value represents a measurement, e.g. of collected light during acquisition in a microscope.\n'
            '<br><img src="' + _get_icon("binary_image") + '" width="24" heigth="24"> In <b>binary images</b> pixels with value 0 mean there is no object present. All other pixels (typically value 1) represent any object.\n'
            '<br><img src="' + _get_icon("label_image") + '" width="24" heigth="24"> In <b>label images</b> the integer pixel intensity corresponds to the object identity. E.g. all pixels of object 2 have value 2.\n'
            '<br><img src="' + _get_icon("parametric_image") + '" width="24" heigth="24"> In <b>parametric images</b> the pixel value represents an object measurement. All pixels of an object can for example contain the same value, e.g. the objects circularity or area.\n'
            '<br><img src="' + _get_icon("mesh_image") + '" width="24" heigth="24"> In <b>mesh images</b> we can visualize connectivity between objects and distances as intensity along lines.\n'
            '<br><img src="' + _get_icon("any_image") + '" width="24" heigth="24"> This icon means one can use <b>any kind of image</b> for this operation.'
            '</html>'
        )
        help.setMaximumWidth(20)
        search_and_help.layout().addWidget(self.seach_field)
        search_and_help.layout().addWidget(help)

        self.layout().addWidget(search_and_help)
        self.layout().addWidget(self.icon_grid)

        self.layout().setContentsMargins(5, 5, 5, 5)
        self.setMinimumWidth(345)

        self._on_selection()

    def _code_menu(self):
        menu = QMenu(self)

        for name, cb in self.actions:
            submenu = menu.addAction(name)
            submenu.triggered.connect(cb)

        menu.move(QCursor.pos())
        menu.show()

    def _workflow_menu(self):
        menu = QMenu(self)

        for name, cb in self.workflow_actions:
            submenu = menu.addAction(name)
            submenu.triggered.connect(cb)

        menu.move(QCursor.pos())
        menu.show()

    def _on_selection(self):
        for layer, (dw, gui) in self._layers.items():
            if layer in self._viewer.layers.selection:
                dw.show()    
            else:
                if layer in self._viewer.layers:
                    dw.hide()
        self._highlight_next_steps()

        try:
            _modify_layer_gui(self._viewer)
        except:
            pass

    def _highlight_next_steps(self):
        def dock_widget_category(name):
            if dw.name in CATEGORIES:
                return CATEGORIES[dw.name]
            return get_category_of_function(func_name=dw.name)

        highlighted_categories = []
        for layer, (dw, gui) in self._layers.items():
            if layer in self._viewer.layers.selection:
                category = dock_widget_category(dw.name) 
                if category is not None:
                    highlighted_categories += category.next_step_suggestions

                
        for key in CATEGORIES:
            try:
                self.icon_grid.item_mapping[key].setBackground(
                    _get_background_brush()
                )
            except RuntimeError:
                continue
            if key in highlighted_categories:
                self.icon_grid.item_mapping[key].setBackground(
                    _get_highlight_brush()
                )
        

    def _on_active_layer_change(self, event):
        for layer, (dw, gui) in self._layers.items():
            dw.show() if event.value is layer else dw.hide()

    def _on_layer_removed(self, event):
        layer = event.value
        if layer in self._layers:
            dw = self._layers[layer][0]
            try:
                self._viewer.window.remove_dock_widget(dw)
            except KeyError:
                pass
            # remove layer from internal list
            self._layers.pop(layer)


    def _on_item_clicked(self, item):
        self._activate(CATEGORIES.get(item.text()))

    def _get_active_layer(self):
        return self._viewer.layers.selection.active

    def _activate(self, category = Union[Category, Callable]):
        if callable(category):
            category()
            return

        # get currently active layer (before adding dock widget)
        input_layer = self._get_active_layer()
        if not input_layer:
            warn("Please select a layer first")
            return

        # make a new widget
        gui = make_gui_for_category(category, self.seach_field.text(), self._viewer,autocall=category.auto_call)
        # prevent auto-call when adding to the viewer, to avoid double calls
        # do this here rather than widget creation for the sake of
        # non-Assistant-based widgets.
        gui._auto_call = False
        # add gui to the viewer
        dw = self._viewer.window.add_dock_widget(gui, area="right", name=category.name)
        # workaround for https://github.com/napari/napari/issues/4348
        dw._close_btn = False
        # make sure the originally active layer is the input
        try:
            gui.input0.value = input_layer
        except ValueError:
            pass # this happens if input0 should be labels but we provide an image
        # call the function widget &
        # track the association between the layer and the gui that generated it
        if category.output in ['image', 'labels']:
            layer = gui()
            if layer is not None:
                self._layers[layer] = (dw, gui)
        # optionally turn on auto_call, and make sure that if the input changes we update
        gui._auto_call = category.auto_call
        self._connect_to_all_layers()
        self._on_selection()
        return gui

    def _refesh_data(self, event):
        self._refresh(event.source)

    def _refresh(self, changed_layer):
        """Goes through all layers and refreshs those which have changed_layer as input

        Parameters
        ----------
        changed_layer
        """
        for layer, (dw, mgui) in self._layers.items():
            for w in mgui:
                if w.value == changed_layer:
                    #mgui()
                    from napari_workflows import WorkflowManager
                    manager = WorkflowManager.install(self._viewer)
                    manager.invalidate([changed_layer.name])

    def _connect_to_all_layers(self):
        """Attach an event listener to all layers that are currently open in napari
        """
        for layer in self._viewer.layers:
            layer.events.data.disconnect(self._refesh_data)
            layer.events.data.connect(self._refesh_data)

    def load_sample_data(self, fname="Lund_000500_resampled-cropped.tif"):
        data_dir = Path(__file__).parent.parent / "data"
        self._viewer.open(str(data_dir / fname))

    def _id_to_name(self, id, dict):
        if id not in dict.keys():
            new_name = "image" + str(len(dict.keys()))
            dict[id] = new_name
        return dict[id]

    def to_python(self, filename=None):
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(self, "Save code as...", ".", "*.py")
        #return Pipeline.from_assistant(self).to_jython(filename)

        from napari_workflows import WorkflowManager
        manager = WorkflowManager.install(self._viewer)
        code = manager.to_python_code()

        if filename:
            filename = Path(filename).expanduser().resolve()
            filename.write_text(code)

    def to_notebook_using_napari(self, filename=None, execute=True):
        return self.to_notebook(filename, execute, True)

    def to_notebook(self, filename=None, execute=True, use_napari=False):
        if not filename:
            filename, _ = QFileDialog.getSaveFileName(self, "Save code as notebook...", ".", "*.ipynb")
        #return Pipeline.from_assistant(self).to_notebook(filename)

        if not filename.endswith(".ipynb"):
            filename += ".ipynb"

        from napari_workflows import WorkflowManager
        manager = WorkflowManager.install(self._viewer)
        code = manager.to_python_code(notebook=True, use_napari=use_napari)

        import jupytext

        # jython code is created in the jupytext light format
        # https://jupytext.readthedocs.io/en/latest/formats.html#the-light-format

        jt = jupytext.reads(code, fmt="py:light")
        nb = jupytext.writes(jt, fmt="ipynb")
        if filename:
            filename = Path(filename).expanduser().resolve()
            filename.write_text(nb)
            # could use a NamedTemporaryFile to run this even without write
            if execute:
                from subprocess import Popen
                from shutil import which

                executable = "jupyter-lab"
                if not which(executable):
                    executable = "jupyter-notebook"
                    if not which(executable):
                        raise RuntimeError("Cannot find jupyter-lab or jupyter-notebook executable. Please install it using pip install jupyterlab")

                try:
                    Popen([executable, "-y", str(filename)])
                except Exception as e:
                    warn(f"Failed to execute notebook: {e}")
        return nb

    def to_napari_plugin(self):
        from napari_assistant_plugin_generator import make_plugin
        self._viewer.window.add_dock_widget(make_plugin())

    def to_clipboard(self):
        import pyperclip

        from napari_workflows import WorkflowManager
        manager = WorkflowManager.install(self._viewer)
        pyperclip.copy(manager.to_python_code())

    def to_script_editor(self):
        import napari_script_editor
        editor = napari_script_editor.ScriptEditor.get_script_editor_from_viewer(self._viewer)

        from napari_workflows import WorkflowManager
        manager = WorkflowManager.install(self._viewer)
        editor.set_code(manager.to_python_code())

    def to_file(self, filename=None):
        from napari_workflows import WorkflowManager, _io_yaml_v1

        if not filename:
            filename, _ = QFileDialog.getSaveFileName(self, "Export workflow ...", ".", "*.yaml")

        # get the workflow, should one be installed
        workflow_manager = WorkflowManager.install(self._viewer)
        _io_yaml_v1.save_workflow(filename, workflow_manager.workflow)

    def load_workflow(self, filename=None):
        from napari_workflows import _io_yaml_v1
        from .. _workflow_io_utility import initialise_root_functions, load_remaining_workflow

        layer_names = [str(lay) for lay in self._viewer.layers]
        if not layer_names:
            warn("No images opened. Please open an image before loading the workflow!")
            return

        if not filename:
            filename, _ = QFileDialog.getOpenFileName(self, "Import workflow ...", ".", "*.yaml")
        if filename == '':
            # nothing loaded
            return
        self.workflow = _io_yaml_v1.load_workflow(filename)

        w_dw = initialise_root_functions(
            self.workflow, 
            self._viewer,
        )
        w_dw += load_remaining_workflow(
            self.workflow, 
            self._viewer,
        )

        for gui, dw in w_dw:
            # call the function widget &
            # track the association between the layer and the gui that generated it
            category = get_category_of_function(
                find_function(gui.op_name.current_choice)
            )
            if category.output in ['image', 'labels']:
                layer = gui()
                if layer is not None:
                    self._layers[layer] = (dw, gui)

        self._viewer.layers.select_previous()
        self._viewer.layers.select_next()

    def undo_action(self):
        if len(self._viewer.dims.current_step) > 3:
            raise NotImplementedError("Undo/redo is not supported for 4D data (yet).")

        from .._undo_redo import clear_and_load_workflow, _change_widget_parameters#
        from napari_workflows import WorkflowManager, Workflow
        # install the workflow manager and get the current workflow and controller
        manager: WorkflowManager = WorkflowManager.install(self._viewer)
        controller = manager.undo_redo_controller
        workflow: Workflow = manager.workflow
        # only reload if there is an undo to be performed
        if controller.undo_stack:

            # undo workflow step: workflow is now the undone workflow
            undo_wf: Workflow = controller.undo()
            controller.freeze_stacks = True
            if set(undo_wf._tasks.keys()) == set(workflow._tasks.keys()):
                widgets_dict = {
                    key:self._layers[self._viewer.layers[key]][1] 
                    for key in workflow._tasks.keys()
                }
                _change_widget_parameters(
                    manager_workflow=workflow,
                    updated_workflow=undo_wf,
                    widgets=widgets_dict)
            else:
                clear_and_load_workflow(
                    viewer=self._viewer,
                    manager_workflow=workflow,
                    workflow_to_load=undo_wf,
                    layer_list=self._layers
                )

            controller.freeze_stacks = False            

    def redo_action(self):
        if len(self._viewer.dims.current_step) > 3:
            raise NotImplementedError("Undo/redo is not supported for 4D data (yet).")

        from .._undo_redo import clear_and_load_workflow, _change_widget_parameters
        from napari_workflows import WorkflowManager, Workflow

        # install the workflow manager and get the current workflow and controller
        manager: WorkflowManager = WorkflowManager.install(self._viewer)
        controller = manager.undo_redo_controller
        workflow = manager.workflow
        # only reload if there is an undo to be performed
        if controller.redo_stack:

            # undo workflow step: workflow is now the undone workflow
            redo_wf: Workflow = controller.redo()
            controller.freeze_stacks = True
            if len(redo_wf._tasks.keys()) == len(workflow._tasks.keys()):
                widgets_dict = {
                    key:self._layers[self._viewer.layers[key]][1] 
                    for key in workflow._tasks.keys()
                }
                _change_widget_parameters(
                    manager_workflow=workflow,
                    updated_workflow=redo_wf,
                    widgets=widgets_dict)
            else:
                clear_and_load_workflow(
                    viewer=self._viewer,
                    manager_workflow = workflow,
                    workflow_to_load=redo_wf,
                    layer_list=self._layers
                )

            controller.freeze_stacks = False

    def search_napari_hub(self):
        print("Search napari hub")
        from urllib.parse import quote
        _open_url("https://www.napari-hub.org/?search=" + quote(self.seach_field.text()) + "&sort=relevance")

    def search_image_sc(self):
        print("Search image sc")
        from urllib.parse import quote
        _open_url("https://forum.image.sc/search?q=napari%20" + quote(self.seach_field.text()))

    def search_biii(self):
        print("Search biii")
        from urllib.parse import quote
        _open_url("https://biii.eu/search?search_api_fulltext=napari%20" + quote(self.seach_field.text()))


def _open_url(url):
    import webbrowser
    webbrowser.open(url, new=0, autoraise=True)

# see https://github.com/napari/napari/issues/5127
def _modify_layer_gui(viewer):
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter(action='ignore', category=FutureWarning)
        from napari._qt.layer_controls.qt_layer_controls_container import QtLayerControlsContainer
        from napari._qt.layer_controls.qt_image_controls import QtImageControls
        from napari._qt.layer_controls.qt_image_controls_base import range_to_decimals
        from qtpy.QtWidgets import QPushButton

        # search for GUI in napari viewer
        obj = viewer.window.qt_viewer.dockLayerControls
        for i in range(obj.layout().count()):
            if obj.layout().itemAt(i) is not None and obj.layout().itemAt(i).widget is not None:
                item = obj.layout().itemAt(i).widget()
                if isinstance(item, QtLayerControlsContainer):
                    layer_controls = item
                    if layer_controls is not None:
                        obj2 = layer_controls
                        for i in range(obj2.layout().count()):
                            if obj2.layout().itemAt(i) is not None:
                                item = obj2.layout().itemAt(i).widget()
                                if isinstance(item, QtImageControls):
                                    image_controls = item

                                    if image_controls is not None:
                                        # Modify GUI: Add a "Reset" button to the auto-contrast button bar
                                        def reset_display_range():
                                            layer = list(viewer.layers.selection)[0]
                                            layer.contrast_limits_range = [layer.data.min(), layer.data.max()]
                                            layer.contrast_limits = list(layer.contrast_limits_range)

                                            contrastLimitsSlider = image_controls.contrastLimitsSlider
                                            decimals = range_to_decimals(
                                                layer.contrast_limits_range, layer.dtype
                                            )
                                            contrastLimitsSlider.setRange(*layer.contrast_limits_range)
                                            contrastLimitsSlider.setSingleStep(10 ** -decimals)
                                            contrastLimitsSlider.setValue(layer.contrast_limits)

                                        autoscalebar_widget = image_controls.autoScaleBar
                                        if autoscalebar_widget is not None and not hasattr(autoscalebar_widget, "_reset_button"):
                                            autoscalebar_widget._reset_button = QPushButton(('Reset'))
                                            autoscalebar_widget._reset_button.clicked.connect(reset_display_range)
                                            autoscalebar_widget.layout().addWidget(autoscalebar_widget._reset_button)
                                            autoscalebar_widget._auto_btn.setText("Cont.")

