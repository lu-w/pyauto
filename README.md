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
```

For a larger example on how to use this package, look at the [example of the criticality recognition](https://github.com/lu-w/criticality-recognition/blob/main/inputs/example_fuc_2_3.py).

# TODO for convenience functions in extas

- setting geometries
  - 3d rectangles (set height automatically)
  - circles
  - add_geometry_from_polygon
  - create line from point list (not a polygon) (with and without height)
    - with and without width (buffer by geometry)
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