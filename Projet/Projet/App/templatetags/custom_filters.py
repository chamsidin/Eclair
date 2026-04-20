from django import template

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    """
    Custom template filter to get a value from a dictionary by key.
    
    Usage: {{ my_dict|dict_get:key }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

