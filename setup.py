from setuptools import setup, find_packages

with open('asyncio_mqtt/version.py', 'r') as f:
    exec(f.read())

setup(
    name='asyncio_mqtt',
    version=__version__,
    packages=find_packages(),
    url='https://github.com/sbtinstruments/asyncio-mqtt',
    author='Frederik Aalund',
    author_email='fpa@sbtinstruments.com',
    description='Idomatic asyncio wrapper around paho-mqtt.',
    license='Eclipse Public License v1.0 / Eclipse Distribution License v1.0',
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',

        'License :: OSI Approved',

        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: MacOS',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='mqtt async asyncio paho-mqtt wrapper',
    install_requires=['paho-mqtt>=1.5.0'],
)