from __future__ import annotations

from inspect import Parameter, Signature, signature

from qtpy import QtCore
from qtpy.QtCore import QTimer
from qtpy.QtWidgets import QDoubleSpinBox, QComboBox, QWidget

from typing import Any, Optional, TYPE_CHECKING, Sequence
from functools import partial

import toolz
from loguru import logger
from magicgui import magicgui
from typing_extensions import Annotated
import napari
import numpy as np

from .._categories import Category, find_function, get_name_of_function
from qtpy.QtWidgets import QPushButton, QDockWidget
from magicgui.types import PathLike

try:
    import pyclesperanto_prototype as clep
    Image_type = clep.Image
except:
    Image_type = np.ndarray
try:
    import pyclesperanto as cle
    Image_type2 = cle.Image
except:
    Image_type2 = np.ndarray

if TYPE_CHECKING:
    from napari.layers import Layer
    from napari import Viewer

VIEWER_PARAM = "viewer"
OP_NAME_PARAM = "op_name"
OP_ID = "op_id"
DEFAULT_BUTTON_SIZE = 40
LAYER_NAME_PREFIX = "Result of "
# We currently support operations with up to 6 numeric parameters, 3 booleans and 3 strings (see lists below)
FloatRange = Annotated[float, {"min": np.finfo(np.float32).min, "max": np.finfo(np.float32).max, "step": 1}]
BoolType = Annotated[bool, {}]
StringType = Annotated[str, {}]
PathLikeType = Annotated[PathLike, {}]

PositiveFloatRange = Annotated[float, {"min": 0, "max": np.finfo(np.float32).max}]
category_args = [
    ("x", FloatRange, 0),
    ("y", FloatRange, 0),
    ("z", FloatRange, 0),
    ("u", FloatRange, 0),
    ("v", FloatRange, 0),
    ("w", FloatRange, 0),
    ("w1", FloatRange, 0),
    ("w2", FloatRange, 0),
    ("w3", FloatRange, 0),
    ("w4", FloatRange, 0),
    ("a", BoolType, False),
    ("b", BoolType, False),
    ("c", BoolType, False),
    ("d", BoolType, False),
    ("e", BoolType, False),
    ("f", BoolType, False),
    ("g", BoolType, False),
    ("h", BoolType, False),
    ("i", BoolType, False),
    ("j", BoolType, False),
    ("k", StringType, ""),
    ("l", StringType, ""),
    ("m", StringType, ""),
    ("o", PathLikeType, ""),
    ("p", PathLikeType, ""),
    ("q", PathLikeType, ""),
]
category_args_numeric = ["x", "y", "z", "u", "v", "w", "w1", "w2", "w3", "w4"]
category_args_bool = ["a", "b", "c", "d", "e", "f", "g","h","i","j"]
category_args_text = ["k", "l", "m"]
category_args_file = ["o", "p", "q"]

def num_positional_args(func, types=[np.ndarray, napari.types.ImageData, napari.types.LabelsData, Image_type, Image_type2, int, str, float, bool]) -> int:
    params = signature(func).parameters
    return len([p for p in params.values() if p.annotation in types])

def kwarg_key_adapter(func):
    '''
    Returns a dictionary mapping keywords between the category kwarg keys used
    by the napari assistant to the kwarg keys of the input functions as well
    as the reverse mapping.

    Parameters
    ----------

    func: function
        the function for which the mapping should be generated
    '''
    adapter = {}
    sig = signature(func)
    items = sig.parameters.items()
    # get the names of positional parameters in the new operation
    param_names, numeric_param_names, bool_param_names, str_param_names, file_param_names = separate_argnames_by_type(
        items)

    # go through all parameters and collect their values in an args-array
    num_count = 0
    str_count = 0
    bool_count = 0
    file_count = 0
    for key in param_names: 
        if key in numeric_param_names:
            adapter[category_args_numeric[num_count]] = key
            adapter[key] = category_args_numeric[num_count]
            num_count += 1
        elif key in bool_param_names:
            adapter[category_args_bool[bool_count]] = key
            adapter[key] = category_args_bool[bool_count]
            bool_count += 1
        elif key in str_param_names:
            adapter[category_args_text[str_count]] = key
            adapter[key] = category_args_text[str_count]
            str_count += 1
        elif key in file_param_names:
            adapter[category_args_file[file_count]] = key
            adapter[key] = category_args_file[file_count]
            file_count += 1

    other_count = 0    
    other_param_names = [
        name
        for name, param in items
        if param.annotation not in {int, str, float, bool, PathLike}
    ]
    for key in other_param_names:
        adapter["input" + str(other_count)] = key
        adapter[key] = "input" + str(other_count)
        other_count += 1

    return adapter

