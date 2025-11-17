"""
Configuration system for qh with layered defaults.

Configuration flows from general to specific:
1. Global defaults
2. App-level config
3. Function-level config
4. Parameter-level config
"""

from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field, replace
from qh.rules import RuleChain, DEFAULT_RULE_CHAIN, HttpLocation


@dataclass
class RouteConfig:
    """Configuration for a single route (function endpoint)."""

    # Route path (None = auto-generate from function name)
    path: Optional[str] = None

    # HTTP methods for this route
    methods: Optional[List[str]] = None

    # Custom rule chain for parameter transformations
    rule_chain: Optional[RuleChain] = None

    # Parameter-specific overrides {param_name: transform_spec}
    param_overrides: Dict[str, Any] = field(default_factory=dict)

    # Additional metadata
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    response_model: Optional[type] = None

    # Advanced options
    include_in_schema: bool = True
    deprecated: bool = False

    def merge_with(self, other: 'RouteConfig') -> 'RouteConfig':
        """Merge with another config, other takes precedence."""
        return RouteConfig(
            path=other.path if other.path is not None else self.path,
            methods=other.methods if other.methods is not None else self.methods,
            rule_chain=other.rule_chain if other.rule_chain is not None else self.rule_chain,
            param_overrides={**self.param_overrides, **other.param_overrides},
            summary=other.summary if other.summary is not None else self.summary,
            description=other.description if other.description is not None else self.description,
            tags=other.tags if other.tags is not None else self.tags,
            response_model=other.response_model if other.response_model is not None else self.response_model,
            include_in_schema=other.include_in_schema,
            deprecated=other.deprecated or self.deprecated,
        )


@dataclass
class AppConfig:
    """Global configuration for the entire FastAPI app."""

    # Default HTTP methods for all routes
    default_methods: List[str] = field(default_factory=lambda: ['POST'])

    # Path template for auto-generating routes
    # Available placeholders: {func_name}
    path_template: str = '/{func_name}'

    # Path prefix for all routes
    path_prefix: str = ''

    # Global rule chain
    rule_chain: RuleChain = field(default_factory=lambda: DEFAULT_RULE_CHAIN)

    # FastAPI app kwargs
    title: str = "qh API"
    version: str = "0.1.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"

    # Additional FastAPI app kwargs
    fastapi_kwargs: Dict[str, Any] = field(default_factory=dict)

    def to_fastapi_kwargs(self) -> Dict[str, Any]:
        """Convert to FastAPI() constructor kwargs."""
        return {
            'title': self.title,
            'version': self.version,
            'docs_url': self.docs_url,
            'redoc_url': self.redoc_url,
            'openapi_url': self.openapi_url,
            **self.fastapi_kwargs,
        }


# Default configurations
DEFAULT_ROUTE_CONFIG = RouteConfig()
DEFAULT_APP_CONFIG = AppConfig()


def resolve_route_config(
    func: Callable,
    app_config: AppConfig,
    route_config: Optional[Union[RouteConfig, Dict[str, Any]]] = None,
) -> RouteConfig:
    """
    Resolve complete route configuration for a function.

    Precedence (highest to lowest):
    1. route_config (function-specific)
    2. app_config (app-level defaults)
    3. DEFAULT_ROUTE_CONFIG (global defaults)
    """
    # Start with defaults
    config = DEFAULT_ROUTE_CONFIG

    # Apply app-level defaults
    app_level = RouteConfig(
        methods=app_config.default_methods,
        rule_chain=app_config.rule_chain,
    )
    config = config.merge_with(app_level)

    # Apply function-specific config
    if route_config is not None:
        # Convert dict to RouteConfig if necessary
        if isinstance(route_config, dict):
            route_config = RouteConfig(**{
                k: v for k, v in route_config.items()
                if k in RouteConfig.__dataclass_fields__
            })
        config = config.merge_with(route_config)

    # Auto-generate path if not specified
    if config.path is None:
        config = replace(
            config,
            path=app_config.path_template.format(func_name=func.__name__)
        )

    # Auto-generate description from docstring if not specified
    if config.description is None and func.__doc__:
        config = replace(config, description=func.__doc__)

    # Auto-generate summary from first line of docstring
    if config.summary is None and func.__doc__:
        first_line = func.__doc__.strip().split('\n')[0]
        config = replace(config, summary=first_line)

    return config


