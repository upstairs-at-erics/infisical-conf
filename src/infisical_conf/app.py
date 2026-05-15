import os, time
import requests
from infisical_sdk import InfisicalSDKClient

from rich import print as rprint
from rich.table import Table
from rich.tree import Tree

from .logger import log, set_log_level, configure_logger

from .auth import AuthMixin
from .notation import NotationMixin
from .api import APIMixin
from .pull_sdk import PullOpsMixin
from .push_sdk import PushOpsMixin
from .set import SetOpsMixin
from .get import GetCacheMixin
from .cache_ops import PureCacheMixin
from .visualisations import VisualisationsMixin




## Global Severity Constants #################################
## used in log calls 
DEBUG    = "DEBUG"     # dim cyan
INFO     = "INFO"      # green
WARNING  = "WARNING"   # yellow
ERROR    = "ERROR"     # bold red
CRITICAL = "CRITICAL"  # bold white on red
##############################################################


class InfisicalManager(
    AuthMixin, NotationMixin, APIMixin, PullOpsMixin, 
    PushOpsMixin, GetCacheMixin, PureCacheMixin, VisualisationsMixin, SetOpsMixin):
    

    def __init__(self, log_level=INFO, redact=False, visuals=False, readonly=False):

        self.name = "infisical-conf"
        method    = "__init__"
        
        
        # Variable used by Infisical Environment setup 
        self.sources = {}
        
        # Initialise Cache and Defaults
        self._cache = {}
        self.last_response = None  # do we still need this?

        # Snapshot of last known remote values (from pull)
        self._remote_cache = {}      # full_key -> remote value

        # Index of keys that exist in Infisical (from pull)
        self._infisical_index = set()  # { "project.folder.key", ... }

        # Dirty tracking
        self._dirty_updates = set()  # existing keys with changed values
        self._dirty_creates = set()  # new keys not yet in Infisical
        
        # Start the global console log with threshold
        configure_logger(app_name=self.name, method_width=12)

        self.log_level = log_level
        set_log_level(log_level)
        log(method, f"Logger Threshold | [cyan]{log_level}[/cyan]", "DEBUG")

        # Initialise default for Environment
        self.default_env   = "prod"
        log(method, f"Environment | Defaulted to: [cyan]{self.default_env}[/cyan]", "DEBUG")

        # Enable Visuals
        self.visuals = visuals
        visual_state = "[green]Enabled[/green]" if visuals else "[red]Disabled[/red]"
        log(method, f"Logger Visuals | {visual_state}", DEBUG)

        # Enable redaction of secrets in visuals
        self.redact = redact
        redact_state = "[green]Enabled[/green]" if redact else "[red]Disabled[/red]"
        log(method, f"Logger Secrets Redaction | {redact_state}", DEBUG)
        
        # Read-only Flag (prevents any push operations if True)
        self.readonly = readonly
        readonly_state = "[green]Enabled[/green]" if readonly else "[red]Disabled[/red]"
        log(method, f"Read-Only Mode | {readonly_state}", DEBUG)    

        # Initialise Tree display settings
        self.tree_notes = True
        self.tree_tags  = True
        notes_state = "[green]Enabled[/green]" if self.tree_notes else "[red]Disabled[/red]"
        tags_state  = "[green]Enabled[/green]" if self.tree_tags  else "[red]Disabled[/red]"
        log(method, f"Tree Notes  | {notes_state}", DEBUG)
        log(method, f"Tree Tags   | {tags_state}", DEBUG)

        # Load and track sources
        self._bootstrap_environment()
        
        # Get Access Secrets for Infisical
        self.host          = self._get_env_with_source("INFISICAL_HOST")
        self.client_id     = self._get_env_with_source("INFISICAL_CLIENT_ID")
        self.client_secret = self._get_env_with_source("INFISICAL_CLIENT_SECRET")
        
        # Strict Validation
        missing = [k for k, v in {
            "INFISICAL_HOST": self.host,
            "INFISICAL_CLIENT_ID": self.client_id,
            "INFISICAL_CLIENT_SECRET": self.client_secret
        }.items() if not v]

        if missing:
            error_msg = f"Missing required variables: {', '.join(missing)}"
            log(self.name, error_msg, level=CRITICAL)
            raise EnvironmentError(error_msg)

        # Initialize and Auth
        self.client = InfisicalSDKClient(host=self.host)
        self._authenticate()

        # Pull and cache Projects
        self.pull_projects_list()




    #####################################################################################################
    #######  DEFAULTS (CONTEXT)                                                                   #######
    #####################################################################################################

    def _booler(self, value, setting_name="value"):

        """
            Utility to normalise various truthy/falsy inputs into a boolean True/False.
            Accepts: True/False, 1/0, 'on'/'off', 'enabled'/'disabled' (case-insensitive)
        """

        truthy = {True, 1, "1", "on", "On", "ON", "enabled", "Enabled", "ENABLED"}
        falsy  = {False, 0, "0", "off", "Off", "OFF", "disabled", "Disabled", "DISABLED"}

        if value in truthy: return True
        if value in falsy:  return False

        raise ValueError(
            f"Invalid value for {setting_name}: {value}. "
            "Use True/False, 1/0, 'on'/'off', 'enabled'/'disabled'."
        )

    def set_env(self, env=None):
        
        """ 
            Sets default environment for subsequent cache and infisical operations. 
            If env is None, defaults to 'prod' at startup.
        """
        method = "SETTINGS"
        
        self.default_env = env or "prod"
        log(method, f"Environment | Set | [cyan]({self.default_env})[/cyan]", INFO)

    def set_visuals(self, value):

        """ 
            Runtime toggle for visuals. 
            Accepts: True/False, 1/0, 'on'/'off', 'enabled'/'disabled'
        """
        method = "SETTINGS"
        self.visuals = self._booler(value, "visuals")
        visual_state = "[green]Enabled[/green]" if self.visuals else "[red]Disabled[/red]"
        log(method, f"Logger Visuals | {visual_state}", DEBUG)

        return self.visuals

    def set_tree_tags(self, value):
        
        """ 
            Runtime toggle for showing tags in tree visuals. 
            Accepts: True/False, 1/0, 'on'/'off', 'enabled'/'disabled'
        """
        method = "SETTINGS"
        self.tree_tags = self._booler(value, "tree_tags")
        state = "[green]Enabled[/green]" if self.tree_tags else "[red]Disabled[/red]"
        log(method, f"Tree Tags | {state}", DEBUG)

        return self.tree_tags

    def set_tree_notes(self, value):
        """
            Runtime toggle for showing notes in tree visuals.
            Accepts: True/False, 1/0, 'on'/'off', 'enabled'/'disabled'
        """
        method = "SETTINGS"
        self.tree_notes = self._booler(value, "tree_notes")
        state = "[green]Enabled[/green]" if self.tree_notes else "[red]Disabled[/red]"
        log(method, f"Tree Notes | {state}", DEBUG)

        return self.tree_notes




    


if __name__ == "__main__":

    
    
    #####################################
    ### EXAMPLE USAGE within a script
    #    the manager object can be named anything, but will need to be injected into calls for subsequent use


    # Initialize the manager (checks keys & creates client)
    manager = InfisicalManager(log_level=DEBUG, redact = True, visuals = True, readonly=True )  # redact is default

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
    #rprint(conf)
    conf     = conf["shakedown-sumup-email-orders"]["features"]
    #rprint(conf.get('NEW_ORDER_HA_NOTIFY_ECHOS'), type(conf.get('HA_SPEAKERS')))


    # Get from cache with fully qualified key for a specific project and folder (returns value or None)
    features = manager.get("shakedown-sumup-email-orders.features.*")
    HA_MOBILES = manager.get("shakedown-sumup-email-orders.features.NEW_ORDER_HA_NOTIFY_ECHOS")
    print(HA_MOBILES)

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

 