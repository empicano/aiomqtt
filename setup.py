# SPDX-License-Identifier: BSD-3-Clause
from setuptools import setup, find_packages

with open("asyncio_mqtt/version.py", "r") as f:
    exec(f.read())

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

setup(
    name="asyncio_mqtt",
    version=__version__,
    packages=find_packages(),
    package_data={
        "asyncio_mqtt": ["py.typed"],
    },
    url="https://github.com/sbtinstruments/asyncio-mqtt",
    author="Frederik Aalund",
    author_email="fpa@sbtinstruments.com",
    description="Idomatic asyncio wrapper around paho-mqtt.",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="BSD 3-clause License",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved",
        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="mqtt async asyncio paho-mqtt wrapper",
    install_requires=[
        "paho-mqtt>=1.5.0",
        "async_generator;python_version<'3.7'",
    ],
)
