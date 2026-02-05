"""
Context processors for adding data to all templates
"""
from apps.core.terminal_config import get_terminal_config
from apps.core.models import Store, Brand, StoreBrand


def terminal_config(request):
    """
    Add terminal configuration to all templates
    Usage in templates: {{ terminal_config.terminal_code }}
    """
    try:
        config = get_terminal_config()
        return {
            'terminal_config': config.get_all(),
            'terminal_configured': config.is_configured(),
        }
    except Exception as e:
        # Return empty config if there's an error
        # This prevents context processor from breaking the page
        return {
            'terminal_config': {},
            'terminal_configured': False,
        }


def store_config(request):
    """
    Add store configuration to all templates
    Usage in templates: {{ store_config.store_location }}
    """
    try:
        store = Store.get_current()
        return {
            'store_config': store,
        }
    except Exception as e:
        return {
            'store_config': None,
        }


def global_context(request):
    """
    Add global context variables including brand filter
    """
    try:
        store = Store.get_current()
        
        # Get all brands associated with this store
        available_brands = []
        if store:
            store_brands = StoreBrand.objects.filter(
                store=store, 
                is_active=True
            ).select_related('brand')
            available_brands = [sb.brand for sb in store_brands]
        
        # Get context brand from session
        context_brand_id = request.session.get('context_brand_id', '')
        
        return {
            'available_brands': available_brands,
            'context_brand_id': context_brand_id,
        }
    except Exception as e:
        return {
            'available_brands': [],
            'context_brand_id': '',
        }
