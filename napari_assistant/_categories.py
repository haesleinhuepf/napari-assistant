from dataclasses import dataclass, field
from typing import Any, Sequence, Tuple, Type

import numpy as np
import napari
from napari.layers import Image, Labels, Layer
from typing_extensions import Annotated
import inspect
from functools import lru_cache

ImageInput = Annotated[Image, {"label": "Image"}]
LayerInput = Annotated[Layer, {"label": "Image or labels"}]
LabelsInput = Annotated[Labels, {"label": "Labels"}]
global_magic_opts = {"auto_call": True}

next_steps_at_the_beginning = [
            "Remove noise",
            "Remove background",
            "Binarize",
            "Label",
            "Combine",
            "Filter",
        ]
next_steps_after_labeling = [
            "Process labels",
            "Combine labels",
            "Measure labels",
            "Measure labeled image",
            "Compare label images",
            "Measurement",
            "Mesh",
        ]
next_steps_after_measuring = [
            "Label filters",
            "Label neighbor filters"
        ]

@dataclass
class Category:
    name: str
    description: str
    inputs: Sequence[Type]
    default_op: str
    default_values : Sequence[float]
    next_step_suggestions: Sequence[str] = field(default_factory=list)
    output: str = "image"  # or labels or dataframe
    # categories
    include: Sequence[str] = field(default_factory=tuple)
    exclude: Sequence[str] = field(default_factory=tuple)
    # visualization
    color_map : str = "gray"
    blending : str = None
    tool_tip : str = ""
    tools_menu : str = None
    auto_call : bool = True


