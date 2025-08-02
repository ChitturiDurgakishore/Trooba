# yourapp/templatetags/custom_filters.py

from django import template
import json

register = template.Library()

@register.filter
def dict_key(d, key):
    """
    Safely get a dictionary key in templates.
    Usage: {{ my_dict|dict_key:"key_name" }}
    """
    if isinstance(d, dict):
        return d.get(key)
    return None

@register.filter
def pretty_json(value):
    """
    Pretty-print a dict or JSON object.
    Usage: {{ my_object|pretty_json }}
    """
    try:
        return json.dumps(value, indent=2)
    except Exception:
        return value
