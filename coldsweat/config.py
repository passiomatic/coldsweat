'''
Configuration settings
'''

from pathlib import Path
import os

base_dir = Path(__file__).parent.parent


class Config:
    CDN_DOMAIN = os.environ.get('CDN_DOMAIN', default=None)
    SECRET_KEY = os.environ.get('SECRET_KEY') or "some secret key"
    DATABASE_URL = os.environ.get('DATABASE_URL')\
        or f"sqlite:///{base_dir.joinpath('instance', 'coldsweat.db')}"
        #or f"sqliteext:///{base_dir.joinpath('instance', 'coldsweat.db')}?foreign_keys=1&journal_mode=WAL"


class TestingConfig(Config):
    DATABASE_URL = 'sqlite:///:memory:' # Override    
    TESTING = True
