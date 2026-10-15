"""Market workflows, no paid API and no LLM calls. AI handoff is explicit."""
import json
import re

# Candidate URLs are proposals, NOT confirmed working feeds or publisher partnerships.
CATALOG = [
  dict(id='apple_catalog',name='Apple App Store catalog',type='store',url='https://apps.apple.com/',method='integrated',segments=['all'],note='Public catalog metadata; not downloads/revenue.'),
  dict(id='google_play',name='Google Play listings',type='store',url='https://play.google.com/store/apps',method='optional_connector',segments=['all'],note='Unofficial optional connector; observe site terms and failure rates.'),
  dict(id='trends_us',name='Google Trends Trending US',type='rss',url='https://trends.google.com/trending/rss?geo=US',method='rss',segments=['all'],note='General trending searches, not app demand or downloads.'),
  dict(id='trends_jp',name='Google Trends Trending JP',type='rss',url='https://trends.google.com/trending/rss?geo=JP',method='rss',segments=['all'],note='General trending searches, not app demand or downloads.'),
  dict(id='techcrunch_apps',name='TechCrunch Apps',type='rss',url='https://techcrunch.com/category/apps/feed/',method='rss',segments=['all','app','ai'],note='Editorial coverage; potential low relevance for narrow app categories.'),
  dict(id='pocketgamer',name='PocketGamer.biz',type='rss',url='https://www.pocketgamer.biz/rss/',method='rss',segments=['game'],note='Candidate feed: URL and accessibility require validation.'),
  dict(id='gamesindustry',name='GamesIndustry.biz',type='rss',url='https://www.gamesindustry.biz/feed',method='rss',segments=['game'],note='Candidate feed: URL and accessibility require validation.'),
  dict(id='mobiledevmemo',name='Mobile Dev Memo',type='rss',url='https://mobiledevmemo.com/feed/',method='rss',segments=['game','app'],note='Candidate feed: URL and accessibility require validation.'),
  dict(id='meta_library',name='Meta Ad Library',type='manual',url='https://www.facebook.com/ads/library/',method='manual',segments=['all'],note='Creative research manually; ordinary commercial ads are not a free general-purpose API.'),
  dict(id='google_ads',name='Google Ads Transparency Center',type='manual',url='https://adstransparency.google.com/',method='manual',segments=['all'],note='Public research manually; not ad spend/ROAS.'),
]

def suggest_source_candidates(project,profile,existing_urls=()):
  label=(project.get('name','')+' '+project.get('category','')+' '+str(profile.get('subcategory',''))).lower()
  game=any(w in label for w in ('game','puzzle','casual','rpg','arcade','idle'))
  ai=any(w in label for w in ('photo','ai ','image','headshot','editor'))
  seg='game' if game else 'ai' if ai else 'app'
  geo=set(profile.get('geos') or project.get('geo','US').split(','))
  existing=set(existing_urls)
  results=[]
  for item in CATALOG:
    if item['id']=='trends_us' and 'US' not in geo:continue
    if item['id']=='trends_jp' and 'JP' not in geo:continue
    relevance='high' if seg in item['segments'] else ('medium' if 'all' in item['segments'] else 'low')
    if relevance=='low':continue
    row={**item,'relevance':relevance,'already_added':item['url'] in existing,
      'status':'already_added' if item['url'] in existing else 'candidate_unverified'}
    results.append(row)
  results.sort(key=lambda s:(s['relevance']!='high',s['type']=='manual',s['name']))
  return results

def source_research_packet(project,candidates):
  safe=[{k:v for k,v in c.items() if k in ('id','name','type','url','method','relevance','note')} for c in candidates]
  return '''Bạn là Source Discovery Analyst. CHỈ chọn trong candidate list đã cấp; không tạo URL mới.
Đánh giá nguồn phù hợp với project, khả năng truy cập hợp lệ và những khoảng trống nghiên cứu.
Không coi RSS headline là install trend; không suy ra ad spend, ROAS, revenue.
Nguồn có status candidate_unverified chưa xác minh hoạt động. Không tự bật source.
Project: '''+json.dumps({'name':project.get('name'),'category':project.get('category'),'geo':project.get('geo'),'brief':project.get('brief')},ensure_ascii=False)+'''\nCandidates: '''+json.dumps(safe,ensure_ascii=False)+'''\nTrả về JSON duy nhất: {"recommended_ids":["candidate_id"],"rationale":"...","gaps":["..."]}.'''

def validate_source_import(raw,candidates):
  data=json.loads(raw) if isinstance(raw,str) else raw
  if not isinstance(data,dict) or not isinstance(data.get('recommended_ids'),list):raise ValueError('AI Source Discovery phải trả về recommended_ids dạng array')
  allowed={c['id'] for c in candidates}
  ids=data['recommended_ids']
  if len(ids)>len(allowed) or any(not isinstance(i,str) or i not in allowed for i in ids):raise ValueError('AI trả về source ID không có trong catalog')
  if len(set(ids))!=len(ids):raise ValueError('Source ID bị trùng')
  return {'recommended_ids':ids,'rationale':str(data.get('rationale',''))[:1800], 'gaps':[str(x)[:250] for x in data.get('gaps',[]) if isinstance(x,str)][:10]}

