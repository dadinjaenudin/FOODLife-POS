from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='rupiah')
def rupiah(value):
    """Format number as Indonesian Rupiah with comma thousands separator"""
    if value is None:
        return 'Rp 0'
    
    try:
        # Convert to float and format with comma
        num = float(value)
        # Format with thousands separator (comma) and no decimals
        formatted = '{:,.0f}'.format(num)
        return formatted
    except (ValueError, TypeError):
        return value


@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if dictionary is None:
        return None
    return dictionary.get(key)
