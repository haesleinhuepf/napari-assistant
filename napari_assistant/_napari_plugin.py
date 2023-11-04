
from napari_plugin_engine import napari_hook_implementation

from ._gui import Assistant
from ._categories import attach_tooltips

@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    attach_tooltips()
    return [Assistant]

@napari_hook_implementation
def napari_experimental_provide_function():
    return [_split_stack]

from napari_tools_menu import register_action

@register_action(menu="Scripts > Generate Jupyter Notebook from Workflow (na)")
def generate_jupyter_notebook_from_workflow(viewer:"napari.Viewer"):
    from ._gui._Assistant import Assistant
    assistant = Assistant(viewer)
    assistant.to_notebook()


@register_action(menu="Scripts > Copy Python code representing Workflow (na)")
def generate_jupyter_notebook_from_workflow(viewer:"napari.Viewer"):
    from ._gui._Assistant import Assistant
    assistant = Assistant(viewer)
    assistant.to_clipboard()


def _split_stack(viewer:"napari.Viewer", layer:"napari.layers.Layer", axis:int = 1):
    # This function can be removed once these issues are fixed:
    # https://github.com/napari/napari/pull/3981
    # https://github.com/napari/napari/issues/4885
    from napari.layers.utils import stack_utils
    ll = viewer.layers

    # copied from: https://github.com/napari/napari/blob/f6bdd6235da23d4d23239653b6e4cf02e7f6d4ac/napari/layers/_layer_actions.py#L38
    images = stack_utils.stack_to_images(layer, axis)
    ll.remove(layer)
    ll.extend(images)
    ll.selection = set(images)  # type: ignore

try:
    from napari_tools_menu import register_dock_widget, register_function
    register_dock_widget(Assistant, menu="Utilities > Assistant (na)")
    register_function(_split_stack, menu="Utilities > Split stack (na)")

except ImportError:
    pass

