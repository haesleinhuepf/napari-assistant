from napari_assistant._workflow_io_utility import load_remaining_workflow, initialise_root_functions
from napari_workflows import WorkflowManager
from napari import Viewer

def delete_workflow_widgets_layers(viewer: Viewer):
    """
    Deletes all layers which were created by widgets and closes the widgets prior

    Parameters
    ----------
    viewer: napari.Viewer
    """
    # install the workflow manager and get the current workflow
    manager = WorkflowManager.install(viewer)
    workflow = manager.workflow
    
    #deleting the widgets based on the workflow
    dock_widgets = viewer.window._dock_widgets
    workflow_nodes = list(workflow._tasks.keys())
    for key, widget in list(dock_widgets.items()):
        if ('Result of ' + key in workflow_nodes) or ('Result of '+key[:-22] in workflow_nodes):
            viewer.window.remove_dock_widget(widget=widget)
    
    #deleting the layers if created by a widget
    layers = viewer.layers
    layer_names = [str(lay) for lay in layers]
    for layer_name in layer_names:
        if layers[layer_name].source.widget:
            layers.remove(layer_name)

def undo(viewer: Viewer):
    """
    Deletes all layers which were created by widgets and closes the widgets prior

    Parameters
    ----------
    viewer: napari.Viewer
    """
    # install the workflow manager and get the current workflow and controller
    manager = WorkflowManager.install(viewer)
    workflow = manager.workflow
    controller = manager.undo_redo_controller
    
    
    # only reload if there is an undo to be performed
    if controller.undo_stack:

        # undo workflow step: workflow is now the undone workflow
        controller.undo()

        controller.freeze = True # no actions recorded or performed on workflow
        delete_workflow_widgets_layers(viewer)
        
        initialise_root_functions(workflow=workflow,
                                  viewer=viewer)
        load_remaining_workflow(workflow=workflow,
                                viewer=viewer)
        controller.freeze = False