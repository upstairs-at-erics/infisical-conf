# cache_ops.py

from .logger import log

DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"


class PureCacheMixin:
    """
    Provides pure cache operations.
    No Infisical logic.
    No API calls.
    No notation rules.
    """

    def clear(self):
        """
        Performs a total reset of the manager's state.
        Wipes cache, context, and last response data.
        """

        method = "CLEAR"
        cache_count = len(self._cache)

        # 1. Wipe the data storage
        self._cache = {}

        log(method, f"CACHE CLEAR > Wiped {cache_count} Records ", INFO)

        # 2. Reset the display pointer
        self.last_response = None

    def drop(self, path, env = None, visualise = True):
        """
        Drops keys from cache using dot-notation with controlled wildcard rules.

        VALID:
            project.folder.*     → drop all keys in folder
            project.*.*          → drop all folders in project
            project.folder.key   → drop exact key

        INVALID:
            *.folder.*
            *.*.secret
            project.*.secret

        Rules:
            - project wildcard (*) is NEVER allowed
            - folder wildcard (*) allowed ONLY if key == "*"
            - key wildcard (*) allowed
            - all resolved keys MUST exist in cache
        """

        method = "DROP"

        # Determine environment
        target_env = env or self.default_env
        if not target_env:
            raise ValueError("No ENV provided and no default_env set")

        # Parse dot-notation
        parts = path.split('.')
        if len(parts) != 3:
            raise ValueError(f"[orange1]{path}[/orange1] | Invalid Notation | Expected 'project.folder.key'")

        proj, folder, key = parts

        # Reject project wildcard ALWAYS
        if proj == "*":
            raise ValueError(f"[orange1]{path}[/orange1] | Invalid Notation | Wildcard not allowed in PROJECT")

        # Folder wildcard allowed ONLY if key == "*"
        if folder == "*" and key != "*":
            raise ValueError(
                f"[orange1]{path}[/orange1] | Invalid Notation | Wildcard in FOLDER only allowed when KEY is '*'"
            )

        #   Normalise folder
        folder = folder.strip('/') or "root"

        #   Resolve matching keys
        keys_to_remove = []

        for full_key in list(self._cache.keys()):
            k_proj, k_folder, k_key = full_key.split('.', 2)

            # project must match exactly
            if k_proj != proj: continue

            # folder wildcard → match all folders
            if folder != "*" and k_folder != folder: continue

            # key wildcard → match all keys
            if key != "*" and k_key != key: continue

            keys_to_remove.append(full_key)

        # If nothing matched → error
        if not keys_to_remove:
            log(
                method,
                f"[orange1]{path}[/orange1] [cyan]({target_env})[/cyan] No cache entries — nothing removed",
                WARNING
            )
            if visualise and self.log_level == "DEBUG": self.cache_status()

            return False

        # 8. Remove keys
        for k in keys_to_remove: del self._cache[k]

        log(
            method,
            f"[orange1]{path}[/orange1] [cyan]({target_env})[/cyan] Removed {len(keys_to_remove)} Secrets from Cache",
            INFO
        )

        # Show cache status after operation
        if visualise and self.log_level == "DEBUG":  self.cache_status()

        return True

