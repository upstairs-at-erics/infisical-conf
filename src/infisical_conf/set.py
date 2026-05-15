# set.py

from .logger import log

DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"


class SetOpsMixin:
    """
    Local set operations (no direct Infisical calls).
    """

    def folder_exists_in_infisical(self, project, folder):
        """
        Check if a folder exists in Infisical based on the remote index.
        """
        folder = folder.strip("/")
        prefix = f"{project}.{folder}."
        return any(k.startswith(prefix) for k in self._infisical_index)

    def _display_value(self, value):
        if self.redact:
            return "••••••"
        return repr(value)

    def set_secret(self, path, value):
        """
        Set or update a secret in the local cache.
        Rules:
            - Path must be fully qualified: project.folder.secret
            - No wildcards allowed
            - Project must already exist (Infisical cannot create new projects)
            - Folder may be new (Infisical will create it on push)
            - Secret may be new
        """
        method= "SET"
        proj, folder, key = self.parse_notation(path)

        # Reject wildcards
        if proj == "*" or folder == "*" or key == "*":
            log(method, f"[red]{path}[/red] Invalid wildcard path", ERROR)
            return None

        # Normalise folder
        folder_norm = folder.strip("/") or "root"
        full_key    = f"{proj}.{folder_norm}.{key}"

        # Validate project exists
        if proj not in self._project_meta_cache:
            log(method,
                f"Project: [red]{proj}[/red] does not exist in Infisical",
                ERROR)
            return None

        # Check if folder exists in cache
        folder_exists = any(
            item["project"] == proj and item["folder"].strip("/") == folder_norm
            for _, item in self._cache.items()
        )

        if not folder_exists:
            log(method,
                f"[orange1]{proj}/{folder_norm}[/orange1] Folder: [cyan]{folder}[/cyan] does not exist — will be created on push",
                WARNING
            )

        # Update or create secret
        existing = self._cache.get(full_key)

        if existing:
            log(method,
                f"[orange1]{full_key}[/orange1] Updating existing secret: [cyan]{key}[/cyan] = {self._display_value(value)} (dirty)",
                DEBUG
            )
            env = existing["env"]
        else:
            log(method,
                f"[orange1]{full_key}[/orange1] Creating new secret: [cyan]{key}[/cyan] = {self._display_value(value)} (dirty) ",
                DEBUG
            )
            env = self.default_env

        # Dirty classification
        if full_key in self._infisical_index:

            # Exists remotely → update
            remote_value = self._remote_cache.get(full_key)

            if remote_value != value:
                self._dirty_updates.add(full_key)
                self._dirty_creates.discard(full_key)
            else:
                self._dirty_updates.discard(full_key)

        else:

            # Does not exist remotely → create
            if self.folder_exists_in_infisical(proj, folder_norm):
                self._dirty_creates.add(("existing-folder", full_key))
            else:
                self._dirty_creates.add(("new-folder", full_key))

            self._dirty_updates.discard(full_key)

        # Write to cache
        self._cache[full_key] = {
            "value"    : value,
            "env"      : env,
            "folder"   : f"/{folder_norm}",
            "project"  : proj,
            "dirty"    : True
        }

        # Auto‑visualise
        if self.visuals:  self.show_dirty_tree()

        log(method,
            f"[orange1]{full_key}[/orange1]  [green]OK[/green]  [cyan]{key}[/cyan] = {self._display_value(value)} (dirty)",INFO )

        return True