@logger.catch
def call_op(op_name: str, inputs: Sequence[Layer], timepoint : int = None, viewer: napari.Viewer = None, **kwargs) -> np.ndarray:
    """Call operation `op_name` with specified inputs and args.

    Takes care of transfering data to GPU and omitting extra positional args

    Parameters
    ----------
    op_name : str
        name of operation to execute.
    inputs : Sequence[Layer]
        The napari layer inputs

    Returns
    -------
    np.ndarray
        result image
    """

    if not inputs or inputs[0] is None:
        return

    i0 = inputs[0].data
    gpu_ins = [i.data if i is not None else i0 for i in inputs]

    # call actual cle function ignoring extra positional args
    cle_function = find_function(op_name)
    nargs = num_positional_args(cle_function)


    new_sig = signature(cle_function)
    adapter = kwarg_key_adapter(cle_function)
    # get the names of positional parameters in the new operation
    param_names, _, _, _, _ = separate_argnames_by_type(
        new_sig.parameters.items())

    args = tuple([kwargs[adapter[key]] for key in param_names])

    # in case of clesperanto ops, we need to inject "None" for the output
    if "pyclesperanto" in cle_function.__module__:
        # todo: we should handle all functions equally
        gpu_out = None

        logger.info(f"{op_name}(..., {', '.join(map(str, args))})")
        args = ((*gpu_ins, gpu_out) + args)[:nargs]

        gpu_out = cle_function(*args, viewer=viewer)

        # return output
        return gpu_out, args
    else:
        args = (*gpu_ins, *args)[:nargs+1]

        import inspect
        sig = inspect.signature(cle_function)

        # pass viewer if requested
        kwargs = {}
        for k, v in sig.parameters.items():
            if k == "viewer" or k == "napari_viewer" or "napari.viewer.Viewer" in str(v):
                kwargs[k] = viewer

        # Make sure that the annotated types are really passed to a given function
        for i, k in enumerate(list(sig.parameters.keys())):
            if i >= len(args):
                break
            type_annotation = str(sig.parameters[k].annotation)
            #print("Annotation:", type_annotation)
            args = list(args)
            for typ in ["int", "float", "str"]:
                if typ in type_annotation:
                    converter = eval(typ)
                    #print("converter", converter)
                    args[i] = converter(args[i])

        gpu_out = cle_function(*args, **kwargs)

        if sig.return_annotation in [napari.types.LabelsData, "napari.types.LabelsData"]:
            if gpu_out.dtype is not int:
                gpu_out = gpu_out.astype(int)

        return gpu_out, args


