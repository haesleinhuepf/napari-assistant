from inspect import Signature, signature
from functools import partial
from napari.utils._magicgui import _make_choice_data_setter
from napari.types import ImageData, LabelsData
from sqlalchemy import within_group
from ._gui._category_widget import (
    separate_argnames_by_type,
    category_args_bool,
    category_args_numeric,
    category_args_text,
)
from napari import Viewer
from napari_workflows import Workflow, WorkflowManager

# TODO rewrite all comments to display the right thing
def initialise_root_functions(workflow, viewer, button_size = 32):
    """
    Makes widgets for all functions which have a root image as input. The widgets are 
    added to the viewer and correct input images must be chosen to complete the loading
    of the workflow

    Parameters
    ----------
    workflow:
        napari-workflow object
    viewer:
        napari.Viewer instance
    """
    widget_dw = []

    # find all workflow steps with functions which have root images as an input
    root_functions = wf_steps_with_root_as_input(workflow)
    layer_names = [lay.name for lay in viewer.layers]

    # iterate over root function workflow steps
    for wf_step_name in root_functions:
        # get the fuction from the workflow step and change its signature to
        # the values specified by the workflow
        func = workflow._tasks[wf_step_name][0]

        # create the widget based on the adjusted function and turn off autocall
        # for functions with more than 1 input image
        sources = workflow.sources_of(wf_step_name)
        if len(sources) > 1:
            widget = make_flexible_gui(
                func, 
                viewer,
                autocall= False,
                button_size = button_size
            )
        else:
            widget = make_flexible_gui(
                func, 
                viewer,
                button_size=button_size,
            )

        # determine if all input images are in layer names
        sources_present = True
        for source in sources:
            if source not in layer_names:
                sources_present = False

        # if all input images are present in the layers we can preselct them
        if sources_present:
            dw = viewer.window.add_dock_widget(widget, name= wf_step_name[10:])
            set_choices(workflow= workflow,
                        wf_step_name= wf_step_name,
                        viewer= viewer,
                        widget= widget)
        
        
        else:
            # if the input images aren't present we will leave the dropdowns
            # open to chose the right image - TODO needs fixing
            '''
                # make a tooltip which tells the user to select the input image
                # specified by the workflow
                key_source_list = get_source_keywords_and_sources(workflow,
                                                                wf_step_name)
                for key, source in key_source_list:
                    widget[key].tooltip = f'Select {source} or equivalent'
            '''
            # add the final widget to the napari viewer
            dw = viewer.window.add_dock_widget(widget, name = wf_step_name[10:] + '<b> - SELECT INPUT</b>')
        
        # setting the right parameters
        cat_kwargs = category_kwargs(
            func,
            kwargs_of_wf_step(workflow,wf_step_name),
        )
        for k,v in cat_kwargs.items():
            widget[k].value = v
        

        # calling the widget with the correct input images
        widget()
        widget_dw.append((widget,dw))
    
    return widget_dw

