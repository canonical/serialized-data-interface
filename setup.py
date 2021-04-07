import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="serialized_data_interface",
    version="0.2.0",
    author="Dominik Fleischmann",
    author_email="dominik.fleischmann@canonical.com",
    description="Serialized Data Interface for Juju Operators",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    install_requires=[
        "jsonschema",
        "ops",
        "pyyaml",
        "requests",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
)
