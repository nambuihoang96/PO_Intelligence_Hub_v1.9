import sys,time,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
import research_workspace as w
s.DATA=Path(sys.argv[1]);s.DBPATH=s.DATA/'research.sqlite3'
rid=int(sys.argv[2]);w.retry(s,rid)
while True:
 time.sleep(1)
 with s.LOCK,s.con() as c:r=w.get(c,rid)
 if r['status'] not in w.ACTIVE:break
print(json.dumps(dict(id=rid,status=r['status'],error=r['error']),ensure_ascii=True),flush=True)
