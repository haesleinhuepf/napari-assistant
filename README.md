# napari-assistant
[![License](https://img.shields.io/pypi/l/napari-assistant.svg?color=green)](https://github.com/haesleinhuepf/napari-assistant/raw/master/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/napari-assistant.svg?color=green)](https://pypi.org/project/napari-assistant)
[![Python Version](https://img.shields.io/pypi/pyversions/napari-assistant.svg?color=green)](https://python.org)
[![tests](https://github.com/haesleinhuepf/napari-assistant/workflows/tests/badge.svg)](https://github.com/haesleinhuepf/napari-assistant/actions)
[![codecov](https://codecov.io/gh/haesleinhuepf/napari-assistant/branch/master/graph/badge.svg)](https://codecov.io/gh/haesleinhuepf/napari-assistant)
[![Development Status](https://img.shields.io/pypi/status/napari-assistant.svg)](https://en.wikipedia.org/wiki/Software_release_life_cycle#Alpha)
[![napari hub](https://img.shields.io/endpoint?url=https://api.napari-hub.org/shields/napari-assistant)](https://napari-hub.org/plugins/napari-assistant)
[![DOI](https://zenodo.org/badge/322312181.svg)](https://zenodo.org/badge/latestdoi/322312181)

The napari-assistant is a [napari](https://github.com/napari/napari) meta-plugin for building image processing workflows. 

## Usage

After installing one or more napari plugins that use the napari-assistant as user interface, you can start it from the 
menu `Tools > Utilities > Assistant (na)` or run `naparia` from the command line. 

By clicking on the buttons in the assistant, you can setup a workflow for processing the images.

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/napari-assistant-screenshot.png)

While setting up your workflow, you can at any point select a layer from the layer list (1) and change the parameters of
the corresponding operation (2). The layer will update when you change parameters and also all subsequent operations. 
You can also vary which operation is applied to the image (3). Also make sure the right input image layer is selected (4).

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/design_workflows.png)

### Saving and loading workflows

You can also save and load workflows to disk. 

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/save_and_load.png)

After loading a workflow, make sure that the right input images are selected.

### Code generation

The napari-assistant allows exporting the given workflow as Python script and Jupyter Notebook. 

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/code_generator.png)

Furthermore, if you have the [napari-script-editor](https://www.napari-hub.org/plugins/napari-script-editor) installed,
you can also send the current workflow as code to the script editor from the same menu.

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/napari_script_editor.png)

### Plugin generation

There is also a Napari plugin generator available. Note: For running it you need to be connected to the internet, 
because a [plugin template](https://github.com/haesleinhuepf/cookiecutter-napari-assistant-plugin) will be downloaded. 
The plugin generator can be found in the menu `Tools > Utilities > Generate Napari plugin from workflow (na)` and also 
in the `Generate code...` of the Assistant:

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/generate_napari_plugin1.png)

In the plugin generator dialog, please enter this information:
* **output dir:** Folder where the Napari plugin code should be saved. If not specified, the plugin will be stored in the current directory Napari was started from.
* **plugin name:** Name of the plugin. A folder with this name will be generated in the folder specified above. Plugin names must not contain special characters or spaces. Use `_` instead.
* **developer name:** Your name as it will be displayed later on the [napari-hub](https://napari-hub.org) in case you decide to publish your plugin.
* **developer email:** Your email as it will be stored in the configuration of your plugin. This email-address is visible to the public.
* **github username:** Your username on [github](https://github.com). URLs in the plugin documentation will point to your profile on github.
* **short description:** Please write one sentence explaining what the plugin is doing.
* **license:** Choose the open-source license your plugin code will be licensed. If you are not sure which one to use, consult [choosealicense.com](https://choosealicense.com).
* **tools menu** The menu under `Tools` where your plugin will be found after installing it.
* **menu name** The menu entry will have this title.

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/generate_napari_plugin2.png)

After the Napari plugin code has been generated, open it in the integrated development environment (IDE) of your choice. 
Go through the files in the directory and search for `TODO` entries. Start with the `readme.md` and the `requirements.txt` files:

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/generate_napari_plugin4.png)

It is highly recommended to inspect the generated code and rename variables to be more meaningful.
For renaming variables, make use of your IDE's tools. For example variables can be renamed conveniently in [pycharm](https://www.jetbrains.com/pycharm/) using the right-click menu:

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/generate_napari_plugin3.png)

The `readme.md` file also contains instructions for how to install and distribute your plugin. 
TL:DR: As a plugin developer you typically execute this command from the terminal within your plugin's root directory to install your plugin in an `editable`. 
This command allows you to modify the code and test it without the need for re-installing your plugin.

```
pip install -e .
```

If installation was successful, you will find your plugin in the menu you specified and a dialog will open requesting the parameters of the generated Python function in `<your_plugin_folder>/<your_plugin_folder>/_function.py`:

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/generate_napari_plugin5.png)

![img.png](https://github.com/haesleinhuepf/napari-assistant/raw/main/docs/generate_napari_plugin6.png)


## Installation

It is recommended to install the napari-assistant via one of the plugins that use it as graphical user interface.
You find a complete list of plugins that use the assistant [on the napari-hub](https://www.napari-hub.org/?search=napari-assistant&sort=relevance).

## For developers

If you want to make your napari-plugin accessible from the napari-assistant, consider programming functions with a simple 
interface that consume images, labels, integers, floats and strings. Annotate input and return types, e.g. like this:
```python
def example_function_widget(image: "napari.types.ImageData") -> "napari.types.LabelsData":
    from skimage.filters import threshold_otsu
    binary_image = image > threshold_otsu(image)

    from skimage.measure import label
    return label(binary_image)
```

Furthermore, please add your function to the napari.yaml which uses [npe2](https://github.com/napari/npe2):
```
name: napari-npe2-test
display_name: napari-npe2-test
contributions:
  commands: 
    - id: napari-npe2-test.make_magic_widget
      python_name: napari_npe2_test._widget:example_magic_widget
      title: Make example magic widget
  widgets:
    - command: napari-npe2-test.make_magic_widget
      display_name: Segmentation / labeling > Otsu Labeling (nnpe2t)
```

To put it in the right button within the napari-assistant, please use one of the following prefixes for the `display_name`:
* `Filtering / noise removal > `
* `Filtering / background removal > `
* `Filtering > `
* `Image math > `
* `Transform > `
* `Projection > `
* `Segmentation / binarization > `
* `Segmentation / labeling > `
* `Segmentation post-processing > `
* `Measurement > `
* `Label neighbor filters > `
* `Label filters > `
* `Visualization > `

You find a fully functional example [here](https://github.com/haesleinhuepf/napari-npe2-test).

Last but not least, to make your napari-plugin is listed in the napari-hub when searching for "napari-assistant", make sure
you mention it in your `readme`.

## Feedback welcome!

The napari-assistant is developed in the open because we believe in the open source community. Feel free to drop feedback as [github issue](https://github.com/haesleinhuepf/napari-assistant/issues) or via [image.sc](https://image.sc)

## Contributing

Contributions are very welcome. Please ensure
the test coverage at least stays the same before you submit a pull request.

## License

Distributed under the terms of the [BSD-3] license,
"napari-assistant" is free and open source software

## Acknowledgements
This project was supported by the Deutsche Forschungsgemeinschaft under Germany’s Excellence Strategy – EXC2068 - Cluster of Excellence "Physics of Life" of TU Dresden. 
This project has been made possible in part by grant number [2021-240341 (Napari plugin accelerator grant)](https://chanzuckerberg.com/science/programs-resources/imaging/napari/improving-image-processing/) from the Chan Zuckerberg Initiative DAF, an advised fund of the Silicon Valley Community Foundation.

[BSD-3]: http://opensource.org/licenses/BSD-3-Clause

