"""
Utility functions for social authentication provider management.
Provides consistent, readable names for OAuth providers.
"""

# Map provider keys to human-readable names
PROVIDER_DISPLAY_NAMES = {
    'google': 'Google',
    'apple': 'Apple',
    'facebook': 'Facebook',
    'github': 'GitHub',
    'linkedin': 'LinkedIn',
    'twitter': 'Twitter',
    'microsoft': 'Microsoft',
    'instagram': 'Instagram',
}


def get_provider_display(provider_key: str) -> str:
    """
    Get human-readable display name for a provider.
    
    Args:
        provider_key: The provider identifier (e.g., 'google', 'apple')
    
    Returns:
        str: The display name (e.g., 'Google', 'Apple')
        
    Example:
        >>> get_provider_display('google')
        'Google'
    """
    return PROVIDER_DISPLAY_NAMES.get(provider_key, provider_key.title())


def get_all_provider_choices() -> list:
    """
    Get all available provider choices for form select fields.
    
    Returns:
        list: List of tuples [(key, display_name), ...]
        
    Example:
        >>> get_all_provider_choices()
        [('google', 'Google'), ('apple', 'Apple'), ...]
    """
    return [(key, display) for key, display in PROVIDER_DISPLAY_NAMES.items()]
