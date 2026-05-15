# get.py

import time
from .logger import log
import json,re

from rich import print as rprint

DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"


class GetCacheMixin:

    def _auto_cast(self, value, full_key=None):
        """
        Attempts to convert a string into int, float, bool, list, dict, tuple, or None.
        Logs failures and falls back safely.
        """

        method = "CAST"

        if not isinstance(value, str):
            return value

        v = value.strip()

        # Booleans
        if v.lower() in ("true", "false"):  return v.lower() == "true"

        # None/null
        if v.lower() in ("null", "none"): return None

        # Integers (strict)
        if re.fullmatch(r"-?\d+", v):
            try:
                return int(v)
            except Exception as e:
                log(method, f"CAST-INT FAIL | [cyan]{full_key}[/cyan] → {e}", WARNING)

        # Floats (strict)
        if re.fullmatch(r"-?\d+\.\d+", v):
            try:
                return float(v)
            except Exception as e:
                log(method, f"CAST-FLOAT FAIL | [cyan]{full_key}[/cyan] → {e}", WARNING)

        # JSON list/dict
        if (v.startswith("[") and v.endswith("]")) or (v.startswith("{") and v.endswith("}")):
            # First attempt: raw
            try:
                return json.loads(v)
            except Exception:
                # Second attempt: compact whitespace
                try:
                    compact = re.sub(r"\s+", "", v)
                    return json.loads(compact)
                except Exception as e:
                    log(method, f"CAST | JSON FAIL | [cyan]{full_key}[/cyan] → {e}", WARNING)
                    return value

        # Python tuple syntax
        if v.startswith("(") and v.endswith(")"):
            try:
                inner = v[1:-1].strip()
                if not inner: return ()
                parts = [p.strip() for p in inner.split(",") if p.strip()]
                return tuple(self._auto_cast(p, full_key) for p in parts)
            except Exception as e:
                log(method, f"CAST | TUPLE FAIL | [cyan]{full_key}[/cyan] → {e}", WARNING)
                return value

        return value


    def get_all(self):
        """
        Returns the entire cache as a hierarchical dict:
        {
            project: {
                folder: {
                    key: typed_value
                }
            }
        }
        """
        method = "GET-ALL"
        log(method, "Building hierarchical config tree", DEBUG)

        data  = {}
        count = 0

        for full_key, item in self._cache.items():
            proj   = item["project"]
            folder = item["folder"].strip("/") or "root"
            key    = full_key.split(".")[-1]

            # Pass full_key for better logging context
            value  = self._auto_cast(item["value"], full_key)

            # Ensure project exists
            if proj not in data:  data[proj] = {}

            # Ensure folder exists
            if folder not in data[proj]: data[proj][folder] = {}

            # Assign typed secret value
            data[proj][folder][key] = value
            count += 1

            if self.visuals:
                msg=f"GET-ALL | Loaded [orange1]{full_key}[/orange1] → {type(value).__name__}"
                #log( method,msg,DEBUG)

        log(method,f"Completed: [green]{count}[/green] keys processed",INFO)

        if self.visuals: self.cache_status()

        return data


    def get(self, route):
        """
        Flexible getter with wildcard support.
        Valid:
            project.*.*
            *.*.*
            project.folder.*
            project.folder.secret

        Invalid:
            *.folder.*
            *.*.secret
            project.*.secret
        """
        method = "GET"
        
        # ------------------------------------------------------------
        # SAFE PARSE
        # ------------------------------------------------------------
        proj, folder, secret = self.parse_notation(route)

        if proj is None:
            log(method, f"Invalid notation: [red]{route}[/red]", ERROR)
            return None

        # Normalise folder for matching
        folder_norm = folder.strip("/") if folder != "*" else "*"

        # ------------------------------------------------------------
        # INVALID PATTERNS
        # ------------------------------------------------------------

        # *.folder.*  → wildcard project + fixed folder
        if proj == "*" and folder != "*" and secret == "*":
            log(method, f"Invalid pattern: [red]{route}[/red] (cannot mix wildcard project with fixed folder)", ERROR)
            return None

        # *.*.secret → wildcard project+folder but fixed secret
        if proj == "*" and folder == "*" and secret != "*":
            log(method, f"Invalid pattern: [red]{route}[/red] (cannot request fixed secret across all folders)", ERROR)
            return None

        # project.*.secret → wildcard folder but fixed secret
        if proj != "*" and folder == "*" and secret != "*":
            log(method, f"Invalid pattern: [red]{route}[/red] (cannot request fixed secret across wildcard folders)", ERROR)
            return None

        # ------------------------------------------------------------
        # VALID PATTERNS
        # ------------------------------------------------------------

        # CASE 1: project.folder.secret (exact match)
        if proj != "*" and folder != "*" and secret != "*":
            full_key = f"{proj}.{folder}.{secret}"
            item = self._cache.get(full_key)

            if not item:
                log(method, f"Not found: [red]{full_key}[/red]", ERROR)
                return None

            value = self._auto_cast(item["value"], full_key)
            log(method, f"[orange1]{proj}.{folder}.{secret}[/orange1] Loaded → {type(value).__name__}", DEBUG)
            return value

        # CASE 2: project.folder.* (all secrets in folder)
        if proj != "*" and folder != "*" and secret == "*":
            log(method, f"[orange1]{proj}.{folder}.*[/orange1]  Getting All Secrets in Folder", DEBUG)

            result = {}

            # iterate safely
            for full_key, item in list(self._cache.items()):
                if item["project"] == proj and item["folder"].strip("/") == folder_norm:
                    key = full_key.split(".")[-1]
                    result[key] = self._auto_cast(item["value"], full_key)

            # Count keys
            key_count = len(result)

            if key_count == 0:
                log(method, f"Folder empty or missing: [red]{proj}/{folder}[/red]", WARNING)
            else:
                log(
                    method,
                    f"[orange1]{proj}.{folder}.*[/orange1] Returned "
                    f"[green]{key_count}[/green] secrets",
                    INFO
                )

            return result

        # CASE 3: project.*.* (all folders + secrets in project)
        if proj != "*" and folder == "*" and secret == "*":
            log(method, f"[orange1]{proj}.*.*[/orange1]  Getting All Folders in Project", DEBUG)

            result = {}

            for full_key, item in list(self._cache.items()):
                if item["project"] == proj:
                    fld = item["folder"].strip("/") or "root"
                    key = full_key.split(".")[-1]
                    result.setdefault(fld, {})
                    result[fld][key] = self._auto_cast(item["value"], full_key)

            if not result:
                log(method, f"Missing project: [red]{proj}[/red]", WARNING)

            return result

        # CASE 4: *.*.* (everything)
        if proj == "*" and folder == "*" and secret == "*":
            log(method, f"[orange1]*.*.*[/orange1]  Returning Everything in cache", DEBUG)
            return self.get_all()

        # ------------------------------------------------------------
        # Should never reach here
        # ------------------------------------------------------------
        log(method, f"Unhandled pattern: [red]{route}[/red]", ERROR)
        return None


