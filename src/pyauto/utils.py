"""
Utils for A.U.T.O.
"""

import logging
from pyauto import auto

logger = logging.getLogger(__name__)

_CACHED_CP_CLASSES = dict()


def monkeypatch(cls):
    def decorator(func):
        setattr(cls, func.__name__, func)
        return func

    return decorator


def _get_individual_id(individual) -> str:
    """
    Returns a unique identifier as a string for the given individual.
    :param individual: The individual to get the ID for.
    :return: A string representing the ID.
    """
    if hasattr(individual, "identifier") and (isinstance(individual.identifier, list) and
                                              len(individual.identifier) > 0 and
                                              type(individual.identifier[0]) in [int, str]) or (
            type(individual.identifier) in [int, str]):
        return str(individual.identifier[0])
    else:
        return str(individual)


def get_most_specific_classes(list_of_individuals, caching=True):
    """
    Helper function that looks up the subsumption hierarchy and returns the most specific classes of a list of
    individuals(i.e. removes all classes that are a parent of some class of the individuals). It looks only at the
    subsumption hierarchy spanned by the domain (L1-L6) and perception, physics, and act ontologies.
    :param list_of_individuals: A list of individuals
    :param caching: Whether to use caching for already computed most specific classes
    :return: A list of tuples containing the individual in the first entry and a list of most specific classes in the
    second entry (as strings)
    """
    res = []
    noncached_list_of_individuals = []
    if caching:
        for i in list_of_individuals:
            if i in _CACHED_CP_CLASSES.keys():
                i_id = _get_individual_id(i)
                res.append((i_id, _CACHED_CP_CLASSES[i]))
            else:
                noncached_list_of_individuals.append(i)
    relevant_iris = [auto.Ontology.L1_Core.value, auto.Ontology.L2_Core.value,
                     auto.Ontology.L3_Core.value, auto.Ontology.L4_Core.value,
                     auto.Ontology.L5_Core.value, auto.Ontology.L6_Core.value, auto.Ontology.L1_DE.value,
                     auto.Ontology.L2_DE.value, auto.Ontology.L3_DE.value, auto.Ontology.L4_DE.value,
                     auto.Ontology.L5_DE.value, auto.Ontology.L6_DE.value]
    relevant_additional_iris = [auto.Ontology.Perception.value, auto.Ontology.Physics.value]
    for individual in noncached_list_of_individuals:
        relevant_classes = [x for x in individual.namespace.ontology.classes() if x.namespace.base_iri in relevant_iris]
        relevant_additional_classes = [x for x in individual.namespace.ontology.classes() if x.namespace.base_iri in
                                       relevant_additional_iris]
        individual_clss = list(filter(lambda x: x in relevant_classes, individual.INDIRECT_is_a))
        if len(individual_clss) == 0:
            # Retry finding something outside of domain ontologies, e.g. physics
            individual_clss = list(filter(lambda x: x in relevant_additional_classes, individual.INDIRECT_is_a))
        individual_id = _get_individual_id(individual)
        most_specific_individual_clss = [str(individual_cls) for individual_cls in individual_clss if
                                         hasattr(individual_cls, "__subclasses__") and len(
                                             set(individual_cls.__subclasses__()).intersection(set(individual_clss)))
                                         == 0]
        res.append((individual_id, most_specific_individual_clss))
        if caching:
            _CACHED_CP_CLASSES[individual] = most_specific_individual_clss
    return res
