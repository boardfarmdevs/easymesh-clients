"""Client models: from a model file to a client's configuration.

A model name is a nickname from models/ (``iphone``), optionally followed by
behaviours from models/behaviours/ (``pixel+btm-refuser``). ``resolve()`` turns
it into the options of wpa_supplicant 2.12 with this repository's patch series,
or into iwd's main.conf. Standard library only.
"""

from .resolve import (
    ModelError,
    iwd_conf,
    key_mgmt,
    list_models,
    load,
    resolve,
    wpa_cli_commands,
    wpa_conf,
)

__all__ = ["ModelError", "iwd_conf", "key_mgmt", "list_models", "load", "resolve",
           "wpa_cli_commands", "wpa_conf"]
