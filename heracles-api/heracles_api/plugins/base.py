"""
Plugin Base Classes
===================

Defines the base classes and interfaces for Heracles plugins.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
import logging

from pydantic import BaseModel


@dataclass
class PluginInfo:
    """Metadata about a plugin."""
    
    name: str
    """Unique identifier for the plugin."""
    
    version: str
    """Plugin version (semver format)."""
    
    description: str
    """Human-readable description."""
    
    author: str = "Heracles Team"
    """Plugin author."""
    
    object_types: List[str] = field(default_factory=list)
    """Object types this plugin attaches to (e.g., ['user', 'group'])."""
    
    object_classes: List[str] = field(default_factory=list)
    """LDAP objectClasses managed by this plugin."""
    
    dependencies: List[str] = field(default_factory=list)
    """Other plugins required by this one."""
    
    required_config: List[str] = field(default_factory=list)
    """Configuration keys required by this plugin."""
    
    priority: int = 50
    """Display priority (lower = displayed first)."""


@dataclass
class TabDefinition:
    """Defines a tab provided by a plugin."""
    
    id: str
    """Unique identifier for the tab."""
    
    label: str
    """Human-readable label displayed in UI."""
    
    icon: str
    """Icon name (e.g., 'terminal', 'key', 'users')."""
    
    object_type: str
    """Object type this tab attaches to ('user' or 'group')."""
    
    activation_filter: str
    """LDAP filter to check if tab is active on an object."""
    
    schema_file: str
    """JSON schema file for UI form generation."""
    
    service_class: Type["TabService"]
    """Service class handling the business logic."""
    
    create_schema: Type[BaseModel]
    """Pydantic schema for creating/activating."""
    
    read_schema: Type[BaseModel]
    """Pydantic schema for reading data."""
    
    update_schema: Type[BaseModel]
    """Pydantic schema for updating data."""
    
    required: bool = False
    """Whether this tab is required (cannot be deactivated)."""


class TabService(ABC):
    """
    Base class for plugin tab services.
    
    Each plugin tab must implement this interface to handle
    CRUD operations on the tab's data.
    """
    
    # ObjectClasses to add when activating the tab
    OBJECT_CLASSES: List[str] = []
    
    # Attributes managed by this tab
    MANAGED_ATTRIBUTES: List[str] = []
    
    def __init__(self, ldap_service: Any, config: Dict[str, Any]):
        """
        Initialize the service.
        
        Args:
            ldap_service: The LDAP service instance.
            config: Plugin configuration dictionary.
        """
        self._ldap = ldap_service
        self._config = config
        self.logger = logging.getLogger(f"heracles.plugins.{self.__class__.__name__}")
    
    @abstractmethod
    async def is_active(self, dn: str) -> bool:
        """
        Check if the tab is active on the given object.
        
        Args:
            dn: Distinguished Name of the object.
            
        Returns:
            True if the tab is active (objectClasses present).
        """
        pass
    
    @abstractmethod
    async def read(self, dn: str) -> Optional[BaseModel]:
        """
        Read tab data from the object.
        
        Args:
            dn: Distinguished Name of the object.
            
        Returns:
            Data as Pydantic model, or None if not active.
        """
        pass
    
    @abstractmethod
    async def activate(self, dn: str, data: BaseModel) -> BaseModel:
        """
        Activate the tab on an object.
        
        Args:
            dn: Distinguished Name of the object.
            data: Creation data.
            
        Returns:
            Created data as Pydantic model.
            
        Raises:
            ValidationError: If already active or invalid data.
        """
        pass
    
    @abstractmethod
    async def update(self, dn: str, data: BaseModel) -> BaseModel:
        """
        Update tab data on an object.
        
        Args:
            dn: Distinguished Name of the object.
            data: Update data.
            
        Returns:
            Updated data as Pydantic model.
            
        Raises:
            ValidationError: If not active or invalid data.
        """
        pass
    
    @abstractmethod
    async def deactivate(self, dn: str) -> None:
        """
        Deactivate the tab on an object.
        
        Removes the objectClasses and attributes managed by this tab.
        
        Args:
            dn: Distinguished Name of the object.
            
        Raises:
            ValidationError: If not active.
        """
        pass


class Plugin(ABC):
    """
    Base class for all Heracles plugins.
    
    A plugin can provide:
    - Tabs for existing object types (user, group)
    - New management types (systems, sudo rules)
    - API endpoints
    - Background tasks
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the plugin.
        
        Args:
            config: Plugin-specific configuration.
        """
        self._config = config or {}
        info = self.info()
        self.logger = logging.getLogger(f"heracles.plugins.{info.name}")
    
    @staticmethod
    @abstractmethod
    def info() -> PluginInfo:
        """
        Return plugin metadata.
        
        Returns:
            PluginInfo with name, version, dependencies, etc.
        """
        pass
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """
        Return tabs provided by this plugin.
        
        Override this method to add tabs to user/group objects.
        
        Returns:
            List of TabDefinition objects.
        """
        return []
    
    @staticmethod
    def routes() -> List[Any]:
        """
        Return API routers provided by this plugin.
        
        Override this method to add custom API endpoints.
        
        Returns:
            List of FastAPI APIRouter objects.
        """
        return []
    
    def on_activate(self) -> None:
        """
        Called when the plugin is activated.
        
        Override for initialization logic.
        """
        self.logger.info(f"Plugin {self.info().name} activated")
    
    def on_deactivate(self) -> None:
        """
        Called when the plugin is deactivated.
        
        Override for cleanup logic.
        """
        self.logger.info(f"Plugin {self.info().name} deactivated")
    
    def validate_config(self) -> List[str]:
        """
        Validate plugin configuration.
        
        Returns:
            List of error messages (empty if valid).
        """
        errors = []
        info = self.info()
        
        for key in info.required_config:
            if key not in self._config:
                errors.append(f"Missing required config: {key}")
        
        return errors