CATEGORIES = {
    "Remove noise": Category(
        name="Remove noise",
        description="Remove noise from images, e.g. by local averaging and blurring.",
        inputs=(ImageInput,),
        default_op="gaussian_blur (pyclesperanto)",
        default_values=[1, 1, 0],
        next_step_suggestions=next_steps_at_the_beginning,
        include=("filter", "denoise"),
        exclude=("combine",),
        tools_menu="Filtering / noise removal",
    ),
    "Remove background": Category(
        name="Remove background",
        description="Remove background intensity, e.g. caused\nby out-of-focus light or uneven illumination.",
        inputs=(ImageInput,),
        default_op="top_hat_box (pyclesperanto)",
        default_values=[10, 10, 0],
        next_step_suggestions=[
            "Binarize",
            "Label",
            "Combine",
            "Filter",
        ],
        include=("filter", "background removal"),
        exclude=("combine",),
        tools_menu="Filtering / background removal",
    ),
    "Filter": Category(
        name="Filter",
        description="Filter images, e.g. to adjust gamma or detect edges.",
        inputs=(ImageInput,),
        default_op="gamma_correction (pyclesperanto)",
        default_values=[1, 1, 0],
        next_step_suggestions=[
            "Binarize",
            "Label",
            "Combine",
        ],
        include=("filter",),
        exclude=("combine", "denoise", "background removal", "binary processing"),
        tools_menu="Filtering",
    ),
    "Combine": Category(
        name="Combine",
        description="Combine images using pixel-wise mathematical operations.",
        inputs=(LayerInput, LayerInput),
        default_op="add_images (pyclesperanto)",
        include=("combine",),
        exclude=("map", 'combine labels',),
        default_values=[1, 1],
        next_step_suggestions=[
            "Binarize",
            "Label",
        ],
        tools_menu="Image math",
    ),
    "Transform": Category(
        name="Transform",
        description="Apply spatial transformation to images.",
        inputs=(LayerInput,),
        default_op="sub_stack (pyclesperanto)",
        output="image",  # can also be labels
        default_values=[0, 0, 0, 1, 1],
        next_step_suggestions=next_steps_at_the_beginning,
        include=("transform",),
        exclude=("combine",),
        tools_menu="Transform",
    ),
    "Projection": Category(
        name="Projection",
        description="Reduce dimensionality of images\nfrom three to two dimensions.",
        inputs=(LayerInput,),
        default_op="maximum_z_projection (pyclesperanto)",
        default_values=[1, 1, 1],
        next_step_suggestions=next_steps_at_the_beginning,
        output="image",  # can also be labels
        include=("projection",),
        tools_menu="Projection",
    ),
    "Binarize": Category(
        name="Binarize",
        description="Turn images into binary images.",
        inputs=(LayerInput,),
        default_op="threshold_otsu (pyclesperanto)",
        output="labels",
        default_values=[1, 1, 0],
        next_step_suggestions=[
            "Label",
            "Process labels",
        ],
        include=("binarize",),
        exclude=("combine",),
        tools_menu="Segmentation / binarization",
    ),
    "Label": Category(
        name="Label",
        description="Turn images into label images by labeling objects.",
        inputs=(LayerInput,),
        default_op="voronoi_otsu_labeling (pyclesperanto)",
        output="labels",
        default_values=[2, 2],
        next_step_suggestions=next_steps_after_labeling,
        include=("label",),
        tools_menu="Segmentation / labeling",
    ),
    "Process labels": Category(
        name="Process labels",
        description="Process label images to improve\nby changing their shape and/or removing\nobjects which don't fulfill certain conditions.",
        inputs=(LabelsInput,),
        default_op="exclude_labels_on_edges (pyclesperanto)",
        output="labels",
        default_values=[2, 100],
        next_step_suggestions=next_steps_after_labeling,
        include=("label processing",),
        exclude=("combine",),
        tools_menu="Segmentation post-processing",
    ),
    "Combine labels": Category(
        name="Combine labels",
        description="Process label images multiple label image\nto create a new label image.",
        inputs=(LabelsInput,LabelsInput,),
        default_op="combine_labels (pyclesperanto)",
        output="labels",
        default_values=[2, 100],
        next_step_suggestions=next_steps_after_labeling,
        include=("label processing","combine labels"),
        exclude=(),
        tools_menu="Segmentation post-processing",
    ),
    "Measure labels": Category(
        name="Measure labels",
        description="Measure and visualize spatial\nfeatures of labeled objects.",
        inputs=(LabelsInput,),
        default_op="pixel_count_map (pyclesperanto)",
        default_values=[1, 1],
        next_step_suggestions=next_steps_after_measuring,
        include=("label measurement", "map"),
        exclude=("combine",),
        color_map="turbo",
        tools_menu="None",
    ),
    "Measure labeled image": Category(
        name="Measure labeled image",
        description="Measure and visualize intensity-based\nfeatures of labeled objects.",
        inputs=(ImageInput, LabelsInput),
        default_op="mean_intensity_map (pyclesperanto)",
        default_values=[1, 1],
        next_step_suggestions=next_steps_after_measuring,
        include=("combine","label measurement", "map",),
        exclude=("label comparison",),
        color_map="turbo",
        tools_menu="None",
    ),
    "Compare label images": Category(
        name="Compare label images",
        description="Measure and visualize differences \nof labeled objects in two label images.",
        inputs=(LabelsInput, LabelsInput),
        output="image",
        default_op="label_overlap_count_map (pyclesperanto)",
        default_values=[],
        next_step_suggestions=next_steps_after_measuring,
        include=("combine","label measurement", "map", "label comparison",),
        exclude=(),
        color_map="turbo",
        tools_menu="None",
    ),
    "Label neighbor filters": Category(
        name="Label neighbor filters",
        description="Process values associated with labeled objects\naccording to the neighborhood-graph of the labels.",
        inputs=(ImageInput, LabelsInput),
        default_op="mean_of_n_nearest_neighbors_map (pyclesperanto)",
        default_values=[1, 100],
        next_step_suggestions=next_steps_after_labeling,
        include=("neighbor",),
        color_map="turbo",
        tools_menu="Label neighbor filters",
    ),
    "Label filters": Category(
        name="Label filters",
        description="Process label images depending on values in corresponding images.\nPleease use parametric maps only as input image.",
        inputs=(ImageInput, LabelsInput),
        default_op="exclude_labels_with_map_values_out_of_range (pyclesperanto)",
        output="labels",
        default_values=[1, 100],
        next_step_suggestions=next_steps_after_labeling,
        include=('label processing', 'combine'),
        exclude=("neighbor",),
        tools_menu="Segmentation post-processing",
    ),
    "Mesh": Category(
        name="Mesh",
        description="Draw connectivity meshes between\ncentroids of labeled objects.",
        inputs=(LabelsInput,),
        default_op="draw_mesh_between_touching_labels (pyclesperanto_prototype)",
        default_values=[1],
        next_step_suggestions=[],
        include=("label measurement", "mesh"),
        color_map="green",
        blending="additive",
        tools_menu="Visualization",
    ),
    "Measurement": Category(
        name="Measurement",
        description="Measure features and show results in a table.",
        inputs=(ImageInput, LabelsInput),
        output="dataframe",
        default_op="Regionprops (nsr)",
        default_values=[],
        next_step_suggestions=[],
        include=(),
        tools_menu="Measurement",
        auto_call=False
    ),
}



