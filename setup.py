from setuptools import setup, find_packages

setup(
    name='imva_rc',
    version='0.1.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Flask',
    ],
    entry_points={
        'console_scripts': [
            'imva_rc=imva_rc.app:main'
        ]
    }
)

