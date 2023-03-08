# imports relevant modules
import owlready2
from pyauto import auto
from pyauto.visualizer import visualizer

# loads A.U.T.O.
scene_1 = owlready2.World()
scene_2 = owlready2.World()
auto.load(world=scene_1)
auto.load(world=scene_2)
# accesses the relevant sub-ontologies easily
l4_de_1 = auto.get_ontology(auto.Ontology.L4_DE, scene_1)
l4_de_2 = auto.get_ontology(auto.Ontology.L4_DE, scene_2)
# scene 1: creates one vehicle
ego_1 = l4_de_1.Passenger_Car()
ego_1.set_geometry(5, 10, 5.1, 2.2)
# scene 2: creates one vehicle
ego_2 = l4_de_2.Passenger_Car()
ego_2.set_geometry(6, 10, 5.1, 2.2)
# saves the ABoxes
scene_1.save("/tmp/scene_1.owl")
scene_2.save("/tmp/scene_2.owl")

# visualizes the ABox
visualizer.visualize_scenario([scene_1, scene_2])
