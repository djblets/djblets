"""Functions to humanize values."""


def humanize_list(value):
    """
    Humanizes a list of values, inserting commas and "and" where appropriate.

      ========================= ======================
      Example List              Resulting string
      ========================= ======================
      ``["a"]``                 ``"a"``
      ``["a", "b"]``            ``"a and b"``
      ``["a", "b", "c"]``       ``"a, b and c"``
      ``["a", "b", "c", "d"]``  ``"a, b, c, and d"``
      ========================= ======================
    """
    if len(value) == 0:
        return ""
    elif len(value) == 1:
        return value[0]

    s = ", ".join(value[:-1])

    if len(value) > 3:
        s += ","

    return "%s and %s" % (s, value[-1])
