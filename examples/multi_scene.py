import logging

import owlready2
from pyauto import auto, augmentator
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.DEBUG)

# creates the empty scenario (and loads A.U.T.O.)
scene_1, scene_2 = auto.new_scenario(2)

# scene 1: creates ego vehicle
l4_de_1 = auto.get_ontology(auto.Ontology.L4_DE, scene_1)
ego_1 = l4_de_1.Passenger_Car()
ego_1.set_geometry(5, 10, 5.1, 2.2)
ego_1.set_velocity(5, 0)

# scene 2: creates ego vehicle
l4_de_2 = auto.get_ontology(auto.Ontology.L4_DE, scene_2)
ego_2 = l4_de_2.Passenger_Car()
ego_2.set_geometry(6, 10, 5.1, 2.2)
ego_2.set_velocity(3, 0)

# augment - will infer speed & yaw from set velocity
augmentator.augment(scene_1, scene_2)

# saves the ABoxes
scene_1.save_abox("/tmp/scene_1.owl")
scene_2.save_abox("/tmp/scene_2.owl")

# visualizes the ABox
visualizer.visualize_scenario([scene_1, scene_2])
