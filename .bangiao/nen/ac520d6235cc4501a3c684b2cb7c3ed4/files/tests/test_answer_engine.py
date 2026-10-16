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
  for geo in ('Worldwide','WORLDWIDE','worldwide'):
   with self.subTest(geo=geo):
    row=dict(id='1',name='ASMR',description='ASMR game for relaxation',category='Games',platform='Unified',geo=geo,period_start=scope['start'],period_end=scope['end'],downloads=145000,delta_pop=45000,delta_yoy=95000)
    status,reasons=w.relevance(row,scope,True)
    self.assertEqual(status,'relevant',reasons)
    e=dict(kind='csv',**row,relevance=status,evidence_id='E1')
    packet=mi.enrich(dict(evidence=[e],signals=[],warnings=[],coverage={},gaps=[]),scope)
    self.assertEqual([(m['before'],m['after']) for m in packet['comparisons']],[(100000,145000),(50000,145000)])
    self.assertEqual(packet['comparisons'][1]['comparison_start'],'2025-09-14')
    self.assertEqual((e['geo'],e['platform'],e['period_start'],e['period_end']),(geo,'Unified',scope['start'],scope['end']))
 def test_discovery_preview_does_not_force_trend(self):
  a=w.preliminary(dict(question='Top app drama'),{})
  self.assertNotIn('trend',a);self.assertEqual(a['schema_version'],'1.9.2')
if __name__=='__main__':unittest.main()
