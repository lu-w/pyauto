from pyauto import auto
from pyauto.visualizer import visualizer

# loads A.U.T.O. into the default world
scene = auto.new_scene()
# accesses the relevant sub-ontologies easily
l4_de = auto.get_ontology(auto.Ontology.L4_DE, scene)
# creates one vehicle
ego = l4_de.Passenger_Car()
ego.set_geometry(5, 10, 5.1, 2.2)
# saves the ABox
scene.save_abox("/tmp/scene.owl")
# visualizes the ABox
visualizer.visualize_scenario([scene])
