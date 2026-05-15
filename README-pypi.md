# Infisical Python Config Manager (infisical-conf)
A fast, lightweight wrapper around the official Infisical Python SDK providing:

- local hierarchical cache
- wildcard pull/get/drop
- explicit set/push workflow
- dirty‑tracking
- automatic folder creation
- strict notation validation
- optional visual diagnostics

## Installation     
``` bash
pip install infisical-conf
```
## Quick Example
``` python
from infisical_conf import InfisicalManager

mgr = InfisicalManager()
mgr.set_env("prod")

# Pull secrets into local cache
mgr.pull("myproj.backend.*")

# Read a secret
db_pass = mgr.get("myproj.backend.DB_PASSWORD")

# Update a secret
mgr.set_secret("myproj.backend.API_KEY", "new-value")
mgr.push()

```

## Documentation  
Full documentation, examples, Django integration, and usage scenarios:  
https://github.com/upstairs-at-erics/infisical-conf

