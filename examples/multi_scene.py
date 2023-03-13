import logging

from pyauto import auto, augmentator
from pyauto.models.scenario import Scenario
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.DEBUG)

# creates a scenario with two empty scenes (and loads A.U.T.O.)
sc = Scenario(2, load_cp=True)

# scene 1: creates ego vehicle & pedestrian
l4_de_1 = sc[0].ontology(auto.Ontology.L4_DE)
l4_co_1 = sc[0].ontology(auto.Ontology.L4_Core)
ego_1 = l4_de_1.Passenger_Car()
ego_1.set_geometry(5, 10, 5.1, 2.2)
ego_1.set_velocity(6, 0)
ped_1 = l4_co_1.Pedestrian()
ped_1.set_geometry(9, 1, 0.6, 0.3)
ped_1.set_velocity(0, 3)
ped_1.has_height = 1.7

# scene 2: creates ego vehicle & pedestrian
l4_de_2 = sc[1].ontology(auto.Ontology.L4_DE)
l4_co_2 = sc[1].ontology(auto.Ontology.L4_Core)
ego_2 = l4_de_2.Passenger_Car()
ego_2.set_geometry(6, 10, 5.1, 2.2)
ego_2.set_velocity(3, 0)
ped_2 = l4_co_2.Pedestrian()
ped_2.set_geometry(9, 2, 0.6, 0.3)
ped_2.set_velocity(0, 0.5)

# augment - will infer speed and yaw from set velocity
augmentator.augment(sc)

# saves the ABoxes
sc.save_abox("/tmp/scenario.owl")

# visualizes the ABox
visualizer.visualize(sc)
