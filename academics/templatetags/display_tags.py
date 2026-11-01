"""Small template helpers for generic master-data list/detail screens."""

from django import template

register = template.Library()


@register.filter
def display(obj, field_path):
    """Resolve a dotted attribute path and render it safely.

    Booleans become Yes/No and ``None`` becomes an em dash so shared
    templates can render heterogeneous master-data models without custom
    per-model templates.
    """
    value = obj
    for part in str(field_path).split("."):
        if value is None:
            return "—"
        value = getattr(value, part, "")
        if callable(value):
            value = value()
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return value
