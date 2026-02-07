"""Base schema with camelCase serialization for API responses."""

from pydantic import BaseModel, ConfigDict


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class BaseSchema(BaseModel):
    """Base schema that all API models must inherit from.

    Converts snake_case Python attributes to camelCase in JSON responses.
    This is critical for frontend/backend consistency.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
