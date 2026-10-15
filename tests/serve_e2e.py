"""Isolated E2E server; external sources replaced with explicit TEST fixtures."""
import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
server.DBPATH=server.ROOT/'tmp'/('e2e-'+str(time.time_ns())+'.sqlite3')
def discover(p):
    time.sleep(1)
    return {'results':[{'name':'E2E Test Utility','platform':'iOS','country':'US','store_id':'e2e123','store_url':'https://apps.apple.com/app/ide2e123','primary_genre':'Utilities','rating':4.2,'reviews':42}], 'errors':['TEST: Android optional connector unavailable'], 'collection_meta':{'queries_attempted':[{'source':'apple','geo':'US','keyword':'mobile apps'},{'source':'google_play','geo':'US','keyword':'mobile apps'}],'geos_requested':['US'],'keywords_used':['mobile apps'],'requests_attempted':2,'requests_succeeded':1}}
server.guided_discover=discover
server.research_news_context=lambda *args:([],[])
server.main()
