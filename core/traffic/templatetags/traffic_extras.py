from django import template

register = template.Library()

@register.filter
def percentage(value, total):
    """Calcula el porcentaje de value sobre total"""
    try:
        value = int(value)
        total = int(total)
        if total == 0:
            return 0
        return int((value / total) * 100)
    except (ValueError, TypeError):
        return 0
