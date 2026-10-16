import unittest
import answer_engine as ae
import research_workspace as w
class AnswerTests(unittest.TestCase):
 def answer(self):
  return dict(schema_version='1.9.2',request_types=['ranking'],direct_answer='App A đáng benchmark.',sections=[dict(title='Ứng dụng',body='Danh sách ứng viên.',claim_ids=['c1'])],apps=[dict(name='App A',app_id='1',reason='Có listing.',evidence_ids=['E1'])],claims=[dict(id='c1',text='App A là app drama.',kind='listing',evidence_ids=['E1'],metric_ids=[],basis_claim_ids=[])],research_gaps=[],next_steps=[])
 def packet(self):return dict(evidence=[dict(evidence_id='E1',kind='public',relevance='possible',name='App A',store_id='1')],comparisons=[])
 def test_listing_without_growth(self):self.assertEqual(w.validate(self.answer(),self.packet())['apps'][0]['name'],'App A')
 def test_false_ranking_rejected(self):
  a=self.answer();a['claims'][0]['kind']='ranking'
  with self.assertRaises(ValueError):w.validate(a,self.packet())
 def test_false_growth_rejected(self):
  a=self.answer();a['claims'][0]['kind']='growth'
  with self.assertRaises(ValueError):w.validate(a,self.packet())
 def test_unverified_web_rejected(self):
  p=self.packet();p['evidence'][0].update(kind='web',verification='unverified')
  with self.assertRaises(ValueError):w.validate(self.answer(),p)
 def test_title_and_intent(self):
  q='Top các app drama trên thị trường';self.assertEqual(w.title_for(w.scope_for(q),q),q);self.assertEqual(w.scope_for(q)['topic'],'short drama');self.assertNotIn('growth',ae.intents(q))
 def test_interpretation_requires_basis(self):
  a=self.answer();a['claims'][0]['kind']='interpretation'
  with self.assertRaises(ValueError):w.validate(a,self.packet())
 def test_pop_yoy_and_worldwide(self):
  import market_intelligence as mi
  scope=w.scope_for('ASMR games',overrides=dict(geo='Worldwide',platforms=['Unified'],start='2026-09-14',end='2026-10-13'))
  verified_packet=None
  for geo in ('Worldwide','WORLDWIDE','worldwide'):
   with self.subTest(geo=geo):
    row=dict(id='1',store_id='1',name='ASMR',description='ASMR game for relaxation',category='Games',platform='Unified',geo=geo,period_start=scope['start'],period_end=scope['end'],downloads=145000,delta_pop=45000,delta_yoy=95000)
    status,reasons=w.relevance(row,scope,True)
    self.assertEqual(status,'relevant',reasons)
    e=dict(kind='csv',**row,relevance=status,evidence_id='E1')
    packet=mi.enrich(dict(evidence=[e],signals=[],warnings=[],coverage={},gaps=[]),scope)
    comparisons=packet['comparisons']
    self.assertEqual([(m['before'],m['after']) for m in comparisons],[(100000,145000),(50000,145000)])
    self.assertEqual((comparisons[0]['comparison_start'],comparisons[0]['comparison_end']),('2026-08-15','2026-09-13'))
    self.assertEqual((comparisons[1]['comparison_start'],comparisons[1]['comparison_end']),('2025-09-14','2025-10-13'))
    self.assertTrue(all(m['eligible'] and m['geo']==geo and m['platform']=='Unified' for m in comparisons))
    self.assertEqual((e['geo'],e['platform'],e['period_start'],e['period_end']),(geo,'Unified',scope['start'],scope['end']))
    self.assertEqual(packet['schema_version'],mi.VERSION)
    verified_packet=packet
  evidence=verified_packet['evidence'][0];metric_ids=[m['id'] for m in verified_packet['comparisons']]
  growth=self.answer();growth['request_types']=['growth'];growth['direct_answer']='ASMR có ước tính downloads tăng trong kỳ.'
  growth['apps']=[dict(name='ASMR',app_id='1',reason='Mô tả xác nhận ASMR.',evidence_ids=[evidence['evidence_id']])]
  growth['claims']=[dict(id='c1',text='Downloads tăng theo hai phép so sánh đã khai báo.',kind='growth',evidence_ids=[evidence['evidence_id']],metric_ids=metric_ids,basis_claim_ids=[])]
  growth['sections'][0]['body']='Các kỳ so sánh được khai báo trong CSV.'
  accepted=w.validate(growth,verified_packet)
  self.assertEqual(accepted['claims'][0]['metric_ids'],metric_ids)
  self.assertTrue(all(m['unit']=='estimated downloads' for m in verified_packet['comparisons']))
  self.assertEqual(verified_packet['schema_version'],mi.VERSION)
 def test_growth_validation_requires_real_metric_and_evidence_ids(self):
  import market_intelligence as mi
  scope=dict(geo='US',platforms=['iOS'],start='2026-09-14',end='2026-10-13',comparison_start='2026-08-15',comparison_end='2026-09-13')
  row=dict(evidence_id='E1',evidence_ids=['E1'],kind='csv',relevance='relevant',id='1',store_id='1',name='App A',platform='iOS',geo='US',period_start=scope['start'],period_end=scope['end'],downloads=150,delta_pop=50)
  enriched=mi.enrich(dict(evidence=[row],warnings=[],signals=[],coverage={},gaps=[]),scope)
  metric=enriched['comparisons'][0]
  self.assertTrue(metric['eligible'])
  packet=dict(evidence=enriched['evidence'],comparisons=enriched['comparisons'])
  answer=self.answer();answer['request_types']=['growth'];answer['claims'][0].update(kind='growth',evidence_ids=['E1'],metric_ids=[metric['id']])
  self.assertEqual(w.validate(answer,packet)['claims'][0]['metric_ids'],[metric['id']])
  answer['claims'][0]['metric_ids']=['METRIC:invented']
  with self.assertRaises(ValueError):w.validate(answer,packet)
  answer['claims'][0]['metric_ids']=[metric['id']];answer['claims'][0]['evidence_ids']=['CSV:999:99']
  with self.assertRaises(ValueError):w.validate(answer,packet)
 def test_discovery_preview_does_not_force_trend(self):
  a=w.preliminary(dict(question='Top app drama'),{})
  self.assertNotIn('trend',a);self.assertEqual(a['schema_version'],'1.9.2')
if __name__=='__main__':unittest.main()
