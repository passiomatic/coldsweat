from setuptools import setup

setup(
    name='coldsweat',
    version='0.9.5',
    packages=['coldsweat'],
    install_requires=[
        'Feedparser',
        'Peewee',
        'Requests',
        'WebOb',
        'Tempita',
    ],
    entry_points={
        'console_scripts': ['sweat=coldsweat.commands:run'],
    },
    include_package_data=True,
    zip_safe=False,
)
