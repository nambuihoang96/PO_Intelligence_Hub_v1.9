"""Typed, deterministic evidence eligibility and a read-only dashboard projection."""
import datetime as dt
import hashlib
import json
import math
from collections import defaultdict

VERSION='1.9.1'
DIMENSIONS=('search_interest','rank','downloads','revenue')
UNITS={'downloads':'estimated downloads','revenue':'USD','rank':'position','search_interest':'index'}

def init(c):
    c.executescript('''CREATE TABLE IF NOT EXISTS intelligence_versions(version TEXT PRIMARY KEY, installed_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS intelligence_web_evidence(
      evidence_id TEXT PRIMARY KEY,run_id INTEGER NOT NULL REFERENCES workspace_runs(id),payload TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS intelligence_web_run ON intelligence_web_evidence(run_id);
    INSERT OR IGNORE INTO intelligence_versions VALUES('1.9.1',strftime('%Y-%m-%dT%H:%M:%SZ','now'));''')

def number(x):
    if isinstance(x,bool):return None
    try:
        v=float(x);return v if math.isfinite(v) else None
    except (TypeError,ValueError,OverflowError):return None

def _geo_key(value):return str(value or '').casefold()

def _iso_date(value):
    if not isinstance(value,str):return None
    try:
        parsed=dt.date.fromisoformat(value)
        return parsed if parsed.isoformat()==value else None
    except (TypeError,ValueError):return None

def key(scope):return (scope.get('start'),scope.get('end'),scope.get('comparison_start'),scope.get('comparison_end'))

def metric_id(parts):return 'METRIC:'+hashlib.sha256(json.dumps(parts,sort_keys=True,default=str).encode()).hexdigest()[:18]

def compare(metric,app,name,platform,geo,scope,before,after,ids,provider,definition=None,eligible=True,reason='',unit=None):
    before,after=number(before),number(after)
    if before is None or after is None or before<0 or after<0:return None
    try:delta=after-before
    except OverflowError:return None
    if not math.isfinite(delta):return None
    direction='up' if delta>0 else 'down' if delta<0 else 'flat'
    definition=definition or metric;unit=unit or UNITS[metric]
    percent=None
    if before:
        try:percent=delta/before*100
        except (OverflowError,ZeroDivisionError):percent=None
        if percent is None or not math.isfinite(percent):return None
    identity=[metric,str(app),platform,_geo_key(geo),scope.get('start'),scope.get('end'),scope.get('comparison_start'),scope.get('comparison_end'),provider,definition,unit]
    return dict(id=metric_id(identity),metric=metric,app_id=str(app),name=name,
      platform=platform,geo=geo,period_start=scope['start'],period_end=scope['end'],comparison_start=scope['comparison_start'],comparison_end=scope['comparison_end'],
      before=before,after=after,delta=delta,percent=percent,zero_base=before==0,direction=direction,
      unit=unit,definition=definition,provider=provider,evidence_ids=list(dict.fromkeys(ids)),
      eligible=bool(eligible),exclusion_reason=reason,classification='observed_estimate' if metric in ('downloads','revenue') and provider=='CSV user export' else 'reported_by_source',
      supports='app_growth' if metric in ('downloads','revenue') else 'visibility' if metric=='rank' else 'search_interest',ua_status='not_assessed')

