import sys, json, re, time
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765'
NEW=BASE+'/v11/index.html'; OLD=BASE+'/v10/index.html'
OUT=sys.argv[1]
R=[]
def ok(name,cond,info=''):
    R.append((name,bool(cond),info)); print(('OK  ' if cond else 'FAIL'),name,info)

def fresh(p,vp=(1300,850)):
    b=p.chromium.launch(args=['--no-proxy-server'])
    ctx=b.new_context(viewport={'width':vp[0],'height':vp[1]},accept_downloads=True)
    return b,ctx
def openp(ctx,url=NEW):
    pg=ctx.new_page(); pg.errs=[]
    pg.on('pageerror',lambda e:pg.errs.append(str(e)))
    pg.on('dialog',lambda d:d.accept())
    pg.goto(url); pg.wait_for_timeout(900); return pg
def appr(pg):
    try: pg.get_by_role('button',name='Выбрать').first.click(timeout=1500); pg.wait_for_timeout(300)
    except: pass
    pg.evaluate("(()=>{const b=document.createElement('button');b.dataset.act='demoOn';b.hidden=true;document.body.appendChild(b);b.click();b.remove()})()"); pg.wait_for_timeout(300)
def keys(pg,code,wait=2500):
    for ch in code: pg.keyboard.press(ch); pg.wait_for_timeout(40)
    pg.wait_for_timeout(wait)
locked=lambda pg: pg.evaluate("!document.getElementById('lockscr').hidden")
dots=lambda pg: pg.evaluate("document.querySelectorAll('#lock-dots i').length")
ls=lambda pg: pg.evaluate("localStorage.getItem('tochka-opory-v1')") or ''
def vault(pg): return pg.evaluate("""new Promise(r=>{const q=indexedDB.open('tochka-opory',1);q.onupgradeneeded=()=>q.result.createObjectStore('v');
  q.onsuccess=()=>{const t=q.result.transaction('v').objectStore('v').get('vault');t.onsuccess=()=>{const v=t.result;r(v?{pinLen:v.pinLen,at:v.at,fmt:v.fmt}:null)};t.onerror=()=>r('err')}})""")
def help_tab(pg): pg.evaluate("document.querySelector('[data-tab=help]')?document.querySelector('[data-tab=help]').click():go('help');document.querySelectorAll('details').forEach(d=>d.open=true)"); pg.wait_for_timeout(300)
def set_code(pg,code):
    help_tab(pg); pg.locator('[data-act=setPin]').first.click(); pg.wait_for_timeout(300)
    keys(pg,code,300); keys(pg,code,4000)
def rec_from_modal(pg):
    t=pg.inner_text('.reccode') if pg.locator('.reccode').count() else ''
    return t.strip()
def rec_done(pg):
    pg.check('#rec-ok'); pg.click('#rec-done'); pg.wait_for_timeout(300)
def first_name(pg): return pg.evaluate("S.clients.length?S.clients[0].name:''")
def clear_tries(pg): pg.evaluate("localStorage.removeItem('tochka-opory-v1-tries')")

