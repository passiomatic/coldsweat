'''
Configuration settings
'''

from pathlib import Path
import os

base_dir = Path(__file__).parent.parent


class Config:
    #CDN_DOMAIN = None
    #CDN_TIMESTAMP = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or "some secret key"
    DATABASE_URL = os.environ.get('DATABASE_URL')\
        or f"sqlite:///{base_dir.joinpath('instance', 'coldsweat.db')}"


class TestingConfig(Config):
    DATABASE_URL = 'sqlite:///:memory:' # Override    
    TESTING = True