def _show_result(
    gpu_out: np.ndarray,
    viewer: Viewer,
    name: str,
    layer_type: str,
    op_id: int,
    translate=None,
    cmap=None,
    blending=None,
    scale=None,
) -> Optional[Layer]:
    """Show `gpu_out` in the napari viewer.

    Parameters
    ----------
    gpu_out : np.ndarray
        an image to show
    viewer : napari.Viewer
        The napari viewer instance
    name : str
        The name of the layer to create or update.
    layer_type : str
        the layer type to create (must be 'labels' or 'image)
    op_id : int
        an ID to associate with the newly created layer (will be added to
        layer.metada['op_id'])
    translate : [type], optional
        translate parameter for layer creation, by default None
    cmap : str, optional
        a colormap to use for images, by default None
    blending : str, optional
        blending mode for visualization, by default None

    Returns
    -------
    layer : Optional[Layer]
        The created/udpated layer, or None if no viewer is present.
    """
    if layer_type == "dataframe":
        # todo: in case an operation returns a dataframe; do we need to do anything with it?
        return None

    #print("OP ID ", op_id)
    if not viewer:
        logger.warning("no viewer, cannot add image")
        return
    # show result in napari
    if "dask" in str(type(gpu_out)):
        clims = None
    else:
        clims = [gpu_out.min(), gpu_out.max()]

        if clims[1] == 0:
            clims[1] = 1

        if clims[0] == clims[1]:
            clims = None

    # conversion will be done inside napari. We can continue working with the potentially OCL-array from here.
    data = gpu_out

    try:
        # look for an existing layer
        layer = next(x for x in viewer.layers if isinstance(x.metadata, dict) and x.metadata.get(OP_ID) == op_id)
        # logger.debug(f"updating existing layer: {layer}, with id: {op_id}")
        layer.data = data
        layer.name = name
        # layer.translate = translate
    except StopIteration:
        # otherwise create a new one
        # logger.debug(f"creating new layer for id: {op_id}")
        add_layer = getattr(viewer, f"add_{layer_type}")
        kwargs = dict(name=name, metadata={OP_ID: op_id})
        if layer_type == "image":
            kwargs["colormap"] = cmap
            kwargs["blending"] = blending
            kwargs['contrast_limits'] = clims

        layer = add_layer(data, **kwargs)

    if scale is not None:
        if len(layer.data.shape) == len(scale):
            layer.scale = scale
        if len(layer.data.shape) < len(scale):
            layer.scale = scale[-len(layer.data.shape):]
    return layer


def _generate_signature_for_category(category: Category, search_string:str= None, viewer:napari.Viewer = None) -> Signature:
    """Create an inspect.Signature object representing a cle Category.

    The output of this function can be used to set function.__signature__ so that
    magicgui can convert it into the appropriate widget.
    """
    if search_string is not None:
        search_string = search_string.lower()

    k = Parameter.KEYWORD_ONLY

    # add inputs (we name them inputN ...)
    params = [
        Parameter(f"input{n}", k, annotation=t) for n, t in enumerate(category.inputs)
    ]
    # Add valid operations choices (will create the combo box)
    from .._categories import operations_in_menu
    choices = list(operations_in_menu(category, search_string))
    #print("choices:", choices)
    op_type = Annotated[str, {"choices": choices, "label": "Operation"}]
    default_op = category.default_op
    if not any(default_op == op for op in choices):
        #print("Default-operation is not in list!")
        default_op = None

    if default_op is None:
        params.append(
            Parameter(OP_NAME_PARAM, k, annotation=op_type)
        )
    else:
        params.append(
            Parameter(OP_NAME_PARAM, k, annotation=op_type, default=default_op)
        )
    # add the args that will be passed to the cle operation.
    for i, (name, type_, default) in enumerate(category_args):
        if i < len(category.default_values):
            default = category.default_values[i]
        params.append(Parameter(name, k, annotation=type_, default=default))

    # add a viewer.  This allows our widget to know if it's in a viewer
    params.append(
        Parameter(VIEWER_PARAM, k, annotation="napari.viewer.Viewer", default=viewer)
    )
    result = Signature(params)
    #print("Signature", result)
    return result

def _get_operation_name_for_category_clicked(category: Category, search_string:str= None) -> str:
    """Create an inspect.Signature object representing a cle Category.

    The output of this function is the operation name for a clicked cataegory given a search string
    """
    # Add valid operations choices (will create the combo box)
    from .._categories import operations_in_menu
    choices = list(operations_in_menu(category, search_string))

    default_op = category.default_op
    if not any(default_op == op for op in choices):
        #print("Default-operation is not in list!")
        default_op = None

    if default_op is None:
        return choices[0]
        
    else:
        return default_op

