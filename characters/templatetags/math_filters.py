from django import template

register = template.Library()


@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """Divide the value by the argument."""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def split(value, arg):
    """Split a string by the given separator."""
    return str(value).split(arg)


@register.filter
def percentage(value, total):
    """Calculate percentage: (value / total) * 100. Returns a string with period decimal separator to avoid locale-aware formatting breaking CSS width values."""
    try:
        if float(total) == 0:
            return "0"
        result = (float(value) / float(total)) * 100
        return f"{result:.4f}"
    except (ValueError, TypeError):
        return "0"