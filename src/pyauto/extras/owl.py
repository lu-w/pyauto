import owlready2

from pyauto import auto


def simulate(thing, mapping: dict[owlready2.NamedIndividual, owlready2.NamedIndividual]):
    """
    Generic simulation method - keeps everything 'as is', i.e. no changes occur. This means that every
    unprotected property of the individual as specified in the mapping will be copied over to this individual.
    Thus, this method does not create a new individual but rather updates the properties of a copied individual.
    This requires therefore the copy() method of its Scene to be called beforehand.
    :param thing: The thing to simulate. Has to be in the given mapping.
    :param mapping: A mapping from the individuals of the previous state of the simulation to the new one.
        For example, {vehicle_t0: vehicle@_t1}.
    """
    # Copies over *all* properties (if they are not already present)
    for var in vars(thing).keys():
        if (getattr(mapping[thing], var) == [] or getattr(mapping[thing], var) is None) and \
                not var.startswith("_"):
            vals = vars(thing)[var]
            if not isinstance(vals, list):
                vals = [vals]
            for val in vals:
                if val in mapping.keys():
                    val = mapping[val]
                if not isinstance(vars(thing)[var], list):
                    setattr(mapping[thing], var, val)
                else:
                    getattr(mapping[thing], var).append(val)
                print("Set " + str(thing) + "." + str(var) + " = " + str(val))


with auto._world.get_ontology("http://www.w3.org/2002/07/owl#"):

    class Thing(owlready2.Thing):
        def simulate(self, mapping: dict[owlready2.NamedIndividual, owlready2.NamedIndividual],
                     delta_t: float | int = 0):
            """
            Generic simulation method - keeps everything 'as is', i.e. no changes occur. This means that every
            unprotected property of the individual as specified in the mapping will be copied over to this individual.
            Thus, this method does not create a new individual but rather updates the properties of a copied individual.
            This requires therefore the copy() method of its Scene to be called beforehand.
            :param mapping: A mapping from the individuals of the previous state of the simulation to the new one.
                For example, {vehicle_t0: vehicle@_t1}.
            :param delta_t: The time step to simulate. For generic OWL Things, this is ignored (defaults to 0).
            """
            simulate(self, mapping)
