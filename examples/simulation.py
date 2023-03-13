import logging

from pyauto import auto, augmentator
from pyauto.models.scenario import Scenario
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.DEBUG)

# creates a scenario with two empty scenes (and loads A.U.T.O.)
sc = Scenario(1, load_cp=True)

# scene 1: creates ego vehicle & pedestrian
l4_de = sc[0].ontology(auto.Ontology.L4_DE)
l4_co = sc[0].ontology(auto.Ontology.L4_Core)
ego = l4_de.Passenger_Car("ego")
ego.set_geometry(5, 10, 5.1, 2.2)
ego.set_velocity(6, 0)
ped = l4_co.Pedestrian("ped")
ped.set_geometry(9, 1, 0.6, 0.3)
ped.set_velocity(0, 3)
ped.has_height = 1.7
ego.is_in_front_of = [ped]

# TODO allow to create a static world which is imported by every scene and set as a property of the scenario.
# but does this work?...

sc.append(sc[0].simulate(delta_t=0.1))

# augment - will infer speed and yaw from set velocity
#augmentator.augment(sc)

# saves the ABoxes
#sc.save_abox("/tmp/scenario.owl")

# visualizes the ABox
visualizer.visualize(sc)
