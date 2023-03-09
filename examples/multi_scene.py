import owlready2
import logging
from pyauto import auto, augmentator
from pyauto.visualizer import visualizer

logging.basicConfig(format="%(asctime)s %(levelname)s  %(message)s", datefmt="%H:%M:%S")

# loads A.U.T.O. for scene 1
scene_1 = owlready2.World()
auto.load(world=scene_1)
l4_de_1 = auto.get_ontology(auto.Ontology.L4_DE, scene_1)

# scene 1: creates ego vehicle
ego_1 = l4_de_1.Passenger_Car()
ego_1.set_geometry(5, 10, 5.1, 2.2)
ego_1.set_velocity(5, 0)

# loads A.U.T.O. for scene 2
scene_2 = owlready2.World()
auto.load(world=scene_2)
l4_de_2 = auto.get_ontology(auto.Ontology.L4_DE, scene_2)

# scene 2: creates ego vehicle
ego_2 = l4_de_2.Passenger_Car()
ego_2.set_geometry(6, 10, 5.1, 2.2)
ego_2.set_velocity(3, 0)

# augment - will infer speed from set velocity
augmentator.augment(scene_1, scene_2)

# saves the ABoxes
scene_1.save_abox("/tmp/scene_1.owl")
scene_2.save_abox("/tmp/scene_2.owl")

# visualizes the ABox
visualizer.visualize_scenario([scene_1, scene_2])