with sync_playwright() as p:
    # T1 задание кода, закрытое хранение, окно кода восстановления
    b,ctx=fresh(p); pg=openp(ctx); appr(pg)
    pg.evaluate("S.clients[0].name='Марина Проверкина';save()"); pg.wait_for_timeout(300)
    set_code(pg,'123456')
    rc=rec_from_modal(pg); ok('T1 окно кода восстановления показано', len(re.sub('[^A-Z0-9]','',rc))==16, rc)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    ok('T1 окно нельзя закрыть без отметки', pg.locator('.reccode').count()==1)
    rec_done(pg)
    raw=ls(pg); ok('T1 в localStorage только метка', '"encV":2' in raw and 'Проверкина' not in raw and 'Ветров' not in raw, raw[:120])
    v=vault(pg); ok('T1 закрытая база в IndexedDB', v and v['pinLen']==6, str(v))
    # T2 перезапуск, неверные коды, пауза
    pg.reload(); pg.wait_for_timeout(1200)
    ok('T2 экран кода, 6 клеточек', locked(pg) and dots(pg)==6)
    ok('T2 до кода сведений о клиентах в памяти нет', pg.evaluate("S.clients.length")==0)
    for i in range(5): keys(pg,'111111',1800)
    note=pg.inner_text('#lock-note'); ok('T2 после 5 ошибок пауза', 'Следующая попытка через' in note, note)
    keys(pg,'123456',2000); ok('T2 во время паузы верный код не принимается', locked(pg))
    pg.reload(); pg.wait_for_timeout(1000); note=pg.inner_text('#lock-note')
    ok('T2 пауза сохраняется после перезагрузки', 'Следующая попытка через' in note, note)
    clear_tries(pg); pg.reload(); pg.wait_for_timeout(1000)
    keys(pg,'123456',3000); ok('T2 верный код открывает', (not locked(pg)) and first_name(pg)=='Марина Проверкина')
    # T3 возврат примера не меняет код (пункт 1)
    help_tab(pg); pg.evaluate("['demoOff','demoOn'].forEach(a=>{const b=document.createElement('button');b.dataset.act=a;b.hidden=true;document.body.appendChild(b);b.click();b.remove()})"); pg.wait_for_timeout(1500)
    pg.reload(); pg.wait_for_timeout(1000); ok('T3 после «Вернуть пример» 6 клеточек', dots(pg)==6)
    keys(pg,'123456',3000); ok('T3 код подходит', not locked(pg))
    pg.evaluate("S.clients[0].name='Марина Проверкина';save()"); pg.wait_for_timeout(800)
    # T4 смена кода и отмена
    set_code(pg,'654321'); ok('T4 смена кода без нового кода восстановления', pg.locator('.reccode').count()==0)
    pg.keyboard.press('Control+z'); pg.wait_for_timeout(800)
    pg.reload(); pg.wait_for_timeout(1000)
    keys(pg,'654321',3000); ok('T4 после отмены действует новый код', not locked(pg))
    # T5 загрузка открытой копии с чужим кодом не меняет код
    copy=pg.evaluate("JSON.stringify(Object.assign({},S,{settings:Object.assign({},S.settings,{pinHash:'abc',pinLen:4})}))")
    open(OUT+'/copy_plain.json','w').write(copy)
    help_tab(pg)
    with pg.expect_file_chooser() as fc: pg.locator('[data-act=import]').first.click()
    fc.value.set_files(OUT+'/copy_plain.json'); pg.wait_for_timeout(1500)
    pg.reload(); pg.wait_for_timeout(1000); ok('T5 после загрузки копии 6 клеточек', dots(pg)==6)
    keys(pg,'654321',3000); ok('T5 код подходит', not locked(pg))
    # T6 закрытая копия
    help_tab(pg)
    with pg.expect_download() as dl: pg.locator('[data-act=export]').first.click()
    path=OUT+'/copy_enc.json'; dl.value.save_as(path); txt=open(path).read()
    ok('T6 копия закрыта', '"encV":2' in txt and 'Проверкина' not in txt and 'Ветров' not in txt)
    pg.evaluate("S.clients[0].name='Изменено';save()"); pg.wait_for_timeout(800)
    with pg.expect_file_chooser() as fc: pg.locator('[data-act=import]').first.click()
    fc.value.set_files(path); pg.wait_for_timeout(600)
    pg.fill('#imp-code','000000'); pg.click('[data-act=importCode]'); pg.wait_for_timeout(2500)
    ok('T6 неверный код к копии не подходит', first_name(pg)=='Изменено')
    pg.fill('#imp-code','654321'); pg.click('[data-act=importCode]'); pg.wait_for_timeout(3000)
    ok('T6 копия открыта кодом входа', first_name(pg)=='Марина Проверкина')
    with pg.expect_file_chooser() as fc: pg.locator('[data-act=import]').first.click()
    fc.value.set_files(path); pg.wait_for_timeout(600)
    pg.fill('#imp-code',rc.lower().replace('-',' ')); pg.click('[data-act=importCode]'); pg.wait_for_timeout(3000)
    ok('T6 копия открыта кодом восстановления', first_name(pg)=='Марина Проверкина')
    # T7 забыт код
    pg.reload(); pg.wait_for_timeout(1000)
    pg.click('#lock-forgot'); pg.fill('#lock-rec-in',rc); pg.click('#lock-rec-go'); pg.wait_for_timeout(2500)
    ok('T7 после кода восстановления просит новый код', 'новый код' in pg.inner_text('#lock-title').lower())
    ok('T7 отмены нет — новый код обязателен', pg.evaluate("document.getElementById('lock-cancel').hidden"))
    keys(pg,'777777',300); keys(pg,'777777',4000)
    pg.reload(); pg.wait_for_timeout(1000); keys(pg,'777777',3000)
    ok('T7 новый код работает, записи на месте', (not locked(pg)) and first_name(pg)=='Марина Проверкина')
    # T8 блокировка: страница недоступна, скачать нельзя, отмена не работает
    pg.evaluate("S.wait.push({id:'zz',cid:'c1',want:'проверка',added:D(0)});pushUndo('x');save()"); pg.wait_for_timeout(800)
    pg.evaluate("lock()"); pg.wait_for_timeout(1500)
    got=[]; pg.on('download',lambda d:got.append(d))
    for i in range(40): pg.keyboard.press('Tab')
    pg.keyboard.press('Enter'); pg.wait_for_timeout(800)
    ok('T8 из-под экрана кода ничего не скачивается', len(got)==0)
    ok('T8 записи выгружены из памяти', pg.evaluate("S.clients.length")==0 and pg.evaluate("document.getElementById('view').innerText.length")<5)
    pg.keyboard.press('Control+z'); pg.wait_for_timeout(500)
    for i in range(8): pg.keyboard.press('Backspace')
    keys(pg,'777777',3000); ok('T8 открыто после ввода кода', not locked(pg)); ok('T8 отмена под экраном кода не сработала', pg.evaluate("S.wait.some(w=>w.id==='zz')"))
    ok('T8 ошибок страницы нет', not pg.errs, str(pg.errs[:3]))
    b.close()

    # T9 прежняя редакция затирает метку — записи целы
    b,ctx=fresh(p); pg=openp(ctx); appr(pg)
    pg.evaluate("S.clients[0].name='Марина Проверкина';save()"); set_code(pg,'123456'); rec_done(pg)
    pg2=openp(ctx,OLD); pg2.wait_for_timeout(1000); pg2.close()
    pg.close(); pg=openp(ctx)
    ok('T9 после прежней редакции — экран кода', locked(pg), ls(pg)[:60])
    keys(pg,'123456',3000); ok('T9 настоящие записи на месте', first_name(pg)=='Марина Проверкина')
    pg.wait_for_timeout(800); ok('T9 метка восстановлена', '"encV":2' in ls(pg))
    b.close()

    # T10/T11 повреждённая и новая запись не затираются
    for name,val in [('повреждена','{bad json'),('новый формат',json.dumps({'fmt':3,'clients':[],'sessions':[]}))]:
        b,ctx=fresh(p); pg=openp(ctx); pg.evaluate("v=>localStorage.setItem('tochka-opory-v1',v)",val)
        pg.reload(); pg.wait_for_timeout(2500)
        ok('T10 '+name+': экран «не удалось открыть»', pg.evaluate("!document.getElementById('badscr').hidden"))
        ok('T10 '+name+': запись не тронута', ls(pg)==val)
        b.close()

    # T12 две вкладки
    b,ctx=fresh(p); A=openp(ctx); appr(A); A.wait_for_timeout(500); B=openp(ctx); B.wait_for_timeout(800)
    ok('T12 вторая вкладка — только просмотр', B.evaluate("RO") and B.is_visible('#robar'))
    B.evaluate("document.querySelector('[data-tab=pay]').click()"); B.wait_for_timeout(300)
    n0=A.evaluate("S.wait.length"); B.locator('[data-act=addWait]').first.click() if B.locator('[data-act=addWait]').count() else None
    A.evaluate("S.wait.push({id:'aa',cid:'c1',want:'из A',added:D(0)});save()"); A.wait_for_timeout(300)
    B.click('#ro-take'); B.wait_for_timeout(3500)
    ok('T12 «Работать здесь»: первая вкладка ушла в просмотр', A.evaluate("RO"))
    ok('T12 правка первой вкладки видна во второй', B.evaluate("S.wait.some(w=>w.id==='aa')") and not B.evaluate("RO"))
    b.close()

    # T13 снятие кода сразу после правки
    b,ctx=fresh(p); pg=openp(ctx); appr(pg); set_code(pg,'123456'); rec_done(pg)
    help_tab(pg); pg.evaluate("S.clients[0].name='Сразу';save()"); pg.locator('[data-act=pinOff]').first.click(); pg.wait_for_timeout(2500)
    pg.reload(); pg.wait_for_timeout(1500)
    ok('T13 код убран, правка на месте, база открыта', (not locked(pg)) and first_name(pg)=='Сразу' and 'Сразу' in ls(pg) and vault(pg) is None)
    b.close()

    # T14 код из прежней редакции (4 цифры)
    b,ctx=fresh(p); pg=openp(ctx,OLD); appr(pg); help_tab(pg)
    pg.locator('[data-act=setPin]').first.click(); pg.wait_for_timeout(300); keys(pg,'1234',300); keys(pg,'1234',800)
    pg.close(); pg=openp(ctx)
    ok('T14 4 клеточки для прежнего кода', locked(pg) and dots(pg)==4)
    keys(pg,'1234',5000); ok('T14 прежний код открывает и выдаёт код восстановления', (not locked(pg)) and pg.locator('.reccode').count()==1)
    rec_done(pg); pg.wait_for_timeout(500)
    ok('T14 записи закрыты', '"encV":2' in ls(pg) and 'Соколова' not in ls(pg))
    pg.reload(); pg.wait_for_timeout(1000); ok('T14 после перезапуска 4 клеточки', dots(pg)==4)
    keys(pg,'1234',3000); ok('T14 код подходит', not locked(pg))
    help_tab(pg); ok('T14 подсказка задать 6 цифр', 'шести цифр' in pg.inner_text('#view'))
    b.close()

    # T15 видеовстреча не закрывает кабинет
    b,ctx=fresh(p); pg=openp(ctx); appr(pg); set_code(pg,'123456'); rec_done(pg)
    pg.evaluate("S.settings.myRoom='https://ktalk.ru/test-room';save();document.querySelector('[data-tab=today]').click()"); pg.wait_for_timeout(300)
    with ctx.expect_page() as np_: pg.get_by_role('button',name='Войти во встречу').first.click()
    np_.value.close(); pg.wait_for_timeout(300)
    pg.evaluate("Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(500)
    ok('T15 во время встречи кабинет не закрылся', not locked(pg))
    pg.evaluate("S.ui.meet=null;document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(500)
    ok('T15 без встречи при уходе закрывается', locked(pg))
    b.close()

    # T16 большая база
    b,ctx=fresh(p); pg=openp(ctx); appr(pg)
    pg.evaluate("""(()=>{const s=S.sessions[0];for(let i=0;i<1800;i++){const c=JSON.parse(JSON.stringify(s));c.id='big'+i;c.date=D(-400+(i%390));c.note={tpl:'DAP',d:'x'.repeat(1500)};S.sessions.push(c)}save()})()""")
    size=len(ls(pg)); set_code(pg,'123456'); ok('T16 большая база закрыта кодом', pg.locator('.reccode').count()==1, 'знаков '+str(size)); rec_done(pg)
    pg.reload(); pg.wait_for_timeout(1000); keys(pg,'123456',5000)
    ok('T16 после перезапуска всё на месте', (not locked(pg)) and pg.evaluate("S.sessions.length")>1800)
    pg.evaluate("S.clients[0].name='После кода';save()"); pg.wait_for_timeout(3000); pg.reload(); pg.wait_for_timeout(1000); keys(pg,'123456',5000)
    ok('T16 правка после кода сохранилась', first_name(pg)=='После кода')
    b.close()

    # T17 выход с экрана «Придумайте код»
    b,ctx=fresh(p); pg=openp(ctx); appr(pg); help_tab(pg); pg.locator('[data-act=setPin]').first.click(); pg.wait_for_timeout(300)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300); ok('T17 Esc закрывает «Придумайте код»', not locked(pg))
    pg.locator('[data-act=setPin]').first.click(); pg.wait_for_timeout(300); pg.click('#lock-cancel'); pg.wait_for_timeout(300)
    ok('T17 кнопка «Отмена» закрывает', not locked(pg) and ls(pg).startswith('{"'))
    b.close()

    # T18 дата по часам устройства
    b=p.chromium.launch(args=['--no-proxy-server']); ctx=b.new_context(timezone_id='Asia/Vladivostok'); pg=ctx.new_page(); pg.goto(NEW); pg.wait_for_timeout(800)
    d=pg.evaluate("[D(0), (()=>{const x=new Date();return x.getFullYear()+'-'+String(x.getMonth()+1).padStart(2,'0')+'-'+String(x.getDate()).padStart(2,'0')})()]")
    ok('T18 «сегодня» по местным часам', d[0]==d[1], str(d)); b.close()

print('ИТОГ', sum(1 for r in R if r[1]),'из',len(R))
json.dump(R,open(OUT+'/result.json','w'),ensure_ascii=False,indent=1)
