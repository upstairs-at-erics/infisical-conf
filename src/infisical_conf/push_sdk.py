# push.py

import time
from .logger import log
from datetime import datetime, timezone
import socket
import getpass


DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"



class PushOpsMixin:

    #####################################################################################################
    # PUSH ONE SECRET (fully-qualified: project.folder.key)
    #####################################################################################################

    def push(self, route):
        """
        Push exactly one secret using fully-qualified notation:
            project.folder.secret

        Validation rules:
            - project must exist
            - folder may be created if missing
            - secret may be created or updated
            - must exist in local cache (value source of truth)
        """

        method = "PUSH"

        proj, folder, key = self.parse_notation(route)
        folder_norm       = folder.strip("/") or "root"
        full_key          = f"{proj}.{folder_norm}.{key}"

        # Validate project ---
        if proj not in self._project_meta_cache:
            log(method, f"Invalid project: [red]{proj}[/red]", ERROR)
            return False

        # Validate presence of Secret in local cache ---
        item = self._cache.get(full_key)
        if not item:
            log(method, f"No such key in cache: [cyan]{full_key}[/cyan]", ERROR)
            return False

        # Determine operation type (create vs update) for logging and dirty state management
        is_update = full_key in self._dirty_updates
        is_create = any(full_key == fk for _, fk in self._dirty_creates)

        if not (is_update or is_create):
            log(self.name, f"[orange1]{full_key}[/orange1] No changes Marked", DEBUG)
            return True

        # Ensure folder exists remotely 
        self._ensure_folder(proj, folder_norm, item["env"])

        # Push secret ---
        self._push_secret(item, key, full_key)

        # Clear dirty state ---
        self._dirty_updates.discard(full_key)
        self._dirty_creates = {t for t in self._dirty_creates if t[1] != full_key}
        item["dirty"] = False

        return True


    #####################################################################################################
    # PUSH ALL DIRTY SECRETS
    #####################################################################################################

    def push_all(self):
        """
        Push all dirty secrets to Infisical.
        Order:
            1. Refresh remote state
            2. Create missing folders
            3. Create new secrets in existing folders
            4. Create new folders + secrets
            5. Update existing secrets
        """

        method = "PUSH-ALL"

        start = time.perf_counter()

        # THIS IS WRONG. It assumes that Infisical is the master and over-writes our local cache with the remote state rather than pushing the dirty state to Infisical. 
        # #################################################################################################################################################################
        # We need to push the dirty state to Infisical and only then pull the remote state to refresh the cache. 
        # Otherwise we lose the dirty state on pull and end up with a cache that is out of sync with our local changes. 
        # We should only pull after pushing all the dirty secrets to ensure that our local cache is updated with the latest remote state after our changes have been applied. 
        # Refactor for Release 0.1.1 - which means updating pypi package and pip uninstalling/reinstalling in the project
        # 
        # Refresh Infisical state
        #self.pull(f"{self.project}.*.*", silent=True)
        #
        #
        ###################################################################################################################################################################

        # Create missing folders ---
        new_folders = sorted({
            fk.split(".", 2)[1]
            for create_type, fk in self._dirty_creates
            if create_type == "new-folder"
        })

        for folder in new_folders:
            self._ensure_folder(self.project, folder, self.environment)

        # Push 'create secret' in existing folders
        for create_type, full_key in sorted(self._dirty_creates):
            if create_type == "existing-folder":
                self.push(full_key)

        # Push any 'create secrets in new folders'
        for create_type, full_key in sorted(self._dirty_creates):
            if create_type == "new-folder":
                self.push(full_key)

        # Push Secret Value Updates 
        for full_key in sorted(self._dirty_updates):  self.push(full_key)

        duration = (time.perf_counter() - start) * 1000
        log(method, f"Completed in {duration:.2f}ms", INFO)

        if self.visuals:
            print('')
            self.show_dirty_tree(title="DIRTY KEYS After <push_all> - Expect to be all clear")
            print('')


    #####################################################################################################
    # INTERNAL HELPERS
    #####################################################################################################

    def _build_metadata(self, source):

        """
           Builds metadata for secrets to be created/updated on Infisical via the manager. 
           Can be extended to include more context as needed.
        """
        return [
            {"key": "source", "value": source},
            {"key": "operator", "value": getattr(self, "operator_name", getpass.getuser())},
            {"key": "hostname", "value": socket.gethostname()},
            {"key": "timestamp", "value": datetime.now(timezone.utc).isoformat()},
        ]


    def _ensure_folder(self, project, folder, env):

        """
            Ensures the specified folder exists in Infisical for the given project and environment.
            If the folder is 'root' or empty, it is considered as the default and no action is taken.   
                Validation:
                    - If folder is 'root' or empty → skip (considered default)
                    - If folder exists in Infisical → skip
                    - Else → attempt to create folder via API
        """

        method = "PUSH"

        if folder in ["", "root"]: return

        project_id = self._get_project_id(project)
        start      = time.perf_counter()

        try:
            self.client.folders.create_folder(
                name             = folder,
                environment_slug = env,
                project_id       = project_id,
                path             = "/"
            )
            duration = (time.perf_counter() - start) * 1000
            log(method, f"[orange1]{project}.{folder} [/orange1] Folder created: [cyan]{folder}[/cyan] "
                        f"[blue]({duration:.2f}ms)[/blue]", DEBUG)

        except Exception as e:
            msg = str(e).lower()
            duration = (time.perf_counter() - start) * 1000

            if "already exists" in msg:
                log(method, f"[orange1]{project}.{folder} [/orange1] Folder exists: [cyan]{folder}[/cyan] "
                            f"[blue]({duration:.2f}ms[/blue])", DEBUG)
            else:
                clean = self._clean_infisical_error(str(e))
                log(method, f"[orange1]{project}.{folder} [/orange1] Folder error: {clean} "
                            f"[blue]({duration:.2f}ms[/blue])", ERROR)


    def _push_secret(self, item, key, full_key):

        """ Pushes a single secret to Infisical, determining whether to create or update based on dirty state. """

            # Read-only mode: block all writes
        if self.readonly:
            log("PUSH", f"[orange1]{full_key}[/orange1] SKIPPED (read‑only mode)", WARNING)
            return

        start = time.perf_counter()
        method = "PUSH"

        try:
            if full_key in self._dirty_updates:

                # UPDATE existing secret (positional args only)
                self.client.secrets.update_secret_by_name(
                    key,                                    # current_secret_name
                    item["folder"],                         # secret_path
                    item["env"],                            # environment_slug
                    self._get_project_id(item["project"]),  # project_id
                    str(item["value"]),                     # secret_value
                    "Updated via InfisicalManager",         # secret_comment
                    secret_metadata=self._build_metadata("update")
                )
                action = "UPDATED"

            else:
                
                # CREATE new secret (this API supports keyword args)

                self.client.secrets.create_secret_by_name(
                    secret_name      = key,
                    project_slug     = item["project"],
                    environment_slug = item["env"],
                    secret_path      = item["folder"],
                    secret_value     = str(item["value"]),
                    secret_comment   = "Created via InfisicalManager",
                    secret_metadata  = self._build_metadata("create")
                )
                action = "CREATED"

            duration = (time.perf_counter() - start) * 1000
            log(method, f"[orange1]{full_key}[/orange1] {action}:  "
                        f"[blue]({duration:.2f}ms)[/blue]", INFO)

        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            clean = self._clean_infisical_error(str(e))
            log(method, f"[orange1]{full_key}[/orange1] FAILED: {clean} "
                        f"[blue]({duration:.2f}ms)[/blue]", ERROR)
