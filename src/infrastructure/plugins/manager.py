from typing import Dict
from src.application.interfaces.source_plugin import SourcePlugin
from src.infrastructure.plugins.telegram import TelegramSourcePlugin
from src.infrastructure.logging import get_logger

logger = get_logger("POSTS")

class PluginManager:
    def __init__(self) -> None:
        self.plugins: Dict[str, SourcePlugin] = {}
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        try:
            self.plugins["TELEGRAM"] = TelegramSourcePlugin()
            logger.info("Registered TELEGRAM source plugin")
        except Exception as e:
            logger.error("Failed to register TELEGRAM source plugin", error=str(e))

    def get_plugin(self, source_type: str) -> SourcePlugin:
        source_type_upper = source_type.upper()
        if source_type_upper in self.plugins:
            return self.plugins[source_type_upper]
        raise ValueError(f"No plugin registered for source type: {source_type_upper}")
