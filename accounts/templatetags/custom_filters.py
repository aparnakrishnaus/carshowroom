from django import template

register = template.Library()

@register.filter
def pretty_label(value):
    if not isinstance(value, str):
        return value
    return value.replace('_', ' ').title()


