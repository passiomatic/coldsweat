'''
Coldsweat - RSS aggregator and web reader compatible with the Fever API
'''

__author__ = 'Andrea Peltrin'
__version__ = (0, 10, 0, '')
__license__ = 'MIT'

__all__ = [
    'VERSION_STRING',
    'USER_AGENT',

    # Synthesized entries and feed URI's
    'FEED_TAG_URI',
    'ENTRY_TAG_URI',
]

VERSION_STRING = '%d.%d.%d%s' % __version__
USER_AGENT = ('Coldsweat/%s Feed Fetcher <http://lab.passiomatic.com/'
              'coldsweat/>' % VERSION_STRING)

FEED_TAG_URI = 'tag:lab.passiomatic.com,2017:coldsweat:feed:%s'
ENTRY_TAG_URI = 'tag:lab.passiomatic.com,2017:coldsweat:entry:%s'

# Figure out installation directory. This has
#  to work for the fetcher script too

# installation_dir = os.environ.get("COLDSWEAT_INSTALL_DIR")

# if not installation_dir:
#     installation_dir, _ = os.path.split(
#         os.path.dirname(os.path.abspath(__file__)))

# template_dir = os.path.join(installation_dir, 'coldsweat/templates')

# ------------------------------------------------------
# Load up configuration settings
# ------------------------------------------------------

# config_path = os.environ.get("COLDSWEAT_CONFIG_PATH")

# if not config_path:
#     config_path = os.path.join(installation_dir, 'config')

# config = load_config(config_path)

# ------------------------------------------------------
# Configure logger
# ------------------------------------------------------

# Shared logger instance
# for module in 'peewee', 'requests':
#     logging.getLogger(module).setLevel(logging.WARN)

# logger = logging.getLogger()

# if config.log.filename == 'stderr':
#     logger.addHandler(logging.StreamHandler())
#     logger.setLevel(config.log.level)
# elif config.log.filename:
#     logging.basicConfig(
#         filename=config.log.filename,
#         level=getattr(logging, config.log.level),
#         format='[%(asctime)s] %(process)d %(levelname)s %(message)s',
#     )
# else:
#     # Silence is golden
#     logger.addHandler(logging.NullHandler())