def load_remaining_workflow(workflow, viewer, button_size):
    """
    Loads the remaining workflow once initialise_root_functions has been called with
    the same workflow and the same napari viewer

    Parameters
    ----------
    workflow:
        napari-workflow object
    viewer:
        napari.Viewer instance
    """
    # find all workflow steps with functions which have root images as an input
    root_functions = wf_steps_with_root_as_input(workflow)
    # get the layer object from the napari viewer
    layers = viewer.layers

    # start the iteration with the followers of the root functions
    followers = []
    widget_dw = []
    for root in root_functions:
        followers += workflow.followers_of(root)

    # iteration over followers: the list of followers gets bigger the more functions 
    # have been added with followers of their own
    for i,follower in enumerate(followers):
        # get current layer names
        layer_names = [str(lay) for lay in layers]
        # find all sources of the current function being added
        sources = workflow.sources_of(follower)

        # checking if we have all input images to the function in the napari layers
        sources_present = True
        for source in sources:
            if source not in layer_names:
                sources_present = False

        # if some input images are missing we will move to other functions first
        if not sources_present:
            if follower not in followers[i+1:]:
                followers.append(follower)

        # if all input images are there we can continue
        else:
            # get the fuction from the workflow step
            func = workflow._tasks[follower][0]

            # if more than one source is needed autocall needs to be set to false
            # in order to avoid crashing
            if len(sources) > 1:
                widget = make_flexible_gui(func, 
                                           viewer,
                                           autocall= False,
                                           button_size = button_size
                )
            else:
                widget = make_flexible_gui(func, 
                                           viewer, 
                                           button_size = button_size
                )

            # add the final widget to the napari viewer and set the input images in
            # the dropdown to the specified input images
            dw = viewer.window.add_dock_widget(widget, name= follower[10:])
            set_choices(workflow= workflow,
                        wf_step_name= follower,
                        viewer= viewer,
                        widget= widget)
            
            # setting the right parameters
            cat_kwargs = category_kwargs(
                func,
                kwargs_of_wf_step(workflow,follower),
            )
            for k,v in cat_kwargs.items():
                widget[k].value = v


            # calling the widget with the correct input images
            widget()

            widget_dw.append((widget,dw))
            # finding new followers of the current workflow step
            new_followers = workflow.followers_of(follower)

            # checking if the new followers are already in the que of workflow steps
            # to be added
            for new_follower in new_followers:
                if new_follower not in followers[i+1:]:
                    followers.append(new_follower)
        
    return widget_dw

# TODO remove
def load_workflow_undo_redo(
    new_workflow: Workflow, 
    viewer: Viewer):
    # init
    manager = WorkflowManager.install(viewer)

    # loading root functions
    init_undos = initialise_root_functions(new_workflow,viewer,undo_redo_loading=True)
    #for nothing in range(init_undos):
    #    manager.undo_redo_controller.undo()
    print(f'undos initialisation: {init_undos}') # TODO remove
    # loading remaining functions
    init_undos = load_remaining_workflow(new_workflow,viewer,undo_redo_loading=True)
    #for nothing in range(init_undos):
    #    manager.undo_redo_controller.undo()
    print(f'undos remaining workflow: {init_undos}') # TODO remove

def make_flexible_gui(func, viewer, autocall = True, button_size = 32):
    """
    Function returns a widget with a GUI for the function provided in the parameters,
    that can be added to the napari viewer. Largely copied from @haesleinhuepf (I can't remember where though)
    

    Parameters
    ----------
    func: 
        input function to generate the gui for
    viewer:
        napari.Viewer instance to which the widget is added
    wf_step_name: str
        name of the workflow step matching the function
    autocall: Boolean
        sets the auto_call behaviour of the magicgui.magicgui function
    """
    gui = None

    from ._categories import get_category_of_function, get_name_of_function
    category = get_category_of_function(func)

    if category is None:
        raise ModuleNotFoundError("Cannot build user interface for not installed function " + str(func))
    else:
        from ._gui._category_widget import make_gui_for_category
        gui = make_gui_for_category(
            category, 
            viewer=viewer, 
            operation_name=get_name_of_function(func), 
            autocall=autocall, 
            button_size= button_size
        )

    return gui

def signature_w_kwargs_from_function(workflow, wf_step_name) -> Signature:
    """
    Returns a new signature for a function in which the default values are replaced
    with the arguments specified in the workflow. Input images are not not specified 
    in the signature as this can only be done with set_choices

    Parameters
    ----------
    workflow: 
        napari-workflows object containing the function
    wf_step_name: str
        key of the workflow step for which the signature should be generated
    """
    func     = workflow._tasks[wf_step_name][0]
    arg_vals = workflow._tasks[wf_step_name][1:]

    # getting the keywords corresponding to the values
    keyword_list = list(signature(func).parameters.keys())

    # creating the kwargs dict
    kw_dict = {}
    for kw, val in zip(keyword_list, arg_vals):
        kw_dict[kw] = val

    dict_keys = list(kw_dict.keys())    
    input_image_names = workflow.sources_of(wf_step_name)
    for name in dict_keys:
        if ((kw_dict[name] in input_image_names) and (name != 'viewer')):
            kw_dict.pop(name)

    return signature(partial(func, **kw_dict))