def enrich(packet,scope):
    """Never promote reviews, search result counts or ad counts into growth metrics."""
    evidence=packet.get('evidence',[]);comparisons=[];warnings=list(packet.get('warnings',[]))
    packet.setdefault('coverage',{}).update(total=len(evidence),assessed=len(evidence),not_assessed=0,
      **{kind:sum(e.get('relevance')==kind for e in evidence) for kind in ('relevant','possible','unrelated')})
    geo_equal=lambda left,right:_geo_key(left)==_geo_key(right)
    public={(str(e.get('store_id')),e.get('platform'),str(e.get('country') or '').casefold()):e for e in evidence if e.get('kind')=='public' and e.get('relevance')=='relevant'}
    csv=[e for e in evidence if e.get('kind')=='csv']
    related_csv=[e for e in csv if e.get('relevance')!='unrelated']
    def refs(row):
        result=[]
        if isinstance(row.get('evidence_id'),str) and row['evidence_id']:result.append(row['evidence_id'])
        declared=row.get('evidence_ids')
        if isinstance(declared,(list,tuple)):
            result.extend(value for value in declared if isinstance(value,str) and value)
        return list(dict.fromkeys(result))
    def lineage_state(row,field,ids):
        sources=row.get('field_sources')
        if sources in (None,{}):return True
        if not isinstance(sources,dict):return False
        if field not in sources:return True
        src=sources[field]
        if not isinstance(src,dict):return False
        import_id,line=src.get('import_id'),src.get('line')
        if isinstance(import_id,bool) or isinstance(line,bool):return False
        if not str(import_id or '').isdigit() or not str(line or '').isdigit():return False
        try:import_id,line=int(import_id),int(line)
        except (ValueError,OverflowError):return False
        if import_id<=0 or line<=0:return False
        return 'CSV:'+str(import_id)+':'+str(line) in ids
    def row_state(row):
        verified=row.get('relevance')=='relevant' or bool(row.get('store_id')) and (str(row['store_id']),row.get('platform'),str(row.get('geo') or '').casefold()) in public
        prefix='Downloads không khớp:'
        conflict=any(isinstance(warning,str) and warning.strip().startswith(prefix) and warning.strip()[len(prefix):].strip()==str(row.get('id')) for warning in warnings)
        in_scope=geo_equal(row.get('geo'),scope.get('geo')) and row.get('platform') in scope.get('platforms',[])
        reason='' if verified else 'Chủ đề chưa được xác minh; tên app không đủ chứng minh.'
        if not in_scope:verified=False;reason='GEO hoặc OS không khớp phạm vi nghiên cứu.'
        if conflict:verified=False;reason='Nguồn CSV mâu thuẫn; cần đối chiếu trước khi kết luận.'
        return verified,reason,conflict
    for row in csv:
        # Cross-source identity uses an exact store ID + OS + GEO only, never a name join.
        verified,reason,conflict=row_state(row);ids=refs(row)
        if row.get('relevance')=='unrelated':continue
        if row.get('period_start')!=scope['start'] or row.get('period_end')!=scope['end']:continue
        delta=number(row.get('delta_pop'));current=number(row.get('downloads'))
        if delta is not None and current is not None:
            try:prior=current-delta
            except OverflowError:prior=None
            old=[x for x in related_csv if (str(x.get('id')),x.get('platform'),geo_equal(x.get('geo'),row.get('geo')),x.get('period_start'),x.get('period_end'))==(str(row.get('id')),row.get('platform'),True,scope.get('comparison_start'),scope.get('comparison_end'))]
            baseline=[number(x.get('downloads')) for x in old];baseline_refs=[e for x in old for e in refs(x)]
            baseline_bad=any(value is None or value<0 or not refs(x) or not row_state(x)[0] or row_state(x)[2] for x,value in zip(old,baseline))
            baseline_conflict=bool(baseline) and (len(set(baseline))>1 or any(value!=prior for value in baseline))
            unrelated=[x for x in csv if x.get('relevance')=='unrelated' and (str(x.get('id')),x.get('platform'),geo_equal(x.get('geo'),row.get('geo')),x.get('period_start'),x.get('period_end'))==(str(row.get('id')),row.get('platform'),True,scope.get('comparison_start'),scope.get('comparison_end')) and number(x.get('downloads')) is not None and number(x.get('downloads'))>=0 and number(x.get('downloads'))!=prior]
            lineage_ok=lineage_state(row,'delta_pop',ids)
            unsafe_prior=prior is None or prior<0
            why=reason if not verified else 'Nguồn CSV mâu thuẫn với delta PoP.' if baseline_conflict or unrelated else 'Lineage delta PoP không hợp lệ hoặc không được khai báo.' if not lineage_ok else 'Baseline không đủ điều kiện xác minh.' if baseline_bad else 'Baseline không hợp lệ theo delta PoP.' if unsafe_prior else ''
            unrelated_refs=[ref for x in unrelated for ref in refs(x)]
            refs_ok=bool(ids)
            why=why or ('' if refs_ok else 'Nguồn CSV không khai báo evidence ID hợp lệ.')
            m=compare('downloads',row['id'],row['name'],row['platform'],row['geo'],scope,prior if prior is not None else -1,current,ids+baseline_refs+unrelated_refs,'CSV user export',eligible=verified and lineage_ok and refs_ok and prior is not None and prior>=0 and not baseline_bad and not baseline_conflict and not unrelated,reason=why)
            if m:m['comparison_basis']='PoP declared by export; preceding equal-length period';comparisons.append(m)
        yoy=number(row.get('delta_yoy'))
        if yoy is not None and current is not None:
            year_scope=dict(scope)
            for field in ('start','end'):
                date=_iso_date(scope.get(field))
                if date is None:year_scope=None;break
                try:previous=date.replace(year=date.year-1)
                except ValueError:previous=date.replace(year=date.year-1,day=28)
                year_scope['comparison_'+field]=str(previous)
            lineage_ok=lineage_state(row,'delta_yoy',ids)
            if year_scope is None:continue
            try:yoy_prior=current-yoy
            except OverflowError:yoy_prior=None
            refs_ok=bool(ids)
            m=compare('downloads',row['id'],row['name'],row['platform'],row['geo'],year_scope,yoy_prior if yoy_prior is not None else -1,current,ids,'CSV user export',definition='downloads_yoy',eligible=verified and lineage_ok and refs_ok and yoy_prior is not None,reason=reason if not verified else '' if lineage_ok and refs_ok else 'Lineage delta YoY hoặc evidence ID không hợp lệ hoặc không được khai báo.')
            if m:m['comparison_basis']='YoY declared by export';comparisons.append(m)
        for metric in ('downloads','revenue'):
            if metric=='downloads' and delta is not None:continue
            old=[x for x in related_csv if (str(x.get('id')),x.get('platform'),geo_equal(x.get('geo'),row.get('geo')),x.get('period_start'),x.get('period_end'))==(str(row.get('id')),row.get('platform'),True,scope['comparison_start'],scope['comparison_end'])]
            if not old:continue
            values=[number(x.get(metric)) for x in old];prior=values[0]
            currency=row.get('currency');currency_ok=metric!='revenue' or currency not in (None,'','Unknown') and all(currency==x.get('currency') for x in old)
            prior_conflict=any(value!=prior for value in values[1:]);baseline_bad=any(value is None or value<0 or not refs(x) or not row_state(x)[0] or row_state(x)[2] for x,value in zip(old,values))
            why=reason if not verified else 'Các baseline có giá trị mâu thuẫn.' if prior_conflict else 'Baseline không đủ điều kiện xác minh.' if baseline_bad else 'Thiếu hoặc không khớp đơn vị tiền tệ trong CSV.' if not currency_ok else ''
            refs_ok=bool(ids)
            m=compare(metric,row['id'],row['name'],row['platform'],row['geo'],scope,prior,row.get(metric),ids+[e for x in old for e in refs(x)],'CSV user export',eligible=verified and refs_ok and currency_ok and not baseline_bad and not prior_conflict,reason=why or ('' if refs_ok else 'Nguồn CSV không khai báo evidence ID hợp lệ.'),unit=(currency if currency is not None else 'Unknown') if metric=='revenue' else None)
            if m:m['comparison_basis']='Matched app ID, OS, GEO and explicit equal-length periods';comparisons.append(m)
    for ev in evidence:
        if ev.get('kind')!='web' or ev.get('verification')!='verified':continue
        for obs in ev.get('observations',[]):
            if not obs.get('verified') or obs.get('metric') not in DIMENSIONS:continue
            matching=[e for e in evidence if e.get('kind')=='public' and e.get('relevance')=='relevant' and str(e.get('store_id'))==str(obs.get('app_id')) and e.get('platform')==obs.get('platform') and geo_equal(e.get('country'),obs.get('geo'))]
            if not geo_equal(obs.get('geo'),scope['geo']) or obs.get('platform') not in scope['platforms']:continue
            if any(obs.get(k)!=scope[k] for k in ('period_start','period_end','comparison_start','comparison_end')):continue
            if not matching:continue
            if not any(e.get('name','').casefold() in ev.get('quote','').casefold() for e in matching):continue
            m=compare(obs['metric'],obs['app_id'],matching[0]['name'],obs['platform'],obs['geo'],scope,obs.get('before'),obs.get('after'),[ev['evidence_id'],matching[0]['evidence_id']],ev.get('origin_url') or ev['url'],obs.get('definition'),unit=obs.get('unit'))
            if m:comparisons.append(m)
    unique={};conflicts=set()
    for m in comparisons:
        previous=unique.get(m['id'])
        if previous and (m['before'],m['after'])!=(previous['before'],previous['after']):conflicts.add(m['id'])
        if previous:
            previous['evidence_ids']=list(dict.fromkeys(previous['evidence_ids']+m['evidence_ids']))
            if not m['eligible']:
                previous['eligible']=False;previous['exclusion_reason']=m.get('exclusion_reason') or previous['exclusion_reason']
        else:unique[m['id']]=dict(m)
    for identity in conflicts:
        unique[identity]['eligible']=False;unique[identity]['exclusion_reason']='Hai nguồn cùng định nghĩa và kỳ có giá trị mâu thuẫn.'
    packet['comparisons']=list(unique.values())
    daily=defaultdict(dict);daily_conflicts=set();daily_sources={}
    for row in csv:
        start_date=_iso_date(row.get('period_start'));end_date=_iso_date(row.get('period_end'));scope_start=_iso_date(scope.get('start'));scope_end=_iso_date(scope.get('end'))
        if start_date is None or end_date is None or scope_start is None or scope_end is None or start_date!=end_date or not scope_start<=start_date<=scope_end:continue
        if row.get('relevance')=='unrelated' or not refs(row):continue
        eligible,_,row_conflict=row_state(row)
        if not eligible or row_conflict:continue
        for metric in ('downloads','revenue'):
            value=number(row.get(metric))
            currency=row.get('currency')
            if value is None or value<0 or metric=='revenue' and currency in (None,'','Unknown'):continue
            group=(str(row['id']),row['platform'],_geo_key(row['geo']),metric,currency if metric=='revenue' else UNITS[metric])
            point=dict(date=row['period_start'],value=value,evidence_ids=refs(row))
            if point['date'] in daily[group]:
                if daily[group][point['date']]['value']!=value:daily_conflicts.add(group)
                daily[group][point['date']]['evidence_ids']=list(dict.fromkeys(daily[group][point['date']]['evidence_ids']+point['evidence_ids']))
            else:daily[group][point['date']]=point
            daily_sources.setdefault(group,row)
    packet['time_series']=[]
    for group,points in daily.items():
        if len(points)<4 or group in daily_conflicts:continue
        source=daily_sources[group]
        packet['time_series'].append(dict(id=metric_id(group),app_id=group[0],app_name=source['name'],platform=group[1],geo=source['geo'],metric=group[3],unit=group[4],provider='CSV user export',definition='Daily observed export; missing days not interpolated',granularity='day',chart_type='line',points=sorted(points.values(),key=lambda p:p['date']),evidence_ids=list(dict.fromkeys(e for p in points.values() for e in p['evidence_ids']))))
    packet['schema_version']=VERSION
    packet['coverage']['comparable_metrics']=sum(m['eligible'] for m in unique.values())
    packet['gaps']=list(dict.fromkeys(packet.get('gaps',[])+(['Chưa có downloads/revenue cùng kỳ và chủ đề được xác minh.'] if not any(m['eligible'] and m['metric'] in ('downloads','revenue') for m in unique.values()) else [])))
    return packet

