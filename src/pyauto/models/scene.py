from __future__ import annotations

import logging
import os
import pathlib
import tempfile

import numpy
import owlready2
import owlready2_augmentator

from xml.etree import ElementTree

import pyauto.utils
from .. import auto

logger = logging.getLogger(__name__)


class Scene(owlready2.World):
    """
    A scene represent a single measurement sample in a scenario and is modeled as an owlready2.World, spearated from all
    other scenes (i.e., worlds).
    """

    _SCENERY_COMMENT = "_auto_scenery"  # enables unique identification of scenery elements in OWL files.

    def __init__(self, timestamp: float | int = 0, parent_scenario=None, scenery=None, scenery_file: str = None,
                 folder: str = None, add_extras: bool = True, more_extras: list[str] = None, load_cp: bool = False,
                 name: str = None):
        """
        Creates a new scene and loads A.U.T.O. into this scene (this may take some time).
        :param timestamp: Optional point in time of this scene.
        :param parent_scenario: If the scene belongs to a list of scenes, this points to the parent scenario of type
            pyauto.models.scenario.Scenario.
        :param scenery: The scenery object of this scene.
        :param scenery_file: An optional string representing a file path of the scenery OWL file, to avoid saving
            an ABox multiple times.
        :param folder: The folder to look for, should contain the `automotive_urban_traffic_ontology.owl`. Can be None,
            in this case, it takes the ontology located in the pyauto repository.
        :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
        :param more_extras: A name of an importable module that contains more extra functionality to load from. Will be
            imported in the given order. Using wildcards at the end is possible, e.g. "a.b.*", which then recursively
            imports *all* Python files located in the package's (sub)folder(s).
        :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
        :param name: An optional name (string) of this scenario. If not set, will use a generic name based on timestamp.
        """
        super().__init__()
        self._scenario = parent_scenario
        self._timestamp = timestamp
        self._added_extras = add_extras
        self._more_extras = more_extras
        self._loaded_cp = load_cp
        self._name = name
        # Note: We use an sqlite3-file as backend. This uses disk and not memory, but is actually a bit more efficient.
        backend_dir = pyauto.utils.make_temporary_subfolder("backend")
        with tempfile.NamedTemporaryFile(dir=backend_dir, suffix=".sqlite3", delete=False) as f:
            logger.debug("Creating scene " + str(self) + " at " + f.name)
            self.set_backend(filename=f.name)
        auto.load(folder=folder, load_into_world=self, add_extras=add_extras, more_extras=more_extras, load_cp=load_cp)
        self._scenery_file = self.set_scenery(scenery, scenery_file)

    def __str__(self):
        if self._name is not None:
            return self._name
        else:
            if self._scenario is not None:
                return "Scene[" + str(self._scenario) + "]@" + str(self._timestamp)
            else:
                return "Scene@" + str(self._timestamp)

    def ontology(self, ontology: auto.Ontology) -> owlready2.Ontology:
        """
        Can be used to fetch a specific sub-ontology of A.U.T.O. from a given world. Also handles the case of saving and
        re-loading ontologies into owlready2, where (due to import aggregation into a single ontology), ontologies were
        merged but namespaces remain.
        :param ontology: The ontology to fetch.
        :return: The ontology object corresponding to the given ontology.
        """
        iri = ontology.value
        if self.ontologies and iri in self.ontologies.keys():
            return self.ontologies[iri]
        else:
            return self.get_ontology("http://anonymous#").get_namespace(iri)

    def save_abox(self, file: str = None, format: str = "rdfxml", save_scenery=False,
                  scenery_file: str = None, to_ignore: set[str] = None, iri=None, **kargs) -> str:
        """
        Works analogously to the save() method of owlready2.World, but saves the ABox auf A.U.T.O. only.
        Note that right now, only the "rdfxml" format is supported. If some other format is given, the plain save()
        method is executed. This method also removes all existing color individuals of A.U.T.O.'s physics ontology since
        we do not want to have those individuals doubly present.
        It adds an import to the internet location of A.U.T.O. such that the ABox is well-defined by the imports.
        Note: This method overwrites existing files.
        :param file: A string to a file location to save the ABox to.
        :param format: The format to save in (one of: rdfxml, ntriples, nquads). Recommended: rdfxml.
        :param save_scenery: The scenery is always an imported ontology. Therefore, we can control whether to ignore it,
            or to save it as well in a separate file (then, called file_scenery.owl). Default is False, since we assume
            that the top level scenario takes care of saving the scenery. Then, however, we can use the scenery_file.
        :param scenery_file: A file location to the scenery file that is to be imported. Can be useful if the scenery
            was already saved somewhere else, and we want to avoid saving it again. If set, save_scenery is ignored.
        :param to_ignore: If given, individuals (also indirectly) belonging to this set of classes are not saved.
            Classes are given as their string representation including their namespace (e.g. geosparql.Geometry).
        :param uri: The IRI of the ontology. If none, it is "http://purl.org/auto/{file_base_name}"
        :returns: The IRI that was assigned to the ABox as str.
        """
        # First, we remove all individuals belonging to some class in to_ignore.
        undos_ignore = []
        if to_ignore is not None:
            for i in self.individuals():
                if not set([str(x) for x in i.INDIRECT_is_a]).isdisjoint(to_ignore):
                    undos_ignore.append(owlready2.destroy_entity(i, undoable=True))

        # Then, we remove all individuals from the scenery, if an import is given (as these will be imported later).
        # However, we keep them 'bare' in this scene, as to also keep their relations to individuals in this scene.
        undos_scenery = {}
        scenery_inds = []
        if save_scenery or scenery_file is not None:
            for i in self.individuals():
                if Scene._SCENERY_COMMENT in i.comment:
                    undos_scenery[i] = {"comment": Scene._SCENERY_COMMENT}
                    for prop in i.get_properties():
                        if prop.python_name != "comment":
                            to_keep = []
                            undos_scenery[i][prop.python_name] = []
                            for i2 in prop[i]:
                                if not isinstance(i2, owlready2.Thing) or \
                                        (hasattr(i2, "comment") and Scene._SCENERY_COMMENT in i2.comment):
                                    undos_scenery[i][prop.python_name].append(i2)
                                else:
                                    to_keep.append(i2)
                            prop[i] = to_keep
                    undos_scenery[i]["is_a"] = []
                    undos_scenery[i]["is_a"].extend(i.is_a)
                    i.is_a = []
                    scenery_inds.append(i)

        for i in scenery_inds:
            i.comment = []

        # Saves ABox - we will parse it and remove irrelevant stuff later
        self.save(file, format, **kargs)

        # Undo deletion of individuals - in case we want to work further with the scene
        for undo in list(reversed(undos_ignore)):
            undo()

        for i in list(reversed(undos_scenery.keys())):
            for prop in list(reversed(undos_scenery[i].keys())):
                if len(undos_scenery[i][prop]) > 0:
                    if isinstance(getattr(i, prop), list):
                        getattr(i, prop).extend(undos_scenery[i][prop])
                    else:
                        setattr(i, prop, undos_scenery[i][prop][0])

        for i in scenery_inds:
            i.comment = [Scene._SCENERY_COMMENT]

        # Post-processing
        if file is not None and format == "rdfxml":
            # Creates folder in case it does not yet exist
            pathlib.Path(os.path.dirname(file)).mkdir(parents=True, exist_ok=True)

            # First, create the file name of the scene
            file_name = os.path.basename(file)
            file_ending = ""
            if "." in file_name:
                split = file_name.split(".")
                file_name = split[:-1]
                file_ending = split[-1]
                file_name = ".".join(file_name)

            # Saves scenery to have a scenery file name that we can later import
            if save_scenery and scenery_file is not None:
                scenery_file = file_name + "_scenery" + file_ending
                self._scenery.save_abox(scenery_file, format, kargs)

            # Read in file again
            tree = ElementTree.parse(file)

            # Remove all unwanted elements
            _TO_DELETE = {"Class", "Datatype", "AllDisjointClasses", "DatatypeProperty",
                          "ObjectProperty", "Ontology", "AnnotationProperty"}
            _COLORS_DELETE = {"Blue", "Green", "Red", "White", "Yellow"}

            root = tree.getroot()
            for child in reversed(root):
                _, _, tag = child.tag.rpartition("}")
                if tag in _TO_DELETE or (tag in "Color" and
                                         child.attrib["{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"]
                                                 .split("#")[-1] in _COLORS_DELETE):
                    root.remove(child)

            # Adds owl prefix
            root.set("xmlns:owl", "http://www.w3.org/2002/07/owl#")
            root.set("xml:base", "file:" + str(file_name))

            # Set ontology name and add AUTO as import (since all other ontologies and imports were removed)
            onto = ElementTree.Element("owl:Ontology")
            if not iri:
                iri = "http://purl.org/auto/" + file_name
            onto.set("rdf:about", iri)
            ElementTree.SubElement(onto, "owl:imports", {"rdf:resource": "http://purl.org/auto/"})
            # If scenery needs to be imported, do so
            if scenery_file:
                ElementTree.SubElement(onto, "owl:imports", {"rdf:resource": "file:" + os.path.basename(scenery_file)})
            root.insert(0, onto)

            # Save file again
            tree.write(file)

            return iri

    def set_scenery(self, scenery, scenery_file: str = None):
        """
        Sets the scenery for the given scene. Also propagates psuedo random number generators to the scenery.
        :param scenery: The scenery to set as a Scenery object (which is then stored to disk and re-loaded into this
            scene).
        :param scenery_file: An optional string representing a file path of the scenery OWL file, to avoid saving
            an ABox multiple times.
        :returns: The file name of the scenery which is created on disk during loading of the scenery (for possible
            later usage, e.g., efficiency), or scenery_file, if given.
        """
        if scenery is not None:
            # We load the scenery by saving only its ABox (temporarily) and loading it from the file.
            # This is the easiest way to prevent double loading of individuals.
            self._scenery = scenery
            if scenery_file is None:
                scenery_dir = pyauto.utils.make_temporary_subfolder("scenery_tmp")
                with tempfile.NamedTemporaryFile(dir=scenery_dir, suffix=".owl", delete=False) as f:
                    scenery_file = f.name
                    logger.debug("Writing scenery to file " + scenery_file)
                    self._scenery.save_abox(scenery_file)
            logger.debug("Loading scenery from " + scenery_file)
            self.get_ontology("file://" + scenery_file).load()
            # We make individuals from the scenery identifiable later on by adding a comment.
            for i in self.get_ontology("file://" + scenery_file + "#").individuals():
                if Scene._SCENERY_COMMENT not in i.comment:
                    i.comment.append(Scene._SCENERY_COMMENT)
            # Propagates scenario to scenery, if needed.
            if self._scenery is not None and self._scenery._scenario is None:
                self._scenery._scenario = self._scenario
            if not hasattr(scenery, "_random") and hasattr(self, "_random"):
                scenery._random = self._random
            if not hasattr(scenery, "_np_random") and hasattr(self, "_np_random"):
                scenery._np_random = self._np_random
            logger.debug("Finished setting scenery for scene " + str(self))
            return scenery_file

    def copy(self, delta_t: float | int = 0, to_keep: set = None) -> \
            tuple[dict[owlready2.NamedIndividual, owlready2.NamedIndividual], Scene]:
        """
        Copies this scene, i.e., creates a new scene object and copies over:
        - all individuals with their given name,
        - their directly specified classes, and
        - all properties specified in the to_keep set (can be specified as strings, or anything whose __str__ maps to a
            suitable representation of the property).
        Sets the new time stamp of the new scene according to delta_t. Can be 0, then the new scene has the same time
        stamp as this scene.
        :param delta_t: The time difference from the new to this scene.
        :param to_keep: The properties of individuals to copy over during copying.
        :returns: A tuple of a mapping from the old (i.e. in this scene) to the new individuals (i.e. in the returned
            scene) and the newly created scene.
        """
        timestamp = self._timestamp + delta_t
        if "." in str(delta_t):
            timestamp = numpy.round(timestamp, len(str(delta_t).split(".")[1]))
        new = Scene(timestamp=timestamp, parent_scenario=self._scenario, scenery=self._scenery,
                    scenery_file=self._scenery_file, add_extras=self._added_extras, more_extras=self._more_extras,
                    load_cp=self._loaded_cp)
        mapping = {}

        logger.debug("Copying individuals and relations")

        # Creates all new individuals
        for ind in self.individuals():
            # Only create individuals that are not already there (e.g. exclude colors)
            if ind.iri not in [x.iri for x in new.individuals()]:
                if not isinstance(type(ind), owlready2.FusionClass):
                    nsp = new.get_ontology(type(ind).namespace.base_iri)
                    new_ind = getattr(nsp, type(ind).name)(ind.name)
                else:
                    nsp = new.get_ontology(type(ind).is_a[0].namespace.base_iri)
                    new_ind = getattr(nsp, type(ind).is_a[0].name)(ind.name)
                mapping[ind] = new_ind
                for cls in ind.is_a:
                    # Right now, we only support is_a entries that are either direct classes or a role restriction with
                    # a direct class as its value.
                    if not hasattr(cls, "namespace") or not hasattr(cls, "name"):
                        if isinstance(cls, owlready2.Restriction) and \
                                isinstance(cls.value, owlready2.entity.ThingClass):
                            prop = cls.property
                            new_onto = new.get_ontology(prop.namespace.base_iri)
                            restriction = getattr(getattr(new_onto, prop.python_name),
                                                  owlready2.class_construct._restriction_type_2_label[cls.type])
                            if hasattr(cls, "cardinality"):
                                new_cls = restriction(cls.cardinality, getattr(new_onto, cls.value.name))
                            else:
                                new_cls = restriction(getattr(new_onto, cls.value.name))
                        else:
                            raise NotImplementedError("Copying for is_a entry " + str(cls) + " (type: "
                                                      + str(type(cls)) + ") not yet supported")
                    else:
                        new_cls = getattr(new.get_ontology(cls.namespace.base_iri), cls.name)
                    if new_cls not in new_ind.is_a:
                        new_ind.is_a.append(new_cls)

        # After copying all individuals, we copy the relations that were to_keep
        for ind in mapping.keys():
            for var in ind.get_properties():
                if str(var) in [str(x) for x in to_keep]:
                    vals = getattr(ind, var.python_name)
                    if not isinstance(vals, list):
                        vals = [vals]
                    for val in vals:
                        if val in mapping.keys():
                            val = mapping[val]
                        if not isinstance(getattr(ind, var.python_name), list):
                            setattr(mapping[ind], var.python_name, val)
                        elif val not in getattr(mapping[ind], var.python_name):
                            getattr(mapping[ind], var.python_name).append(val)

        return mapping, new

    def simulate(self, delta_t: float | int, to_keep: set = None, prioritize: list[str] = None) -> Scene:
        """
        Performs one simulation step, starting from this scene. Creates a new scene (by means of copying) and calls
        the simulate method for the given time difference for each individual.
        :param delta_t: The time difference to simulate.
        :param to_keep: The properties of individuals to copy over when creating new scenes.
        :param prioritize: A list of OWL classes or attributes of those individuals who are to prioritize in simulation.
        """
        logger.debug("Starting scene simulation")
        ge = self.ontology(auto.Ontology.GeoSPARQL)
        ph = self.ontology(auto.Ontology.Physics)
        rdfs = self.get_ontology("http://www.w3.org/2000/01/rdf-schema")
        ke = {ge.hasGeometry, ge.asWKT, ph.has_height, rdfs.comment}
        if to_keep is not None:
            ke = ke.union(to_keep)
        mapping, new = self.copy(delta_t, ke)
        # Ensures that things are in order (e.g. for prioritizing drivers in simulation)
        if prioritize is not None:
            def prio_key(a):
                for i, prio in enumerate(prioritize):
                    if len([x for x in a.INDIRECT_is_a if prio in str(x)]) > 0 or hasattr(a, prio):
                        return i
                return abs(hash(a) + len(prioritize))
            key = prio_key
        else:
            key = hash

        # Main simulation loop over individuals
        inds = sorted(mapping.keys(), key=key)
        for ind in inds:
            if hasattr(ind, "simulate"):
                ind.simulate(mapping, delta_t)

        return new

    def augment(self):
        """
        Augments this scene by using the `owlready2_augmentator`. Augmentation methods are given in `extras`.
        Note that only those methods will be called for augmentations that are decorated with @augment within classes
        that are decorated with @augment_class and loaded by a Python import.
        """
        owlready2_augmentator.reset()
        owlready2_augmentator.do_augmentation(*self.ontologies.values())

    def has_accident(self):
        """
        Checks whether there is an accident in this scene, i.e., some non-zero height spatial objects intersect.
        :returns: True iff. an accident was detected in this scene.
        """
        objs = list(self.search(type=self.get_ontology(auto.Ontology.Physics.value).Spatial_Object))
        for i, obj1 in enumerate(objs):
            for obj2 in objs[:i]:
                if obj1.has_accident_with(obj2):
                    return True
        return False

    def individuals(self):
        """
        Returns all individuals within this scene.
        This function behaves as the overriden owlready2 function if this scene was not loaded from file. Otherwise,
        it avoids duplicate entries in the individual generation due to a bug in owlready2.
        """
        generated = set()
        for i in super().individuals():
            if i.storid not in generated:
                yield i
                generated.add(i.storid)
