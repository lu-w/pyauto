import signal

import owlready2
import os
import argparse
import importlib
import logging

from enum import Enum

import pyauto.utils
from .models import scenario
from .visualizer import visualizer

"""
Loads A.U.T.O. globally into owlready2. Also provides an easier enum interface to access the sub-ontologies of A.U.T.O.
"""

# Logging
logger = logging.getLogger(__name__)

# The world that A.U.T.O. was loaded into the last time load() was called. Standard is owlready2.default_world.
world = owlready2.default_world

# Imported modules of extras (in order to be able to reload them in case of more than one world)
_extras = dict()


class Ontology(Enum):
    """
    Contains an enumeration of all sub-ontologies of A.U.T.O. pointing to their IRIs (as str)
    """
    AUTO = "http://purl.org/auto/#"
    Criticality_Phenomena = "http://purl.org/auto/criticality_phenomena#"
    Criticality_Phenomena_Formalization = "http://purl.org/auto/criticality_phenomena_formalization#"
    Physics = "http://purl.org/auto/physics#"
    Perception = "http://purl.org/auto/perception#"
    Communication = "http://purl.org/auto/communication#"
    GeoSPARQL = "http://www.opengis.net/ont/geosparql#"
    TE_Core = "http://purl.org/auto/traffic_entity_core#"
    Descriptive_TE_Core = "http://purl.org/auto/descriptive_traffic_entity_core#"
    Descriptive_TE_DE = "http://purl.org/auto/descriptive_traffic_entity_de#"
    Interpretative_TE_Core = "http://purl.org/auto/interpretative_traffic_entity_core#"
    Interpretative_TE_DE = "http://purl.org/auto/interpretative_traffic_entity_de#"
    L1_Core = "http://purl.org/auto/l1_core#"
    L1_DE = "http://purl.org/auto/l1_de#"
    L2_Core = "http://purl.org/auto/l2_core#"
    L2_DE = "http://purl.org/auto/l2_de#"
    L3_Core = "http://purl.org/auto/l3_core#"
    L3_DE = "http://purl.org/auto/l3_de#"
    L4_Core = "http://purl.org/auto/l4_core#"
    L4_DE = "http://purl.org/auto/l4_de#"
    L5_Core = "http://purl.org/auto/l5_core#"
    L5_DE = "http://purl.org/auto/l5_de#"
    L6_Core = "http://purl.org/auto/l6_core#"
    L6_DE = "http://purl.org/auto/l6_de#"


def load(folder: str = None, load_into_world: owlready2.World = None, add_extras: bool = True,
         more_extras: list[str] = None, load_cp: bool = False):
    """
    Loads A.U.T.O. from a given folder location.
    :param folder: The folder to look for, should contain the `automotive_urban_traffic_ontology.owl`. Can be None, in
        this case, it takes the ontology located in this repository.
    :param load_into_world: The world to load A.U.T.O. into. If None, loads into the default world.
    :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
    :param more_extras: A name of an importable module that contains more extra functionality to load from. Will be
        imported in the given order. Using wildcards at the end is possible, e.g. "a.b.*", which then recursively
        imports *all* Python files located in the package's (sub)folder(s).
    :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
    :raise FileNotFoundError: if given an invalid folder location.
    """
    global world
    # Loading ontology into world (or default world)
    if load_into_world is None:
        world = owlready2.default_world
    else:
        world = load_into_world
    if folder is None:
        folder = os.path.dirname(os.path.realpath(__file__)) + "/auto"
    if os.path.isdir(folder):
        logger.debug("Loading A.U.T.O. from " + str(folder))
        # Setting correct path for owlready2
        for i, j, k in os.walk(folder + "/"):
            owlready2.onto_path.append(i)
        owlready2.onto_path.remove(folder + "/")
        world.get_ontology(folder + "/automotive_urban_traffic_ontology.owl").load()
        if load_cp:
            world.get_ontology(folder + "/criticality_phenomena.owl").load()
            world.get_ontology(folder + "/criticality_phenomena_formalization.owl").load()
        # Importing extras only required for non-default worlds as otherwise this is handled via owlready2 already.
        if add_extras and world is not owlready2.default_world:
            logger.debug("Loading extra modules into A.U.T.O.")
            _add_extras(more_extras)
        logger.debug("Done loading A.U.T.O.")
    else:
        logger.error("A.U.T.O. not found")
        raise FileNotFoundError(folder)


