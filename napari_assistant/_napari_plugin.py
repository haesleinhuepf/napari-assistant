# Implementation of napari hooks according to
# https://napari.org/docs/dev/plugins/for_plugin_developers.html#plugins-hook-spec
from napari_plugin_engine import napari_hook_implementation

from ._gui import Assistant
from ._categories import attach_tooltips

@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    attach_tooltips()
    return [Assistant]

try:
    from napari_tools_menu import register_dock_widget
    register_dock_widget(Assistant, menu="Utilities > Assistant (na)")
except ImportError:
    pass
