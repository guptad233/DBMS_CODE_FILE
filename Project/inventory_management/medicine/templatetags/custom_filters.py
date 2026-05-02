from django import template
import math

register = template.Library()

@register.filter
def abs_value(value):
    """Return the absolute value of a number."""
    try:
        return abs(value)
    except (ValueError, TypeError):
        return value

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def subtract(value, arg):
    """Subtract the argument from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return value

@register.filter
def percentage(value, arg):
    """Calculate percentage of value relative to arg."""
    try:
        return (float(value) / float(arg)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def format_currency(value):
    """Format a number as currency."""
    try:
        return "${:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def get_dict_item(dictionary, key):
    """Get an item from a dictionary using key."""
    return dictionary.get(key)

@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
    
@register.filter
def add_class(field, css_class):
    """Add a CSS class to the form field."""
    return field.as_widget(attrs={"class": css_class})