import owlready2

from shapely.affinity import translate

from pyauto import auto
from pyauto.extras.physics.dynamical_object import Dynamical_Object

l4_de = auto.world.get_ontology(auto.Ontology.L4_DE.value)

with l4_de:
    class Passenger_Car(Dynamical_Object):
        def simulate(self, mapping: dict[owlready2.NamedIndividual, owlready2.NamedIndividual], delta_t: float | int = 0):
            # Computes new data
            acceleration_x = -2
            speed_x = self.get_speed() + acceleration_x * delta_t
            # Writes update to object in new scene
            new_self = mapping[self]
            new_self.set_acceleration(acceleration_x, 0)
            new_self.set_velocity(speed_x, 0)
            new_self.has_yaw = self.has_yaw
            new_geo = translate(self.get_geometry(), xoff=speed_x * delta_t, yoff=0, zoff=0)
            new_self.hasGeometry[0].asWKT = [new_geo.wkt]