def make_gui_for_category(category: Category, search_string:str = None, viewer: napari.Viewer = None, button_size=DEFAULT_BUTTON_SIZE, operation_name:str=None, autocall:bool=True) -> magicgui.widgets.FunctionGui[Layer]:
    """Generate a magicgui widget for a Category object

    Parameters
    ----------
    category : Category
        An instance of a _categories.Category. (holds information about the cle operations,
        input types, and arguments that the widget needs to represent.)

    Returns
    -------
    magicgui.widgets.FunctionGui
        A magicgui widget instance
    """
    widget = None
    def gui_function(**kwargs) -> Optional[Layer]:
        """A function that calls a cle operation `call_op` and shows the result.

        This is the function that will be called by our magicgui widget.
        We modify it's __signature__ below.
        """
        viewer = kwargs.pop(VIEWER_PARAM, None)
        inputs = []
        for i in [kwargs.pop(k) for k in list(kwargs) if k.startswith("input")]:
            if isinstance(i, napari.layers.Layer):
                inputs.append(i)
            else:
                from napari_workflows._workflow import _get_layer_from_data
                inputs.append(_get_layer_from_data(viewer, i))

        result_layer = None
        t_position = None
        if viewer is not None and len(viewer.dims.current_step) == 4:
            # in case we process a 4D-data set, we need read out the current timepoint
            # and consider it further down in call_op
            t_position = viewer.dims.current_step[0]

            currstep_event = viewer.dims.events.current_step

            def update(event):
                #currstep_event.disconnect(update)
                if result_layer is not None:
                    from napari_workflows import WorkflowManager
                    manager = WorkflowManager.install(viewer)
                    manager.invalidate([result_layer.name])
                #widget()

            if hasattr(widget, 'updater'):
                currstep_event.disconnect(widget.updater)

            widget.updater = update

            currstep_event.connect(update)

        # todo: deal with 5D and nD data
        op_name = kwargs.pop("op_name")
        try:
            result, used_args = call_op(op_name, inputs, t_position, viewer, **kwargs)
        except TypeError as e:
            result = None
            used_args = []
            import warnings
            warnings.warn("Operation failed. Please check input parameters and documentation.\n" + str(e))

        # add a help-button
        description = find_function(op_name).__doc__
        if description is not None:
            description = description.replace("\n    ", "\n").replace("\n", "<br/>")
            getattr(widget, OP_NAME_PARAM).native.setToolTip("<html>" + description + "</html>")

        if result is not None:
            from napari.layers._source import layer_source
            with layer_source(widget=widget):
                result_layer = _show_result(
                    result,
                    viewer,
                    name=LAYER_NAME_PREFIX + f"{op_name}",
                    layer_type=category.output,
                    op_id=id(gui_function),
                    cmap=category.color_map,
                    blending=category.blending,
                    scale=inputs[0].scale,
                )
            if result_layer is None:
                return None

            # notify workflow manager that something was created / updated
            try:
                from napari_workflows import WorkflowManager
                manager = WorkflowManager.install(viewer)

                # this step basically separates actual arguments from kwargs as this can cause 
                # conflicts when setting the workflow step. 
                signat = signature(find_function(op_name))
                only_args = [
                    arg for arg, param in zip(used_args,signat.parameters.values()) 
                    if param.default is param.empty
                ]
                determined_kwargs = {
                    name:value for (name,param),value in zip(signat.parameters.items(),used_args) 
                    if not (param.default is param.empty)
                }
                # debugging prints
                #print(f'only arguments: {only_args}')
                #print(f'det kwargs:     {determined_kwargs}')
                manager.update(result_layer, find_function(op_name), *only_args, **determined_kwargs)
                #print("notified", result_layer.name, find_function(op_name))
            except ImportError:
                pass # recording workflows in the WorkflowManager is a nice-to-have at the moment.

            def _on_layer_removed(event):
                layer = event.value
                if layer in inputs or layer is result_layer:
                    try:
                        viewer.window.remove_dock_widget(widget.native)
                    # TODO find more elegant or specific solution 
                    # because this could break some stuff
                    except:
                        pass

            viewer.layers.events.removed.connect(_on_layer_removed)

            return result_layer
        return None

    gui_function.__name__ = f'do_{category.name.lower().replace(" ", "_")}'
    gui_function.__signature__ = _generate_signature_for_category(category, search_string, viewer)

    # create the widget
    widget = magicgui(gui_function, auto_call=autocall)
    widget.native.setMinimumWidth(100)
    modify_layout(widget.native, button_size=button_size)

    if operation_name == None:
        operation_name = _get_operation_name_for_category_clicked(category,search_string)
    
    # when the operation name changes, we want to update the argument labels
    # to be appropriate for the corresponding cle operation.
    op_name_widget = getattr(widget, OP_NAME_PARAM)
    op_name_widget.value = operation_name

    @op_name_widget.changed.connect
    def update_positional_labels(*_: Any):
        func = find_function(op_name_widget.value)
        new_sig = signature(func)
        # get the names of positional parameters in the new operation
        param_names, numeric_param_names, bool_param_names, str_param_names, file_param_names = separate_argnames_by_type(
            new_sig.parameters.items())
        num_count = 0
        str_count = 0
        bool_count = 0
        file_count = 0

        # show needed elements and set right label
        n_params = len(param_names)
        for n, arg in enumerate(category_args):
            arg_gui_name = arg[0]
            arg_gui_type = arg[1]
            wdg = getattr(widget, arg_gui_name)
            if arg_gui_type == FloatRange:
                if num_count < len(numeric_param_names):
                    arg_func_name = numeric_param_names[num_count]
                    num_count = num_count + 1
                else:
                    wdg.hide()
                    continue
            elif arg_gui_type == BoolType:
                if bool_count < len(bool_param_names):
                    arg_func_name = bool_param_names[bool_count]
                    bool_count = bool_count + 1
                else:
                    wdg.hide()
                    continue
            elif arg_gui_type == StringType:
                if str_count < len(str_param_names):
                    arg_func_name = str_param_names[str_count]
                    str_count = str_count + 1
                else:
                    wdg.hide()
                    continue
            elif arg_gui_type == PathLikeType:
                if file_count < len(file_param_names):
                    arg_func_name = file_param_names[file_count]
                    file_count = file_count + 1
                else:
                    wdg.hide()
                    continue
            else:
                arg_func_name = "?"
                print("Unsupported type:", arg_gui_type)
                continue

            wdg.label = arg_func_name
            wdg.text = arg_func_name
            wdg.show()

    # run it once to update the labels
    update_positional_labels()

    return widget


