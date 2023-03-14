import owlready2
import os
import importlib
import logging

from enum import Enum

"""
Loads A.U.T.O. globally into owlready2. Also provides an easier enum interface to access the sub-ontologies of A.U.T.O.
"""

# Logging
logger = logging.Logger(__name__)

# The world that A.U.T.O. was loaded into the last time load() was called. Standard is owlready2.default_world.
world = owlready2.default_world

# Imported modules of extras (in order to be able to reload them in case of more than one world)
_extras = []


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
    :param more_extras: A name of an importable module that contains more extra functionality to load from.
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
            _add_extras(more_extras)
    else:
        raise FileNotFoundError(folder)


def _add_extras(more_extras: list[str] = None):
    """
    Loads all extra module functionality (i.e. those members specified in the `extras` module and its submodules) into
    the classes provided by owlready2. The global world is the world to load the functionality into. Note that all
    other worlds won't have this functionality!
    :param more_extras: A name of an importable module that contains more extra functionality to load from.
    """
    global _extras
    # Load all modules (does not reload already loaded module - will handle later)
    if more_extras is None:
        extra_mods = []
    else:
        extra_mods = more_extras
    for root, dirs, files in os.walk(os.path.dirname(os.path.realpath(__file__)) + "/extras"):
        for file in files:
            if file.endswith(".py") and file != "__init__.py":
                extra_mod = "pyauto." + root.split("pyauto/")[-1].replace("/", ".") + "." + file.replace(".py", "")
                extra_mods.append(extra_mod)
    for extra_mod in extra_mods:
        try:
            mod = importlib.import_module(extra_mod)
            _extras.append(mod)
            logger.debug("Loaded extra module " + extra_mod + " into A.U.T.O.")
        except ModuleNotFoundError:
            logger.debug("Extra module " + extra_mod + " not installed, not loaded into A.U.T.O.")
    # Reload all already loaded modules
    for mod in _extras:
        importlib.reload(mod)
