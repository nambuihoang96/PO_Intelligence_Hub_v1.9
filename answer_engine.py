"""Question-led answers; legacy growth reports remain readable."""
import re

VERSION = '1.9.2'
def intents(question):
    q=question.casefold()
    rules={'ranking':r'\btop\b|xếp hạng|hàng đầu','comparison':r'so sánh|compare|versus|\bvs\b','benchmark':r'benchmark|học hỏi','growth':r'tăng trưởng|growth|trending|xu hướng|scale','ua':r'\bua\b|roas|cpi|payback','opportunity':r'cơ hội|opportunit'}
    return [k for k,p in rules.items() if re.search(p,q)] or ['discovery']

def obj(properties):
    return dict(type='object',additionalProperties=False,properties=properties,required=list(properties))
S={'type':'string'}
def arr(item):return dict(type='array',items=item)
IDS=arr(S)
CLAIM=obj(dict(id=S,text=S,kind=dict(type='string',enum=['listing','ranking','growth','ua','interpretation','recommendation']),evidence_ids=IDS,metric_ids=IDS,basis_claim_ids=IDS))
APP=obj(dict(name=S,app_id=S,reason=S,evidence_ids=IDS))
SECTION=obj(dict(title=S,body=S,claim_ids=IDS))
SCHEMA=obj(dict(schema_version=dict(type='string',enum=[VERSION]),request_types=IDS,direct_answer=S,sections=arr(SECTION),apps=arr(APP),claims=arr(CLAIM),research_gaps=IDS,next_steps=arr(obj(dict(title=S,reason=S,evidence_ids=IDS)))))

def validate(result,packet,shape):
    shape(result,SCHEMA)
    if packet.get('request_types') and set(result['request_types'])!=set(packet['request_types']):raise ValueError('Loại yêu cầu phải bám câu hỏi gốc')
    evidence={}
    for e in packet.get('evidence',[]):
        if e.get('relevance')=='unrelated':continue
        if e.get('kind')=='web' and e.get('verification')!='verified':continue
        for eid in [e.get('evidence_id')]+e.get('evidence_ids',[]):
            if eid:evidence[eid]=e
    metrics={m['id']:m for m in packet.get('comparisons',[]) if m.get('eligible')}
    claims={c['id']:c for c in result['claims']}
    if len(claims)!=len(result['claims']):raise ValueError('Claim ID trùng')
    for claim in result['claims']:
        if any(i not in evidence for i in claim['evidence_ids']):raise ValueError('Claim dùng evidence chưa xác minh hoặc không tồn tại')
        if any(i not in claims or i==claim['id'] for i in claim['basis_claim_ids']):raise ValueError('Căn cứ claim không hợp lệ')
        if claim['kind'] not in ('recommendation','interpretation') and not claim['evidence_ids']:raise ValueError('Claim thực tế cần nguồn')
        if claim['kind']=='interpretation' and not claim['basis_claim_ids']:raise ValueError('Nhận xét cần claim làm căn cứ')
        if claim['kind']=='ranking' and not any(evidence[i].get('kind')=='web' and evidence[i].get('source_kind') in ('ranking','chart','report') for i in claim['evidence_ids']):raise ValueError('Ranking cần nguồn ranking/chart/report đã xác minh')
        if claim['kind']=='growth':
            if not claim['metric_ids'] or any(i not in metrics or metrics[i]['metric'] not in ('downloads','revenue') for i in claim['metric_ids']):raise ValueError('Growth cần metric so sánh downloads/revenue')
        if claim['kind']=='ua':
            rows=[evidence[i] for i in claim['evidence_ids']]
            qualified=[e for e in rows if e.get('cohort_window') and all(isinstance(e.get(k),(int,float)) for k in ('ua_spend','ua_cpi','retention_percent','roas_percent'))]
            if not qualified:raise ValueError('UA cần spend/CPI/retention/ROAS và cohort có nguồn')
            if re.search(r'có lãi|profitable|hiệu quả|scale tốt',claim['text'],re.I) and not any(e.get('roas_target_percent') is not None for e in qualified):raise ValueError('Kết luận hiệu quả UA cần mục tiêu do PO khai báo')
    for section in result['sections']:
        if any(i not in claims for i in section['claim_ids']):raise ValueError('Section tham chiếu claim không tồn tại')
    for app in result['apps']:
        if not app['evidence_ids'] or any(i not in evidence for i in app['evidence_ids']):raise ValueError('App cần nguồn đã xác minh')
        sources=[evidence[i] for i in app['evidence_ids']]
        identity=any((str(e.get('store_id') or e.get('id'))==str(app['app_id']) and e.get('name','').casefold()==app['name'].casefold()) or (e.get('kind')=='web' and app['name'].casefold() in e.get('quote','').casefold()) for e in sources)
        if not identity:raise ValueError('App không khớp định danh hoặc tên trong nguồn trích dẫn')
    for step in result['next_steps']:
        if any(i not in evidence for i in step['evidence_ids']):raise ValueError('Action có nguồn không tồn tại')
    if not result['direct_answer'].strip():raise ValueError('Thiếu câu trả lời trực tiếp')
    return result
