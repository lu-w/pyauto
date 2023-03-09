import logging

from pyauto import auto, augmentator
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.DEBUG)

# creates the empty scenario (and loads A.U.T.O.)
scene_1, scene_2 = auto.new_scenario(2, load_cp=True)

# scene 1: creates ego vehicle & dog
l4_de_1 = auto.get_ontology(auto.Ontology.L4_DE, scene_1)
ego_1 = l4_de_1.Passenger_Car()
ego_1.set_geometry(5, 10, 5.1, 2.2)
ego_1.set_velocity(6, 0)
dog_1 = l4_de_1.Dog()
dog_1.set_geometry(9, 1, 0.6, 0.3)
dog_1.set_velocity(0, 0.5)

# scene 2: creates ego vehicle & dog
l4_de_2 = auto.get_ontology(auto.Ontology.L4_DE, scene_2)
ego_2 = l4_de_2.Passenger_Car()
ego_2.set_geometry(6, 10, 5.1, 2.2)
ego_2.set_velocity(3, 0)
dog_2 = l4_de_2.Dog()
dog_2.set_geometry(9, 2, 0.6, 0.3)
dog_2.set_velocity(0, 0.5)

# augment - will infer speed from set velocity
augmentator.augment(scene_1, scene_2)

# saves the ABoxes
scene_1.save_abox("/tmp/scene_1.owl")
scene_2.save_abox("/tmp/scene_2.owl")

# visualizes the ABox
visualizer.visualize_scenario([scene_1, scene_2])
