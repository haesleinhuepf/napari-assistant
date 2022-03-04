def Viewer(show_assistant: bool = True, *args, **kwargs):
    import napari
    from qtpy.QtCore import QTimer

    viewer = napari.Viewer(*args, **kwargs)

    def later():
        if show_assistant:
            from ._gui._Assistant import Assistant
            viewer.window.add_dock_widget(Assistant(viewer), name="Assistant")

    QTimer.singleShot(300, later)

    return viewer
