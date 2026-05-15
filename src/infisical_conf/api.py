# api.py

import time
import requests
from .logger import log

DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"


class APIMixin:
    
    """
    - Any common low-level API calls to Infisical.
    """

    def pull_projects_list(self):

        """Fetches all project metadata from Infisical API."""

        method = "PROJECTS"

        start_time = time.perf_counter()

        # Initialise cache if missing
        if not hasattr(self, "_project_meta_cache"):   self._project_meta_cache = None

        # Return cached metadata if available
        if self._project_meta_cache is not None:
            if self.visuals:  self.projects_table(self._project_meta_cache.keys())
            return self._project_meta_cache

        # Continue here to pull projects from Server 
        log(method, "Fetching project list", DEBUG)

        url     = f"{self.host}/api/v1/projects"
        headers = {"Authorization": f"Bearer {self.accesstoken}"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            projects = data.get("projects", [])

            # Build project metadata cache: { slug -> { type, id, environments } }
            self._project_meta_cache = self._build_project_meta_cache(projects)


            # Report result
            duration = (time.perf_counter() - start_time) * 1000
            log(
                method,
                f"PROJECTS | Retrieved {len(self._project_meta_cache)} projects from Infisical| "
                f"[bold magenta]{duration:.2f}ms[/bold magenta]",
                INFO
            )

            # Display projects table if visuals enabled
            if self.visuals: self.projects_table(self._project_meta_cache)

            return self._project_meta_cache

        except Exception as e:
            log(method, f"Could not fetch project list: {e}", ERROR)
            return {}


    def _get_project_id(self, project_slug):
        """
        Return the Infisical project ID for a given project slug.
        """

        # Ensure project list is loaded
        if not hasattr(self, "_project_meta_cache") or self._project_meta_cache is None:
            self.pull_projects_list()

        meta = self._project_meta_cache.get(project_slug)

        if not meta:  raise ValueError(f"Unknown project slug: {project_slug}")

        return meta["id"]

    def _build_project_meta_cache(self, projects):

        """
          Builds a cache of project metadata for quick lookup by slug. 
          Input is the list of projects from the API, output is a dict keyed by slug.
        """

        meta = {}
        for p in projects:
            slug = p["slug"]
            meta[slug] = {
                "type"          : p.get("type", "unknown"),
                "id"            : p.get("id"),
                "environments"  : [env["slug"] for env in p.get("environments", [])]
            }
        return meta