from django import template
import math

register = template.Library()

@register.filter
def stars(rating, max_stars=5):
    """
    Return a list of length `max_stars` with values: 'full', 'half', 'empty'
    depending on the numeric rating (float or int).
    Example for rating=4.2 -> ['full','full','full','full','half']
    """
    try:
        r = float(rating or 0)
    except (TypeError, ValueError):
        r = 0.0

    # Clamp rating between 0 and max_stars
    r = max(0.0, min(r, float(max_stars)))

    full = int(math.floor(r))
    frac = r - full

    # Determine half star threshold (use 0.25..0.75 as half, >=0.75 as full)
    if frac >= 0.75:
        half = 0
        full += 1
    elif frac >= 0.25:
        half = 1
    else:
        half = 0

    empty = max_stars - full - half

    return ['full'] * full + ['half'] * half + ['empty'] * empty
