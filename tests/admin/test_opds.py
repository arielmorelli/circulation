from nose.tools import (
    set_trace,
    eq_
)

import feedparser

from api.admin.opds import AdminAnnotator
from api.opds import AcquisitionFeed

from .. import DatabaseTest

class TestOPDS(DatabaseTest):

    def test_feed_includes_suppress_link(self):
        work = self._work(with_open_access_download=True)
        lp = work.license_pools[0]
        lp.suppressed = False
        self._db.commit()

        feed = AcquisitionFeed(self._db, "test", "url", [work], AdminAnnotator(None, test_mode=True))
        [entry] = feedparser.parse(unicode(feed))['entries']
        [suppress_link] = [x for x in entry['links'] if x['rel'] == "http://librarysimplified.org/terms/rel/hide"]
        assert lp.identifier.identifier in suppress_link["href"]
        unsuppress_links = [x for x in entry['links'] if x['rel'] == "http://librarysimplified.org/terms/rel/restore"]
        eq_(0, len(unsuppress_links))

        lp.suppressed = True
        self._db.commit()

        feed = AcquisitionFeed(self._db, "test", "url", [work], AdminAnnotator(None, test_mode=True))
        [entry] = feedparser.parse(unicode(feed))['entries']
        [unsuppress_link] = [x for x in entry['links'] if x['rel'] == "http://librarysimplified.org/terms/rel/restore"]
        assert lp.identifier.identifier in unsuppress_link["href"]
        suppress_links = [x for x in entry['links'] if x['rel'] == "http://librarysimplified.org/terms/rel/hide"]
        eq_(0, len(suppress_links))

    def test_feed_includes_edit_link(self):
        work = self._work(with_open_access_download=True)
        lp = work.license_pools[0]
 
        feed = AcquisitionFeed(self._db, "test", "url", [work], AdminAnnotator(None, test_mode=True))
        [entry] = feedparser.parse(unicode(feed))['entries']
        [edit_link] = [x for x in entry['links'] if x['rel'] == "edit"]
        assert lp.identifier.identifier in edit_link["href"]
