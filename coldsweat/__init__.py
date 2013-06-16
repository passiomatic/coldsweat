import logging

logging.basicConfig(level=logging.DEBUG, filename='./coldsweat.log',
                    format='%(asctime)s %(levelname)s: %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
                    
# Quiet Peewee, quiet                    
logging.getLogger("peewee").setLevel(logging.INFO)