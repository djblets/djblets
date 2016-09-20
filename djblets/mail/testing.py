"""Testing utilities for mail-related unit tests."""

from __future__ import unicode_literals

from django.core.cache import cache
from dns import resolver as dns_resolver
from dns.rdtypes.ANY.TXT import TXT
from kgb import SpyAgency


class DmarcDnsTestsMixin(object):
    """Mixin to help with e-mail tests that need to perform DMARC lookups.

    This mixin makes it easy for unit tests to fake DMARC results, in order
    to prevent the need from looking up real data from real records.

    Unit tests can provide a mapping from domain names to TXT record strings
    in the :py:attr:`dmarc_txt_records` dictionary. When a DMARC lookup is
    performed, this dictionary will be used for the lookup.

    Note that this mixin will also clear the memory cache before each test
    run.

    Attributes:
        dmarc_txt_records (dict):
            A dictionary of domain names to DMARC TXT record strings.
    """

    def setUp(self):
        super(DmarcDnsTestsMixin, self).setUp()

        self.dmarc_txt_records = {}

        self._dmarc_spy_agency = SpyAgency()
        self._dmarc_spy_agency.spy_on(dns_resolver.query,
                                      call_fake=self._dns_query)
        cache.clear()

    def tearDown(self):
        super(DmarcDnsTestsMixin, self).tearDown()

        self._dmarc_spy_agency.unspy_all()

    def _dns_query(self, qname, rdtype, *args, **kwargs):
        try:
            return [TXT(1, 16, [self.dmarc_txt_records[qname]])]
        except KeyError:
            raise dns_resolver.NXDOMAIN
