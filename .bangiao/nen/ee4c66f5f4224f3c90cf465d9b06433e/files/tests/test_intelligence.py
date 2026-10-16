import copy,datetime as dt,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import research_workspace as w
import market_intelligence as mi
import public_research as pr

class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.scope=w.scope_for('ASMR games')
        self.row=dict(kind='csv',id='42',name='ASMR Test',platform='iOS',geo='US',category='Games',relevance='relevant',period_start=self.scope['start'],period_end=self.scope['end'],downloads=145000,delta_pop=45000,revenue=1000,currency='USD',evidence_id='CSV:1:2',evidence_ids=['CSV:1:2'],sources={'pop':dict(import_id=1,line=2,filename='test.csv')},field_sources={})
        self.packet=dict(evidence=[self.row],signals=[],warnings=[],coverage={},gaps=[])
    def assess(self):return mi.enrich(self.packet,self.scope)
    def test_download_comparison_and_lineage(self):
        p=self.assess();m=p['comparisons'][0];self.assertEqual((m['before'],m['after'],m['percent']),(100000,145000,45));self.assertTrue(m['eligible']);self.assertEqual(m['evidence_ids'],['CSV:1:2'])
    def test_reviews_cannot_become_growth_or_market_trend(self):
        self.packet['evidence']=[];self.packet['signals']=[dict(id='review1',metric='review_count_delta',value=999999,app_id='42',evidence_ids=['STOREH:1'])]
        p=self.assess();a=mi.assessment(p,self.scope);self.assertFalse(a['app_growth']);self.assertFalse(a['comparison_count'])
        with self.assertRaisesRegex(ValueError,'review'):mi.enforce_ai(dict(trend=dict(status='rising',evidence_ids=['STOREH:1']),scale_candidates=[]),p)
    def test_ads_and_search_counts_never_promoted(self):
        self.packet['evidence']=[];self.packet['signals']=[dict(metric='ad_count',value=1000),dict(metric='search_result_count',value=100000)]
        self.assertFalse(self.assess()['comparisons'])
    def test_rank_and_interest_are_separate_from_growth(self):
        self.packet['comparisons']=[dict(id='rank1',eligible=True,metric='rank',provider='chart',platform='iOS',geo='US',unit='position',definition='free chart',before=100,after=10,delta=-90,app_id='42',evidence_ids=['WEB:1'])]
        a=mi.assessment(self.packet,self.scope);self.assertFalse(a['app_growth']);self.assertEqual(a['market_assessment'][1]['status'],'comparable')
        with self.assertRaises(ValueError):mi.enforce_ai(dict(trend=dict(status='rising',evidence_ids=['WEB:1']),scale_candidates=[]),self.packet)
    def test_unknown_topic_ineligible(self):
        self.row['relevance']='possible';m=self.assess()['comparisons'][0];self.assertFalse(m['eligible']);self.assertFalse(mi.assessment(self.packet,self.scope)['app_growth'])
    def test_exact_id_public_corroborates_topic_but_name_join_does_not(self):
        self.row['relevance']='possible';pub=dict(kind='public',store_id='43',name='ASMR Test',platform='iOS',country='US',relevance='relevant',evidence_id='STOREH:1')
        self.packet['evidence'].append(pub);self.assertFalse(self.assess()['comparisons'][0]['eligible']);pub['store_id']='42'
        self.assertFalse(self.assess()['comparisons'][0]['eligible'])
        self.row['store_id']='42';self.assertTrue(self.assess()['comparisons'][0]['eligible'])
    def test_wrong_period_no_comparison(self):
        self.row['period_end']='2020-01-01';self.assertFalse(self.assess()['comparisons'])
    def test_conflicting_csv_blocked(self):
        self.packet['warnings']=['Downloads không khớp: 42'];m=self.assess()['comparisons'][0];self.assertFalse(m['eligible'])
    def test_zero_base_no_infinite_percent(self):
        self.row['downloads']=45000;self.assertIsNone(self.assess()['comparisons'][0]['percent'])
    def test_negative_inferred_prior_disallowed(self):
        self.row['downloads']=100;self.assertFalse(self.assess()['comparisons'])
    def test_explicit_revenue_period_and_currency(self):
        old=dict(self.row,period_start=self.scope['comparison_start'],period_end=self.scope['comparison_end'],revenue=500,evidence_id='CSV:2:2',evidence_ids=['CSV:2:2']);self.packet['evidence'].append(old)
        metrics=self.assess()['comparisons'];revenue=next(m for m in metrics if m['metric']=='revenue');self.assertEqual(revenue['unit'],'USD');self.assertTrue(revenue['eligible'])
        old['currency']='EUR';self.assertFalse(next(m for m in self.assess()['comparisons'] if m['metric']=='revenue')['eligible'])
    def test_daily_chart_only_from_actual_daily_records(self):
        self.packet['evidence']=[dict(self.row,period_start=str(dt.date.fromisoformat(self.scope['start'])+dt.timedelta(days=i)),period_end=str(dt.date.fromisoformat(self.scope['start'])+dt.timedelta(days=i)),downloads=i+1) for i in (0,1,3,4)]
        p=self.assess();self.assertFalse(p['comparisons']);self.assertEqual(len(p['time_series'][0]['points']),4);self.assertEqual(p['time_series'][0]['granularity'],'day')
    def test_two_periods_stay_two_bars(self):
        self.assertFalse(self.assess()['time_series'])
    def test_ua_never_inferred_from_downloads(self):
        a=mi.assessment(self.assess(),self.scope);self.assertTrue(a['app_growth']);self.assertEqual(a['ua_assessment']['status'],'not_assessed')
    def test_ua_explicit_cohort_and_user_target_only(self):
        self.row.update(ua_spend=1000,ua_cpi=.5,retention_percent=35,roas_percent=120,cohort_window='D7',cohort_start=self.scope['start'],cohort_end=self.scope['end'],measurement_date=str(dt.date.fromisoformat(self.scope['end'])+dt.timedelta(days=7)))
        a=mi.assessment(self.assess(),self.scope);self.assertEqual(a['ua_assessment']['status'],'metrics_only')
        self.row['roas_target_percent']=130;a=mi.assessment(self.assess(),self.scope);self.assertEqual(a['ua_assessment']['metrics'][0]['status'],'below_target')
        self.row['roas_target_percent']=110;a=mi.assessment(self.assess(),self.scope);self.assertEqual(a['ua_assessment']['metrics'][0]['status'],'meets_target')
        self.row['measurement_date']=self.scope['end'];a=mi.assessment(self.assess(),self.scope);self.assertEqual(a['ua_assessment']['status'],'metrics_only')

