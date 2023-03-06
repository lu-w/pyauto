# pyauto

A python module for accessing the [Automotive Urban Traffic Ontology](https://github.com/lu-w/auto/) using owlready2.
It basically provides an easier access to
- loading A.U.T.O. into owlready2
- A.U.T.O.'s set of IRIs
- retrieving a single ontology of A.U.T.O. based on a given IRI
- a web-based visualizer for ABoxes specified in the A.U.T.O. TBox

## Install

(TODO)

## Example

This small example loads A.U.T.O., creates a vehicle in the ABox, saves, and visualizes it.

```python
# imports pyauto
from pyauto import auto, auto_visualizer
# creates an ABox
world = owlready2.World()
# loads A.U.T.O. into this world
auto.load(world)
# accesses the relevant sub-ontologies easily
l4_de = auto.get_ontology(auto.Ontology.L4_De, world)
ge = auto.get_ontology(auto.Ontology.GeoSPARQL, world)
# creates a vehicle
from shapely import geometry
ego = l4_de.Passenger_Car()
ego_geometry = ge.Geometry()
ego_geometry.asWKT = [geometry.Polygon([(4, 23), (9, 23), (9, 21), (4, 21), (4, 23)]).wkt]
ego.hasGeometry = [ego_geometry]
# saves the ABox
world.save("/tmp/world.owl")
# visualizes the ABox
auto_visualizer.visualize_scenario(world)
```

For a larger example on how to use this module, look at the [example of the criticality recognition program](https://github.com/lu-w/criticality-recognition/blob/main/inputs/example_fuc_2_3.py).

# TODO

- make an installable python module out of this (empty __init__?)
- rename auto_visualizer to visualizer

# Plans for module
- implement functions that abstract creation of commonly used objects (e.g. geometry etc.)
  - best as constructors
  - provide some convenience functions for accessing geometries, calculating distances etc.
- relocate omega2auto in separate git and import pyauto
  - use new constructors for this
- 