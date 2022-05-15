from napari_assistant._workflow_io_utility import load_remaining_workflow, initialise_root_functions
from napari_workflows import WorkflowManager, Workflow
from napari import Viewer
from ._gui._category_widget import DEFAULT_BUTTON_SIZE

def delete_workflow_widgets_layers(viewer: Viewer) -> None:
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

def clear_and_load_workflow(
    viewer: Viewer,
    manager_workflow: Workflow, 
    workflow_to_load: Workflow,
    layer_list:list,
    button_size = DEFAULT_BUTTON_SIZE
) -> list:
    """
    Loads a workflow by only initializing operations where the workflow
    is different from the currently loaded workflow.
    """
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

    from ._categories import find_function, get_category_of_function
    for gui, dw in w_dw:
        # call the function widget and
        # track the association between the layer and the gui that generated it
        category = get_category_of_function(
            find_function(gui.op_name.current_choice)
        )
        if category.output in ['image', 'labels']:
            layer = gui()
            if layer is not None:
                layer_list[layer] = (dw, gui)

    viewer.layers.select_previous()
    viewer.layers.select_next()

# EXPERIMENTAL        
def _change_widget_parameters(
    manager_workflow: Workflow, 
    updated_workflow:Workflow,
    widgets: dict,
) -> None:
    """
    Go through two workflows and update widgets where the workflows are different
    """
    from ._workflow_io_utility import category_kwargs, kwargs_of_wf_step

    for key in manager_workflow._tasks.keys():
        if manager_workflow._tasks[key] != updated_workflow._tasks[key]:
            kwargs = kwargs_of_wf_step(updated_workflow,key)
            for param_name, value in kwargs.items():
                if value in manager_workflow.sources_of(key):
                    pass # change input image
        
            widget = widgets[key]

            # setting the right parameters
            cat_kwargs = category_kwargs(
                updated_workflow._tasks[key][0],
                kwargs,
            )
            for k,v in cat_kwargs.items():
                widget[k].value = v

        