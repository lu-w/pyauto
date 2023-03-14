import logging

from pyauto import auto, augmentator
from pyauto.models.scenario import Scenario
from pyauto.models.scenery import Scenery
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.DEBUG)

# first, create a scenery with one lane
statics = Scenery(load_cp=True)
l1_core = statics.ontology(auto.Ontology.L1_Core)
lane = l1_core.Lane()
lane.set_geometry(5, 0, 20, 5)

# creates a scenario with one empty scene, adds the scenery to it
sc = Scenario(1, scenery=statics, load_cp=True)
sc.set_scenery(statics)

# populates scene 1: creates ego vehicle & pedestrian
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

# creates a new scene by means of simulation and adds it to the scenario (scenery will be added automatically)
sc.append(sc[0].simulate(delta_t=0.1))

# augment - will infer speed and yaw from set velocity
# augmentator.augment(sc)

# saves the ABoxes (scenery and single scenes) - "scenario.owl" only serves as a template
# sc.save_abox("/tmp/scenario_full.owl")

# and once more for a reduced, non-geometrical version
# sc.save_abox("/tmp/scenario_reduced.owl", to_ignore={"geosparql.Geometry"})

# TODO move visualizer into its own package
# TODO fix visualizer not depending on individual ordering for color consistency
# visualizes the ABoxes
visualizer.visualize(sc)
