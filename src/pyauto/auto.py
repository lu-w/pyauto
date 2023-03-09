import owlready2
import os
import importlib
import logging
from xml.etree import ElementTree
from enum import Enum

from pyauto.utils import monkeypatch

"""
Loads A.U.T.O. globally into owlready2. Also provides an easier enum interface to access the sub-ontologies of A.U.T.O.
"""

logger = logging.Logger(__name__)

# The world that A.U.T.O. was loaded into the last time load() was called. Standard is owlready2.default_world.
_world = owlready2.default_world
# Imported modules of extras (in order to be able to reload them in case of more than one world)
_extras = []


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


def load(folder: str = None, world: owlready2.World = None, add_extras: bool = True, load_cp: bool = False) -> None:
    """
    Loads A.U.T.O. from a given folder location.
    :param folder: The folder to look for, should contain the `automotive_urban_traffic_ontology.owl`. Can be None, in
        this case, it takes the ontology located in this repository.
    :param world: The world to load A.U.T.O. into. If None, loads into the default world.
    :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
    :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
    :raise FileNotFoundError: if given an invalid folder location.
    """
    global _world
    # Loading ontology into world (or default world)
    if world is None:
        _world = owlready2.default_world
    else:
        _world = world
    if folder is None:
        folder = os.path.dirname(os.path.realpath(__file__)) + "/../../auto"
    if os.path.isdir(folder):
        # Setting correct path for owlready2
        for i, j, k in os.walk(folder + "/"):
            owlready2.onto_path.append(i)
        owlready2.onto_path.remove(folder + "/")
        _world.get_ontology(folder + "/automotive_urban_traffic_ontology.owl").load()
        if load_cp:
            _world.get_ontology(folder + "/criticality_phenomena.owl").load()
            _world.get_ontology(folder + "/criticality_phenomena_formalization.owl").load()
        # Importing extras only required for non-default worlds as otherwise this is handled via owlready2 already.
        if add_extras and _world is not owlready2.default_world:
            _add_extras()
    else:
        raise FileNotFoundError(folder)


def _add_extras():
    """
    Loads all extra module functionality (i.e. those members specified in `extras`) into the classes provided by
    owlready2. The global _world is the world to load the functionality into. Note that all other worlds won't have this
    functionality!
    """
    global _extras
    if len(_extras) == 0:
        for file in os.listdir(os.path.dirname(os.path.realpath(__file__)) + "/extras"):
            if file.endswith(".py") and file != "__init__.py":
                mod = importlib.import_module("pyauto.extras." + file.replace(".py", ""))
                _extras.append(mod)
    else:
        for mod in _extras:
            importlib.reload(mod)


@monkeypatch(owlready2.World)
def save_abox(self, file: str = None, format: str = "rdfxml", **kargs):
    """
    Works analogously to the save() method of owlready2.World, but saves the ABox auf A.U.T.O. only.
    Note that right now, only the "rdfxml" format is supported. If some other format is given, the plain save() method
    is executed. This method also removes all existing color individuals of A.U.T.O.'s physics ontology since we do not
    want to have those individuals doubly present.
    It adds an import to the internet location of A.U.T.O. such that the ABox is well-defined by the imports.
    Note: This method overwrites existing files.
    :param file: A string to a file location to save the ABox to.
    :param format: The format to save in (one of: rdfxml, ntriples, nquads). Recommended: rdfxml.
    """
    self.save(file, format, **kargs)
    if file is not None and format == "rdfxml":
        # Read in file again
        tree = ElementTree.parse(file)

        # Remove all unwanted elements
        _TO_DELETE = {"Class", "Datatype", "AllDisjointClasses", "Description", "DatatypeProperty", "ObjectProperty",
                      "Ontology", "AnnotationProperty"}
        _COLORS_DELETE = {"Blue", "Green", "Red", "White", "Yellow"}

        root = tree.getroot()
        for child in reversed(root):
            _, _, tag = child.tag.rpartition("}")
            if tag in _TO_DELETE or (tag in "Color" and
                                     child.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"].split("#")[ -1]
                                     in _COLORS_DELETE):
                root.remove(child)

        # Adds owl prefix
        root.set("xmlns:owl", "http://www.w3.org/2002/07/owl#")

        # Set ontology name and add AUTO as import (since all other ontologies and imports were removed)
        onto = ElementTree.Element("owl:Ontology")
        filename = os.path.basename(file)
        if "." in filename:
            filename = filename.split(".")[:-1]
            filename = ".".join(filename)
        onto.set("rdf:about", "http://purl.org/auto/" + filename)
        ElementTree.SubElement(onto, "owl:imports", {"rdf:resource": "http://purl.org/auto/"})
        root.insert(0, onto)

        # Save file again
        tree.write(file)
