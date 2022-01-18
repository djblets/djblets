"""Compatibility for features removed in Python 3.

Note that this module is not considered API-stable. Changes may be made that
remove or alter functionality in the future. Please use at your own risk.
"""

cmp = lambda x, y: (x > y) - (x < y)


__all__ = (
    'cmp',
)
