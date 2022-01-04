### IMPORTANT ANNOUNCEMENT ###
#
# All additions to AGB will now cease.
# AGB's management will be limited to the following:
# - Optimization
# - Bug Fixes
# - Basic Maintenance
#
# DO NOT ADD ANY NEW FEATURES TO AGB
# ALL NEW FEATURES WILL BE RESERVED FOR MEKU
#
### IMPORTANT ANNOUNCEMENT ###

import psycopg
from utils import default

config = default.get("db_config.json")

db2 = psycopg.connect(
    dbname=config.database,
    user=config.user,
    password=config.password,
    host=config.host,
)
db2.autocommit = True

csr2 = db2.cursor()