def investigation_packet(action,project,report):
  allowed_urls={x.get('url') for x in report.get('top_competitors',[]) if x.get('url')}
  allowed_urls|={x.get('url') for x in report.get('market_news',[]) if x.get('url')}
  evidence=[e for e in json.loads(action.get('evidence_json','[]')) if e.get('url') in allowed_urls]
  compact={
    'action_id':action['id'],'project':{'name':project['name'],'category':project['category'],'geo':project['geo']},
    'research_goal':project.get('brief',''),
    'question':action['title'],'reason':action['description'],
    'evidence':evidence[:10],
    'comparison':[{'name':x.get('name'),'platform':x.get('platform'),'url':x.get('url'),'tags':x.get('tags'),'summary':x.get('summary')} for x in report.get('top_competitors',[])[:14]],
    'coverage':report.get('coverage'), 'limitations':report.get('limitations',[])[:12],
    'market_news':report.get('market_news',[])[:8],
    'dataset_evidence':report.get('dataset_evidence',[])[:35],
    'market_findings':report.get('market_findings',[])[:20],
  }
  return '''Bạn là Product Intelligence Analyst. Đây là yêu cầu Deep Investigation, không phải research trên danh sách keyword.
Chỉ dựa vào evidence packet. Phân biệt FACT / INFERENCE / HYPOTHESIS. Không tự bịa số liệu, rating, revenue hoặc source URL.
Nếu thiếu in-app walkthrough/reviews, đề xuất bước thu thập, KHÔNG kết luận feature adoption.
Trả về JSON theo schema: {"action_id":number,"executive_summary":string,"findings":[{"claim":string,"type":"fact|inference|hypothesis","confidence":"low|medium|high","evidence_urls":[string]}],"next_steps":[{"title":string,"priority":"low|medium|high","validation_step":string}],"opportunity_drafts":[{"title":string,"user_problem":string,"hypothesis":string,"confidence":"low|medium|high","impact":"unknown|low|medium|high","validation_step":string,"evidence_urls":[string]}],"missing_evidence":[string],"limitations":[string]}.
Chỉ điền opportunity_drafts khi có evidence URL hợp lệ và giả thuyết người dùng rõ ràng; nếu không, trả về [] thay vì bịa cơ hội. Đây luôn là NHÁP và cần PO duyệt, không tự coi là validated.
Bộ evidence URL cho phép chỉ gồm URL trong packet, mọi FACT phải có URL bằng chứng. Không tự truy cập web hoặc filesystem.
Packet: '''+json.dumps(compact,ensure_ascii=False)

def validate_investigation(raw,action_id,allowed_urls):
  r=json.loads(raw) if isinstance(raw,str) else raw
  if not isinstance(r,dict) or r.get('action_id')!=action_id:raise ValueError('action_id không khớp')
  if not isinstance(r.get('executive_summary'),str) or not r['executive_summary'].strip():raise ValueError('Thiếu executive_summary')
  fields=('findings','next_steps','missing_evidence','limitations')
  if any(not isinstance(r.get(f),list) for f in fields):raise ValueError('Thiếu danh sách findings/next_steps/missing_evidence/limitations')
  if len(r['findings'])>20 or len(r['next_steps'])>12:raise ValueError('Quá nhiều findings/next_steps')
  for finding in r['findings']:
    if not isinstance(finding,dict) or finding.get('type') not in ('fact','inference','hypothesis') or finding.get('confidence') not in ('low','medium','high') or not isinstance(finding.get('claim'),str) or not isinstance(finding.get('evidence_urls'),list):raise ValueError('Finding không hợp lệ')
    if not all(isinstance(url,str) and url in allowed_urls for url in finding['evidence_urls']):raise ValueError('Evidence URL chưa có trong dữ liệu nguồn')
    if finding['type']=='fact' and not finding['evidence_urls']:raise ValueError('FACT phải có evidence URL')
  for step in r['next_steps']:
    if not isinstance(step,dict) or step.get('priority') not in ('high','medium','low') or not all(isinstance(step.get(k),str) and step[k].strip() for k in ('title','validation_step')):raise ValueError('Next step không hợp lệ')
  drafts=r.get('opportunity_drafts',[])
  if not isinstance(drafts,list) or len(drafts)>8:raise ValueError('opportunity_drafts không hợp lệ')
  for idea in drafts:
    if not isinstance(idea,dict) or not all(isinstance(idea.get(k),str) and idea[k].strip() for k in ('title','user_problem','hypothesis','validation_step')):
      raise ValueError('Opportunity AI thiếu user problem, giả thuyết hoặc validation step')
    if idea.get('confidence') not in ('low','medium','high') or idea.get('impact') not in ('unknown','low','medium','high'):
      raise ValueError('Opportunity AI có confidence/impact không hợp lệ')
    urls=idea.get('evidence_urls')
    if not isinstance(urls,list) or not urls or any(url not in allowed_urls for url in urls):
      raise ValueError('Opportunity AI phải tham chiếu evidence URL có trong packet')
  for field in ('limitations','missing_evidence'):
    if not all(isinstance(x,str) for x in r[field]):raise ValueError(field+' phải gồm chuỗi')
  return r
