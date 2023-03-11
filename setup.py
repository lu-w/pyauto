from distutils.core import setup

setup(
    name="pyauto",
    version="0.1",
    description="Python module for accessing A.U.T.O. based on owlready2",
    author ="Lukas Westhofen",
    author_email="lukas.westhofen@dlr.de",
    include_package_data=True,
    package_data={"pyauto": ["auto"]},
    install_requires=[
        "owlready2",
        "matplotlib",
        "mpld3",
        "shapely",
        "sympy",
        "numpy",
        "screeninfo",
        "tqdm",
        "owlready2_augmentator"
    ]
)
