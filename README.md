# pyauto

A python package for accessing the [Automotive Urban Traffic Ontology](https://github.com/lu-w/auto/) using owlready2.
It basically provides an easier access to
- loading A.U.T.O. into owlready2
- A.U.T.O.'s set of IRIs
- retrieving a single ontology of A.U.T.O. based on a given IRI
- creating scenarios, scenes, and sceneries within A.U.T.O.
- saving such models to an OWL file
- a web-based visualizer for A.U.T.O. scenarios and scenes

## Install

First, initialize submodules: `git submodule update --init --recursive`.
Install the requirements using `pip install -r requirements.txt`, and then this package via `pip install .`.

## Example

This small example loads A.U.T.O., creates a vehicle in the ABox, saves, and visualizes it.

```python
from pyauto import auto
from pyauto.models.scene import Scene
from pyauto.visualizer import visualizer

# creates a scene and loads A.U.T.O. into it
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
```

For examples, have a look at the `examples` folder in this repository.

# TODO for convenience functions in extras

- setting geometries
  - 3d rectangles (and set height automatically)
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
- integrate this package in omega2auto
