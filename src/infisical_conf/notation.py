# notation.py

class NotationMixin:
    """
    Pure dot-notation parser:
        
        project.folder.key

    """

    def parse_notation(self, path: str):

        """ 
            Parses and validates dot-notation paths for get/set/drop operations.  
            Returns a tuple of (project, folder, key) or raises ValueError for invalid patterns.
        """
        parts = path.split('.')
        if len(parts) != 3:  raise ValueError(f"[orange1]{path}[/orange1] | Invalid Notation | Expected 'project.folder.key'")

        proj, folder, key = parts

        folder = folder.strip('/') or "root"

        # NEW: normalise wildcard
        if key.strip() == "*":
            key = "*"

        return proj, folder, key

    def folder_exists_in_infisical(self, project, folder):

        """ Checks if a folder exists in the Infisical index. Used for validation in set operations. """

        folder = folder.strip("/")
        prefix = f"{project}.{folder}."
        return any(k.startswith(prefix) for k in self._infisical_index)
