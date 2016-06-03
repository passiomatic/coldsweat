from setuptools import setup

setup(
    name='coldsweat',
    version='0.9.5',
    packages=['coldsweat'],
    install_requires=[
        'Feedparser==5.2.1',
        'Peewee==2.7.3',
        'Requests==2.2.1',
        'WebOb==1.3.1',
        'Tempita==0.5.1',
    ],
    entry_points={
        'console_scripts': ['sweat=coldsweat.commands:run'],
    },
    include_package_data=True,
    zip_safe=False,
)
