# auth.py

import os
from .logger import log
from infisical_sdk import InfisicalSDKClient

DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"

#####################################################################################################
#######  INFISICAL ENVIRONMENT                                                                #######
#####################################################################################################

class AuthMixin:

    def _get_env_with_source(self, key, default=None):

        """ Utility to get environment variable value along with its source for logging purposes. """

        method = "AUTH"

        val    = os.getenv(key, default)
        source = self.sources.get(key, "SYSTEM SHELL")
        log(method, f"Loaded {key:<25} | Source: [bold cyan]{source}[/bold cyan]", DEBUG)
        return val

    def _bootstrap_environment(self):

        """ 
            Bootstraps the environment by loading variables from multiple sources in order of precedence:
            1. System Environment Variables
            2. .env file (if python-dotenv is installed)
            3. /etc/environment file (Unix-like systems)
        """

        try:
            from dotenv import dotenv_values
            env_vals = dotenv_values(".env")
            for k, v in env_vals.items():
                if k not in os.environ:
                    os.environ[k] = v
                    self.sources[k] = ".ENV FILE"
        except ImportError: pass

        self._load_etc_environment()

    def _load_etc_environment(self):

        """ Loads environment variables from /etc/environment if it exists. 
            Common location for system-wide environment variables on Unix-like systems. 
        """
        method = "AUTH"

        env_path = "/etc/environment"
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if "=" in line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            value      = value.strip("'").strip('"').strip()
                            if key not in os.environ:
                                os.environ[key] = value
                                self.sources[key] = "/ETC/ENVIRONMENT"
            except Exception as e:
                log(method, f"Could not read {env_path}: {e}", WARNING)

    def _authenticate(self):

        """ 
        Authenticates with Infisical using client credentials and retrieves an access token.
        Logs success or failure of authentication.
         """
        method = "AUTH"
        log(method, "Authenticating with Infisical...", INFO)  
        
        try:
            response = self.client.auth.universal_auth.login(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.accesstoken = response.accessToken
            log(method, f"[green]SUCCESS[/green]. Access Token Received", INFO)

        except Exception as e:
            log(method, f"[red]FAILED[/red]: {e}", CRITICAL)
            raise
