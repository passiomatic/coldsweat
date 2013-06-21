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
config = load_config(path.join(installation_dir, 'coldsweat.ini'))

logging.basicConfig(
    level=logging.DEBUG, 
    filename=path.join(installation_dir, 'coldsweat.log'),
    format='%(asctime)s %(levelname)s: %(message)s',    
    datefmt='%Y-%m-%d %H:%M:%S')
                    
# Quiet Peewee, quiet                    
logging.getLogger("peewee").setLevel(logging.INFO)

log = logging.getLogger()
