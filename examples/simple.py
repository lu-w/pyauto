# imports relevant modules
import owlready2
from pyauto import auto
from pyauto.visualizer import visualizer

# loads A.U.T.O. into the default world
auto.load()
# accesses the relevant sub-ontologies easily
l4_de = auto.get_ontology(auto.Ontology.L4_DE)
# creates one vehicle
ego = l4_de.Passenger_Car()
ego.set_geometry(5, 10, 5.1, 2.2)
# saves the ABox
owlready2.default_world.save("/tmp/world.owl")
# visualizes the ABox
visualizer.visualize_scenario([owlready2.default_world])
