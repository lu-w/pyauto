import owlready2

from ... import auto

l1_core = auto.world.get_ontology(auto.Ontology.L4_Core.value)

with l1_core:

    class Crossing(owlready2.Thing):

        def set_roads(self, **roads):
            self.connects = [r for r in roads]