def set_choices(workflow, wf_step_name: str, viewer, widget):
    """
    Sets the choices for image drop down menu to the images specified by the workflow

    Parameters
    ----------
    workflow:
        napari-workflow object
    wf_step_name: str
        the string of the workflow step for which the choices in the widget will
        be modified
    viewer:
        napari.Viewer instance
    widget:
        the magicgui FunctionGui object for which the input choices should be changed
    """
    func = workflow._tasks[wf_step_name][0]
    args = workflow._tasks[wf_step_name][1:]
    sources = workflow.sources_of(wf_step_name)

    keyword_list = list(signature(func).parameters.keys())
    image_keywords = [(key,value) for key, value in zip(keyword_list,args) if value in sources]

    for i, (key, name) in enumerate(image_keywords):
        try:
            widget[key].choices = get_layers_data_of_name(name, viewer, widget[key])
        except AttributeError:
            widget["input" + str(i)].choices = get_layers_data_of_name(name, viewer, widget["input" + str(i)])


def get_layers_data_of_name(layer_name: str, viewer, gui):
    """
    Returns a choices dictionary which can be utilised to set an input image of a 
    widget with the function set_choices. code modified from napari/utils/_magicgui
    get_layers_data function.

    Parameters
    ----------
    layer_name: str
        the layer which should be selected as the only choice in a drop down menu
    viewer:
        napari.Viewer instance
    gui:
        magicgui Combobox instance for which the choices should
    """
    choices = []
    for layer in [x for x in viewer.layers if str(x) == layer_name]:
        choice_key = f'{layer.name}'
        choices.append((choice_key, layer.data))
        layer.events.data.connect(_make_choice_data_setter(gui, choice_key))

    return choices

def wf_steps_with_root_as_input(workflow):
    """
    Returns a list of workflow steps that have root images as an input

    Parameters
    ----------
    workflow: 
        napari_workflows Workflow class
    """
    roots = workflow.roots()
    wf_step_with_rootinput = []
    for result, task in workflow._tasks.items():
            for source in task:
                if isinstance(source, str):
                    if source in roots:
                        wf_step_with_rootinput.append(result)
                        break
    return wf_step_with_rootinput

# TODO modify for category guis 
def get_source_keywords_and_sources(workflow, wf_step_name):
    """
    Returns a list of tuples containing (function_keyword, image_name) for all 
    sources of a workflow step with name: wf_step_name

    Parameters
    ----------
    workflow: 
        napari_workflows Workflow class
    wf_step_name: str
        name of the workflow step for which function keywords and image names
        should be returned
    """
    func = workflow._tasks[wf_step_name][0]
    args = workflow._tasks[wf_step_name][1:]
    
    sources = workflow.sources_of(wf_step_name)
    keyword_list = list(signature(func).parameters.keys())
    image_keywords = [(key,value) for key, value in zip(keyword_list,args) if value in sources]
    
    return image_keywords



def category_kwargs(func,kwargs):
    category_kwargs = {}
    new_sig = signature(func)
    # get the names of positional parameters in the new operation
    param_names, numeric_param_names, bool_param_names, str_param_names = separate_argnames_by_type(
        new_sig.parameters.items())

    # go through all parameters and collect their values in an args-array
    num_count = 0
    str_count = 0
    bool_count = 0
    for key in param_names: 
        if key in numeric_param_names:
            category_kwargs[category_args_numeric[num_count]] = kwargs[key]
            num_count = num_count + 1
        elif key in bool_param_names:
            category_kwargs[category_args_bool[bool_count]] = kwargs[key]
            bool_count = bool_count + 1
        elif key in str_param_names:
            category_kwargs[category_args_text[str_count]] = kwargs[key]
            str_count = str_count + 1
    return category_kwargs

def kwargs_of_wf_step(workflow,wf_step_name):
    func     = workflow._tasks[wf_step_name][0]
    arg_vals = workflow._tasks[wf_step_name][1:]

    # getting the keywords corresponding to the values
    keyword_list = list(signature(func).parameters.keys())

    # creating the kwargs dict
    kw_dict = {}
    for kw, val in zip(keyword_list, arg_vals):
        kw_dict[kw] = val
        
    return kw_dict

