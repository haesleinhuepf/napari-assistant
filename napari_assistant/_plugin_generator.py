from __future__ import annotations
from warnings import warn
from napari.layers import Labels, Image
from magicgui import magic_factory
from napari_tools_menu import register_dock_widget

@register_dock_widget(menu="Utilities > Generate Napari plugin from workflow (na)")
@magic_factory(
    license=dict(choices=["BSD-3", "MIT", "Mozilla Public License 2.0", "Apache Software License 2.0", "GNU LGPL v3.0",
                          "GNU GPL v3.0"]),
    tools_menu=dict(choices=["Filtering / noise removal", "Filtering / background removal",
                             "Filtering / edge enhancement", "Filtering / deconvolution", "Games", "Image math",
                             "Registration", "Scripts", "Segmentation / binarization", "Segmentation / labeling",
                             "Segmentation post - processing", "Measurement", "Visualization", "Utilities"]),
    output_dir=dict(widget_type='FileEdit', mode='d'),
)
def make_plugin(
        output_dir: str = ".",
        plugin_name: str = "my_napari_assistant_plugin",

        developer_name:str = "Developer Name",
        developer_email:str = "email@domain.com",
        github_username:str = "github_username",
        short_description:str = "Short plugin description",
        license:str = "BSD-3",
        tools_menu:str = "Scripts",
        menu_name:str = "Process image",

        viewer:"napari.Viewer"=None,
):
    from cookiecutter.main import cookiecutter
    from napari_workflows import WorkflowManager
    wm = WorkflowManager.install(viewer)
    workflow = wm.workflow

    plugin_name = plugin_name.replace("-", "_").replace(" ", "_").lower()

    python_code, python_parameters, output_type, requirements = _generate_code(workflow, viewer)

    cookiecutter(
        'https://github.com/haesleinhuepf/cookiecutter-napari-plugin',

        no_input=True,
        output_dir=output_dir,
        checkout="2022.10.30",
        extra_context={
            "full_name": developer_name,
            "email": developer_email,
            "github_username": github_username,
            "plugin_name": plugin_name,
            "module_name": plugin_name,
            "short_description": short_description,
            "include_reader_plugin": "n",
            "include_writer_plugin": "n",
            "include_dock_widget_plugin": "n",
            "include_function_plugin": "y",
            "docs_tool": "none",
            "license": license,
            "python_parameters": python_parameters,
            "python_code": python_code,
            "output_type": output_type,
            "tools_menu":tools_menu,
            "menu_name":menu_name,
            "pip_requirements":requirements
        }
    )

    #import os
    #os.system("pip install -e ./" + plugin_name)


def _generate_code(workflow, viewer):
    if len(workflow.leafs()) == 0:
        raise RuntimeError("No workflow configured. Read the documentation to setup workflows: https://github.com/haesleinhuepf/napari-assistant#usage")

    code, input_parameters, output_type, requirements = _generate_python_code(workflow, viewer)

    code = code.replace("\n", "\n    ")

    python_parameters = ""
    for k, v in input_parameters.items():
        var_name = k
        var_type = v[0]
        var_value = v[1]
        if var_type == "str":
            var_value = "'" + var_value + "'"
        python_parameters = python_parameters + ", " + var_name + ": " + var_type
        if var_value is not None:
            python_parameters = python_parameters + " = " + str(var_value)

    return code, python_parameters[2:], output_type, requirements


