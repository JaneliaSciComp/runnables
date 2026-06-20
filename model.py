"""Pydantic models for the runnables.yaml app manifest schema.

This is a standalone copy of the manifest models from
fileglancer.model, kept here so the schema generator has no
dependency on the main fileglancer package.

Note: the `env_parameters` field that exists on the entry point in
fileglancer.model is intentionally omitted here. It is an internal
mechanism used by auto-generated manifests (Nextflow, Pixi, future
adapters) and is not part of the authoring surface — hand-authored
manifests keep all user inputs on the Parameters tab.
"""

import re
from typing import Annotated, Any, Dict, List, Literal, Optional, Union

from pydantic import (
    BaseModel,
    Discriminator,
    Field,
    Tag,
    field_validator,
    model_validator,
)


class AppParameter(BaseModel):
    """A parameter definition for an app entry point"""

    flag: Optional[str] = Field(
        description="CLI flag syntax (e.g. '--outdir', '-n'). Omit for positional arguments.",
        default=None,
    )
    key: str = Field(
        description="Internal key for this parameter, auto-generated from flag or positional index",
        default="",
    )
    name: str = Field(description="Display name of the parameter")
    type: Literal[
        "string", "integer", "number", "boolean", "file", "directory", "enum"
    ] = Field(description="The data type of the parameter")
    description: Optional[str] = Field(
        description="Description of the parameter", default=None
    )
    required: bool = Field(
        description="Whether the parameter is required", default=False
    )
    default: Optional[Any] = Field(
        description="Default value for the parameter", default=None
    )
    options: Optional[List[Union[str, int, float]]] = Field(
        description="Allowed values for enum type", default=None
    )
    min: Optional[float] = Field(
        description="Minimum value for numeric types", default=None
    )
    max: Optional[float] = Field(
        description="Maximum value for numeric types", default=None
    )
    pattern: Optional[str] = Field(
        description="Regex validation pattern for string types", default=None
    )
    hidden: bool = Field(
        description="Whether the parameter is hidden by default in the UI",
        default=False,
    )
    raw: bool = Field(
        description="If true, value is appended to the command without shell quoting",
        default=False,
    )

    @field_validator("flag")
    @classmethod
    def validate_flag(cls, v):
        if v is not None:
            if not v.startswith("-"):
                raise ValueError(f"Flag must start with '-', got '{v}'")
            stripped = v.lstrip("-")
            if not stripped:
                raise ValueError("Flag must have content after dashes")
        return v


class AppParameterSection(BaseModel):
    """A collapsible section that groups parameters in the UI"""

    section: str = Field(description="Section title")
    description: Optional[str] = Field(default=None)
    collapsed: bool = Field(default=False)
    parameters: List[AppParameter] = Field(default=[])


def _param_item_discriminator(v):
    if isinstance(v, dict):
        return "section" if "section" in v else "parameter"
    return "section" if isinstance(v, AppParameterSection) else "parameter"


AppParameterItem = Annotated[
    Union[
        Annotated[AppParameter, Tag("parameter")],
        Annotated[AppParameterSection, Tag("section")],
    ],
    Discriminator(_param_item_discriminator),
]


class AppResourceDefaults(BaseModel):
    """Resource defaults for an app entry point"""

    cpus: Optional[int] = Field(description="Number of CPUs", default=None)
    memory: Optional[str] = Field(
        description="Memory allocation (e.g. '16 GB')", default=None
    )
    walltime: Optional[str] = Field(
        description="Wall time limit (e.g. '04:00')", default=None
    )
    queue: Optional[str] = Field(
        description="Cluster queue/partition name", default=None
    )


SUPPORTED_TOOLS = {"pixi", "npm", "maven", "miniforge", "apptainer", "nextflow"}

# Canonical parser for a single requirement spec, kept in sync with
# fileglancer.model so manifest validation matches the runtime check.
# Groups: 1=tool name, 2=operator (or None), 3=version (or None).
_REQUIREMENT_OPERATOR_PATTERN = re.compile(r">=|<=|!=|==|>|<")
_REQUIREMENT_PATTERN = re.compile(
    r"^([a-zA-Z][a-zA-Z0-9_-]*)\s*(?:(>=|<=|!=|==|>|<)\s*([^,\s><=!]+))?$"
)

_SHELL_METACHAR_PATTERN = re.compile(r"[;&|`$(){}!<>\n\r]")
_CONDA_ENV_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")
_CONDA_ENV_PATH_FORBIDDEN = re.compile(r"[;&|`$(){}!<>\n\r]")


def _validate_requirements(requirements: List[str]) -> List[str]:
    for req in requirements:
        stripped = req.strip()
        match = _REQUIREMENT_PATTERN.match(stripped)
        if not match:
            if (
                "," in stripped
                or len(_REQUIREMENT_OPERATOR_PATTERN.findall(stripped)) > 1
            ):
                raise ValueError(
                    "Compound requirement specs are not supported; use at most "
                    "one version comparison per tool, e.g. 'pixi>=0.40'."
                )
            raise ValueError(
                f"Invalid requirement format: {req!r}. Expected a tool name "
                "with an optional single version comparison, e.g. 'pixi>=0.40'."
            )

        tool = match.group(1)
        if tool not in SUPPORTED_TOOLS:
            raise ValueError(
                f"Unsupported tool: '{tool}'. Supported: {SUPPORTED_TOOLS}"
            )
    return requirements


