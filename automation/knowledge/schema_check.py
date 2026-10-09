"""Minimal JSON Schema validator for the knowledge schemas (standard library only).

Supports the subset the knowledge schemas use: ``type`` (string or list),
``properties``, ``required``, ``additionalProperties`` (bool or schema),
``items``, ``enum``, ``const``, ``pattern``, ``minLength``, ``minItems``,
``uniqueItems``, ``minimum``, ``maximum``, ``anyOf`` and ``$ref`` to
``#/$defs/...`` or ``<file>.schema.json#/$defs/...`` in the schema directory.

An unsupported keyword raises instead of being ignored, so a schema can never
appear to pass because the validator skipped a constraint. When the optional
``jsonschema`` package is installed, tests also cross-check with it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SUPPORTED = {
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description", "examples",
    "type", "properties", "required", "additionalProperties", "items", "enum", "const",
    "pattern", "minLength", "minItems", "uniqueItems", "minimum", "maximum", "anyOf",
}
TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
}


class SchemaError(Exception):
    """The schema itself uses something this validator cannot enforce."""


def _is_type(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPES[name])


class Validator:
    def __init__(self, schema_dir: Path):
        self.schema_dir = schema_dir
        self._cache: dict[str, dict] = {}

    def load(self, name: str) -> dict:
        if name not in self._cache:
            self._cache[name] = json.loads((self.schema_dir / name).read_text(encoding="utf-8"))
        return self._cache[name]

    def _resolve(self, ref: str, root_name: str) -> tuple[dict, str]:
        file_part, _, pointer = ref.partition("#")
        name = file_part or root_name
        node: Any = self.load(name)
        for token in [t for t in pointer.split("/") if t]:
            node = node[token]
        return node, name

    def validate(self, instance: Any, schema_name: str) -> list[str]:
        errors: list[str] = []
        self._check(instance, self.load(schema_name), schema_name, "$", errors)
        return errors

    def _check(self, value: Any, schema: dict, root: str, path: str, errors: list[str]) -> None:
        unknown = set(schema) - SUPPORTED
        if unknown:
            raise SchemaError(f"{root}: unsupported keyword(s) {sorted(unknown)} at {path}")
        if "$ref" in schema:
            target, target_root = self._resolve(schema["$ref"], root)
            self._check(value, target, target_root, path, errors)
        if "anyOf" in schema:
            branches = []
            for option in schema["anyOf"]:
                trial: list[str] = []
                self._check(value, option, root, path, trial)
                branches.append(trial)
            if all(branches):
                errors.append(f"{path}: matches none of anyOf ({branches[0][0] if branches[0] else ''})")
        if "type" in schema:
            names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
            if not any(_is_type(value, n) for n in names):
                errors.append(f"{path}: expected {'/'.join(names)}, got {type(value).__name__}")
                return
        if "const" in schema and value != schema["const"]:
            errors.append(f"{path}: must equal {schema['const']!r}")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: {value!r} not in {schema['enum']}")
        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                errors.append(f"{path}: shorter than {schema['minLength']} characters")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: below minimum {schema['minimum']}")
            if "maximum" in schema and value > schema["maximum"]:
                errors.append(f"{path}: above maximum {schema['maximum']}")
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                errors.append(f"{path}: fewer than {schema['minItems']} items")
            if schema.get("uniqueItems"):
                seen = [json.dumps(v, sort_keys=True) for v in value]
                if len(seen) != len(set(seen)):
                    errors.append(f"{path}: items are not unique")
            if "items" in schema:
                for index, item in enumerate(value):
                    self._check(item, schema["items"], root, f"{path}[{index}]", errors)
        if isinstance(value, dict):
            for key in schema.get("required", []):
                if key not in value:
                    errors.append(f"{path}: missing required property {key!r}")
            properties = schema.get("properties", {})
            for key, item in value.items():
                if key in properties:
                    self._check(item, properties[key], root, f"{path}.{key}", errors)
                else:
                    extra = schema.get("additionalProperties", True)
                    if extra is False:
                        errors.append(f"{path}: unexpected property {key!r}")
                    elif isinstance(extra, dict):
                        self._check(item, extra, root, f"{path}.{key}", errors)