def assessment(packet,scope):
    comparisons=packet.get('comparisons',[]);axes=[];by_id={};conflicts=set()
    for metric in comparisons:
        identity=(metric.get('metric'),str(metric.get('app_id')),metric.get('platform'),_geo_key(metric.get('geo')),metric.get('period_start'),metric.get('period_end'),metric.get('comparison_start'),metric.get('comparison_end'),metric.get('provider'),metric.get('definition'),metric.get('unit'))
        previous=by_id.get(identity)
        if previous and (previous.get('before'),previous.get('after'))!=(metric.get('before'),metric.get('after')):conflicts.add(identity)
        elif previous:
            previous['evidence_ids']=list(dict.fromkeys(previous.get('evidence_ids',[])+metric.get('evidence_ids',[])))
            if not metric.get('eligible'):previous['eligible']=False
        else:by_id[identity]=dict(metric)
    comparisons=[metric for identity,metric in by_id.items() if identity not in conflicts]
    for dimension in DIMENSIONS:
        metrics=[m for m in comparisons if m['metric']==dimension and m['eligible']]
        groups=defaultdict(list)
        for m in metrics:groups[(m['provider'],m['platform'],_geo_key(m['geo']),m['unit'],m['definition'],m.get('period_start'),m.get('period_end'),m.get('comparison_start'),m.get('comparison_end'))].append(m)
        summaries=[]
        for group,items in groups.items():
            if dimension in ('downloads','revenue'):
                try:
                    before=sum(m['before'] for m in items);after=sum(m['after'] for m in items)
                    change=(after-before)/before*100 if before else None
                    if not math.isfinite(before) or not math.isfinite(after) or change is not None and not math.isfinite(change):raise OverflowError
                except (OverflowError,ValueError):
                    continue
                text=f'{len(items)} app trong tập có kỳ so sánh; chỉ kết luận trong tập này.'
            else:before=after=change=None;text=f'{len(items)} phép so sánh riêng; không cộng các thang rank/search.'
            summaries.append(dict(provider=group[0],platform=group[1],geo=items[0]['geo'],unit=group[3],definition=group[4],period_start=group[5],period_end=group[6],comparison_start=group[7],comparison_end=group[8],before=before,after=after,percent=change,app_count=len(items),metric_ids=[m['id'] for m in items],evidence_ids=list(dict.fromkeys(e for m in items for e in m['evidence_ids'])),limitation=text))
        safe_metric_ids={identity for group in summaries for identity in group['metric_ids']}
        axes.append(dict(dimension=dimension,status='comparable' if summaries else 'insufficient_evidence',groups=summaries,metric_ids=[m['id'] for m in metrics if m['id'] in safe_metric_ids]))
    growth=[m for m in comparisons if m['eligible'] and m['metric'] in ('downloads','revenue') and m['delta']>0]
    related=[e for e in packet.get('evidence',[]) if e.get('kind') in ('csv','public') and e.get('relevance')!='unrelated' and not any(str(m['app_id'])==str(e.get('store_id') if e['kind']=='public' else e.get('id')) and m['platform']==e.get('platform') for m in growth)]
    related_by_app={}
    for e in related:
        identity=(e['kind'],str(e.get('store_id') if e['kind']=='public' else e.get('id')),e.get('platform'),_geo_key(e.get('geo') or e.get('country')))
        if identity not in related_by_app:related_by_app[identity]=dict(e)
        else:
            previous=related_by_app[identity]
            previous['evidence_ids']=list(dict.fromkeys((previous.get('evidence_ids') or [previous['evidence_id']])+(e.get('evidence_ids') or [e['evidence_id']])))
    related=list(related_by_app.values())
    ua=[]
    for e in packet.get('evidence',[]):
        if e.get('kind')!='csv' or e.get('relevance')!='relevant' or e.get('period_start')!=scope['start'] or e.get('period_end')!=scope['end']:continue
        fields=('ua_spend','ua_cpi','retention_percent','roas_percent')
        if not any(e.get(k) is not None for k in fields):continue
        item={k:e.get(k) for k in fields+('roas_target_percent','cohort_window','cohort_start','cohort_end','measurement_date','currency')}
        item.update(name=e['name'],app_id=e['id'],platform=e['platform'],geo=e['geo'],evidence_ids=e.get('evidence_ids') or [e['evidence_id']],status='metrics_only',reason='Chưa đủ cohort, độ trưởng thành hoặc mục tiêu để chấm hiệu quả.')
        try:
            window=int(str(e['cohort_window']).upper().removeprefix('D'))
            maturity=dt.date.fromisoformat(e['cohort_end'])+dt.timedelta(days=window)
            eligible=window>0 and maturity<=dt.date.fromisoformat(e['measurement_date']) and scope['start']<=e['cohort_start']<=e['cohort_end']<=scope['end']
            eligible=eligible and e.get('currency') not in (None,'Unknown') and all(number(e.get(k)) is not None and number(e[k])>=0 for k in fields)
            if eligible and number(e.get('roas_target_percent')) is not None:
                item['status']='meets_target' if e['roas_percent']>=e['roas_target_percent'] else 'below_target'
                item['reason']='So với mục tiêu ROAS được khai báo trong CSV; không tự suy ra lợi nhuận toàn phần.'
        except (KeyError,ValueError,TypeError):pass
        ua.append(item)
    ua_status='target_assessed' if any(x['status'] in ('meets_target','below_target') for x in ua) else 'metrics_only' if ua else 'not_assessed'
    for m in growth:
        match=next((u for u in ua if (u['app_id'],u['platform'],_geo_key(u['geo']))==(m['app_id'],m['platform'],_geo_key(m['geo']))),None)
        if match:m.update(ua_status=match['status'],ua_details=match)
    return dict(schema_version=VERSION,market_assessment=axes,app_growth=growth,
      ua_assessment=dict(status=ua_status,answer='Chưa đánh giá hiệu quả UA: cần spend, CPI, retention, ROAS theo cohort và mục tiêu do PO cung cấp.' if not ua else 'Có số liệu UA theo app; chỉ chấm mục tiêu khi cohort đã đủ tuổi và mục tiêu được khai báo.',metrics=ua,target='user_provided_only' if ua_status=='target_assessed' else None),
      related_apps=related,comparison_count=sum(m['eligible'] for m in comparisons),growth_answer=f'{len(growth)} phép so sánh cho thấy app tăng downloads/revenue trong phạm vi dữ liệu.' if growth else 'Chưa có app đủ bằng chứng tăng trưởng trong phạm vi nghiên cứu.')

