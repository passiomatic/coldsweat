from os import path
from ConfigParser import SafeConfigParser
import logging

# Figure out installation directory. This has 
#  to work for the fetcher script too
installation_dir, _ = path.split(path.dirname(path.abspath(__file__)))

def load_config(filename):
    
    config = SafeConfigParser({
        'engine': 'sqlite', 
        'filename': 'data/coldsweat.db', 
    })
    
    config.read(filename)    

    return config

# Set up configuration settings
config = load_config(path.join(installation_dir, 'etc/config'))

logging.basicConfig(
    filename    = config.get('log', 'filename', 'coldsweat.log'),
    level       = getattr(logging, config.get('log', 'level', 'DEBUG')),
    format      = config.get('log', 'format', '%(asctime)s %(levelname)s: %(message)s'),
    datefmt     = config.get('log', 'datefmt', '%Y-%m-%d %H:%M:%S'),
)
                    
# Quiet Peewee, quiet                    
logging.getLogger("peewee").setLevel(logging.INFO)

# Shared logger instance
log = logging.getLogger()
