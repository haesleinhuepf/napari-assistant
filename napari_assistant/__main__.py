def main():
    # napari 0.6.0 warns that plugins are potentially not working,
    # and ask plugin developers to fix this.
    # However, the plugins are working, they just broke the menu discovery.
    # This code fixes the menu discovery and removes the warning.
    def dummy(whatever):
        pass
    from napari._qt.qt_main_window import _QtMainWindow
    _QtMainWindow._warn_on_shimmed_plugins = dummy

    # import plugins ourself
    try:
        from importlib.metadata import entry_points

        # Discover all napari plugins
        try:
            napari_plugins = entry_points(group='napari.plugin')
        except TypeError:
            all_plugins = entry_points()
            try:
                napari_plugins = all_plugins['napari.plugins']
            except KeyError:
                napari_plugins = []
        print("plugins found:", len(napari_plugins))

        # import all plugins
        for ep in napari_plugins:
            #print("loading", ep.name)
            import time
            start_time = time.time()
            try:
                ep.load()
            except:
                print(f"Error while loading plugin {ep.name}")
            finally:
                delta_time = time.time() - start_time
                if delta_time > 0.1:
                    print(f"Loading plugin {ep.name} took {delta_time} seconds")
    except:
        pass

    # open a napari viewer
    import sys
    from ._viewer import Viewer
    from qtpy.QtCore import QTimer

    viewer = Viewer()

    if len(sys.argv) > 1:
        def later():
            for pos, arg in enumerate(sys.argv):
                print('Argument %d: %s' % (pos, arg))
                if pos > 0:
                    viewer.open(arg)

        QTimer.singleShot(600, later)

    import napari
    napari.run()


if __name__ == '__main__':
    main()