def attach_tooltips():
    """
    Attach tooltips to categories which contain all functions
    This is necessary so that the search later finds operations by name in categories.
    The search searches in the tooltip.

    Todo: This only works if the tools-menu is initialized.
          We should alternatively search for menu names + functions in npe2.
    """
    # attach tooltips
    for k, c in CATEGORIES.items():
        choices = operations_in_menu(c)
        c.tool_tip = c.description + "\n\nOperations:\n* " + "\n* ".join(choices).replace("_", " ")


@lru_cache(maxsize=1)
def all_operations():
    """Get a dictionary of all compatible functions of installed plugins

    Returns
    -------
    dict(str:callable)
        Dictionary of name-function pairs

    """
    # harvest functions from clesperanto
    cle_ops = collect_from_pyclesperanto_if_installed()

    # harvest functions from napari-tools-menu
    tools_ops = collect_from_tools_menu_if_installed()

    # harvest from napari-plugin-enginge-2
    npe2_ops = collect_from_npe2_if_installed()

    # combine all
    all_ops = {**cle_ops, **tools_ops, **npe2_ops}

    all_ops = remove_duplicate_operations(all_ops)

    return all_ops


def remove_duplicate_operations(all_ops):
    """Remove duplicate operations from all_ops

    This is an internal workaround for the fact that some operations are registered twice.
    It may become obsolete when napari-pyclesperanto-assistant or its menu entries retired.

    Parameters
    ----------
    all_ops : dict
        Dictionary of name-function pairs

    Returns
    -------
    dict
        Dictionary of name-function pairs
    """
    # remove duplicates
    new_ops = {}
    for k, v in all_ops.items():
        other_name = k.replace(" (box, ", "_box (").\
                       replace("Gaussian background", "gaussian_background").\
                       replace("Gaussian ", "gaussian_blur ").\
                       replace("component labeling", "components labeling box").\
                       replace(" ", "_").\
                       replace("-", "_").\
                       replace("_/_", " / ").\
                       replace("_(", " (").\
                       replace("noise_", "noise ").\
                       replace("background_", "background ").\
                       replace("_post_", " post-").\
                       replace(">label_", ">").\
                       lower()

        other_name = other_name[0].upper() + other_name[1:]

        if other_name != k:
            if other_name in all_ops:
                # print("Removing duplicate operation: ", k, other_name)
                continue

        new_ops[k] = v
    return new_ops

def get_name_of_function(func):
    """
    Searches all functions for a given function
    and returns its human-readable name
    """
    for k, v in all_operations().items():
        if v is func or getattr(v, '__wrapped__', None) is func:
            if ">" in k:
                return k.split(">")[1]
            else:
                return k
    return None