class ConfigBuilder:
    """Fluent interface for building configurations."""

    def __init__(self):
        self.app_config = AppConfig()
        self.route_configs: Dict[Callable, RouteConfig] = {}

    def with_path_prefix(self, prefix: str) -> 'ConfigBuilder':
        """Set path prefix for all routes."""
        self.app_config.path_prefix = prefix
        return self

    def with_path_template(self, template: str) -> 'ConfigBuilder':
        """Set path template for auto-generation."""
        self.app_config.path_template = template
        return self

    def with_default_methods(self, methods: List[str]) -> 'ConfigBuilder':
        """Set default HTTP methods."""
        self.app_config.default_methods = methods
        return self

    def with_rule_chain(self, chain: RuleChain) -> 'ConfigBuilder':
        """Set global rule chain."""
        self.app_config.rule_chain = chain
        return self

    def for_function(self, func: Callable) -> 'FunctionConfigBuilder':
        """Start configuring a specific function."""
        return FunctionConfigBuilder(self, func)

    def build(self) -> tuple[AppConfig, Dict[Callable, RouteConfig]]:
        """Build final configuration."""
        return self.app_config, self.route_configs


class FunctionConfigBuilder:
    """Fluent interface for building function-specific configuration."""

    def __init__(self, parent: ConfigBuilder, func: Callable):
        self.parent = parent
        self.func = func
        self.config = RouteConfig()

    def at_path(self, path: str) -> 'FunctionConfigBuilder':
        """Set custom path for this function."""
        self.config.path = path
        return self

    def with_methods(self, methods: List[str]) -> 'FunctionConfigBuilder':
        """Set HTTP methods for this function."""
        self.config.methods = methods
        return self

    def with_summary(self, summary: str) -> 'FunctionConfigBuilder':
        """Set OpenAPI summary."""
        self.config.summary = summary
        return self

    def with_tags(self, tags: List[str]) -> 'FunctionConfigBuilder':
        """Set OpenAPI tags."""
        self.config.tags = tags
        return self

    def done(self) -> ConfigBuilder:
        """Finish configuring this function."""
        self.parent.route_configs[self.func] = self.config
        return self.parent


# Convenience functions for common patterns

def from_dict(config_dict: Dict[str, Any]) -> AppConfig:
    """Create AppConfig from dictionary."""
    return AppConfig(**{
        k: v for k, v in config_dict.items()
        if k in AppConfig.__dataclass_fields__
    })


def normalize_funcs_input(
    funcs: Union[Callable, List[Callable], Dict[Callable, Dict[str, Any]]],
) -> Dict[Callable, RouteConfig]:
    """
    Normalize various input formats to Dict[Callable, RouteConfig].

    Supports:
    - Single callable
    - List of callables
    - Dict mapping callable to config dict
    - Dict mapping callable to RouteConfig
    """
    if callable(funcs):
        # Single function
        return {funcs: RouteConfig()}

    elif isinstance(funcs, list):
        # List of functions
        return {func: RouteConfig() for func in funcs}

    elif isinstance(funcs, dict):
        # Dict of functions to configs
        result = {}
        for func, config in funcs.items():
            if config is None:
                result[func] = RouteConfig()
            elif isinstance(config, RouteConfig):
                result[func] = config
            elif isinstance(config, dict):
                # Convert dict to RouteConfig
                result[func] = RouteConfig(**{
                    k: v for k, v in config.items()
                    if k in RouteConfig.__dataclass_fields__
                })
            else:
                raise ValueError(f"Invalid config type for {func}: {type(config)}")
        return result

    else:
        raise TypeError(f"Invalid funcs type: {type(funcs)}")
