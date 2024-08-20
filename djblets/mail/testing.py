"""Testing utilities for mail-related unit tests."""

from __future__ import annotations

from typing import Dict, List, TYPE_CHECKING, Union

import dns.message
import dns.rdataclass
import dns.rdatatype
import dns.resolver
from django.core.cache import cache
from django.utils.encoding import force_bytes
from dns.rdtypes.ANY.TXT import TXT
from kgb import SpyAgency

if TYPE_CHECKING:
    from djblets.testing.testcases import TestCase as MixinParentClass
else:
    MixinParentClass = object


class DmarcDnsTestsMixin(MixinParentClass):
    """Mixin to help with e-mail tests that need to perform DMARC lookups.

    This mixin makes it easy for unit tests to fake DMARC results, in order
    to prevent the need from looking up real data from real records.

    Unit tests can provide a mapping from domain names to TXT record strings
    in the :py:attr:`dmarc_txt_records` dictionary. When a DMARC lookup is
    performed, this dictionary will be used for the lookup.

    Note that this mixin will also clear the memory cache before each test
    run.
    """

    #: A dictionary of domain names to DMARC TXT record data.
    #:
    #: Type:
    #:     dict
    dmarc_txt_records: Dict[str, Union[bytes, str, list[Union[bytes, str]]]]

    def setUp(self) -> None:
        self.dmarc_txt_records = {}

        self._dmarc_spy_agency = SpyAgency()
        self._dmarc_spy_agency.spy_on(dns.resolver.resolve,
                                      call_fake=self._dns_query)
        cache.clear()

        # This has to happen after we clear the cache. Some other test cases
        # (such as webapi or siteconfig tests) rely on cached data that gets
        # set up in their setUp methods.
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()

        self._dmarc_spy_agency.unspy_all()

    def _dns_query(
        self,
        qname: str,
        *args,
        **kwargs,
    ) -> List:
        """Return a fake answer for a DNS query.

        This will return either a TXT record or a NXDOMAIN error based on the
        presence of a key in :py:attr:`dmarc_txt_records`.

        Note that technically this should be returning a
        :py:class:`dns.resolver.Answer`, but that's fairly complex to set up,
        and our usage turns this into a list of results anyway.

        Args:
            qname (str):
                The domain being queried.

            *args (tuple, unused):
                Unused positional arguments.

            **kwargs (tuple, unused):
                Unused keyword arguments.

        Returns:
            list:
            The list of resulting records.

        Raises:
            dns.resolve.NXDOMAIN:
                The domain did not have a pre-populated result.
        """
        try:
            strings: list[Union[bytes, str]]
            value = self.dmarc_txt_records[qname]

            if isinstance(value, list):
                strings = value
            else:
                strings = [value]

            return [TXT(1, 16, [
                force_bytes(s)
                for s in strings
            ])]
        except KeyError:
            raise dns.resolver.NXDOMAIN
