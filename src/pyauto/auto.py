import owlready2
import os
import importlib
import logging
from enum import Enum

import pyauto.extras.physics

"""
Loads A.U.T.O. globally into owlready2. Also provides an easier enum interface to access the sub-ontologies of A.U.T.O.
"""

logger = logging.Logger(__name__)


class Ontology(Enum):
    """
    Contains an enumeration of all sub-ontologies of A.U.T.O. pointing to their IRIs (as str)
    """
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


def get_ontology(ontology: Ontology, world: owlready2.World = owlready2.default_world) -> owlready2.Ontology:
    """
    Can be used to fetch a specific sub-ontology of A.U.T.O. from a given world. Also handles the case of saving and
    re-loading ontologies into owlready2, where (due to import aggregation into a single ontology), ontologies were
    merged but namespaces remain.
    :param ontology: The ontology to fetch.
    :param world: The world to search for the ontology (the default world if not set)
    :return: The ontology object corresponding to the given ontology.
    """
    iri = ontology.value
    if world.ontologies and iri in world.ontologies.keys():
        return world.ontologies[iri]
    else:
        return world.get_ontology("http://anonymous#").get_namespace(iri)


def load(folder: str = None, world: owlready2.World = None, add_extras: bool = True) -> None:
    """
    Loads A.U.T.O. from a given folder location.
    :param folder: The folder to look for, should contain the `automotive_urban_traffic_ontology.owl`. Can be None, in
        this case, it takes the ontology located in this repository.
    :param world: The world to load A.U.T.O. into. If None, loads into the default world.
    :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
    :raise FileNotFoundError: if given an invalid folder location.
    """
    if folder is None:
        folder = os.path.dirname(os.path.realpath(__file__)) + "/../../auto"
    if os.path.isdir(folder):
        # Setting correct path for owlready2
        for i, j, k in os.walk(folder + "/"):
            owlready2.onto_path.append(i)
        owlready2.onto_path.remove(folder + "/")
        # Loading ontology into world (or default world)
        if world is None:
            world = owlready2.default_world
        world.get_ontology(folder + "/automotive_urban_traffic_ontology.owl").load()
        if add_extras:
            _add_extras(world)
    else:
        raise FileNotFoundError(folder)


def load_cp(folder: str = None, world: owlready2.World = None, add_extras: bool = True) -> None:
    """
    Loads A.U.T.O. along with the criticality phenomena ontologies (vocabulary, formalization) from a given folder
    location.
    :param folder: The folder to look for, should contain the `automotive_urban_traffic_ontology.owl`,
    criticality_phenomena.owl`, `criticality_phenomena_formalization.owl`
    :param world: The world to load A.U.T.O. & CPs into. If None, loads into the default world.
    :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
    :raise FileNotFoundError: if given an invalid folder location.
    """
    if folder is None:
        folder = os.path.dirname(os.path.realpath(__file__)) + "/../../auto"
    if os.path.isdir(folder):
        # Setting correct path for owlready2
        for i, j, k in os.walk(folder + "/"):
            owlready2.onto_path.append(i)
        owlready2.onto_path.remove(folder + "/")
        # Loading ontology into world (or default world)
        if world is None:
            world = owlready2.default_world
        world.get_ontology(folder + "/automotive_urban_traffic_ontology.owl").load()
        world.get_ontology(folder + "/criticality_phenomena.owl").load()
        world.get_ontology(folder + "/criticality_phenomena_formalization.owl").load()
        if add_extras:
            _add_extras(world)
    else:
        raise FileNotFoundError(folder)


def _add_extras(world: owlready2.World = owlready2.default_world):
    """
    Loads all extra module functionality (i.e. those members specified in `extras`) into the classes provided by
    owlready2.
    :param world: The world to load the functionality into. Note that all other worlds won't have this functionality!
    """
    for file in os.listdir(os.path.dirname(os.path.realpath(__file__)) + "/extras"):
        if file.endswith(".py") and file != "__init__.py":
            mod = importlib.import_module("pyauto.extras." + file.replace(".py", ""))
            if hasattr(mod, "apply"):
                mod.apply(world)
