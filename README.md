# pyauto

A python package for accessing the [Automotive Urban Traffic Ontology](https://github.com/lu-w/auto/) using owlready2.
It basically provides access to
- loading A.U.T.O. into owlready2
- A.U.T.O.'s set of IRIs
- retrieving a single ontology of A.U.T.O. based on a given IRI
- creating scenarios, scenes, and sceneries within A.U.T.O.
- saving such models to an OWL file
- a web-based visualizer for A.U.T.O. scenarios and scenes

## Install

`pyauto` requires Python >= 3.10.
First, initialize submodules: `git submodule update --init --recursive`.
Install the requirements using `pip install -r requirements.txt`, and then this package via `pip install .`.

## Example

This small example loads A.U.T.O., creates a vehicle in the ABox, saves, and visualizes it.

```python
import logging

from pyauto import auto
from pyauto.models.scenario import Scenario
from pyauto.visualizer import visualizer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# creates a scenario with two empty scenes (and loads A.U.T.O.)
sc = Scenario(1, name="Example Scenario")

# scene: creates ego vehicle & pedestrian
l4_de_1 = sc[0].ontology(auto.Ontology.L4_DE)
l4_co_1 = sc[0].ontology(auto.Ontology.L4_Core)
ego_1 = l4_de_1.Passenger_Car()
ego_1.set_geometry(5, 10, 5.1, 2.2)
ego_1.set_velocity(6, 0)
ped_1 = l4_co_1.Pedestrian()
ped_1.set_geometry(9, 1, 0.6, 0.3)
ped_1.set_velocity(0, 3)

# saves the ABoxes - also creates /tmp/scenario.kbs
sc.save_abox("/tmp/scenario.owl")

# visualizes the ABox
visualizer.visualize(sc)
```

For examples, have a look at the `examples` folder in this repository.

## Visualization

`pyauto` can be used to visualize saved A.U.T.O. ABoxes in form `.kbs` files.
For this, call `pyauto /tmp/scenario.kbs` after installing `pyauto` (for the .kbs file created by the example above).
More information are available in `pyauto -h`.
