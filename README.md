# pyauto

A python package for accessing the [Automotive Urban Traffic Ontology](https://github.com/lu-w/auto/) using owlready2.
It basically provides an easier access to
- loading A.U.T.O. into owlready2
- A.U.T.O.'s set of IRIs
- retrieving a single ontology of A.U.T.O. based on a given IRI
- a web-based visualizer for ABoxes specified in the A.U.T.O. TBox

## Install

First, initialize submodules: `git submodule update --init --recursive`.
Install this package via `pip install .`.

## Example

This small example loads A.U.T.O., creates a vehicle in the ABox, saves, and visualizes it.

```python
# imports relevant modules
import owlready2
from pyauto import auto, visualizer

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
```

For a larger example on how to use this package, look at the [example of the criticality recognition](https://github.com/lu-w/criticality-recognition/blob/main/inputs/example_fuc_2_3.py).

# TODO
- implement functions that abstract creation of commonly used objects (e.g. geometry etc.)
  - provide some convenience functions for accessing geometries, calculating distances etc.

## List of convenience functions needed

- setting geometries
  - 2d rectangles (done) (set width automatically TODO)
  - points (done)
  - 3d rectangles (set height automatically)
  - add_geometry_from_polygon
  - create line from point list (not a polygon) (with and without height)
    - with and without width (buffer by geometry)
  - getting geometries as shapely objects?
- setting velocity (and add speed vector directly from this)
- same for acceleration
- Environment class
  - add_precipitation(mmh: float) that automatically stores the amount and assigns the correct classification
  - same for wind
  - same for cloudiness
  - same for daytime
  - same for air (temp, rel humd, visibility, pressure)
- add_marker() for selected objects e.g. Pedestrian_Ford, Bicycle_Ford, etc. (see lateral_marking.py)
- applies_to relation when adding marker's geometry automatically by checking which previously created lanes and their roads it intersects
- creating a road network
  - determining successor lanes based on connecting geometries?
  - create an n-lane road given its overall width and length and a querschnitt -> list of classes and their proportion of the overall road
    - e.g. `fill_road({l1_core.Roadwalk: 0.1, l1_core.Lane: 0.4, l1_core.Lane: 0.4, l1_core.Roadwalk: 0.1})`
- Bicyclist (create a bicycle automatically that is driven by it)
- copy from a previously created world