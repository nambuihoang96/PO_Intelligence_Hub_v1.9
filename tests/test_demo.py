import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.dbpatch=patch.object(server,'DBPATH',Path(self.dir.name)/'test.sqlite3')
        self.dbpatch.start()
        server.init()
    def tearDown(self):
        self.dbpatch.stop();self.dir.cleanup()
    def test_seed(self):
        b=server.bootstrap()
        self.assertEqual(len(b['projects']),3)
        self.assertEqual(len(b['signals']),5)
        self.assertEqual(len(b['tasks']),5)
        self.assertFalse(b['settings']['codex_allowed'])
    def test_demo_scan_creates_signal_and_task(self):
        before=server.bootstrap()
        r=server.demo_scan(1)
        after=server.bootstrap()
        self.assertEqual(r['new_signals'],1)
        self.assertEqual(len(after['signals']),len(before['signals'])+1)
        self.assertEqual(len(after['tasks']),len(before['tasks'])+1)
    def test_manual_analysis_to_action(self):
        row=server.bootstrap()['tasks'][0]
        x=server.sample_result(row['id'])
        server.submit_analysis(row['id'],x)
        b=server.bootstrap()
        self.assertEqual(len(b['insights']),1)
        i=b['insights'][0]
        self.assertEqual(i['task_id'],row['id'])
        server.action_update(i['id'],{'state':'approved'})
        self.assertEqual(server.bootstrap()['insights'][0]['state'],'approved')
    def test_wrong_task_id_rejected(self):
        row=server.bootstrap()['tasks'][0]
        x=server.sample_result(row['id']); x['task_id']='RS-9999'
        with self.assertRaises(ValueError): server.submit_analysis(row['id'],x)
    def test_rss_baseline_and_new_keyword_article(self):
        self.assertGreater(len(server.bootstrap()['sources']),0)
        first=b'<rss><channel><item><title>Short drama older update</title><link>https://trends.google.com/a</link><guid>a</guid></item></channel></rss>'
        second=b'<rss><channel><item><title>Short drama NEW feature</title><link>https://trends.google.com/b</link><guid>b</guid></item><item><title>Short drama older update</title><link>https://trends.google.com/a</link><guid>a</guid></item></channel></rss>'
        class FakeResponse:
            def __init__(self, body): self.body=body
            def __enter__(self): return self
            def __exit__(self,*a): return False
            def read(self,*a): return self.body
            def geturl(self): return 'https://trends.google.com/trending/rss?geo=US'
        with server.con() as c:
            c.execute('DELETE FROM rss_sources WHERE project_id=1 AND name!=?',('Google Trends Trending US',))
        with patch.object(server.urllib.request,'urlopen',side_effect=[FakeResponse(first),FakeResponse(second)]):
            self.assertEqual(server.scan_rss(1)['new_signals'],0)
            self.assertEqual(server.scan_rss(1)['new_signals'],1)
    def test_live_baseline_and_diff_dedupe(self):
        p=server.new_competitor({'project_id':1,'name':'Test App','store_id':'12345','country':'US','store_url':'https://apps.apple.com/app/id12345'})
        old={'trackName':'Test App','version':'1.0','description':'Before','averageUserRating':4.2,'userRatingCount':10,'releaseNotes':'first','currentVersionReleaseDate':'2026-09-10'}
        new={**old,'version':'1.1','releaseNotes':'New feature'}
        with patch.object(server,'request_json',side_effect=[{'results':[old]},{'results':[new]},{'results':[new]}]),patch.object(server.time,'sleep'):
            self.assertEqual(server.live_scan(1)['new_signals'],0)
            self.assertEqual(server.live_scan(1)['new_signals'],2)
            self.assertEqual(server.live_scan(1)['new_signals'],0)

if __name__=='__main__': unittest.main()
