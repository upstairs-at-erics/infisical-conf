from infisical_conf import InfisicalManager, DEBUG
from rich import print as rprint




# Initialize the manager (checks keys & creates client)
manager = InfisicalManager(log_level=DEBUG, redact = False, visuals = True )  # redact is default

manager.set_visuals(True)

# Pull into cache
manager.set_env('vps')
manager.pull("shakedown-backend-api.tianji.*" )  # visualise = False if dont want diagnostics
manager.pull("shakedown-backend-api.tianji.TIANJI_URL")
manager.pull("shakedown-backend-api.*.*" )

# Drop it
manager.drop("shakedown-backend-api.*.*" )

# Force Some Errors
manager.pull("*.*.*")                  # Forbidden 
manager.pull("cloudflarewww.*.zone")    # Forbidden
manager.pull("cloudflarewww.*.*")      # Error in 'project-name'

# Set New default env for next project
manager.set_env('prod')

# Pull Whole Project (with wildcards) into Cache
manager.pull("shakedown-sumup-email-orders.*.*" )

# Get from everything from Cache with wildcards (returns a dict)
features = manager.get("*.*.*")
# or with the get_all helper which returns the full cache (same as get with wildcards)
conf     = manager.get_all()
conf     = conf["shakedown-sumup-email-orders"]["features"]
rprint(conf.get('NEW_ORDER_HA_NOTIFY_ECHOS'), type(conf.get('HA_SPEAKERS')))


# Get from cache with fully qualified key for a specific project and folder (returns value or None)
features = manager.get("shakedown-sumup-email-orders.features.*")
HA_MOBILES = manager.get("shakedown-sumup-email-orders.features.NEW_ORDER_HA_NOTIFY_ECHOS")
#print(HA_MOBILES)

# Set a Key - will load new folder in cache if doesn't exist
# project must exist 
# New Folder will be created in Infisical on push (if folder doesn't exist)
manager.set_secret("shakedown-sumup-email-orders.features.NEW_KEY_FEATURE", 12)

# Set a new feature in new folder
focus = "shakedown-sumup-email-orders.new-folder.NEW_KEY_FEATURE"
manager.set_secret(focus, 24)

# Show the dirty tree of pending changes before push
#manager.show_dirty_tree()

# Push Everything (only the dirty keys will be pushed, and new folders will be created as needed)
manager.push_all()

# Check the cache status after push to see the key/folder    counts
#manager.cache_status()

# again but withe a single key (fully qualified path)
manager.set_secret(focus, 333)
manager.push(focus)

# Finally Drop everything in the cache
manager.clear()
manager.cache_status()