def decorate(result,packet,scope):
    if result.get('schema_version')=='1.9.2':return result
    result.update(assessment(packet,scope));return result

def enforce_ai(result,packet):
    """Legacy JSON remains accepted, with stricter semantics than its original schema."""
    metrics={m['id']:m for m in packet.get('comparisons',[]) if m['eligible']}
    growth={k:m for k,m in metrics.items() if m['metric'] in ('downloads','revenue')}
    if result['trend']['status']!='insufficient_evidence':
        cited=set(result['trend']['evidence_ids'])
        if not any(cited&set(m['evidence_ids']) for m in growth.values()):raise ValueError('Market growth cần downloads/revenue so sánh hợp lệ; review/rank/search/ads không đủ.')
    for candidate in result.get('scale_candidates',[]):
        ids=candidate.get('signal_ids',[])
        for sid in ids:
            if sid not in growth or growth[sid]['delta']<=0 or str(growth[sid]['app_id'])!=str(candidate['app_id']):raise ValueError('Ứng viên tăng trưởng phải dùng metric downloads/revenue tăng hợp lệ; không dùng review/rank/ads.')
    return result

def dashboard(c,args):
    import research_workspace as w
    topic=args.get('topic','');geo=args.get('geo','');platform=args.get('platform','');days=int(args.get('days',30))
    if days not in (7,30,60,90,180,365):raise ValueError('Khoảng thời gian dashboard không hợp lệ')
    cutoff=str(dt.date.today()-dt.timedelta(days=days));projects=[];topics=set();geos=set();recent=[];attention=[];series=[];matrix=[];all_metrics=[];running=[];missing=[];research_ids=[]
    for project in c.execute('SELECT * FROM projects ORDER BY id DESC'):
        run_headers=[dict(r) for r in c.execute('SELECT id,status FROM workspace_runs WHERE research_id=? ORDER BY id DESC',(project['id'],))]
        if not run_headers:
            old_scope=w.scope_for(project['brief'] or project['name'])
            old_geos=str(project['geo']).split(',')
            old_scope['geo']=old_geos[0] if old_geos else 'US'
            old_scope.update(start='Chưa xác định',end='',comparison_start='',comparison_end='')
            label=old_scope.get('topic') or old_scope['product_type'];topics.add(label);geos.update(old_geos)
            if topic and topic!=label or geo and geo not in old_geos or platform and platform not in old_scope['platforms'] or project['created_at'][:10]<cutoff:continue
            research_ids.append(project['id'])
            context=dict(research_id=project['id'],run_id=None,name=project['name'],topic=label,scope=old_scope)
            recent.append(dict(context,status='legacy',displayed_result_run_id=None,using_previous=False,updated_at=project['created_at'],data_at=None,legacy=True,answer='Dữ liệu cũ được giữ nguyên; chưa có kết quả metric v1.9.1.'))
            missing.append(context)
            for dimension in DIMENSIONS:matrix.append(dict(context,dimension=dimension,status='insufficient_evidence',groups=[]))
            continue
        latest=w.get(c,run_headers[0]['id']);scope=latest['scope'];topics.add(scope.get('topic') or scope['product_type']);geos.add(scope['geo'])
        if topic and topic!=(scope.get('topic') or scope['product_type']) or geo and geo!=scope['geo'] or platform and platform not in scope['platforms']:continue
        if latest['created_at'][:10]<cutoff:continue
        research_ids.append(project['id']);projects.append(dict(project))
        if latest['status'] in w.ACTIVE:running.append(dict(research_id=project['id'],run_id=latest['id'],name=project['name'],status=latest['status']))
        completed_header=next((r for r in run_headers if r['status']=='ready'),None)
        completed=latest if latest['status']=='ready' else w.get(c,completed_header['id']) if completed_header else None
        chosen=completed or latest;packet=chosen.get('packet') or chosen.get('preview') or {};is_legacy=packet.get('schema_version')!=VERSION
        data=assessment(packet,chosen['scope']) if not is_legacy else assessment({},chosen['scope'])
        if not data['comparison_count']:missing.append(dict(research_id=project['id'],run_id=chosen['id'],name=project['name']))
        context=dict(research_id=project['id'],run_id=chosen['id'],name=project['name'],topic=scope.get('topic') or scope['product_type'],scope=chosen['scope'])
        stale=chosen['scope']['end']<str(dt.date.today()-dt.timedelta(days=7))
        recent.append(dict(context,status=latest['status'],displayed_result_run_id=chosen['id'],using_previous=chosen['id']!=latest['id'],stale_data=stale,updated_at=chosen['updated_at'],data_at=(chosen.get('result') or {}).get('data_at'),legacy=is_legacy,answer=(chosen.get('result') or {}).get('direct_answer') or (chosen.get('result') or {}).get('trend',{}).get('answer','Chưa có câu trả lời hoàn chỉnh.')))
        if stale:attention.append(dict(context,kind='gap',text='Kỳ dữ liệu kết thúc hơn 7 ngày trước; đọc kết quả cùng thời điểm nguồn.',evidence_ids=[]))
        for axis in data['market_assessment']:
            groups=[g for g in axis['groups'] if not platform or g['platform']==platform]
            matrix.append(dict(context,dimension=axis['dimension'],status='comparable' if groups else 'insufficient_evidence',groups=groups))
        for m in packet.get('comparisons',[]) if not is_legacy else []:
            if platform and m['platform']!=platform:continue
            if not m['eligible']:
                attention.append(dict(context,kind='conflict' if 'mâu thuẫn' in m['exclusion_reason'] else 'gap',text=m['exclusion_reason'],evidence_ids=m['evidence_ids']));continue
            enriched=dict(m,research_id=context['research_id'],run_id=context['run_id'],research_name=context['name'],topic=context['topic'],scope=context['scope']);all_metrics.append(enriched)
            series.append(dict(id=m['id'],**context,metric=m['metric'],unit=m['unit'],provider=m['provider'],platform=m['platform'],geo=m['geo'],definition=m['definition'],granularity='period',chart_type='bar',points=[dict(start=m['comparison_start'],end=m['comparison_end'],value=m['before']),dict(start=m['period_start'],end=m['period_end'],value=m['after'])],evidence_ids=m['evidence_ids'],app_name=m['name']))
        for daily_series in packet.get('time_series',[]) if not is_legacy else []:
            if not platform or daily_series['platform']==platform:series.append(dict(daily_series,**context))
        for source in packet.get('sources',[]):
            if source.get('status') not in ('ready','verified') or source.get('count')==0:
                attention.append(dict(context,kind='source',text=source.get('source','Nguồn')+': '+str(source.get('error') or source.get('note') or source.get('status')),evidence_ids=[]))
        for warning in packet.get('warnings',[]):attention.append(dict(context,kind='conflict',text=warning,evidence_ids=[]))
        if is_legacy:attention.append(dict(context,kind='legacy',text='Report cũ: chưa xác thực theo hợp đồng metric v1.9.1.',evidence_ids=[]))
    dedup={};conflicts=[]
    for m in all_metrics:
        identity=(m['metric'],m['app_id'],m['platform'],_geo_key(m['geo']),m['period_start'],m['period_end'],m['comparison_start'],m['comparison_end'],m['provider'],m['definition'],m['unit'])
        if identity in dedup and (dedup[identity]['before'],dedup[identity]['after'])!=(m['before'],m['after']):
            conflicts.append(identity);attention.append(dict(research_id=m['research_id'],run_id=m['run_id'],name=m['name'],kind='conflict',text='Cùng app/nguồn/kỳ có số liệu khác nhau giữa research; không xếp hạng.',evidence_ids=m['evidence_ids']))
        else:dedup.setdefault(identity,m)
    usable=[m for k,m in dedup.items() if k not in conflicts]
    growth=[m for m in usable if m['metric'] in ('downloads','revenue') and m['delta']>0]
    growth.sort(key=lambda m:(m['metric']!='downloads',-m['delta']))
    for m in growth:attention.insert(0,dict(research_id=m['research_id'],run_id=m['run_id'],name=m['name'],kind='finding',text=m['name']+': '+m['metric']+' có kỳ so sánh tăng.',metric_id=m['id'],evidence_ids=m['evidence_ids']))
    decisions=[]
    for row in c.execute("SELECT * FROM action_registry WHERE state NOT IN ('done','rejected') ORDER BY id DESC"):
        if row['project_id'] not in research_ids:continue
        link=c.execute('SELECT run_id FROM workspace_links WHERE action_id=?',(row['id'],)).fetchone()
        decisions.append(dict(id=row['id'],kind='action',title=row['title'],state=row['state'],research_id=row['project_id'],run_id=link[0] if link else None))
    for row in c.execute("SELECT * FROM opportunities WHERE state NOT IN ('validated','rejected') ORDER BY id DESC"):
        if row['project_id'] in research_ids:decisions.append(dict(id=row['id'],kind='opportunity',title=row['title'],state=row['state'],research_id=row['project_id'],action_id=row['action_id']))
    return dict(schema_version=VERSION,filters=dict(topic=topic,geo=geo,platform=platform,days=days),options=dict(topics=sorted(topics),geos=sorted(geos)),
      summary=dict(running=len(running),comparable_findings=len(usable),pending_actions=sum(x['kind']=='action' for x in decisions),missing_research=len(missing)),
      running=running,missing=missing,findings=usable,series=series,topic_matrix=matrix,growth_apps=growth,attention=attention,decisions=decisions,recent=recent,
      data_at=max((r.get('data_at') or r['updated_at'] for r in recent),default=None),counts_definition='Chỉ số vận hành nghiên cứu trong bộ lọc; không phải quy mô thị trường.')
