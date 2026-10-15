"""Read-only copy of the user's database; migrate only the copy."""
import json,sqlite3,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
source_path=Path(sys.argv[1]);target=server.ROOT/'tmp'/'migration-copy.sqlite3'
assert not Path(str(source_path)+'-wal').exists(),'Use SQLite online backup while WAL exists'
source=sqlite3.connect(source_path.as_uri()+'?mode=ro&immutable=1',uri=True)
dest=sqlite3.connect(target)
try:source.backup(dest)
finally:source.close();dest.close()
def inspect():
 c=sqlite3.connect(target)
 try:
  tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
  return {t:c.execute('SELECT COUNT(*) FROM "'+t+'"').fetchone()[0] for t in tables}
 finally:c.close()
def digests(tables):
 c=sqlite3.connect(target)
 try:return {t:hashlib.sha256(json.dumps(c.execute('SELECT * FROM "'+t+'" ORDER BY rowid').fetchall(),ensure_ascii=False,default=str).encode()).hexdigest() for t in tables}
 finally:c.close()
before=inspect();hashes=digests(before);server.DBPATH=target;server.init();after=inspect()
assert hashes==digests(before),'Existing table contents changed'
assert all(after[t]==n for t,n in before.items()),'Existing row counts changed'
c=sqlite3.connect(target)
try:assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
finally:c.close()
result={'existing_tables_preserved':len(before),'existing_rows_preserved':sum(before.values()),'integrity':'ok','all_original_table_content_hashes_unchanged':True,'original_modified':False,'new_tables':sorted(set(after)-set(before))}
print(json.dumps(result,indent=2))
(server.ROOT/'tmp'/'migration-results.json').write_text(json.dumps(result,indent=2),encoding='utf8')
