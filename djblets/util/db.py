#
# db.py -- Database utilities.
#
# Copyright (c) 2007  David Trowbridge
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#


from django.db import models, IntegrityError
from django.db.models.query import Q, QAnd, QOr


#
# This is a hack to work around the stupid default behavior of Q objects and OR
# operators.  By default, querying (Q(x) | Q(y)) | Q(z) when foreign keys are
# involved will result in some small set of objects, instead of the union of x,
# y and z.
#
# This implementation comes from http://www.djangosnippets.org/snippets/274/
# By user "dottedmag" on djangosnippets.  Distributed under the generic terms of
# the djangosnippets web site.
#
class QLeftOuterJoins(Q):
    "Replaces all INNER JOINs with LEFT OUTER JOINs inside"
    def __init__(self, q):
        self.q = q

    def __and__(self, other):
        return QAnd(self, other)

    def __or__(self, other):
        return QOr(self, other)

    def get_sql(self, opts):
        joins, where, params = self.q.get_sql(opts)
        for join_name, join in joins.iteritems():
            joins[join_name] = (join[0], "LEFT OUTER JOIN", join[2])
        return joins, where, params


class ConcurrencyManager(models.Manager):
    """
    A class designed to work around database concurrency issues.
    """
    def get_or_create(self, **kwargs):
        """
        A wrapper around get_or_create that makes a final attempt to get
        the object if the creation fails.

        This helps with race conditions in the database where, between the
        original get() and the create(), another process created the object,
        causing us to fail. We'll then execute a get().

        This is still prone to race conditions, but they're even more rare.
        A delete() would have to happen before the unexpected create() but
        before the get().
        """
        try:
            return super(ConcurrencyManager, self).get_or_create(**kwargs)
        except IntegrityError:
            return self.get(**kwargs)
