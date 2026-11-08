"""Documented Hermes facades for a dashboard served before chat registration."""
from __future__ import annotations


class DashboardContext:
    def __init__(self):
        from agent.plugin_llm import PluginLlm
        self.llm = PluginLlm(plugin_id="gambit")

    def get_config(self, key, default=None):
        from hermes_cli.config import load_config_readonly
        config = load_config_readonly() or {}
        entry = config.get("plugins", {}).get("entries", {}).get("gambit", {})
        settings = entry.get("settings") or {}
        if key in settings:
            return settings[key]
        return (entry.get("config") or {}).get(key, default)
