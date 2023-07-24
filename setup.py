from distutils.core import setup

setup(
    name="pyauto",
    version="0.1",
    description="Python module for accessing A.U.T.O. based on owlready2",
    author ="Lukas Westhofen",
    author_email="lukas.westhofen@dlr.de",
    include_package_data=True,
    package_data={"pyauto": ["auto", "visualizer/files"]},
    install_requires=[
        "owlready2",
        "matplotlib",
        "mpld3",
        "shapely==1.8.0",
        "sympy",
        "numpy",
        "screeninfo",
        "tqdm",
        "owlready2_augmentator"
    ],
    entry_points={
        'console_scripts': [
            'pyauto = pyauto.auto:main',
        ],
    }
)
