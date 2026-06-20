"""Generate a JSON Schema for runnables.yaml from the Pydantic models.

Usage:
    pixi run generate-schema
    python generate_schema.py              # writes to runnables.schema.json
    python generate_schema.py out.json     # writes to custom path
"""

import json
import sys
from pathlib import Path

from model import AppManifest


def generate_schema() -> dict:
    schema = AppManifest.model_json_schema()

    # The 'key' field on AppParameter is auto-generated at runtime by
    # AppEntryPoint.generate_parameter_keys and should not appear in
    # user-authored YAML files.  Remove it from the schema so it doesn't
    # confuse manifest authors.
    param_schema = schema.get("$defs", {}).get("AppParameter", {})
    if "properties" in param_schema:
        param_schema["properties"].pop("key", None)
    if "key" in param_schema.get("required", []):
        param_schema["required"].remove("key")

    # Add schema metadata
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = "https://fileglancer.org/schemas/runnables.schema.json"

    return schema


def main():
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("runnables.schema.json")
    dest.parent.mkdir(parents=True, exist_ok=True)

    schema = generate_schema()
    dest.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"Wrote {dest}")


if __name__ == "__main__":
    main()
