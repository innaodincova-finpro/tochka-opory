# Обмен через Яндекс Диск: два отдельных устройства и поддельный Диск.
import json, hashlib, sys
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
URL='http://127.0.0.1:8765/v11/index.html'
STORE={}; OK=[]; BAD=[]
def ok(n,c):
    (OK if c else BAD).append(n); print(('ok   ' if c else 'FAIL ')+n)
CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Authorization, Content-Type, Accept','Access-Control-Allow-Methods':'GET, PUT, OPTIONS'}
def handler(route):
    rq=route.request;u=urlparse(rq.url)
    if rq.method=='OPTIONS':return route.fulfill(status=200,headers=CORS,body='')
    if u.netloc=='cloud-api.yandex.net':
        if rq.headers.get('authorization','')!='OAuth TOKEN1':return route.fulfill(status=401,headers=CORS,body='{}')
        q=parse_qs(u.query);p=q.get('path',[''])[0]
        if u.path.endswith('/resources'):
            if p not in STORE:return route.fulfill(status=404,headers=CORS,body='{}')
            return route.fulfill(status=200,headers=CORS,content_type='application/json',body=json.dumps({'md5':hashlib.md5(STORE[p].encode()).hexdigest(),'modified':'x'}))
        if u.path.endswith('/download'):
            if p not in STORE:return route.fulfill(status=404,headers=CORS,body='{}')
            return route.fulfill(status=200,headers=CORS,content_type='application/json',body=json.dumps({'href':'https://downloader.mock/get?p='+p}))
        if u.path.endswith('/upload'):
            return route.fulfill(status=200,headers=CORS,content_type='application/json',body=json.dumps({'href':'https://uploader.mock/put?p='+p,'method':'PUT'}))
    if u.netloc=='downloader.mock':
        p=parse_qs(u.query)['p'][0];return route.fulfill(status=200,headers=CORS,body=STORE[p])
    if u.netloc=='uploader.mock':
        p=parse_qs(u.query)['p'][0];STORE[p]=rq.post_data;return route.fulfill(status=201,headers=CORS,body='')
    route.abort()
def dev(b):
    c=b.new_context(viewport={'width':1280,'height':800});pg=c.new_page();pg.on('dialog',lambda d:d.accept())
    for h in ['https://cloud-api.yandex.net/**','https://downloader.mock/**','https://uploader.mock/**']:pg.route(h,handler)
    errs=[];pg.on('pageerror',lambda e:errs.append(str(e)));pg.errs=errs
    pg.goto(URL);pg.wait_for_timeout(900)
    if pg.locator('text=Выбрать').count():pg.get_by_role('button',name='Выбрать').first.click();pg.wait_for_timeout(300)
    return pg
