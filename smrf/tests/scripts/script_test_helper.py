import os
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader


def create_script_spec(script_name):

    # This path doesn't exist in docker or if it's installed as a package
    SMRF_SCRIPT_HOME = os.path.abspath(
        __file__ + '../../../../../') + '/scripts/'
    if not os.path.exists(SMRF_SCRIPT_HOME):
        SMRF_SCRIPT_HOME = '/usr/local/bin/'

    return spec_from_loader(
        script_name,
        SourceFileLoader(
            script_name,
            SMRF_SCRIPT_HOME + script_name
        )
    )


def load_script_as_module(script_name):
    """
    Load given script file in the 'scripts' folder and load it as a module.

    Example:

    .. code-block:: Python

        from .script_test_helper import load_script_as_module

        script = load_script_as_module('script_name')

        script.method_from_script()

    Args:
        script_name: string
            Name of the script

    Returns:
        Script as module
    """
    spec = create_script_spec(script_name)
    script = module_from_spec(spec)
    spec.loader.exec_module(script)

    return script
