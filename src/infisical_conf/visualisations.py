# visualisations.py

from .logger import log

from rich import print as rprint
from rich.table import Table
from rich.tree import Tree


DEBUG    = "DEBUG"
INFO     = "INFO"
WARNING  = "WARNING"
ERROR    = "ERROR"
CRITICAL = "CRITICAL"

class VisualisationsMixin:

    def visual_tree_dynamic(self, response=None, title="Displaying Tree of Secrets"):

        """ 
            renders a dynamic tree of secrets from a pull response, using metadata for context.
            - If response is None, will attempt to use last_response (if available) for rendering
            - Metadata used for title and tree context (project/env) if available on response object
            - Redaction of secret values supported via manager redact attribute (True/False)       
        """

        res = response or self.last_response
        if not res:
            log(self.name, "CONTEXT TREE DISPLAY - No data. Run pull() first.", WARNING)
            return

        project = getattr(res, "_meta_project", "Unknown")
        env     = getattr(res, "_meta_env", "Unknown")

        tree      = Tree(f"🎯 [bold magenta]SECRETS[/bold magenta] [dim](env:{env})[/dim]")
        proj_node = tree.add(f"🏗️  [bold blue]PROJECT: {project}[/bold blue]")

        folder_nodes   = {}
        sorted_secrets = sorted(res.secrets, key=lambda x: x.secretPath or "/")

        for s in sorted_secrets:
            path = s.secretPath or "/"

            if path not in folder_nodes:  folder_nodes[path] = proj_node.add(f"📂 [yellow]{path}[/yellow]")

            display_value = "******" if getattr(self, "redact", False) else s.secretValue
            secret_node = folder_nodes[path].add(
                f"[green]{s.secretKey}[/green] = [cyan]{display_value}[/cyan]"
            )

            # NOTES
            if getattr(self, "tree_notes", False):
                notes = getattr(s, "secretComment", None)
                if notes:
                    secret_node.add(f"[dim]{notes}[/dim]")

            # TAGS
            if getattr(self, "tree_tags", False):
                tags = getattr(s, "tags", None)
                if tags:
                    normalised = []
                    if isinstance(tags, list):
                        for t in tags:
                            if isinstance(t, dict):   normalised.append(t.get("name", str(t)))
                            else:  normalised.append(str(t))
                    else:  normalised.append(str(tags))

                    tags_str = ", ".join(normalised)
                    secret_node.add(f"[dim]tags: {tags_str}[/dim]")

        print("")
        rprint(f"[black on cyan]{title}[/black on cyan]")
        rprint(tree)
        print("")


    def cache_status(self):

        """ 
            Displays a summary table of the current cache structure, showing projects, folders, and secret counts.
             - If cache is empty, shows a message indicating no data
        """

        method = "CACHE STATUS"

        if not self._cache:
            log(method, "Cache is empty.", INFO)
            return

        structure = {}

        for full_key in self._cache.keys():
            try:
                proj, folder, key = full_key.split('.', 2)
            except ValueError:
                continue

            structure.setdefault(proj, {})
            structure[proj].setdefault(folder, 0)
            structure[proj][folder] += 1

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Project", style="white")
        table.add_column("Folder", style="white")

        rprint("[bold cyan]CACHE STATUS[/bold cyan]")

        for proj in sorted(structure.keys()):
            folders = structure[proj]
            first = True

            for folder, count in sorted(folders.items()):
                folder_display = f"{folder} ({count} secrets)"
                table.add_row(proj if first else "", folder_display)
                first = False

        rprint(table)
        print("")


    def projects_table(self, project_meta):

        """ 
            Displays a table of available projects and their environments based on provided metadata.
            - project_meta should be a dict with project slugs as keys and metadata dicts as values, where 
              metadata dicts contain an 'environments' key with a list of environment names.
            - If project_meta is empty, shows a message indicating no projects available.
        """

        print("")
        rprint("[bold cyan]AVAILABLE PROJECTS[/bold cyan]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Project", style="white")
        table.add_column("Envs", style="white")

        for slug in sorted(project_meta.keys()):
            meta = project_meta[slug]
            envs = ",".join(meta.get("environments", [])) or "none"
            table.add_row(slug, envs)

        rprint(table)
        print("")

    def show_dirty_tree(self, title="DIRTY KEYS (Will Update/Create on Push)"):
        
        """
        Visualise dirty keys using the existing visual_tree_dynamic() renderer.
        - Updates = keys that exist in Infisical but whose values changed locally
        - Creates = keys that do not exist in Infisical and will be created on push
        (distinguishes between new secret in existing folder vs new folder)
        """

        dirty_updates = getattr(self, "_dirty_updates", set())
        dirty_creates = getattr(self, "_dirty_creates", set())

        if not dirty_updates and not dirty_creates:
            print('')
            rprint("[bold green]No dirty keys. Cache is clean.[/bold green]")
            print('')
            return

        # --- Build a synthetic response object for visual_tree_dynamic() ---
        class FakeSecret:
            def __init__(self, path, key, label):
                self.secretPath   = path
                self.secretKey    = key
                self.secretValue  = label   # redaction handled by visual_tree_dynamic
                self.secretComment = None
                self.tags          = None

        class FakeResponse:
            pass

        fake         = FakeResponse()
        fake.secrets = []

        # Use manager metadata
        fake._meta_project = getattr(self, "project", "unknown")
        fake._meta_env     = getattr(self, "environment", getattr(self, "default_env", "prod"))

        # ---------------------- Populate UPDATE keys ----------------------
        for full_key in sorted(dirty_updates):
            try:
                proj, folder, key = full_key.split(".", 2)
            except ValueError: continue

            if proj == fake._meta_project:
                fake.secrets.append(
                    FakeSecret(f"/updates/{folder}", key, "<update>")
                )

        # ---------------------- Populate CREATE keys ----------------------
        for create_type, full_key in sorted(dirty_creates):
            try:
                proj, folder, key = full_key.split(".", 2)
            except ValueError: continue

            if proj != fake._meta_project: continue

            if create_type == "existing-folder":
                # Existing folder → new secret
                path  = f"/existing folder:{folder}"
                label = "<create-secret>"
            else:
                # New folder → new secret
                path  = f"/creates-new-folder: {folder}"
                label = "<create-folder+secret>"

            fake.secrets.append(FakeSecret(path, key, label))

        # Render using your existing tree renderer
        self.visual_tree_dynamic(response=fake, title=title)



