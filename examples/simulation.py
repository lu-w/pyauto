import logging

from pyauto import auto
from pyauto.models.scenario import Scenario
from pyauto.models.scenery import Scenery
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# first, create a scenery with one lane
statics = Scenery(load_cp=True, name="Simple Scenery")
l1_core = statics.ontology(auto.Ontology.L1_Core)
road = l1_core.Road()
road.set_geometry(10, 10, 20, 5)
road.cross_section((l1_core.Lane, 0.4), (l1_core.Lane, 0.6))

# creates a scenario with one empty scene, adds the scenery to it
sc = Scenario(1, scenery=statics, name="Simulation Example", load_cp=True, more_extras=["tobm.sim_models.generic.*"])
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

# creates two new scenes by means of simulation and adds it to the scenario (scenery will be added automatically)
sc.simulate(duration=2, delta_t=1)

# augment - will infer e.g. speed and yaw from set velocity in all ABoxes
sc.augment()

# saves the ABoxes (scenery and single scenes) - "scenario_full.owl" serves as a template
sc.save_abox("/tmp/scenario_full.owl")

# and once more for a reduced, non-geometrical version
sc.save_abox("/tmp/scenario_reduced.owl", to_ignore={"geosparql.Geometry"})

# visualizes the ABoxes
visualizer.visualize(sc)
