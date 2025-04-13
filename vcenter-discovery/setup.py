from setuptools import setup, find_packages

setup(
    name='vcenter-discovery',
    version='0.0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'vcenter-discovery = vcenter_discovery.main:main',
        ],
    },
    install_requires=[
        'netboxlabs-diode-sdk',
        'pyvmomi',
    ],
    author='Eric Hester',
    author_email='hester1@clemson.edu',
    description='Clemson University vCenter Discovery Backend for Orb Agent',
    long_description='A backend for discovering vCenter data and integrating with Orb Agent.',
)