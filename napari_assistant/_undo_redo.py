from napari_assistant._workflow_io_utility import load_remaining_workflow, initialise_root_functions
from napari_workflows import WorkflowManager, Workflow
from napari import Viewer

def delete_workflow_widgets_layers(viewer: Viewer):
    """
    Deletes all layers which were created by widgets and closes the widgets prior

    Parameters
    ----------
    viewer: napari.Viewer
    """
    # install the workflow manager and get the current workflow
    manager: WorkflowManager = WorkflowManager.install(viewer)
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

def clear_and_load_workflow(viewer: Viewer,manager_workflow: Workflow, workflow_to_load: Workflow, button_size = 32):
    delete_workflow_widgets_layers(viewer)
    manager_workflow.clear()

    w_dw = initialise_root_functions(
        workflow_to_load, 
        viewer, 
        button_size=button_size,
    )
    w_dw += load_remaining_workflow(
        workflow_to_load, 
        viewer,
        button_size=button_size,
    )
    return w_dw
            
def change_widget_parameters(manager_workflow: Workflow, updated_workflow:Workflow):
    from ._workflow_io_utility import category_kwargs, kwargs_of_wf_step
    for key in manager_workflow._tasks.keys():
        if manager_workflow._tasks[key] != updated_workflow._tasks[key]:
            if key in manager_workflow.sources_of(key):
                return # change input image
            # make adapter and change widget parameters
        widget = None # still need to find a way to access it!
        # setting the right parameters

        cat_kwargs = category_kwargs(
            updated_workflow._tasks[key][0],
            kwargs_of_wf_step(updated_workflow,key),
        )
        for k,v in cat_kwargs.items():
            widget[k].value = v

        