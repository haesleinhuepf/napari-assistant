from inspect import signature
from napari.utils._magicgui import _make_choice_data_setter
from ._categories import get_category_of_function, get_name_of_function
from ._gui._category_widget import (
    separate_argnames_by_type,
    kwarg_key_adapter,
    make_gui_for_category,
    DEFAULT_BUTTON_SIZE,
    LAYER_NAME_PREFIX,
)
from napari import Viewer
from napari_workflows import Workflow

# TODO look if comments are accurate
def initialise_root_functions(workflow: Workflow, viewer: Viewer, button_size: int = DEFAULT_BUTTON_SIZE):
    """
    Makes widgets for all functions which have a root image as input. The widgets are 
    added to the viewer and correct input images must be chosen to complete the loading
    of the workflow if they are not already present in the layers

    Parameters
    ----------
    workflow:
        napari-workflow object
    viewer:
        napari.Viewer instance
    button_size: int
        button size parameter that is passed to make_category_gui    
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
        
        # if more than one source is needed autocall needs to be set to false
        # in order to avoid crashing
        if len(sources) > 1:
            widget = make_flexible_gui(
                func, 
                viewer,
                autocall= False,
                button_size = button_size,
            )
        else:
            widget = make_flexible_gui(
                func, 
                viewer, 
                button_size = button_size,
            )
            widget._auto_call = False

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
            # open to chose the right image - make a tooltip which tells the 
            # user to select the input image specified by the workflow
            key_source_list = get_source_keywords_and_sources(workflow,
                                                            wf_step_name)
            for key, source in key_source_list:
                widget[key].tooltip = f'Select {source} or equivalent'

            # add the final widget to the napari viewer
            dw = viewer.window.add_dock_widget(widget, name = wf_step_name[10:] + '<b> - SELECT INPUT</b>')
        
        # setting the right parameters
        cat_kwargs = category_kwargs(
            func,
            kwargs_of_wf_step(workflow,wf_step_name),
        )
        for k,v in cat_kwargs.items():
            widget[k].value = v
        
        if len(sources) <2:
            widget._auto_call = True
        # calling the widget with the correct input images
        widget()
        widget_dw.append((widget,dw))
    
    return widget_dw

def load_remaining_workflow(workflow: Workflow, viewer: Viewer, button_size: int = DEFAULT_BUTTON_SIZE):
    """
    Loads the remaining workflow once initialise_root_functions has been called with
    the same workflow and the same napari viewer with given button sie. Returns widgets
    and respective dockwidgets as a list of tupules: [(widget, dockwidget)]

    Parameters
    ----------
    workflow:
        napari-workflow object
    viewer:
        napari.Viewer instance
    button_size: int
        button size parameter that is passed to make_category_gui
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
            continue    

        # if all input images are there we can continue
        
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
            widget._auto_call = False
        # add the final widget to the napari viewer and set the input images in
        # the dropdown to the specified input images
        dw = viewer.window.add_dock_widget(
            widget, 
            name= follower[len(LAYER_NAME_PREFIX):],
            )
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

        if len(sources) <2:
            widget._auto_call = True
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

def make_flexible_gui(func, viewer: Viewer, autocall: bool = True, button_size: int = DEFAULT_BUTTON_SIZE):
    """
    Function returns a widget with a GUI for the function provided in the parameters,
    that can be added to the napari viewer.

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
    button_size: int
        button size parameter that is passed to make_category_gui
    """
    gui = None
    category = get_category_of_function(func)

    if category is None:
        raise ModuleNotFoundError("Cannot build user interface for not installed function " + str(func))
    else:
        gui = make_gui_for_category(
            category, 
            viewer=viewer, 
            operation_name=get_name_of_function(func), 
            autocall=autocall, 
            button_size= button_size
        )

    return gui

def set_choices(workflow: Workflow, wf_step_name: str, viewer: Viewer, widget):
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
    adapter = kwarg_key_adapter(func)
    keyword_list = list(signature(func).parameters.keys())
    image_keywords = [(key,value) for key, value in zip(keyword_list,args) if value in sources]

    for i, (key, name) in enumerate(image_keywords):
        widget[adapter[key]].choices = get_layers_data_of_name(name, viewer, widget[adapter[key]])

def get_layers_data_of_name(layer_name: str, viewer: Viewer, gui):
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

def wf_steps_with_root_as_input(workflow: Workflow):
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

def get_source_keywords_and_sources(workflow: Workflow, wf_step_name: str):
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
    adapter = kwarg_key_adapter(func)
    
    sources = workflow.sources_of(wf_step_name)
    keyword_list = list(signature(func).parameters.keys())
    image_keywords = [
        (adapter[key],value) for key, value in zip(keyword_list,args) if value in sources
    ]
    
    return image_keywords

def category_kwargs(func,kwargs):
    """
    Returns a dict of kwargs mapping the napari assistant keywords to 
    the values specified by the functions

    Parameters
    ----------
    func: function
        input function for which the assistant kwargs should be generated for
    kwargs: dict
        kwargs of func
    """
    category_kwargs = {}
    adapter = kwarg_key_adapter(func)

    sig = signature(func)
    # get the names of positional parameters in the new operation
    param_names, foo, bar, foobar, fbar = separate_argnames_by_type(
        sig.parameters.items())

    category_kwargs = {adapter[key] : kwargs[key] for key in param_names}

    return category_kwargs

def kwargs_of_wf_step(
    workflow: Workflow, 
    wf_step_name: str
) -> dict:
    """
    Returns a dictionary with kwargs specified by the function and parameters
    of a specific workflow step

    Parameters
    ----------
    workflow:
        workflow object specifying functions and parameters
    wf_step_name:
        name of the worflow step for which the kwargs will be generated
    """
    func     = workflow._tasks[wf_step_name][0]
    arg_vals = workflow._tasks[wf_step_name][1:]

    # getting the keywords corresponding to the values
    keyword_list = list(signature(func).parameters.keys())

    # creating the kwargs dict
    kw_dict = {}
    for kw, val in zip(keyword_list, arg_vals):
        kw_dict[kw] = val
        
    return kw_dict

