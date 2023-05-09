from ... import auto
from . import vehicle

l4_core = auto.world.get_ontology(auto.Ontology.L4_Core.value)

with l4_core:

    class Bicycle(vehicle.Vehicle):

        def _get_relevant_lanes(self):
            """
            :returns: A list of lanes in which the vehicle can be validly be located upon.
            """
            l1_co = self.namespace.world.get_ontology(auto.Ontology.L1_Core.value)
            l1_de = self.namespace.world.get_ontology(auto.Ontology.L1_DE.value)
            return l1_co.search(type=(l1_co.Driveable_Lane | l1_de.Bikeway_Lane))