def collect_from_pyclesperanto_if_installed():
    """
    Collect all functions from pyclesperanto and _prototype that are annotated with "in assistant"
    """
    from napari_time_slicer import time_slicer

    result = {}
    available_already = []

    try:
        import pyclesperanto as cle
        for k, c in CATEGORIES.items():
            if not callable(c):
                if len(list(c.include)) > 0:
                    choices = cle.operations(['in assistant'] + list(c.include), c.exclude)
                    for choice, func in choices.items():
                        result[c.tools_menu + ">" + choice + " (pyclesperanto)"] = time_slicer(func)
                        available_already.append(choice)

    except ImportError:
        print("Assistant skips harvesting pyclesperanto as it's not installed.")

    try:
        import pyclesperanto_prototype as cle
        for k, c in CATEGORIES.items():
            if not callable(c):
                if len(list(c.include)) > 0:
                    choices = cle.operations(['in assistant'] + list(c.include), c.exclude)
                    for choice, func in choices.items():
                        if choice not in available_already:
                            result[c.tools_menu + ">" + choice + " (pyclesperanto_prototype)"] = time_slicer(func)
                        available_already.append(choice)

    except ImportError:
        print("Assistant skips harvesting pyclesperanto_prototype as it's not installed.")

    return result


def collect_from_tools_menu_if_installed():
    """
    Collect all functions that process images (no dock-widgets and actions) from napari-tools-menu
    """
    try:
        from napari_tools_menu import ToolsMenu
    except ImportError:
        print("Assistant skips harvesting tools menu as it's not installed.")
        return {}

    import pandas

    allowed_types = ["napari.types.LabelsData", "napari.types.ImageData", "int", "float", "str", "bool",
                     "napari.viewer.Viewer", "napari.Viewer", "magicgui.types.PathLike", "typing.Union[pathlib.Path, str, bytes]"]
    allowed_types = allowed_types + ["<class '" + t + "'>" for t in allowed_types]

    result = {}
    for k, v in ToolsMenu.menus.items():
        typ = v[1]
        if typ == "function":
            f = v[0]
            sig = inspect.signature(f)

            # all parameters must be images, labels, int, float or str
            skip = False
            for i, key in enumerate(list(sig.parameters.keys())):
                type_annotation = str(sig.parameters[key].annotation)
                if not "function NewType.<locals>.new_type" in type_annotation:
                    if type_annotation not in allowed_types:
                        # print("Skip", k, "because", str(type_annotation), "not in allowed types")
                        skip = True
                        break
            if skip:
                continue

            # return type must be image or label_image
            if sig.return_annotation not in [napari.types.LabelsData, "napari.types.LabelsData",
                                             napari.types.ImageData, "napari.types.ImageData",
                                             pandas.DataFrame, "pandas.DataFrame"]:
                continue

            result[k] = f

    return result


def collect_from_npe2_if_installed():
    """
    Collect all functions provided by the NPE2 interface (napari) which contain
    a menu name
    """
    try:
        import npe2
    except ImportError:
        print("Assistant skips harvesting npe2 as it's not installed.")
        return {}
    pm = npe2.PluginManager.instance()

    result = {}
    for pname, item in pm._manifests.items():
        if item.contributions.widgets is not None:
            for c in item.contributions.widgets:
                wname = c.display_name
                # only harvest items which look like a menu decription
                # todo: as soon as npe2 supports menus, change this here
                if ">" in pname or ">" in wname:
                    # print("loading ", pname, wname)

                    t = get_widget_contribution(pname, wname)
                    if t is not None:
                        factory = t[0]
                        menu = t[1]
                        kwargs = {}
                        w = factory(**kwargs)
                        menu = menu.replace(" > ", ">")
                        result[menu] = w._function
    return result


# source: https://github.com/napari/napari/blob/1363bd47da668a5826a75a73be93f7a7f8042fd7/napari/plugins/_npe2.py#L91
def get_widget_contribution(
        plugin_name: str, widget_name: str = None
):
    import npe2
    for contrib in npe2.PluginManager.instance().iter_widgets():
        if contrib.plugin_name == plugin_name and (
                not widget_name or contrib.display_name == widget_name
        ):
            return contrib.get_callable(), contrib.display_name
    return None


