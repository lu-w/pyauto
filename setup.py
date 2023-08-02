from setuptools import setup, find_packages

setup(
    name="pyauto",
    version="0.1",
    python_requires='>=3.10',
    packages=["src/pyauto"],
    description="Python module for accessing A.U.T.O. based on owlready2",
    author ="Lukas Westhofen",
    author_email="lukas.westhofen@dlr.de",
    include_package_data=True,
    package_data={"pyauto": ["auto", "visualizer/files"]},
    install_requires=[
        "owlready2==0.40",
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
