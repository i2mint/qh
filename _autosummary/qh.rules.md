# qh.rules

Transformation rule system for qh.

Supports multi-dimensional matching:

- Type-based
- Argument name-based
- Function name-based
- Function object-based
- Default value-based
- Any combination thereof

Rules are layered with first-match semantics, from specific to general.

### Functions

| [`extract_param_context`](#qh.rules.extract_param_context)(func, param_name)           | Extract context information for a parameter.          |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| [`resolve_transform`](#qh.rules.resolve_transform)(func, param_name[, rule_chain]) | Resolve transformation specification for a parameter. |

### Classes

| [`CompositeRule`](#qh.rules.CompositeRule)(rules[, combine_mode, spec])   | Rule that combines multiple conditions.                       |
|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| [`DefaultValueRule`](#qh.rules.DefaultValueRule)(predicate, spec)            | Rule that matches based on default values.                    |
| [`FuncNameRule`](#qh.rules.FuncNameRule)(pattern_map)                    | Rule that matches based on function name pattern.             |
| [`FuncRule`](#qh.rules.FuncRule)(func_map)                           | Rule that matches based on function.                          |
| [`HttpLocation`](#qh.rules.HttpLocation)(\*values)                       | Where in HTTP request/response to map a parameter.            |
| [`NameRule`](#qh.rules.NameRule)(name_map)                           | Rule that matches based on parameter name.                    |
| [`Rule`](#qh.rules.Rule)(\*args, \*\*kwargs)                     | Protocol for transformation rules.                            |
| [`RuleChain`](#qh.rules.RuleChain)([rules])                           | Chain of rules evaluated in order with first-match semantics. |
| [`TransformSpec`](#qh.rules.TransformSpec)([http_location, ingress, ...]) | Specification for how to transform a parameter.               |
| [`TypeRule`](#qh.rules.TypeRule)(type_map)                           | Rule that matches based on parameter type.                    |

### *class* qh.rules.CompositeRule(rules, combine_mode='all', spec=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that combines multiple conditions.

#### match(, param_name, param_type, param_default, func, func_name)

Match based on combination of sub-rules.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]

### *class* qh.rules.DefaultValueRule(predicate, spec)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on default values.

#### match(, param_name, param_type, param_default, func, func_name)

Match if predicate returns True for default value.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]

### *class* qh.rules.FuncNameRule(pattern_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on function name pattern.

#### match(, param_name, param_type, param_default, func, func_name)

Match by function name pattern.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]

### *class* qh.rules.FuncRule(func_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on function.

#### match(, param_name, param_type, param_default, func, func_name)

Match by function object and parameter name.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]

### *class* qh.rules.HttpLocation(\*values)

Bases: [`Enum`](https://docs.python.org/3/library/enum.html#enum.Enum)

Where in HTTP request/response to map a parameter.

### *class* qh.rules.NameRule(name_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on parameter name.

#### match(, param_name, param_type, param_default, func, func_name)

Match by parameter name.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]

### *class* qh.rules.Rule(\*args, \*\*kwargs)

Bases: [`Protocol`](https://docs.python.org/3/library/typing.html#typing.Protocol)

Protocol for transformation rules.

#### match(, param_name, param_type, param_default, func, func_name)

Check if this rule matches the given parameter context.

* **Parameters:**
  * **param_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The parameter’s name.
  * **param_type** ([`type`](https://docs.python.org/3/builtins/functions.html#type)) – The parameter’s type annotation.
  * **param_default** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – The parameter’s default, or `inspect.Parameter.empty`.
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – The function the parameter belongs to.
  * **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `func`’s name.
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]
* **Returns:**
  TransformSpec if matched, None otherwise

### *class* qh.rules.RuleChain(rules=None)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Chain of rules evaluated in order with first-match semantics.

Rules are tried from most specific to most general.

```pycon
>>> chain = RuleChain()
>>> chain.add_rule(TypeRule({int: TransformSpec(http_location=HttpLocation.QUERY)}))
>>> chain.match(param_name='x', param_type=int).http_location
<HttpLocation.QUERY: 'query'>
>>> chain.match(param_name='y', param_type=str) is None
True
```

#### add_rule(rule, priority=0)

Add a rule with optional priority (higher = evaluated earlier).

#### match(\*, param_name, param_type=<class 'NoneType'>, param_default, func=None, func_name='')

Find first matching rule.

* **Parameters:**
  * **param_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The parameter’s name.
  * **param_type** ([`type`](https://docs.python.org/3/builtins/functions.html#type)) – The parameter’s type annotation.
  * **param_default** ([`Any`](https://docs.python.org/3/library/typing.html#typing.Any)) – The parameter’s default, or `inspect.Parameter.empty`.
  * **func** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]) – The function the parameter belongs to, if known.
  * **func_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – `func`’s name.
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]
* **Returns:**
  TransformSpec from first matching rule, or None if no match

### *class* qh.rules.TransformSpec(http_location=HttpLocation.JSON_BODY, ingress=None, egress=None, http_name=None, metadata=<factory>)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Specification for how to transform a parameter.

### *class* qh.rules.TypeRule(type_map)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Rule that matches based on parameter type.

#### match(, param_name, param_type, param_default, func, func_name)

Match by type, including type hierarchy.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`TransformSpec`](#qh.rules.TransformSpec)]

### qh.rules.extract_param_context(func, param_name)

Extract context information for a parameter.

* **Return type:**
  [`Dict`](https://docs.python.org/3/library/typing.html#typing.Dict)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

### qh.rules.resolve_transform(func, param_name, rule_chain=None)

Resolve transformation specification for a parameter.

Resolution order:

1. Rule chain (explicit rules)
2. Type registry (registered types)
3. Default fallback (JSON body, no transformation)

* **Parameters:**
  * **func** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)) – The function containing the parameter
  * **param_name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the parameter
  * **rule_chain** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`RuleChain`](#qh.rules.RuleChain)]) – Custom rule chain (uses DEFAULT_RULE_CHAIN if None)
* **Return type:**
  [`TransformSpec`](#qh.rules.TransformSpec)
* **Returns:**
  TransformSpec with transformation details
