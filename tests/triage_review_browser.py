"""Regression tests for failed adoption and coalesced draft persistence.
Run: python3 tests/triage_review_browser.py
"""
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
passed=[]
def check(name,condition):
    assert condition,name
    passed.append(name)
    print('PASS',name)

try:
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
        page.wait_for_function('storageReady')
        page.evaluate('''async()=>{
            closeSettings();
            S.documents.book={id:'book',title:'Buch',category:'epub',last_opened_at:'2026-10-14T12:00:00.000Z'};
            reconcileTriage(S);await saveState();renderAll();setView('triage');
        }''')
        page.locator('#triageInterest').select_option('5')
        page.locator('input[value=soon]').check()
        page.locator('#triageNote').fill('Frühere Entscheidung')
        page.locator('#triageAction').select_option('archive')
        page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
        page.wait_for_function('!triageBusy')
        page.evaluate('''async()=>{
            S.documents.book.last_opened_at='2026-10-15T12:00:00.000Z';
            reconcileTriage(S);await saveState();renderTriage();
            window.originalTransaction=db.transaction.bind(db);
            db.transaction=function(...args){
                if(args[1]==='readwrite') throw new Error('Injected write failure');
                return originalTransaction(...args);
            };
        }''')
        page.get_by_role('button',name='Frühere Entscheidung bewusst übernehmen').click()
        page.wait_for_function('document.getElementById("triageSaveStatus").textContent.includes("fehlgeschlagen")')
        check('Failed adoption displays adopted fields and unsaved status',
              page.locator('#triageInterest').input_value()=='5' and
              page.locator('#triageNote').input_value()=='Frühere Entscheidung' and
              page.locator('#triageAction').input_value()=='archive' and
              page.evaluate('triageContent(triageDraft(S.triage.current))===triageContent({interest_rating:5,routes:["soon"],personal_note:document.getElementById("triageNote").value,reader_action:"archive"})'))
        check('Failed adoption does not persist draft or advance card',page.evaluate('''async()=>{
            var stored=await idbGetState();
            return stored.triage.current===S.triage.current && !stored.triage.drafts[S.triage.current] && !stored.triage.decisions[S.triage.current];
        }'''))
        page.evaluate('()=>{db.transaction=originalTransaction;}')
        adopted=page.evaluate('S.triage.current')
        page.locator('#triageNote').fill('Sichtbare Korrektur nach Fehler')
        page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
        page.wait_for_function('!triageBusy')
        check('Save after recovery commits visible corrected values',page.evaluate('''id=>{
            var d=S.triage.decisions[id];return d.personal_note==='Sichtbare Korrektur nach Fehler' && d.interest_rating===5 && d.reader_action==='archive';
        }''',adopted))
        page.reload();page.wait_for_function('storageReady')
        check('Corrected adopted decision survives reload',page.evaluate('id=>S.triage.decisions[id].personal_note',adopted)=='Sichtbare Korrektur nach Fehler')
        # Hold a real IndexedDB transaction open while another view requests a save.
        def prepare_delayed_write():
            page.evaluate('''async()=>{
                closeSettings();S=defaultState();
                S.documents.first={id:'first',title:'Erste Karte',category:'article'};
                S.documents.second={id:'second',title:'Zweite Karte',category:'article'};
                reconcileTriage(S);await saveState();renderAll();setView('triage');await _dbWriteQueue;
                window.raceTransaction=db.transaction.bind(db);
                window.racePending=false;window.raceOutcome=null;window.holdNextWrite=true;
                db.transaction=function(...args){
                    var tx=raceTransaction(...args);
                    if(args[1]==='readwrite' && holdNextWrite){
                        holdNextWrite=false;
                        var objectStore=tx.objectStore.bind(tx);
                        tx.objectStore=function(name){
                            var store=objectStore(name),put=store.put.bind(store);
                            store.put=function(...values){
                                var request=put(...values);
                                request.addEventListener('success',function(){
                                    racePending=true;
                                    function keepAlive(){
                                        if(raceOutcome==='abort'){tx.abort();return;}
                                        if(raceOutcome==='commit')return;
                                        store.get(DB_KEY).onsuccess=keepAlive;
                                    }
                                    keepAlive();
                                });
                                return request;
                            };
                            return store;
                        };
                    }
                    return tx;
                };
            }''')
            return page.evaluate('S.triage.current')

        card=prepare_delayed_write()
        page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
        page.wait_for_function('racePending')
        page.locator('[data-view=calendar]').click()
        check('Tentative decision stays outside shared state during concurrent view save',
              page.evaluate('id=>!S.triage.decisions[id] && S.triage.current===id',card))
        page.evaluate('raceOutcome="abort"')
        page.wait_for_function('!triageBusy')
        page.evaluate('async()=>{await _dbWriteQueue.catch(()=>{});db.transaction=raceTransaction;}')
        check('Aborted decision cannot leak through queued view save',page.evaluate('''async id=>{
            var stored=await idbGetState();
            return !S.triage.decisions[id] && !stored.triage.decisions[id] && stored.triage.current===id && !stored.triage.active;
        }''',card))
        page.reload();page.wait_for_function('storageReady')
        check('Failed decision remains absent after reload',page.evaluate('id=>!S.triage.decisions[id] && S.triage.current===id',card))

        card=prepare_delayed_write()
        page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
        page.wait_for_function('racePending')
        page.locator('[data-view=calendar]').click()
        page.evaluate('raceOutcome="commit"')
        page.wait_for_function('!triageBusy')
        page.evaluate('async()=>{await _dbWriteQueue;db.transaction=raceTransaction;}')
        check('Successful decision survives queued view save with selected view',page.evaluate('''async id=>{
            var stored=await idbGetState();
            return !!stored.triage.decisions[id] && stored.triage.current!==id && !stored.triage.active && currentView==='calendar';
        }''',card))
        page.reload();page.wait_for_function('storageReady')
        check('Successful concurrent decision and view survive reload',page.evaluate('id=>!!S.triage.decisions[id] && currentView==="calendar"',card))

        card=prepare_delayed_write()
        page.get_by_role('button',name='Später entscheiden',exact=True).click()
        page.wait_for_function('racePending')
        page.locator('[data-view=library]').click()
        page.evaluate('raceOutcome="abort"')
        page.wait_for_function('!triageBusy')
        page.evaluate('async()=>{await _dbWriteQueue;db.transaction=raceTransaction;}')
        check('Aborted navigation cannot leak through queued view save',page.evaluate('''async id=>{
            var stored=await idbGetState();
            return S.triage.current===id && stored.triage.current===id && stored.triage.queue[0]===id && stored.triage.trail.length===0;
        }''',card))
        # A Reader response arriving during the triage write must wait for its outcome.
        for outcome in ['abort','commit']:
            card=prepare_delayed_write()
            page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
            page.wait_for_function('racePending')
            page.evaluate('''()=>{
                localStorage.setItem(TOKEN_KEY,'synthetic-test-token');
                window.originalFetchTracked=fetchTrackedDocuments;
                fetchTrackedDocuments=async()=>[{id:'incoming',title:'Während des Schreibens geladen',category:'article',last_opened_at:'2020-01-01T00:00:00.000Z'}];
                window.concurrentSync=syncReadwise();
            }''')
            check('Reader response waits for pending triage write ('+outcome+')',
                  page.evaluate('isSyncing && !S.documents.incoming'))
            page.evaluate('outcome=>{raceOutcome=outcome;}',outcome)
            page.evaluate('async()=>{await concurrentSync;await _dbWriteQueue;db.transaction=raceTransaction;fetchTrackedDocuments=originalFetchTracked;localStorage.removeItem(TOKEN_KEY);}')
            check('Reader observations and triage outcome both survive ('+outcome+')',page.evaluate('''async x=>{
                var stored=await idbGetState();
                return !!stored.documents.incoming && Object.values(stored.triage.observations).some(o=>o.reader_id==='incoming') && !!stored.triage.decisions[x.card]===(x.outcome==='commit');
            }''',dict(card=card,outcome=outcome)))

        # Large library: keyboard events must not serialize one full snapshot per character.
        page.evaluate('''async()=>{
            closeSettings();S=defaultState();
            for(var i=0;i<1000;i++) S.documents['doc'+i]={id:'doc'+i,title:'Dokument '+i,category:'article',summary:'x'.repeat(2048)};
            reconcileTriage(S);await saveState();renderAll();setView('triage');await _dbWriteQueue;
            window.snapshots=0;window.transactions=0;
            window.originalPersist=persistState;
            persistState=function(state){snapshots++;return originalPersist(state);};
            window.countTransaction=db.transaction.bind(db);
            db.transaction=function(...args){if(args[1]==='readwrite')transactions++;return countTransaction(...args);};
        }''')
        # Clock pauses timer execution while real per-character input events are sent.
        page.clock.install()
        page.clock.pause_at('2030-01-01T00:00:00Z')
        text='Lange persönliche Notiz mit echten Tastatureingaben. '*4
        page.locator('#triageNote').press_sequentially(text)
        check('Typing a long note queues no per-character snapshots or transactions',page.evaluate('snapshots===0 && transactions===0') and page.locator('#triageNote').input_value()==text)
        page.clock.run_for(350)
        page.wait_for_function('document.getElementById("triageSaveStatus").textContent==="Entwurf lokal gespeichert"')
        check('Typing pause persists only the final snapshot',page.evaluate('snapshots===1 && transactions===1') and page.evaluate('async()=>{var x=await idbGetState();return x.triage.drafts[x.triage.current].personal_note;}')==text)
        page.evaluate('snapshots=0;transactions=0;')
        page.locator('#triageNote').press_sequentially(' Sofort speichern')
        immediate=page.evaluate('S.triage.current')
        page.get_by_role('button',name='Speichern & nächste Karte',exact=True).click()
        page.wait_for_function('!triageBusy')
        page.clock.run_for(350)
        check('Immediate decision save includes latest note and cancels delayed write',page.evaluate('snapshots===1 && transactions===1 && triageDraftTimer===null') and page.evaluate('id=>S.triage.decisions[id].personal_note',immediate)==text+' Sofort speichern')
        page.evaluate('snapshots=0;transactions=0;')
        page.locator('#triageNote').press_sequentially('Vor Navigation')
        navigating=page.evaluate('S.triage.current')
        page.get_by_role('button',name='Später entscheiden',exact=True).click()
        page.wait_for_function('!triageBusy')
        page.clock.run_for(350)
        check('Navigation persists latest draft without a later duplicate write',page.evaluate('snapshots===1 && transactions===1') and page.evaluate('async id=>(await idbGetState()).triage.drafts[id].personal_note',navigating)=='Vor Navigation')
        page.evaluate('snapshots=0;transactions=0;')
        page.locator('#triageNote').press_sequentially('Vor Tabwechsel')
        page.evaluate('window.dispatchEvent(new Event("pagehide"))')
        page.wait_for_function('document.getElementById("triageSaveStatus").textContent==="Entwurf lokal gespeichert"')
        page.clock.run_for(350)
        check('Page lifecycle flushes pending draft once',page.evaluate('snapshots===1 && transactions===1 && triageDraftTimer===null'))
        page.evaluate('snapshots=0;transactions=0;')
        page.locator('#triageNote').press_sequentially('Bei Import ersetzen')
        page.evaluate('''async()=>{
            pendingImport={state:defaultState(),theme:''};await confirmImport();
        }''')
        page.clock.run_for(350)
        check('Import cancels pending draft and cannot be overwritten by stale timer',page.evaluate('async()=>Object.keys((await idbGetState()).documents).length===0 && snapshots===2 && transactions===2 && triageDraftTimer===null'))
        check('No uncaught JavaScript errors',not errors)
        browser.close()
finally:
    server.shutdown()
print(f'{len(passed)} checks passed')