def _generate_python_code(workflow: "napari_workflows.Workflow", viewer: "napari.Viewer"):
    """
    Takes a Workflow and a viewer an generates python code corresponding to the workflow.
    Precondition: The used functions must be compatible with Workflows and register their
    functionality.

    Parameters
    ----------
    workflow: Workflow
        The workflow which should be converted to code.
    viewer: napari.Viewer
        The viewer where the workflow was set up.

    Returns
    -------
    str
        python code
    str
        requirements in pip format
    dict[str:[str, any]]
        parameter name:[type_str, default_value] dictionary
    """
    imports = []
    code = []
    input_variables = {}

    import dask
    order = dask.order.order(workflow._tasks)

    roots = order.keys()

    image_variable_names = {}
    requirements = ""

    def python_conform_variable_name(value):
        if isinstance(value, str):
            if value not in image_variable_names:
                # Make a short and readable variable name, e.g. turn a layer
                # "Resut of Gaussian blur" into "image1_gb".
                temp = value
                temp = temp.replace("Result of ", "")
                temp = temp.replace(" result", "")
                temp = "".join([t[0] for t in temp.split("_")])
                new_name = "image" + str(len(image_variable_names)) + "_" + temp
                image_variable_names[value] = new_name

            return image_variable_names[value]
        else:
            return str(value)

    def build_output(list_of_items, requirements):
        """
        This function is called to generate code that represents the
        image data flow graph stored in workflow. The graph should be
        sorted in advance, e.g. using dask.order.order() and the resulting
        sorted list of keys can be passed here.

        Parameters
        ----------
        list_of_items: list[str]
            layer names that should be computed iteratively

        Returns
        -------
        str
            requirements
        """
        from napari_workflows._workflow import _viewer_has_layer

        comment_start = "\n# "

        for key in list_of_items:
            result_name = python_conform_variable_name(key)
            try:
                # Retrieve the task that corresponds to this layer
                task = workflow.get_task(key)

                # split it into the used function and corresponding arguments
                function = task[0]
                arguments = task[1:]
                if arguments[-1] is None:
                    arguments = arguments[:-1]

                import inspect
                sig = inspect.signature(function)

                kwargs = {}
                bound = sig.bind(*arguments, **kwargs)
                bound.apply_defaults()
                # Go through arguments and in case it's a callable, remove it
                # We should only have numbers, strings and images as parameters
                used_args = bound.arguments.items()

                # determine package and module
                package_path = function.__module__.split(".")
                module = package_path[0]
                original_module_name = module
                new_import = "import " + module

                # load the module
                loaded_module = __import__(module)

                # if the module has an alias, use this alias in the code
                try:
                    alias = loaded_module.__common_alias__
                    new_import = new_import + " as " + alias

                    if len(package_path) == 1:
                        module = alias
                    else:
                        module = alias + "." + ".".join(package_path[1:])
                except:
                    pass

                # document version
                version = None
                try:
                    version = loaded_module.__version__
                    new_import = new_import + " # version " + str(version)
                except:
                    pass

                # add imports
                if new_import not in imports:
                    imports.append(new_import)

                # add to requirements
                package_name = original_module_name.replace("_", "-")
                if package_name not in requirements:
                    requirements = requirements + package_name
                    if version is not None:
                        requirements = requirements + ">=" + version
                    requirements = requirements + "\n"

                # put together code that calls the function
                named_arguments = []
                for k, v in used_args:
                    # if the value has been processed

                    if v is not None:
                        if isinstance(v, str) and (v in workflow._tasks.keys() or _viewer_has_layer(viewer, v)):
                            named_arguments.append(python_conform_variable_name(v))
                        else:
                            variable_counter = len(input_variables.keys()) + 1
                            new_variable_name = function.__name__ + "_" + k + "_" + str(variable_counter)
                            if isinstance(v, str):
                                input_variables[new_variable_name] = ["str", v]
                            elif isinstance(v, int):
                                input_variables[new_variable_name] = ["int", v]
                            elif isinstance(v, float):
                                input_variables[new_variable_name] = ["float", v]
                            named_arguments.append(k + "=" + new_variable_name)
                arg_str = ", ".join(named_arguments)

                code.append(comment_start + function.__name__.replace("_", " "))
                code.append(f"{result_name} = {module}.{function.__name__}({arg_str})")

            except KeyError:
                try:
                    layer = viewer.layers[key]

                    if isinstance(layer, Image):
                        input_variables[result_name] = ['"napari.types.ImageData"', None]
                    elif isinstance(layer, Labels):
                        input_variables[result_name] = ['"napari.types.LabelsData"', None]
                    else:
                        warn(f"Layer type of {result_name} not supported.")
                except KeyError:
                    warn(f"Layer {key} does not exist.")
                    pass
        return requirements


    requirements = build_output(workflow.roots(), requirements)
    requirements = build_output(roots, requirements)

    final_result_name = workflow.leafs()[0]
    final_result_layer = viewer.layers[final_result_name]
    if len(workflow.leafs()) > 1:
        warn(f"Multiple outputs are not yet supported for code generation. Using {final_result_name}")

    code.append("return " + python_conform_variable_name(final_result_name))

    complete_code = "\n".join(imports) + "\n\n" + "\n".join(code) + "\n"

    # format the code PEP8
    import autopep8
    complete_code = autopep8.fix_code(complete_code)

    if isinstance(final_result_layer, Labels):
        output_type = '"napari.types.LabelsData"'
    else :
        output_type = '"napari.types.ImageData"'

    return complete_code, input_variables, output_type, requirements

