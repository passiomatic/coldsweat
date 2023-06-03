'''
Configuration settings
'''

from pathlib import Path
import os

base_dir = Path(__file__).parent.parent


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or "some secret key"
    DATABASE_URL = os.environ.get('DATABASE_URL')\
        or f"sqlite:///{base_dir.joinpath('instance', 'coldsweat.db')}"


class TestingConfig(Config):
    DATABASE_URL = 'sqlite:///:memory:'
    TESTING = True
