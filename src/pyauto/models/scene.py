from __future__ import annotations

import logging
import os
import owlready2

from xml.etree import ElementTree

from pyauto import auto

logger = logging.getLogger(__name__)


class Scene(owlready2.World):
    def __init__(self, timestamp: float | int = 0, parent_scenario=None, add_extras: bool = True,
                 load_cp: bool = False):
        """
        Creates a new scene and loads A.U.T.O. into this scene (this may take some time).
        :param timestamp: Optional point in time of this scene.
        :param parent_scenario: If the scene belongs to a list of scenes, this points to the parent scenario of type
            pyauto.models.scenario.Scenario.
        :param add_extras: Whether to import the extra functionality that is added the classes from owlready2.
        :param load_cp: Whether to load the criticality_phenomena.owl (and formalization) as well.
        """
        super().__init__()
        self._scenario = parent_scenario
        self._timestamp = timestamp
        self._added_extras = add_extras
        self._loaded_cp = load_cp
        auto.load(world=self, add_extras=add_extras, load_cp=load_cp)

    def __str__(self):
        if self._scenario is not None:
            return str(self._scenario) + " @ " + str(self._timestamp)
        else:
            return "Scene @ " + str(self._timestamp)

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

    def save_abox(self, file: str = None, format: str = "rdfxml", **kargs):
        """
        Works analogously to the save() method of owlready2.World, but saves the ABox auf A.U.T.O. only.
        Note that right now, only the "rdfxml" format is supported. If some other format is given, the plain save()
        method is executed. This method also removes all existing color individuals of A.U.T.O.'s physics ontology since
        we do not want to have those individuals doubly present.
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
            _TO_DELETE = {"Class", "Datatype", "AllDisjointClasses", "Description", "DatatypeProperty",
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
        new = Scene(self._timestamp + delta_t, self._scenario, self._added_extras, self._loaded_cp)
        mapping = {}

        # Creates all new individuals
        for ind in self.individuals():
            # Only create individuals that are not already there (e.g. exclude colors)
            if ind.iri not in [x.iri for x in new.individuals()]:
                if len(ind.is_a) > 0:
                    cls = new.get_ontology(ind.is_a[0].namespace.base_iri)
                    new_ind = getattr(cls, ind.is_a[0].name)(ind.name)
                    mapping[ind] = new_ind
                    for cls in ind.is_a[1:]:
                        new_cls = new.get_ontology(cls.namespace.base_iri)
                        new_ind.is_a.append(new_cls)
                else:
                    logger.warning("Can not copy over an individual " + str(ind) + " which has no classes.")

        # After copying all individuals, we copy the relations that were to_keep
        for ind in mapping.keys():
            for var in vars(ind).keys():
                if var in [t._name for t in to_keep]:
                    vals = vars(ind)[var]
                    if not isinstance(vals, list):
                        vals = [vals]
                    for val in vals:
                        if val in mapping.keys():
                            val = mapping[val]
                        if not isinstance(vars(ind)[var], list):
                            setattr(mapping[ind], var, val)
                        else:
                            getattr(mapping[ind], var).append(val)

        return mapping, new

    def simulate(self, delta_t: float | int) -> Scene:
        """
        Performs one simulation step, starting from this scene. Creates a new scene (by means of copying) and calls
        the simulate method for the given time difference for each individual.
        :param delta_t: The time difference to simulate.
        """
        ge = self.ontology(auto.Ontology.GeoSPARQL)
        ph = self.ontology(auto.Ontology.Physics)
        to_keep = {ge.hasGeometry, ge.asWKT, ph.has_height}
        mapping, new = self.copy(delta_t, to_keep)
        for ind in mapping.keys():
            if hasattr(ind, "simulate"):
                ind.simulate(mapping, delta_t)
        return new
