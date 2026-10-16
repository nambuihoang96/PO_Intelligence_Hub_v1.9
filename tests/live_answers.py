import os
os.environ['PYTHONIOENCODING']='utf-8'
"""Live acceptance uses isolated storage, never reads user datasets."""
import sys,json,time,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import research_workspace as w
folder=Path(tempfile.mkdtemp(prefix='po-live-'));s.DATA=folder;s.DBPATH=folder/'research.sqlite3';s.init()
with s.con() as c:c.execute("UPDATE settings SET value='true' WHERE key='codex_allowed'")
questions=['Top các app drama trên thị trường','So sánh ReelShort và DramaBox để chọn app benchmark','App drama mới nên benchmark những gì, vì sao?']
output=[]
for q in questions:
 r=w.launch(s,dict(question=q,mode='auto'));rid=r['id']
 while True:
  time.sleep(2)
  with s.LOCK,s.con() as c:r=w.get(c,rid)
  if r['status'] not in w.ACTIVE:break
 output.append(r)
 Path('data/live-answer-acceptance.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(dict(question=q,status=r['status'],error=r.get('error')),ensure_ascii=True),flush=True)
print('LIVE_DB',folder,flush=True)