def filter_operations(menu_name: str):
    """
    Find functions that contain a given name
    Parameters
    ----------
    menu_name: str
        case sensitive search string

    Returns
    -------
    dict(str:callable)
        Dictionary of name-function pairs
    """
    result = {}
    for k,v in all_operations().items():
        if menu_name+">" in k:
            result[k] = v
    return result

def operations_in_menu(category, search_string: str = None):
    """
    Return all functions as list in a given category that contain a
    given search string.
    """
    if not hasattr(category, "tools_menu"):
        return []
    menu_name = category.tools_menu
    choices = filter_operations(menu_name)

    all_ops = all_operations()

    if search_string is not None and len(search_string) > 0:
        choices_dict = {k: all_ops[k] for k in choices}
        choices = [c for c, v in choices_dict.items() if search_string in c.lower() or (v.__doc__ is not None and search_string in v.__doc__.lower())]
    choices = [c.split(">")[1].strip() for c in choices]
    choices = sorted(choices, key=str.casefold)

    # check if the image parameters fit
    result = []
    for name in choices:
        func = find_function(name)
        sig = inspect.signature(func)

        # count number of image-like parameters and compare to category
        num_image_parameters_in_category = len(category.inputs)
        num_image_parameters_in_function = 0
        for i, key in enumerate(list(sig.parameters.keys())):
            type_annotation = str(sig.parameters[key].annotation)

            if "NewType.<locals>.new_type" in type_annotation or \
                "Image" in type_annotation or \
                "LabelsData" in type_annotation or \
                "LayerData" in type_annotation or \
                "numpy.ndarray" in type_annotation:
                num_image_parameters_in_function = num_image_parameters_in_function + 1
            else:
                break

        if "pyclesperanto" in func.__module__:
            # all clesperanto function have an output image which we don't pass
            num_image_parameters_in_function -= 1

        # only keep the function in this category if it matches
        if num_image_parameters_in_category == num_image_parameters_in_function:
            if category.name == "Measurement":
                if str(sig.return_annotation) == "pandas.DataFrame":
                    result.append(name)
            else:
                result.append(name)

    return result


def find_function(op_name):
    """
    Find a function by name (in menu)
    """
    all_ops = all_operations()
    found_function = None

    # find exact match first
    for k, f in all_ops.items():
        if ">" in k:
            k = k.split(">")[1]
        if op_name == k:
            found_function = f
            break

    if found_function is None:
        # find approximate match
        for k, f in all_ops.items():
            if op_name in k:
                found_function = f

    if found_function is None:
        print("No function found for", op_name)
    return found_function


def get_category_of_function(func = None, func_name = None):
    """
    Searches categories for a given function and returns the first (!)
    category that contains the function
    """
    
    if func_name is None:
        func_name = get_name_of_function(func)

    for k, c in CATEGORIES.items():
        if not callable(c):
            ops = operations_in_menu(c)
            if func_name in ops:
                return c
    return None


def filter_categories(search_string: str = ""):
    """Return all categories that have a function that contains a
    given search string in their name.
    """
    if search_string is None or len(search_string) == 0:
        search_string = ""

    from copy import copy

    all_categories = {}
    for k, c in CATEGORIES.items():
        #if callable(c) or search_string in c.tool_tip.lower():
        new_c = copy(c)
        all_categories[k] = new_c

    category_found = False
    result = {}
    for k, c in all_categories.items():
        if callable(c):
            if category_found ^ ("Search" in k):
                result[k] = c
        else:
            choices = operations_in_menu(c, search_string)
            c.tool_tip = c.description + "\n\nOperations:\n* " + "\n* ".join(choices).replace("_", " ")
            if len(choices) > 0:
                result[k] = c
                category_found = True

    return result