def _add_extras(more_extras: list[str] = None):
    """
    Loads all extra module functionality (i.e. those members specified in the `extras` module and its submodules) into
    the classes provided by owlready2. The global world is the world to load the functionality into. Note that all
    other worlds won't have this functionality!
    :param more_extras: A name of an importable module that contains more extra functionality to load from. Will be
        imported in the given order. Using wildcards at the end is possible, e.g. "a.b.*", which then recursively
        imports *all* Python files located in the package's (sub)folder(s).
    """
    global _extras

    importlib.invalidate_caches()

    # Reload all already loaded modules
    importlib.invalidate_caches()
    for mod in sorted(_extras.keys(), reverse=True):
        importlib.reload(_extras[mod])

    # Load all modules that are not already loaded (handled by importlib)
    if more_extras is None:
        extra_mods = []
    else:
        extra_mods = more_extras
    # Everything in pyauto.extra module is loaded by default
    for root, dirs, files in os.walk(os.path.dirname(os.path.realpath(__file__)) + "/extras"):
        for file in files:
            if file.endswith(".py") and not file.startswith("_"):
                extra_mod = "pyauto." + root.split("pyauto/")[-1].replace("/", ".") + "." + file.replace(".py", "")
                if extra_mod not in extra_mods:
                    extra_mods.append(extra_mod)
    succ_mods = []
    fail_mods = []
    for extra_mod in extra_mods:
            try:
                mod = extra_mod
                while mod.endswith(".*"):
                    mod = extra_mod[:-2]
                imp = importlib.import_module(mod)
                if extra_mod.endswith(".*"):
                    for root, dirs, files in os.walk("/".join(imp.__file__.split("/")[:-1])):
                        for file in files:
                            if file.endswith(".py") and not file.startswith("_"):
                                wc_mod = mod + "." + file.replace(".py", "")
                                if wc_mod not in _extras.keys():
                                    wc_imp = importlib.import_module(wc_mod)
                                    succ_mods.append(wc_mod)
                                    _extras[wc_mod] = wc_imp
                else:
                    if mod not in _extras.keys():
                        succ_mods.append(mod)
                        _extras[mod] = imp
            except ModuleNotFoundError:
                fail_mods.append(extra_mod)
    logger.debug("Loaded extra modules " + ", ".join(succ_mods) + " into A.U.T.O.")
    if len(fail_mods) > 0:
        logger.warning("Extra modules " + ", ".join(fail_mods) + " not installed, not loaded into A.U.T.O.")


def main():
    parser = argparse.ArgumentParser(
        prog='auto.py',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="An interface (read & visualize) to traffic scenarios specified as ABoxes in A.U.T.O.")
    parser.add_argument("file", type=str, help="Path to a .kbs file containing a list of ABoxes to read")
    parser.add_argument("--read", "-r", action='store_true', help="Only reading, no visualization")
    parser.add_argument("--hertz", "-hz", type=int, default=20, help="The sampling rate (Hertz) of the scenario")
    parser.add_argument("--verbose", "-v", action='store_true', help="If set, gives verbose output")
    args = parser.parse_args()

    if args.verbose:
        loglevel = logging.DEBUG
    else:
        loglevel = logging.INFO
    logging.basicConfig(level=loglevel, format="%(asctime)s %(levelname)s: %(message)s")

    def int_handler(sig, frame):
        pyauto.utils.delete_temporary_folder()
        os._exit(0)
    signal.signal(signal.SIGINT, int_handler)

    loaded_scenario = scenario.Scenario(file=args.file, hertz=args.hertz, seed=0)
    if not args.read:
        visualizer.visualize(loaded_scenario)
    else:
        pyauto.utils.delete_temporary_folder()


if __name__ == "__main__":
    main()
