"""Common symbols useful for function signatures.

Version Added:
    3.3
"""


class UnsetSymbol:
    """A symbol indicating an unset value.

    This can be useful in functions that take default values to distinguish
    between a value not provided and a false/``None`` value.

    Version Added:
        3.3
    """


#: An instance of a symbol indicating an unset value.
#:
#: Version Added:
#:     3.3
UNSET = UnsetSymbol()
