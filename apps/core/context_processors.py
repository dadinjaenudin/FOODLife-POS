"""
Context processors for adding data to all templates
"""
from apps.core.terminal_config import get_terminal_config


def terminal_config(request):
    """
    Add terminal configuration to all templates
    Usage in templates: {{ terminal_config.terminal_code }}
    """
    config = get_terminal_config()
    return {
        'terminal_config': config.get_all(),
        'terminal_configured': config.is_configured(),
    }
