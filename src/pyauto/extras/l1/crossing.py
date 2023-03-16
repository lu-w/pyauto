import owlready2

from ... import auto

l1_de = auto.world.get_ontology(auto.Ontology.L1_DE.value)

with l1_de:

    class Crossing(owlready2.Thing):

        def set_roads(self, *roads):
            self.connects = [r for r in roads]