class SourcesTests(unittest.TestCase):
    def fake_server(self):
        import threading,contextlib,types
        class C:
            def execute(self,*args):return self
            def fetchone(self):return ('awaiting_manual',)
        @contextlib.contextmanager
        def con():yield C()
        return types.SimpleNamespace(LOCK=threading.RLock(),con=con)
    def test_source_failure_keeps_verified_source(self):
        quote='This is a source excerpt long enough to verify the original article content.'
        sources=[dict(url='https://example.com/a',title='TEST',published_at='2026-01-01',quote=quote,origin_url='',source_kind='report',observations=[]),dict(url='https://example.com/b',quote=quote)]
        def fetch(url):
            if url.endswith('/b'):raise ValueError('Source blocked')
            return dict(text=quote,url=url,links=[])
        with patch.object(pr,'fetch_public',side_effect=fetch):results=pr.verify_sources(self.fake_server(),1,sources)
        self.assertEqual(results[0]['verification'],'verified');self.assertEqual(results[0]['published_at'],'');self.assertEqual(results[1]['verification'],'unverified')
    def test_quote_mismatch_never_verified(self):
        source=dict(url='https://example.com/a',quote='This exact claim is completely invented and cannot be found on the page.')
        with patch.object(pr,'fetch_public',return_value=dict(text='Actual page has different content',links=[])):
            results=pr.verify_sources(self.fake_server(),1,[source])
        self.assertEqual(results[0]['verification'],'unverified')
    def test_observation_numbers_scope_and_unit_checked(self):
        scope=w.scope_for('ASMR games');quote='ASMR Test US iOS downloads estimated downloads 100 200 '+ ' '.join(scope[k] for k in ('start','end','comparison_start','comparison_end'))
        obs=dict(metric='downloads',app_id='42',platform='iOS',geo='US',unit='estimated downloads',definition='downloads',before=100,after=200,**{k:scope[k] for k in ('comparison_start','comparison_end')},period_start=scope['start'],period_end=scope['end'])
        source=dict(url='https://example.com/a',quote=quote,observations=[obs])
        with patch.object(pr,'fetch_public',return_value=dict(text=quote,links=[])):
            results=pr.verify_sources(self.fake_server(),1,[source]);self.assertTrue(results[0]['observations'][0]['verified'])
            obs['after']=300;results=pr.verify_sources(self.fake_server(),1,[source]);self.assertFalse(results[0]['observations'][0]['verified'])
    def test_manual_numeric_shape_rejects_boolean(self):
        with self.assertRaises(ValueError):w.validate_shape(True,{'type':'number'})
    def test_canonical_removes_tracking_preserves_real_query(self):
        self.assertEqual(pr.canonical('https://example.com/report?a=1&utm_source=x#top'),'https://example.com/report?a=1')
    def test_non_public_url_blocked(self):
        for url in ('file:///tmp/a','http://example.com','https://a:b@example.com'):
            with self.assertRaises(ValueError):pr.canonical(url)
        with patch.object(pr.socket,'getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]):
            with self.assertRaises(ValueError):pr.check_public('https://example.com')
    def test_abbreviated_number_not_turned_into_million(self):
        self.assertFalse(pr.number_present(1000000,'one app has 1M downloads'))
    def test_web_prompt_contains_no_private_csv(self):
        prompt=pr.research_prompt('ASMR games',w.scope_for('ASMR games'),[dict(kind='csv',name='SECRET',downloads=999999),dict(kind='public',name='Public App',store_id='42')]);self.assertNotIn('SECRET',prompt);self.assertNotIn('999999',prompt)

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.original=(s.DATA,s.DBPATH);s.DATA=Path(self.tmp.name);s.DBPATH=s.DATA/'test.sqlite3';s.init()
        self.scope=w.scope_for('ASMR games')
    def tearDown(self):s.DATA,s.DBPATH=self.original;self.tmp.cleanup()
    def save(self,before=100,after=150,status='ready',legacy=False,pid=None):
        if not pid:pid=s.new_project(dict(name='ASMR growth',brief='ASMR games'))['id']
        row=dict(kind='csv',id='42',name='ASMR Game',platform='iOS',geo='US',category='Games',relevance='relevant',period_start=self.scope['start'],period_end=self.scope['end'],downloads=after,delta_pop=after-before,evidence_id='CSV:1:2',evidence_ids=['CSV:1:2'],sources={},field_sources={})
        packet=mi.enrich(dict(evidence=[row],signals=[],warnings=[],coverage={},gaps=[],sources=[]),self.scope)
        if legacy:packet.pop('schema_version')
        with s.con() as c:
            c.execute('INSERT INTO workspace_runs(research_id,question,mode,status,scope_json,packet_json,result_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(pid,'ASMR games','manual',status,json.dumps(self.scope),json.dumps(packet),json.dumps(dict(trend={'answer':'TEST'},data_at=s.now())),s.now(),s.now()))
            return pid,c.execute('SELECT last_insert_rowid()').fetchone()[0]
    def dashboard(self,**args):
        with s.con() as c:return mi.dashboard(c,args)
    def test_empty_dashboard_no_fabricated_metrics(self):
        d=self.dashboard();self.assertFalse(d['series']);self.assertEqual(d['summary']['comparable_findings'],0)
    def test_complete_periods_render_bars(self):
        self.save();d=self.dashboard();self.assertEqual(d['series'][0]['chart_type'],'bar');self.assertEqual(len(d['series'][0]['points']),2);self.assertEqual(d['growth_apps'][0]['name'],'ASMR Game')
    def test_duplicate_research_not_double_counted(self):
        self.save();self.save();d=self.dashboard();self.assertEqual(d['summary']['comparable_findings'],1);self.assertEqual(len(d['growth_apps']),1)
    def test_conflicting_research_not_ranked(self):
        self.save();self.save(after=160);d=self.dashboard();self.assertFalse(d['growth_apps']);self.assertTrue(any(a['kind']=='conflict' for a in d['attention']))
    def test_filters_do_not_mutate_results(self):
        self.save();d=self.dashboard(geo='JP');self.assertFalse(d['recent']);self.assertEqual(self.dashboard()['growth_apps'][0]['after'],150)
    def test_running_research_shows_previous_completed_version(self):
        pid,old=self.save();_,current=self.save(status='collecting',pid=pid);d=self.dashboard();self.assertEqual(d['summary']['running'],1);self.assertEqual(d['recent'][0]['run_id'],old);self.assertTrue(d['recent'][0]['using_previous'])
    def test_legacy_not_promoted(self):
        self.save(legacy=True);d=self.dashboard();self.assertFalse(d['series']);self.assertFalse(d['growth_apps']);self.assertTrue(d['recent'][0]['legacy'])

if __name__=='__main__':unittest.main()
