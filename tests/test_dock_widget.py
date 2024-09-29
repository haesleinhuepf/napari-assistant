import numpy as np

# test fails with recent napari
def something_with_viewer(make_napari_viewer):

    from napari_assistant import Assistant
    from napari_assistant._categories import CATEGORIES, attach_tooltips

    attach_tooltips()

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

    # assistant._activate(CATEGORIES.get("Remove noise"))
    # assistant._activate(CATEGORIES.get("Remove background"))
    # assistant._activate(CATEGORIES.get("Filter"))
    # assistant._activate(CATEGORIES.get("Binarize"))
    # assistant._activate(CATEGORIES.get("Label"))
    assistant.seach_field.setText("Gauss")