def modify_layout(widget, button_size = 32):
    QTimer.singleShot(100, partial(_modify_layout, widget, button_size))

def _modify_layout(widget, button_size=32):
    try:
        if hasattr(widget, "layout"):
            layout = widget.layout()
            if layout is not None:
                if isinstance(widget, QWidget):
                    layout.setContentsMargins(5, 1, 5, 1)
                    layout.setSpacing(0)

                for i in range(layout.count()):
                    w = layout.itemAt(i)
                    if isinstance(w.widget(), QDoubleSpinBox):
                        w.widget().setStyleSheet("""
                           QDoubleSpinBox::down-button{
                               width: {button_size};
                               height: {button_size}
                           }
                           QDoubleSpinBox::up-button{
                               height: {button_size};
                               width: {button_size};
                           }""".replace("{button_size}", str(button_size)))
                        w.widget().setMinimumHeight(button_size)
                    if isinstance(w.widget(), QComboBox):
                        w.widget().setMinimumHeight(button_size)
                        w.widget().view().setWordWrap(True)
                    modify_layout(w.widget(), button_size=button_size)
    except:
        pass

def separate_argnames_by_type(items):
    param_names = [
        name
        for name, param in items
        if param.annotation in {int, str, float, bool, PathLike}
    ]
    numeric_param_names = [
        name
        for name, param in items
        if param.annotation in {int, float}
    ]
    bool_param_names = [
        name
        for name, param in items
        if param.annotation in {bool}
    ]
    str_param_names = [
        name
        for name, param in items
        if param.annotation in {str}
    ]
    file_param_names = [
        name
        for name, param in items
        if param.annotation in {PathLike}
    ]
    return param_names, numeric_param_names, bool_param_names, str_param_names, file_param_names
