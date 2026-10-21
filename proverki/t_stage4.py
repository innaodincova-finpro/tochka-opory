import json
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8765/v11/index.html'; R=[]
def ok(n,c,i=''): R.append(bool(c)); print(('OK  ' if c else 'FAIL'),n,i)
def act(pg,a,**kw):
    pg.evaluate("""([a,kw])=>{const b=document.createElement('button');b.dataset.act=a;Object.entries(kw).forEach(([k,v])=>b.dataset[k]=v);b.hidden=true;document.body.appendChild(b);b.click();b.remove()}""",[a,kw]); pg.wait_for_timeout(500)
def keys(pg,c,w=2500):
    for ch in c: pg.keyboard.press(ch); pg.wait_for_timeout(40)
    pg.wait_for_timeout(w)
O='/tmp/claude-0/-home-claude/871422d8-68b2-5fc8-b99e-a6edeea11466/scratchpad/stage1/out/'
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-proxy-server']); ctx=b.new_context(viewport={'width':1300,'height':850},accept_downloads=True)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:(dl.append(d.message),d.accept())); dl=[]
    pg.goto(U); pg.wait_for_timeout(900); pg.get_by_role('button',name='Выбрать').first.click(); pg.wait_for_timeout(300)
    act(pg,'demoOn'); pg.evaluate("snapTake(true)"); pg.wait_for_timeout(800)
    snaps=pg.evaluate("idbGet('snaps').then(x=>(x||[]).length)"); ok('запасная копия отложена', snaps==1)
    act(pg,'snaps'); ok('окно «Прежние состояния» со списком', pg.locator('#modal [data-act=snapBack]').count()==1); act(pg,'closeModal')
    # изменение и возврат
    act(pg,'delClient',id='c1'); ok('клиент удалён', pg.evaluate("!S.clients.some(c=>c.id==='c1')"))
    pg.evaluate("go('help');document.querySelectorAll('details').forEach(d=>d.open=true)"); act(pg,'snaps'); pg.locator('#modal [data-act=snapBack]').first.click(); pg.wait_for_timeout(600)
    ok('возврат к прежнему состоянию вернул клиента', pg.evaluate("S.clients.some(c=>c.id==='c1')"))
    # копия старее
    pg.evaluate("go('help');document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(200)
    with pg.expect_download() as d: pg.locator('[data-act=export]').first.click()
    d.value.save_as(O+'c_old.json')
    pg.wait_for_timeout(1200); act(pg,'delClient',id='c2'); pg.wait_for_timeout(300)
    dl.clear()
    with pg.expect_file_chooser() as fc: pg.locator('[data-act=import]').first.click()
    fc.value.set_files(O+'c_old.json'); pg.wait_for_timeout(800)
    ok('при загрузке старой копии предупреждение', any('старее текущих' in m for m in dl), dl[-1][:160] if dl else '')
    # с кодом: копии закрыты
    pg.evaluate("go('help');document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.locator('[data-act=setPin]').first.click(); pg.wait_for_timeout(300); keys(pg,'123456',300); keys(pg,'123456',4000)
    pg.check('#rec-ok'); pg.click('#rec-done'); pg.wait_for_timeout(300)
    act(pg,'delClient',id='c3'); pg.wait_for_timeout(800)
    pg.evaluate("snapTake(true)"); pg.wait_for_timeout(800)
    enc=pg.evaluate("idbGet('snaps').then(x=>x[x.length-1].enc&&!('text' in x[x.length-1]))"); ok('с кодом запасная копия закрыта', enc)
    pg.evaluate("go('help');document.querySelectorAll('details').forEach(d=>d.open=true)"); act(pg,'snaps'); pg.locator('#modal [data-act=snapBack]').first.click(); pg.wait_for_timeout(800)
    ok('закрытая копия возвращается', pg.evaluate("S.clients.length>0"))
    # справка
    pg.evaluate("go('help');document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(200); ok('в справке строка про автокопию', 'Автокопия' in pg.inner_text('#auto-st'), pg.inner_text('#auto-st')[:80])
    ok('кнопка включения автокопии на компьютере', pg.locator('[data-act=autoSet]').count()==1)
    ok('полосы сбоя нет', pg.evaluate("document.getElementById('errbar').hidden"))
    pg.evaluate("setTimeout(()=>{throw new Error('проверка')},0)"); pg.wait_for_timeout(300)
    ok('при сбое показано сообщение с «Обновить»', not pg.evaluate("document.getElementById('errbar').hidden") and 'сохранены' in pg.inner_text('#errbar'))
    errs=[e for e in errs if 'проверка' not in e]
    ok('ошибок страницы нет', not errs, str(errs[:2]))
    b.close()
print('ИТОГ',sum(R),'из',len(R))
