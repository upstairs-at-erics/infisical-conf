# pull.py

import time
from .logger import log

DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"


class PullOpsMixin:
    """
    Contains all pull-related operations for Infisical.
    """

    #####################################################################################################
    #######  USE SDK TO ACCESS INFISICAL                                                          #######
    #####################################################################################################

    def _clean_infisical_error(self, msg: str) -> str:
        """
        Cleans and normalises Infisical SDK error messages.
        Removes boilerplate and rewrites known patterns into clean operator-grade errors.
        """

        msg = msg.strip()

        # Remove status code e.g. "(Status: 404)"
        if "(Status:" in msg: msg = msg.split("(Status:", 1)[0].strip()

        lower = msg.lower()

        # --- Known Infisical sdk error patterns -------------------------------------

        # 1. Folder not found  "Folder with path '/tianji' in environment 'prod' was not found"
        
        if "folder with path" in lower and "was not found" in lower:
            # Extract folder path and environment
            import re
            m = re.search(r"Folder with path '([^']+)' in environment '([^']+)'", msg)
            if m:
                folder, env = m.groups()
                return f"Folder not found: [red]{folder}[/red] - [cyan]Check env matches[/cyan]"

        # 2. Project not found "Project with slug 'shakedown-backend-apiXX' not found"

        if "project with slug" in lower and "not found" in lower:
            import re
            m = re.search(r"Project with slug '([^']+)'", msg)
            if m:
                slug = m.group(1)
                return f"Project not found: [red]{slug}[/red]"


        # Remove boilerplate sentence
        boilerplate = "please ensure the environment slug and secret path is correct"
        if boilerplate in lower:
            idx = lower.index(boilerplate)
            msg = msg[:idx].strip()

        # Clean trailing punctuation
        return msg.rstrip(". ").strip()

    #####################################################################################################
    #######  VALIDATION FOR PULL                                                                   #######
    #####################################################################################################

    def validate_for_pull(self, path, env):
        """
        Strict dot-notation parser for:
            project.folder.secret

        Rules:
            - project MUST be a real project (no wildcard)
            - folder MAY be '*' or a real folder
            - secret MAY be '*' or a real key
            - invalid: project.*.specific_key
            - valid:   project.folder.*
        """

        parts = path.split('.')
        if len(parts) != 3:
            raise ValueError(
                f"[orange1]{path}[/orange1] | Invalid Notation | 'project.folder.key' with * allowed for FOLDER & SECRET."
            )

        proj, folder, key = parts
        pointer = f"[orange1]{proj}.{folder}.{key}[/orange1] [cyan]({env})[/cyan]"

        # 1. Project must NOT be wildcard
        if proj == "*":
            raise ValueError(f"{pointer} | Invalid Notation | Wildcard in PROJECT")

        # 2. Folder wildcard is allowed
        folder = folder.strip('/') or "root"

        # 3. Invalid: project.*.specific_key
        if folder == "*" and key != "*":
            raise ValueError(f"{pointer} | Invalid Notation | Wildcard in FOLDER for specific SECRET")

        return proj, folder, key

    #####################################################################################################
    #######  PULL OPERATION                                                                        #######
    #####################################################################################################

    def pull(self, path_pattern, env=None, silent=False):
        """
        Loads secrets from Infisical into the local cache.

        Supports:
            project.folder.key
            project.folder.*
            project.*.*
            *.*.*
            *.*.key
            project.*.key

        Wildcards:
            * in project   → all projects
            * in folder    → all folders
            * in key       → all keys
        """
        method     = "PULL"
        start_time = time.perf_counter()

        # Determine environment
        target_env = env or self.default_env

        # Parse the path into project, folder, key-pattern
        pointer = f"[orange1]{path_pattern}[/orange1] [cyan]({target_env})[/cyan]"
        try:
            proj, folder, key_pattern = self.validate_for_pull(path_pattern, target_env)
        except ValueError as e:
            if not silent: log(method, f"{e}", ERROR)
            return None

        # Determine recursion
        is_recursive = "*" in folder or key_pattern == "*"

        # Convert folder to Infisical path
        actual_folder = "/" if folder == "*" else f"/{folder.strip('/')}"

        # Log that we are fetching
        pointer = f"[orange1]{proj}.{folder}.{key_pattern}[/orange1] [cyan]({target_env})[/cyan]"
        if not silent: log(method, f"{pointer} | Fetching ", DEBUG)

        # SDK CALL
        try:
            response = self.client.secrets.list_secrets(
                project_slug      = proj,
                environment_slug  = target_env,
                secret_path       = actual_folder,
                recursive         = is_recursive,
                include_imports   = True
            )
        except Exception as e:
            clean = self._clean_infisical_error(str(e))
            if not silent: log(method, f"{pointer} | {clean}", ERROR)
            return None

        # Process secrets
        secrets_loaded  = 0
        new_keys        = 0
        existing_keys   = 0

        # --- NEW: rebuild remote index + remote cache  ---------------------------
        # Used for dirty tracking and to detect deleted secrets on next pull
        self._infisical_index.clear()
        self._remote_cache.clear()
        # -------------------------------------------------------------------------


        for s in response.secrets:
            try:
                cache_folder = s.secretPath.strip("/") or "root"
                full_cache_key = f"{proj}.{cache_folder}.{s.secretKey}"

                # --- NEW: populate Infisical index + remote cache ---
                self._infisical_index.add(full_cache_key)
                self._remote_cache[full_cache_key] = s.secretValue
                # ---------------------------------------------------

                # Wildcard filtering
                if key_pattern != "*" and key_pattern != s.secretKey:
                    continue

                # Count new vs existing
                if full_cache_key in self._cache: existing_keys += 1
                else: new_keys += 1

                # Store in cache
                self._cache[full_cache_key] = {
                    "value": s.secretValue,
                    "env": target_env,
                    "folder": s.secretPath,
                    "project": proj,
                    "dirty": False
                }

                secrets_loaded += 1

            except Exception as inner_e:
                if not silent: log(method, f"Error processing secret '{s.secretKey}': {inner_e}", WARNING)

        # Detect missing specific secret
        if key_pattern != "*" and secrets_loaded == 0:
            if not silent: log(
                method,
                f"{pointer} | Secret not found: [red]{key_pattern}[/red] ",
                ERROR
            )
            return None

        response._meta_project  = proj
        response._meta_env      = target_env
        self.last_response      = response

        # --- NEW: store active project/env on the manager ---
        self.project     = proj
        self.environment = target_env
        # ----------------------------------------------------

        # Duration logging
        duration = (time.perf_counter() - start_time) * 1000
        msg = (
            f"{pointer} | Success | Loaded: {secrets_loaded} keys "
            f"| New: [green]{new_keys}[/green] "
            f"| Existing: [yellow]{existing_keys}[/yellow] "
            f"| [bold magenta]{duration:.2f}ms[/bold magenta]"
        )
        if not silent: log(method, msg, INFO)

        # Tree Display if enabled
        if self.visuals and not silent:
            self.visual_tree_dynamic(response, title=f'[PULL RESPONSE] for: {proj}.{folder}.{key_pattern} ({target_env})')
            self.cache_status()

        return response
