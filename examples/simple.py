from pyauto import auto
from pyauto.models.scene import Scene
from pyauto.visualizer import visualizer

# loads A.U.T.O. into the default world
scene = Scene()
# accesses the relevant sub-ontologies easily
l4_de = scene.ontology(auto.Ontology.L4_DE)
# creates one vehicle
ego = l4_de.Passenger_Car()
ego.set_geometry(5, 10, 5.1, 2.2)
# saves the ABox
scene.save_abox("/tmp/scene.owl")
# visualizes the ABox
visualizer.visualize(scene)
