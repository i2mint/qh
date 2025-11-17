"""
Transformation rule system for qh.

Supports multi-dimensional matching:
- Type-based
- Argument name-based
- Function name-based
- Function object-based
- Default value-based
- Any combination thereof

Rules are layered with first-match semantics, from specific to general.
"""

from typing import Any, Callable, Dict, Optional, Protocol, Union, TypeVar, get_type_hints
from dataclasses import dataclass, field
from enum import Enum
import inspect


class HttpLocation(Enum):
    """Where in HTTP request/response to map a parameter."""
    JSON_BODY = "json_body"  # Field in JSON payload
    PATH = "path"  # URL path parameter
    QUERY = "query"  # URL query parameter
    HEADER = "header"  # HTTP header
    COOKIE = "cookie"  # HTTP cookie
    BINARY_BODY = "binary_body"  # Raw binary payload
    FORM_DATA = "form_data"  # Multipart form data


T = TypeVar('T')


@dataclass
class TransformSpec:
    """Specification for how to transform a parameter."""

    # Where this parameter comes from/goes to in HTTP
    http_location: HttpLocation = HttpLocation.JSON_BODY

    # Transform input (from HTTP to Python)
    ingress: Optional[Callable[[Any], Any]] = None

    # Transform output (from Python to HTTP)
    egress: Optional[Callable[[Any], Any]] = None

    # HTTP-level name (may differ from Python parameter name)
    http_name: Optional[str] = None

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class Rule(Protocol):
    """Protocol for transformation rules."""

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """
        Check if this rule matches the given parameter context.

        Returns:
            TransformSpec if matched, None otherwise
        """
        ...


@dataclass
class TypeRule:
    """Rule that matches based on parameter type."""

    type_map: Dict[type, TransformSpec]

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """Match by type, including type hierarchy."""
        # Exact match first
        if param_type in self.type_map:
            return self.type_map[param_type]

        # Check type hierarchy (MRO)
        for cls in getattr(param_type, '__mro__', []):
            if cls in self.type_map:
                return self.type_map[cls]

        return None


@dataclass
class NameRule:
    """Rule that matches based on parameter name."""

    name_map: Dict[str, TransformSpec]

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """Match by parameter name."""
        return self.name_map.get(param_name)


@dataclass
class FuncRule:
    """Rule that matches based on function."""

    # Map from function object to param specs
    func_map: Dict[Callable, Dict[str, TransformSpec]]

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """Match by function object and parameter name."""
        if func in self.func_map:
            param_specs = self.func_map[func]
            return param_specs.get(param_name)
        return None


@dataclass
class FuncNameRule:
    """Rule that matches based on function name pattern."""

    # Map from function name pattern to param specs
    pattern_map: Dict[str, Dict[str, TransformSpec]]

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """Match by function name pattern."""
        # TODO: Support regex patterns
        if func_name in self.pattern_map:
            param_specs = self.pattern_map[func_name]
            return param_specs.get(param_name)
        return None


@dataclass
class DefaultValueRule:
    """Rule that matches based on default values."""

    # Predicate that checks default value
    predicate: Callable[[Any], bool]
    spec: TransformSpec

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """Match if predicate returns True for default value."""
        if param_default is not inspect.Parameter.empty:
            if self.predicate(param_default):
                return self.spec
        return None


@dataclass
class CompositeRule:
    """Rule that combines multiple conditions."""

    rules: list[Rule]
    combine_mode: str = "all"  # 'all' (AND) or 'any' (OR)
    spec: TransformSpec = field(default_factory=TransformSpec)

    def match(
        self,
        *,
        param_name: str,
        param_type: type,
        param_default: Any,
        func: Callable,
        func_name: str,
    ) -> Optional[TransformSpec]:
        """Match based on combination of sub-rules."""
        results = [
            rule.match(
                param_name=param_name,
                param_type=param_type,
                param_default=param_default,
                func=func,
                func_name=func_name,
            )
            for rule in self.rules
        ]

        if self.combine_mode == "all":
            # All must match
            if all(r is not None for r in results):
                return self.spec
        elif self.combine_mode == "any":
            # Any must match
            if any(r is not None for r in results):
                return self.spec

        return None