class AppEntryPoint(BaseModel):
    """An entry point (command) within an app"""

    id: str = Field(description="Unique identifier for the entry point")
    name: str = Field(description="Display name of the entry point")
    type: Literal["job", "service"] = Field(
        description="Whether this is a batch job or long-running service",
        default="job",
    )
    description: Optional[str] = Field(
        description="Description of the entry point", default=None
    )
    command: str = Field(description="The base CLI command to execute")
    parameters: List[AppParameterItem] = Field(
        description="Parameters for this entry point", default=[]
    )
    resources: Optional[AppResourceDefaults] = Field(
        description="Default resource requirements", default=None
    )
    env: Optional[Dict[str, str]] = Field(
        description="Default environment variables", default=None
    )
    pre_run: Optional[str] = Field(
        description="Script to run before the main command", default=None
    )
    post_run: Optional[str] = Field(
        description="Script to run after the main command", default=None
    )
    conda_env: Optional[str] = Field(
        description="Conda environment name or path to activate before running",
        default=None,
    )
    container: Optional[str] = Field(
        description="Container image URL for Apptainer (e.g. 'ghcr.io/org/image:tag')",
        default=None,
    )
    bind_paths: Optional[List[str]] = Field(
        description="Additional paths to bind-mount into the container",
        default=None,
    )
    container_args: Optional[str] = Field(
        description="Default extra arguments for container exec (e.g. '--nv')",
        default=None,
    )
    requirements: List[str] = Field(
        description="Required tools for this entry point, e.g. ['apptainer']. Merged with manifest-level requirements.",
        default=[],
    )

    @field_validator("requirements")
    @classmethod
    def validate_entry_point_requirements(cls, v):
        return _validate_requirements(v)

    @field_validator("conda_env")
    @classmethod
    def validate_conda_env(cls, v):
        if v is None:
            return v
        if v.startswith("/"):
            # Absolute path: reject shell metacharacters
            if _CONDA_ENV_PATH_FORBIDDEN.search(v):
                raise ValueError(
                    f"conda_env path contains forbidden characters: {v!r}"
                )
        else:
            # Name: must be alphanumeric, dots, dashes, underscores
            if not _CONDA_ENV_NAME_PATTERN.match(v):
                raise ValueError(
                    f"conda_env name must match [a-zA-Z0-9_.-]+, got: {v!r}"
                )
        return v

    @field_validator("container")
    @classmethod
    def validate_container(cls, v):
        if v is None:
            return v
        if _SHELL_METACHAR_PATTERN.search(v):
            raise ValueError(f"container URL contains forbidden characters: {v!r}")
        return v

    @field_validator("bind_paths")
    @classmethod
    def validate_bind_paths(cls, v):
        if v is None:
            return v
        for p in v:
            if _SHELL_METACHAR_PATTERN.search(p):
                raise ValueError(
                    f"bind_paths entry contains forbidden characters: {p!r}"
                )
        return v

    def flat_parameters(self) -> List[AppParameter]:
        """Return a flat list of all parameters, traversing sections."""
        result = []
        for item in self.parameters:
            if isinstance(item, AppParameterSection):
                result.extend(item.parameters)
            else:
                result.append(item)
        return result

    @model_validator(mode="after")
    def generate_parameter_keys(self):
        positional_index = 0
        keys_seen: dict[str, str] = {}
        for param in self.flat_parameters():
            if param.flag is not None:
                param.key = param.flag.lstrip("-")
            else:
                param.key = f"_arg{positional_index}"
                positional_index += 1
            if param.key in keys_seen:
                raise ValueError(
                    f"Duplicate parameter key '{param.key}' "
                    f"(from '{param.name}' and '{keys_seen[param.key]}')"
                )
            keys_seen[param.key] = param.name
        return self

    @model_validator(mode="after")
    def check_conda_container_exclusive(self):
        if self.conda_env and self.container:
            raise ValueError(
                "conda_env and container are mutually exclusive — use one or the other"
            )
        if self.bind_paths and not self.container:
            raise ValueError("bind_paths requires container to be set")
        return self


class AppManifest(BaseModel):
    """Top-level app manifest (runnables.yaml)"""

    name: str = Field(description="Display name of the app")
    description: Optional[str] = Field(
        description="Description of the app", default=None
    )
    repo_url: Optional[str] = Field(
        description="GitHub repo URL where the tool code lives. If absent, uses the repo containing this manifest.",
        default=None,
    )
    requirements: List[str] = Field(
        description="Required tools, e.g. ['pixi>=0.40', 'npm']",
        default=[],
    )
    runnables: List[AppEntryPoint] = Field(
        description="Available entry points for this app"
    )

    @field_validator("requirements")
    @classmethod
    def validate_requirements(cls, v):
        return _validate_requirements(v)
