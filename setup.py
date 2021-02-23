import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="serialized_data_interface",
    version="0.0.1",
    author="Dominik Fleischmann",
    author_email="dominik.fleischmann@canonical.com",
    description="Serialized Data Interface for Juju Operators",
    long_description=long_description,
    long_description_content_type="text/markdown",
    py_modules=["require_interface", "provide_interface", "interface_schema"],
    install_requires=[
        "ops",
        "pyyaml",
        "jsonschema",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
