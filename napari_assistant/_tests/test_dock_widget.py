import numpy as np
from napari_assistant._categories import CATEGORIES, LabelsInput

def assistant(make_napari_viewer):
    viewer = make_napari_viewer()
    viewer.window.add_plugin_dock_widget("clEsperanto", "Assistant")
    dw = viewer.window._dock_widgets["clEsperanto: Assistant"]
    return dw.widget()


def test_individual_categories(category, assistant):
    assistant.load_sample_data()
    if LabelsInput in category.inputs:
        assistant._activate(CATEGORIES.get("Binarize"))
    assistant._activate(category)
    assistant.to_clipboard()


def test_workflow_processing_labels(make_napari_viewer):
    import napari_pyclesperanto_assistant
    from pathlib import Path

    root = Path(napari_pyclesperanto_assistant.__file__).parent
    img_path = str(root / 'data' / 'Lund_000500_resampled-cropped.tif')

    # start napari
    viewer = make_napari_viewer()
    viewer.open(img_path)
    viewer.window.add_plugin_dock_widget("clEsperanto", "Background removal")
    viewer.window.add_plugin_dock_widget("clEsperanto", "Binarize")
    viewer.window.add_plugin_dock_widget("clEsperanto", "Label")
    viewer.window.add_plugin_dock_widget("clEsperanto", "Label measurements")


def test_something_with_viewer(make_napari_viewer):

    from napari_pyclesperanto_assistant import Assistant
    viewer = make_napari_viewer()

    assistant = Assistant(viewer)

    num_dw = len(viewer.window._dock_widgets)
    viewer.window.add_dock_widget(assistant)
    assert len(viewer.window._dock_widgets) == num_dw + 1

    image = np.asarray([
        [0, 0, 0, 0, 0, 0, 0],
        [1, 1, 1, 0, 0, 1, 1],
        [1, 2, 1, 0, 0, 1, 2],
        [1, 1, 1, 0, 0, 1, 1],
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 1, 2, 1, 0, 0],
    ])

    viewer.add_image(image)

    assistant._activate(CATEGORIES.get("Remove noise"))
    assistant._activate(CATEGORIES.get("Remove background"))
    assistant._activate(CATEGORIES.get("Filter"))
    assistant._activate(CATEGORIES.get("Binarize"))
    assistant._activate(CATEGORIES.get("Label"))
    assistant._activate(CATEGORIES.get("Measure labeled image"))
    assistant.seach_field.setText("Gauss")
