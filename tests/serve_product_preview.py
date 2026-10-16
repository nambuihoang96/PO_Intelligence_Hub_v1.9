"""Preview stored live results on an isolated copy. Never run new research."""
import sqlite3,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server as s
folder=Path(tempfile.mkdtemp(prefix='po-ui-preview-'))
s.DATA=folder;s.DBPATH=folder/'research.sqlite3'
source=Path('C:/Users/Admin/AppData/Local/Temp/po-live-9x6_coft/research.sqlite3')
with sqlite3.connect('file:'+source.as_posix()+'?mode=ro',uri=True) as original:
 with sqlite3.connect(s.DBPATH) as copy:original.backup(copy)
s.main()
