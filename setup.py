from distutils.core import setup

setup(
    name="pyauto",
    version="0.1",
    description="Python module for accessing A.U.T.O. based on owlready2",
    author ="Lukas Westhofen",
    author_email="lukas.westhofen@dlr.de",
    install_requires=[
        "owlready2",
        "matplotlib",
        "mpld3",
        "shapely",
        "numpy",
        "screeninfo",
        "tqdm",
        "owlready2_augmentator"
    ]
)
