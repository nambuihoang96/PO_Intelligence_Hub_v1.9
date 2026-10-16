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

    def fixed_scope(self):
        return dict(geo='US',platforms=['iOS'],start='2026-09-14',end='2026-10-13',
                    comparison_start='2026-08-15',comparison_end='2026-09-13')

    def test_pop_yoy_formulas_identity_and_zero_baseline(self):
        scope=self.fixed_scope()
        pop=mi.compare('downloads','42','ASMR Test','iOS','US',scope,100000,145000,['CSV:P'],'CSV user export')
        yoy_scope=dict(scope,comparison_start='2025-09-14',comparison_end='2025-10-13')
        yoy=mi.compare('downloads','42','ASMR Test','iOS','US',yoy_scope,50000,145000,['CSV:Y'],'CSV user export',definition='downloads_yoy')
        self.assertEqual((pop['before'],pop['after'],pop['delta'],pop['percent']), (100000,145000,45000,45))
        self.assertEqual((pop['comparison_start'],pop['comparison_end']), ('2026-08-15','2026-09-13'))
        self.assertEqual((yoy['before'],yoy['delta'],yoy['percent']), (50000,95000,190))
        self.assertEqual((yoy['comparison_start'],yoy['comparison_end']), ('2025-09-14','2025-10-13'))
        self.assertNotEqual(pop['id'],yoy['id'])
        self.assertEqual((pop['unit'],pop['classification']), ('estimated downloads','observed_estimate'))
        down=mi.compare('downloads','42','ASMR Test','iOS','US',scope,100000,80000,['CSV:D'],'CSV user export')
        self.assertEqual((down['delta'],down['percent'],down['direction']), (-20000,-20,'down'))
        zero=mi.compare('downloads','42','ASMR Test','iOS','US',scope,0,1000,['CSV:Z'],'CSV user export')
        self.assertIsNone(zero['percent']);self.assertTrue(zero['zero_base'])

    def test_metric_identity_uses_comparison_period_and_unit(self):
        scope=self.fixed_scope()
        base=mi.compare('revenue','42','ASMR Test','iOS','US',scope,10,20,['E2','E1'],'CSV user export',unit='USD')
        other_period=dict(scope,comparison_start='2025-09-14',comparison_end='2025-10-13')
        other=mi.compare('revenue','42','ASMR Test','iOS','US',other_period,10,20,['E1','E2'],'CSV user export',unit='USD')
        other_unit=mi.compare('revenue','42','ASMR Test','iOS','US',scope,10,20,['E1','E2'],'CSV user export',unit='EUR')
        reordered=mi.compare('revenue','42','ASMR Test','iOS','US',scope,10,20,['E1','E2'],'CSV user export',unit='USD')
        self.assertNotEqual(base['id'],other['id']);self.assertNotEqual(base['id'],other_unit['id'])
        self.assertEqual(base['id'],reordered['id'])

    def test_invalid_numeric_levels_are_rejected(self):
        scope=self.fixed_scope()
        for value in (-1,True,float('nan'),float('inf')):
            with self.subTest(value=value):
                self.assertIsNone(mi.compare('downloads','42','ASMR','iOS','US',scope,100,value,['E'],'CSV user export'))

    def test_comparison_dedup_conflict_is_sticky_and_unions_real_refs(self):
        scope=self.fixed_scope()
        def row(value,eid):
            return dict(kind='csv',id='42',name='ASMR Test',platform='iOS',geo='US',relevance='relevant',
                        period_start=scope['start'],period_end=scope['end'],downloads=value,delta_pop=45000,
                        evidence_id=eid,evidence_ids=[eid],sources={},field_sources={})
        a,b,c=row(145000,'CSV:A'),row(146000,'CSV:B'),row(146000,'CSV:C')
        for rows in ([a,b,c],[a,b,a,a],[c,b,a,a],[a,c,b]):
            with self.subTest(order=[r['evidence_id'] for r in rows]):
                packet=mi.enrich(dict(evidence=[dict(r) for r in rows],warnings=[],signals=[],coverage={},gaps=[]),scope)
                metric=next(m for m in packet['comparisons'] if m['metric']=='downloads')
                self.assertFalse(metric['eligible'])
                self.assertEqual(set(metric['evidence_ids']),{r['evidence_id'] for r in rows})

    def test_daily_series_validates_dates_and_does_not_reuse_yoy_state(self):
        scope=self.fixed_scope()
        days=['2026-09-14','2026-09-16','2026-09-20','2026-10-13']
        rows=[dict(kind='csv',id='42',name='ASMR Test',platform='iOS',geo='US',relevance='relevant',
                   period_start=day,period_end=day,downloads=i+1,delta_yoy=777,evidence_id=f'CSV:{i}',
                   evidence_ids=[f'CSV:{i}'],sources={},field_sources={}) for i,day in enumerate(days)]
        packet=mi.enrich(dict(evidence=rows,warnings=[],signals=[],coverage={},gaps=[]),scope)
        self.assertFalse(packet['comparisons'])
        self.assertEqual([p['date'] for p in packet['time_series'][0]['points']],days)
        self.assertEqual(len(mi.enrich(dict(evidence=rows[:3],warnings=[],signals=[],coverage={},gaps=[]),scope)['time_series']),0)
        malformed=dict(rows[-1],period_start='2026-09-31',period_end='2026-09-31')
        malformed_packet=mi.enrich(dict(evidence=[*rows[:3],malformed],warnings=[],signals=[],coverage={},gaps=[]),scope)
        self.assertFalse(malformed_packet['time_series'])

    def test_daily_revenue_requires_known_single_currency(self):
        scope=self.fixed_scope();rows=[]
        for i in range(4):
            rows.append(dict(kind='csv',id='42',name='ASMR',platform='iOS',geo='US',relevance='relevant',
                period_start=f'2026-09-{14+i:02d}',period_end=f'2026-09-{14+i:02d}',revenue=10,currency=('USD','EUR',None,'')[i],
                evidence_id=f'CSV:{i}',evidence_ids=[f'CSV:{i}']))
        packet=mi.enrich(dict(evidence=rows,warnings=[],signals=[],coverage={},gaps=[]),scope)
        self.assertFalse(any(s['metric']=='revenue' for s in packet['time_series']))

    def test_assessment_keeps_distinct_comparison_periods(self):
        scope=self.fixed_scope()
        first=mi.compare('downloads','42','ASMR','iOS','US',scope,100,150,['E1'],'CSV user export')
        second=mi.compare('downloads','43','Other','iOS','US',dict(scope,comparison_start='2025-09-14',comparison_end='2025-10-13'),100,150,['E2'],'CSV user export')
        report=mi.assessment(dict(comparisons=[first,second]),scope)
        groups=next(axis for axis in report['market_assessment'] if axis['dimension']=='downloads')['groups']
        self.assertEqual(len(groups),2)

    def test_explicit_baseline_requires_relevance_consistency_and_currency(self):
        scope=self.fixed_scope()
        current=dict(self.row,period_start=scope['start'],period_end=scope['end'],revenue=1000,currency='USD')
        old=dict(self.row,id='42',period_start=scope['comparison_start'],period_end=scope['comparison_end'],downloads=100000,revenue=500,currency='USD',evidence_id='CSV:old',evidence_ids=['CSV:old'])
        old['relevance']='possible'
        packet=mi.enrich(dict(evidence=[current,old],warnings=[],signals=[],coverage={},gaps=[]),scope)
        revenue=next(m for m in packet['comparisons'] if m['metric']=='revenue')
        self.assertFalse(revenue['eligible'])
        old['relevance']='relevant';old['currency']=None
        packet=mi.enrich(dict(evidence=[current,old],warnings=[],signals=[],coverage={},gaps=[]),scope)
        revenue=next(m for m in packet['comparisons'] if m['metric']=='revenue')
        self.assertFalse(revenue['eligible'])
        downloads=next(m for m in packet['comparisons'] if m['metric']=='downloads')
        self.assertTrue(downloads['eligible'])

    def test_conflicting_duplicate_baseline_and_pop_delta_do_not_double_count(self):
        scope=self.fixed_scope()
        current=dict(self.row,period_start=scope['start'],period_end=scope['end'],downloads=145000,delta_pop=45000)
        old=dict(self.row,id='42',period_start=scope['comparison_start'],period_end=scope['comparison_end'],downloads=100000,evidence_id='CSV:old1',evidence_ids=['CSV:old1'])
        old2=dict(old,downloads=99999,evidence_id='CSV:old2',evidence_ids=['CSV:old2'])
        packet=mi.enrich(dict(evidence=[current,old,old2],warnings=[],signals=[],coverage={},gaps=[]),scope)
        downloads=[m for m in packet['comparisons'] if m['metric']=='downloads']
        self.assertEqual(len(downloads),1)
        self.assertFalse(downloads[0]['eligible'])

    def test_duplicate_daily_date_unions_refs_or_rejects_conflict_across_names(self):
        scope=self.fixed_scope()
        dates=['2026-09-14','2026-09-16','2026-09-20','2026-10-13']
        rows=[dict(kind='csv',id='42',name='ASMR',platform='iOS',geo='US',relevance='relevant',period_start=d,period_end=d,downloads=i+10,evidence_id=f'E{i}',evidence_ids=[f'E{i}']) for i,d in enumerate(dates)]
        duplicate=dict(rows[1],name='Renamed listing',evidence_id='E-extra',evidence_ids=['E-extra'])
        packet=mi.enrich(dict(evidence=rows+[duplicate],warnings=[],signals=[],coverage={},gaps=[]),scope)
        series=next(s for s in packet['time_series'] if s['metric']=='downloads')
        point=next(p for p in series['points'] if p['date']==dates[1])
        self.assertEqual(set(point['evidence_ids']),{'E1','E-extra'})
        conflicting=dict(duplicate,downloads=999)
        packet=mi.enrich(dict(evidence=rows+[conflicting],warnings=[],signals=[],coverage={},gaps=[]),scope)
        self.assertFalse(packet['time_series'])

    def test_comparison_never_invents_lineage_and_preserves_import_evidence(self):
        scope=self.fixed_scope()
        row=dict(kind='csv',id='42',name='ASMR',platform='iOS',geo='US',relevance='relevant',period_start=scope['start'],period_end=scope['end'],downloads=145000,delta_pop=45000,evidence_id='E-real',evidence_ids=['E-real'],field_sources={'delta_pop':dict(import_id=77,line=4)},sources={})
        evidence_before=copy.deepcopy([row])
        packet=mi.enrich(dict(evidence=[row],warnings=[],signals=[],coverage={},gaps=[]),scope)
        self.assertEqual(packet['comparisons'][0]['evidence_ids'],['E-real'])
        self.assertEqual(packet['evidence'],evidence_before)

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
