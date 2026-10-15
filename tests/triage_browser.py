"""Functional regression suite. Run: python3 tests/triage_browser.py
Uses an isolated browser profile and a temporary HTTP server; no real API credentials.
"""
import copy
import json
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{server.server_port}/index.html'
passed = []
def check(name, condition=True):
    assert condition, name
    passed.append(name)
    print('PASS', name)

def doc(i, opened=None):
    return dict(id=str(i), title=f'Dokument {i}', author='Autor', category='article',
                location='new', reading_progress=.2, last_opened_at=opened or f'2026-10-{15-int(i)%10:02}T12:00:00.000Z',
                summary='Kurzbeschreibung <script>keine Ausführung</script>', updated_at='2026-10-15T12:00:00.000Z')

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
    page=browser.new_page()
    errors=[]
    requests=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: requests.append((r.method, r.url)))
    page.goto(URL)
    page.wait_for_function('storageReady')
    page.evaluate('closeSettings()')
    check('Initial migration and empty UI', page.evaluate('S.version===3 && Object.keys(S.triage.observations).length===0'))
    legacy=page.evaluate('defaultState()')
    legacy.pop('triage'); legacy['version']=2
    legacy['documents']={str(i):doc(i) for i in range(1,7)}
    legacy['documents']['6']['last_opened_at']=None
    legacy['events']=[dict(id='baseline:1',type='reader_opened',docId='1',observedAt=doc(1)['last_opened_at'],date='2026-10-14',progressAfter=.2,category='article',title='Dokument 1')]
    legacy['historyCursors']={'article':'cursor-old'};legacy['historyPages']={'article':3}
    page.evaluate('async x=>{S=migrateState(x); await saveState(); renderAll();}',legacy)
    check('Legacy migration retains events, documents and lazy history', page.evaluate('S.events.length===1 && S.historyPages.article===3 && S.historyCursors.article==="cursor-old" && S.triage.queue.length===6'))
    page.locator('[data-view=triage]').click()
    check('Triage reachable',page.locator('#triageView').is_visible())
    page.locator('#triageInterest').select_option('5')
    page.locator('input[value=soon]').check();page.locator('input[value=deepen]').check()
    check('Multiple active routes',page.locator('.triage-routes input:checked').count()==2)
    page.locator('input[value=discard]').check()
    check('Discard excludes active routes but retains interest 5', page.locator('.triage-routes input:checked').count()==1 and page.locator('#triageInterest').input_value()=='5')
    page.locator('input[value=park]').check()
    check('Park excludes discard',page.locator('input[value=discard]').is_checked() is False)
    page.locator('input[value=soon]').check();page.locator('input[value=deepen]').check()
    check('Active route excludes park',not page.locator('input[value=park]').is_checked())
    note='  Mein Gedanke\n<unverändert> & ä  '
    page.locator('#triageNote').fill(note)
    page.locator('#triageAction').select_option('archive')
    first=page.evaluate('S.triage.current')
    page.wait_for_function('document.getElementById("triageSaveStatus").textContent==="Entwurf lokal gespeichert"')
    page.reload();page.wait_for_function('storageReady');page.evaluate('closeSettings()')
    check('Draft and current view survive reload',page.locator('#triageView').is_visible() and page.locator('#triageNote').input_value()==note and page.evaluate('S.triage.current')==first)
    for i in range(5):
        page.locator('#triageInterest').select_option(str(5-i))
        page.locator('input[value=soon]').check()
        page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
        page.wait_for_function('!triageBusy')
    check('Five sequential decisions committed',page.evaluate('Object.keys(S.triage.decisions).length===5'))
    saved=page.evaluate('(id)=>S.triage.decisions[id]',first)
    check('Stable IDs and exact notes, independent action',saved['personal_note']==note and saved['reader_action']=='archive' and saved['routes']==['soon','deepen'] and saved['revision']==1)
    page.reload();page.wait_for_function('storageReady');page.evaluate('closeSettings()')
    check('Committed decisions survive reload',page.evaluate('(id)=>S.triage.decisions[id]',first)==saved)
    page.get_by_role('button',name='Letzte Entscheidung bearbeiten',exact=True).click();page.wait_for_function('!triageBusy')
    last=page.evaluate('S.triage.current')
    old=page.evaluate('(id)=>S.triage.decisions[id]',last)
    page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click();page.wait_for_function('!triageBusy')
    check('Unchanged save creates no revision',page.evaluate('(id)=>S.triage.decisions[id]',last)==old)
    page.get_by_role('button',name='Letzte Entscheidung bearbeiten',exact=True).click();page.wait_for_function('!triageBusy')
    page.locator('#triageNote').fill('Korrektur')
    page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click();page.wait_for_function('!triageBusy')
    revised=page.evaluate('(id)=>S.triage.decisions[id]',last)
    check('Changed decision increments revision and retains prior contents', revised['revision']==2 and revised['decision_id']==old['decision_id'] and revised['revisions'][0]['personal_note']==old['personal_note'])
    page.get_by_role('button',name='Zurück',exact=True).click();page.wait_for_function('!triageBusy')
    check('Back returns to saved card',page.evaluate('S.triage.current')==last)
    before=page.evaluate('JSON.stringify(S.triage.decisions)')
    page.evaluate('async()=>{reconcileTriage(S);reconcileTriage(S);await saveState();}')
    check('Repeated reconciliation deduplicates and preserves decisions',page.evaluate('S.triage.queue.length===6 && JSON.stringify(S.triage.decisions)')==before)
    older=doc(7,'2020-01-01T00:00:00.000Z')
    page.evaluate('async d=>{mergeFetchedDocuments([d],new Date().toISOString());await saveState();renderAll();}',older)
    check('Older backfill enters queue and is marked discovered',page.evaluate('Object.values(S.triage.observations).some(o=>o.reader_id==="7" && o.review_visibility==="backfilled")'))
    reopen=doc(1,'2026-10-16T12:00:00.000Z')
    page.evaluate('async d=>{mergeFetchedDocuments([d],new Date().toISOString());await saveState();renderAll();}',reopen)
    check('Reopening preserves historical decision and creates one new observation',page.evaluate('Object.values(S.triage.observations).filter(o=>o.reader_id==="1").length===2'))
    page.evaluate('async()=>{var t=S.triage;t.current=Object.values(t.observations).find(o=>o.reader_id==="1" && o.observed_event_at==="2026-10-16T12:00:00.000Z").observation_id;await saveState();renderTriage();}')
    check('Prior document decision visible and not automatically copied',page.get_by_role('button',name='Frühere Entscheidung bewusst übernehmen').is_visible() and page.locator('#triageInterest').input_value()=='')
    page.get_by_role('button',name='Frühere Entscheidung bewusst übernehmen').click()
    page.wait_for_function('document.getElementById("triageInterest").value==="5"')
    check('Explicit adoption copies note and action',page.locator('#triageNote').input_value()==note and page.locator('#triageAction').input_value()=='archive')
    # Add progress change for same observed opening; repeated identical sync is idempotent.
    progress=copy.deepcopy(reopen);progress['reading_progress']=.7
    page.evaluate('async d=>{mergeFetchedDocuments([d],new Date().toISOString());mergeFetchedDocuments([d],new Date().toISOString());await saveState();}',progress)
    check('Progress change observation references event without duplicates',page.evaluate('Object.values(S.triage.observations).filter(o=>o.reader_id==="1" && o.kind==="progress_change").length===1'))
    check('No opening date invented',page.evaluate('Object.values(S.triage.observations).filter(o=>o.reader_id==="6").every(o=>o.observed_event_at===null && o.last_opened_at===null)'))
    page.evaluate('async()=>{S.triage.current=S.triage.queue.find(id=>!S.triage.decisions[id]);await saveState();renderTriage();}')
    deferred=page.evaluate('S.triage.current')
    page.get_by_role('button',name='Später entscheiden',exact=True).click();page.wait_for_function('!triageBusy')
    check('Defer rotates queue without marking reviewed',page.evaluate('(id)=>S.triage.queue.at(-1)===id && !S.triage.decisions[id] && S.triage.current!==id',deferred))
    # Actual export/download and file import, confirmation, token isolation.
    page.evaluate('localStorage.setItem(TOKEN_KEY,"test-only-local-token")')
    page.evaluate('openSettings()')
    with page.expect_download() as download:
        page.get_by_role('button',name='JSON-Backup exportieren',exact=True).click()
    backup=json.loads(Path(download.value.path()).read_text())
    check('Export includes revision history and navigation without token',backup['appState']['triage']['decisions'][last]['revision']==2 and 'test-only-local-token' not in json.dumps(backup))
    page.evaluate('async()=>{S=defaultState();await saveState();renderAll();}')
    page.locator('#backupFileInput').set_input_files(dict(name='roundtrip.json',mimeType='application/json',buffer=json.dumps(backup).encode()))
    page.wait_for_selector('#importBackdrop.open')
    check('Import preview includes triage and awaits confirmation', 'Triage-Beobachtungen' in page.locator('#importSummary').inner_text() and page.evaluate('Object.keys(S.documents).length===0'))
    page.get_by_role('button',name='Import anwenden',exact=True).click()
    page.wait_for_function('Object.keys(S.triage.decisions).length===5')
    check('Backup roundtrip retains complete triage and token',page.evaluate('S.triage')==backup['appState']['triage'] and page.evaluate('localStorage.getItem(TOKEN_KEY)')=='test-only-local-token')
    # Invalid triage backup must be rejected, leaving current state untouched.
    bad=copy.deepcopy(backup);bad['appState']['triage']['decisions'][last]['routes']=['discard','soon']
    original=page.evaluate('JSON.stringify(S)')
    page.evaluate('openSettings()')
    page.locator('#backupFileInput').set_input_files(dict(name='invalid.json',mimeType='application/json',buffer=json.dumps(bad).encode()))
    page.wait_for_function('document.getElementById("toast").textContent.includes("widersprüchliche")')
    check('Invalid backup rejected without changing current state',page.evaluate('JSON.stringify(S)')==original and page.evaluate('pendingImport===null'))
    page.locator('#backupFileInput').set_input_files(dict(name='legacy.json',mimeType='application/json',buffer=json.dumps(legacy).encode()))
    page.wait_for_selector('#importBackdrop.open')
    page.get_by_role('button',name='Import anwenden',exact=True).click();page.wait_for_function('S.triage.queue.length===6')
    check('Legacy backup imports through real UI',page.evaluate('S.version===3 && S.historyPages.article===3'))
    for view in ['calendar','timeline','library','triage']:
        page.locator('[data-view='+view+']').click()
        assert page.locator('#'+view+'View').is_visible()
    check('All four views remain functional', page.locator('#monthGrid .day').count()>=28)
    page.evaluate('setCategory("article")')
    check('Category filter retains known documents',page.evaluate('filteredDocs().length===6'))
    page.evaluate('setCategory("pdf")')
    check('Empty category filter hides matching cards without deleting state',page.evaluate('filteredDocs().length===0 && S.triage.queue.length===6'))
    page.evaluate('setCategory("all")')
    page.get_by_role('button',name='E-Ink',exact=True).click();page.reload();page.wait_for_function('storageReady')
    check('E-Ink theme persists',page.evaluate('localStorage.getItem(THEME_KEY)==="eink"'))
    page.evaluate('navigator.serviceWorker.ready')
    check('Updated PWA cache installed',page.evaluate('caches.has("reader-log-v4")'))
    page.context.set_offline(True)
    page.reload();page.wait_for_function('storageReady')
    check('PWA reload works offline',page.title()=='Reader Log')
    page.context.set_offline(False)
    check('Triage causes no external requests or Reader writes',not any('readwise.io' in url or method!='GET' for method,url in requests))
    # Inject an aborted transaction: save must not advance and retry must recover.
    page.evaluate('setCategory("all");setView("triage");renderTriage()')
    page.evaluate("""async()=>{
        await _dbWriteQueue;
        window.realTransaction=db.transaction.bind(db);
        db.transaction=function(...args){
            var tx=realTransaction(...args);
            if(args[1]==='readwrite') {
                var originalStore=tx.objectStore.bind(tx);
                tx.objectStore=function(name){
                    var store=originalStore(name),originalPut=store.put.bind(store);
                    store.put=function(...values){
                        var request=originalPut(...values);
                        request.addEventListener('success',()=>tx.abort());
                        return request;
                    };
                    return store;
                };
            }
            return tx;
        };
    }""")
    failure_card=page.evaluate('S.triage.current')
    page.locator('#triageNote').fill('Must survive failure')
    page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click();page.wait_for_function('!triageBusy')
    check('Aborted transaction after successful request never advances card',page.evaluate('S.triage.current')==failure_card)
    page.evaluate('()=>{db.transaction=realTransaction;}')
    page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click();page.wait_for_function('!triageBusy')
    check('Storage queue recovers after failure',page.evaluate('(id)=>S.triage.decisions[id].personal_note',failure_card)=='Must survive failure')
    check('No uncaught browser exceptions',errors==[])
    # Simulate Reader responses at the network boundary; execute the existing API paths.
    from urllib.parse import urlparse, parse_qs
    calls=[]
    scenario={'mode':'initial','rate':True}
    def reader_response(route):
        r=route.request
        query=parse_qs(urlparse(r.url).query)
        calls.append((r.method,query))
        if scenario['rate']:
            scenario['rate']=False
            route.fulfill(status=429,headers={'Retry-After':'1','Access-Control-Expose-Headers':'Retry-After'},body='{}')
            return
        if scenario['mode']=='failure':
            route.fulfill(status=503,body='{}')
            return
        category=query.get('category',[''])[0]
        results=[];cursor=None
        if category=='article':
            if scenario['mode']=='history':
                results=[doc(23,'2019-01-01T00:00:00.000Z')];cursor='next-history'
            elif scenario['mode']=='incremental':
                results=[doc(20,'2026-10-17T12:00:00.000Z')]
            elif query.get('pageCursor'):
                results=[doc(21)]
            else:
                results=[doc(20)];cursor='page-two'
        route.fulfill(status=200,content_type='application/json',body=json.dumps(dict(results=results,nextPageCursor=cursor)))
    page.route('https://readwise.io/**',reader_response)
    page.evaluate('''async()=>{S=defaultState();await saveState();sleep=async()=>{};window.retryWaits=[];waitForRateLimit=async(seconds,pageNo)=>{retryWaits.push(seconds);};renderAll();}''')
    page.evaluate('syncReadwise()')
    check('Reader initial window, all categories and pagination execute', page.evaluate('Object.keys(S.documents).length===2 && !!S.lastSyncAt && !!S.recentWindowStartedAt') and len(set(q.get('category',[''])[0] for _,q in calls))==7 and any(q.get('pageCursor')==['page-two'] for _,q in calls))
    check('HTTP 429 retries with Retry-After handling',page.evaluate('retryWaits.length===1 && retryWaits[0]===2'))
    check('Initial sync keeps 31-day strategy',page.evaluate('Math.abs((Date.now()-Date.parse(S.recentWindowStartedAt))/86400000-31)<.01'))
    scenario['mode']='incremental';calls.clear()
    page.evaluate('syncReadwise()')
    check('Incremental sync uses updatedAfter and creates new opening observation', all('updatedAfter' in q for _,q in calls) and page.evaluate('Object.values(S.triage.observations).filter(o=>o.reader_id==="20").length===2'))
    state_before=page.evaluate('JSON.stringify(S.triage)')
    page.evaluate('syncReadwise()')
    check('Identical API sync does not duplicate observations or decisions',page.evaluate('JSON.stringify(S.triage)')==state_before)
    scenario['mode']='history';calls.clear()
    page.evaluate('setCategory("article");loadOlderHistory()')
    check('Lazy history loads only requested category page and retains cursor', len(calls)==1 and page.evaluate('S.historyCursors.article==="next-history" && S.historyPages.article===1 && !S.historyDone.article'))
    check('Lazy history older observation remains unreviewed',page.evaluate('Object.values(S.triage.observations).some(o=>o.reader_id==="23" && o.review_visibility==="backfilled" && !S.triage.decisions[o.observation_id])'))
    scenario['mode']='failure'
    sync_marker=page.evaluate('S.lastSyncAt')
    page.evaluate('syncReadwise()')
    check('Failed API sync does not advance successful sync marker',page.evaluate('S.lastSyncAt')==sync_marker)
    history_marker=page.evaluate('JSON.stringify([S.historyPages,S.historyCursors])')
    page.evaluate('loadOlderHistory()')
    check('Failed history request does not advance cursor',page.evaluate('JSON.stringify([S.historyPages,S.historyCursors])')==history_marker)
    check('All Reader requests remain GET',all(method=='GET' for method,_ in calls))
    # Validation prevents destructive startup migration; recovery uses existing import UI.
    valid=page.evaluate('backupPayload()')
    corrupt=copy.deepcopy(valid['appState']);corrupt['triage']['queue'].append('missing-observation')
    page.evaluate('x=>persistState(x)',corrupt)
    page.reload()
    page.wait_for_function('document.getElementById("toast").textContent.includes("unverändert")')
    check('Invalid persisted state blocks writes without data loss',page.evaluate('!storageReady') and page.evaluate('idbGetState()')==corrupt)
    page.evaluate('setView("triage")')
    page.evaluate('saveTriageDecision()')
    check('Failed migration cannot overwrite original data',page.evaluate('idbGetState()')==corrupt)
    page.evaluate('openSettings()')
    page.locator('#backupFileInput').set_input_files(dict(name='recovery.json',mimeType='application/json',buffer=json.dumps(valid).encode()))
    page.wait_for_selector('#importBackdrop.open')
    page.get_by_role('button',name='Import anwenden',exact=True).click()
    page.wait_for_function('storageReady')
    check('Recovery import restores writable valid state',page.evaluate('S.triage')==valid['appState']['triage'])
    # Corruption rejection includes revision metadata and future schemas.
    check('Revision, routes, queue and future schema corruption rejected',page.evaluate('''()=>{
      var mutations=[s=>s.version=99,s=>s.triage.queue.push('missing'),s=>s.triage.current='missing'];
      return mutations.every(mutate=>{var x=JSON.parse(JSON.stringify(S));mutate(x);try{migrateState(x);return false;}catch(e){return true;}});
    }'''))
    check('No uncaught exceptions after API and recovery tests',errors==[])
    browser.close()
server.shutdown()
print(f'{len(passed)} checks passed')