class RuleChain:
    """
    Chain of rules evaluated in order with first-match semantics.

    Rules are tried from most specific to most general.
    """

    def __init__(self, rules: Optional[list[Rule]] = None):
        self.rules = rules or []

    def add_rule(self, rule: Rule, priority: int = 0):
        """Add a rule with optional priority (higher = evaluated earlier)."""
        self.rules.append((priority, rule))
        self.rules.sort(key=lambda x: -x[0])  # Sort by priority descending

    def match(
        self,
        *,
        param_name: str,
        param_type: type = type(None),
        param_default: Any = inspect.Parameter.empty,
        func: Optional[Callable] = None,
        func_name: str = "",
    ) -> Optional[TransformSpec]:
        """
        Find first matching rule.

        Returns:
            TransformSpec from first matching rule, or None if no match
        """
        for priority, rule in self.rules:
            result = rule.match(
                param_name=param_name,
                param_type=param_type,
                param_default=param_default,
                func=func or (lambda: None),
                func_name=func_name or "",
            )
            if result is not None:
                return result

        return None

    def __iadd__(self, rule: Rule):
        """Support += operator for adding rules."""
        self.add_rule(rule)
        return self

    def __add__(self, other: 'RuleChain') -> 'RuleChain':
        """Combine two rule chains."""
        new_chain = RuleChain()
        new_chain.rules = self.rules + other.rules
        new_chain.rules.sort(key=lambda x: -x[0])
        return new_chain


# Hardcoded fallback rules for common Python types
def _make_builtin_type_rules() -> TypeRule:
    """Create default type transformation rules for Python builtins."""

    # For now, builtins pass through to JSON (FastAPI handles this)
    # More sophisticated rules can be added later
    builtin_map = {
        str: TransformSpec(http_location=HttpLocation.JSON_BODY),
        int: TransformSpec(http_location=HttpLocation.JSON_BODY),
        float: TransformSpec(http_location=HttpLocation.JSON_BODY),
        bool: TransformSpec(http_location=HttpLocation.JSON_BODY),
        list: TransformSpec(http_location=HttpLocation.JSON_BODY),
        dict: TransformSpec(http_location=HttpLocation.JSON_BODY),
        type(None): TransformSpec(http_location=HttpLocation.JSON_BODY),
    }

    return TypeRule(type_map=builtin_map)


# Default global rule chain
DEFAULT_RULE_CHAIN = RuleChain()
DEFAULT_RULE_CHAIN.add_rule(_make_builtin_type_rules(), priority=-1000)  # Lowest priority


def extract_param_context(func: Callable, param_name: str) -> Dict[str, Any]:
    """Extract context information for a parameter."""
    sig = inspect.signature(func)
    param = sig.parameters.get(param_name)

    if param is None:
        raise ValueError(f"Parameter {param_name} not found in {func.__name__}")

    # Get type hint
    hints = get_type_hints(func) if hasattr(func, '__annotations__') else {}
    param_type = hints.get(param_name, type(None))

    return {
        'param_name': param_name,
        'param_type': param_type,
        'param_default': param.default,
        'func': func,
        'func_name': func.__name__,
    }


def resolve_transform(
    func: Callable,
    param_name: str,
    rule_chain: Optional[RuleChain] = None,
) -> TransformSpec:
    """
    Resolve transformation specification for a parameter.

    Resolution order:
    1. Rule chain (explicit rules)
    2. Type registry (registered types)
    3. Default fallback (JSON body, no transformation)

    Args:
        func: The function containing the parameter
        param_name: Name of the parameter
        rule_chain: Custom rule chain (uses DEFAULT_RULE_CHAIN if None)

    Returns:
        TransformSpec with transformation details
    """
    chain = rule_chain or DEFAULT_RULE_CHAIN
    context = extract_param_context(func, param_name)

    # Try rule chain first
    spec = chain.match(**context)

    # If no rule matched, check type registry
    if spec is None:
        try:
            from qh.types import get_transform_spec_for_type
            param_type = context['param_type']
            spec = get_transform_spec_for_type(param_type)
        except ImportError:
            # Type registry not available
            pass

    # Ultimate fallback: JSON body with no transformation
    if spec is None:
        spec = TransformSpec(http_location=HttpLocation.JSON_BODY)

    return spec