def ev(pg,s):return pg.evaluate(s)
def sync(pg,ms=1500):ev(pg,"YA_BUSY=false;yaSync()");pg.wait_for_timeout(ms)
F='app:/tochka-opory.json'
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-proxy-server'])
    A=dev(b)
    ok('раздел «Телефон и компьютер» в Настройках',(ev(A,"go('help');document.getElementById('ya-sec')!==null")))
    ev(A,"S.clients.push({id:'k1',name:'Ирина Петрова',status:'в работе',code:'К-1'});S.changedAt=new Date().toISOString();save()")
    ev(A,"enableEnc('123456').then(()=>{save()})");A.wait_for_timeout(2500)
    ok('устройство 1: код задан',ev(A,"ENC_ON&&!!ENC"))
    ev(A,"yaSet({t:'TOKEN1',exp:Date.now()+1e9})")
    sync(A,2500)
    ok('устройство 1: файл отправлен на Диск',F in STORE)
    f=json.loads(STORE.get(F,'{}'))
    ok('файл на Диске закрыт (нет имени клиента в открытом виде)','Ирина' not in STORE.get(F,'') and f.get('encV')==2)
    B=dev(b)
    ev(B,"yaSet({t:'TOKEN1',exp:Date.now()+1e9})");sync(B,2500)
    ok('устройство 2: спрашивает код для записей с Диска',B.locator('#ya-code').count()==1)
    B.fill('#ya-code','111111');B.locator('[data-act=yaCode]').click();B.wait_for_timeout(2500)
    ok('устройство 2: неверный код не принимается',ev(B,"!S.clients.some(c=>c.id==='k1')"))
    B.fill('#ya-code','123456');B.locator('[data-act=yaCode]').click();B.wait_for_timeout(3500)
    ok('устройство 2: записи приняты',ev(B,"S.clients.some(c=>c.id==='k1'&&c.name==='Ирина Петрова')"))
    ok('устройство 2: записи закрыты тем же кодом',ev(B,"ENC_ON&&!!ENC"))
    # изменения с двух сторон
    ev(B,"S.clients.push({id:'k2',name:'Олег Смирнов',status:'в работе',code:'К-2'});S.changedAt=new Date().toISOString();save()");B.wait_for_timeout(1500)
    sync(B,2500)
    A.wait_for_timeout(300);ev(A,"cl('k1').name='Ирина Петрова-Ким';save()");A.wait_for_timeout(1500)
    sync(A,3000)
    ok('устройство 1: получило клиента с устройства 2',ev(A,"S.clients.some(c=>c.id==='k2')"))
    ok('устройство 1: своя правка сохранилась',ev(A,"cl('k1').name==='Ирина Петрова-Ким'"))
    sync(B,3000)
    ok('устройство 2: получило правку с устройства 1',ev(B,"cl('k1').name==='Ирина Петрова-Ким'"))
    # удаление
    ev(B,"S.clients=S.clients.filter(c=>c.id!=='k2');save()");B.wait_for_timeout(1500);sync(B,2500);sync(A,3000)
    ok('удаление на устройстве 2 дошло до устройства 1',ev(A,"!S.clients.some(c=>c.id==='k2')"))
    # настройка
    ev(A,"S.settings.price=5500;save()");A.wait_for_timeout(1500);sync(A,2500);sync(B,3000)
    ok('настройка с устройства 1 дошла до устройства 2',ev(B,"S.settings.price===5500"))
    # повтор без изменений не отправляет файл заново
    before=STORE[F];sync(A,2000);sync(B,2000)
    ok('без изменений файл не перезаписывается',STORE[F]==before)
    # смена кода на устройстве 1
    ev(A,"(async()=>{await writeMeta({pinLen:6,pin:await wrapDek(ENC.dek,'654321',KDF_PIN),rec:ENC.meta.rec})})()");A.wait_for_timeout(3000)
    sync(A,2500);sync(B,4000)
    ok('устройство 2: принят новый код входа',ev(B,"(async()=>{try{await unwrapDek(ENC.meta.pin,'654321');return true}catch(e){return false}})()"))
    # перезапуск устройства 2 — записи открываются новым кодом
    B.reload();B.wait_for_timeout(1500)
    for d in '654321':B.keyboard.press(d);B.wait_for_timeout(60)
    B.wait_for_timeout(2500)
    ok('устройство 2 после перезапуска открывается новым кодом',ev(B,"!LOCKED&&S.clients.some(c=>c.id==='k1')"))
    # пример не отправляется и не смешивается
    C=dev(b);C.locator('[data-act=demoOn]').first.click();C.wait_for_timeout(1500)
    before=STORE[F];ev(C,"yaSet({t:'TOKEN1',exp:Date.now()+1e9})");sync(C,2500)
    ok('пример с вымышленными клиентами на Диск не уходит',STORE[F]==before and C.locator('#ya-code').count()==0)
    # с чего начать: кнопка подключения
    D=dev(b);ok('на пустом кабинете есть «Подключить Яндекс Диск»',D.locator('#view [data-act=yaConnect]').count()==1)
    ok('ошибок в коде нет',not A.errs and not B.errs and not C.errs)
    if A.errs or B.errs:print(A.errs,B.errs)
    b.close()
print(len(OK),'ok',len(BAD),'fail')
sys.exit(1 if BAD else 0)
