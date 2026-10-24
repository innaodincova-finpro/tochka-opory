# Доступ по коду: поддельная проверка доступа, кабинет и страница управления.
import json,sys
from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8765/v11/index.html?gate=1'
ST={'codes':{'ABCD-2345':{'disabled':False,'label':'','devs':[]}},'mode':'ok'}
OK=[];BAD=[]
def ok(n,c):(OK if c else BAD).append(n);print(('ok   ' if c else 'FAIL ')+n)
CORS={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type','Access-Control-Allow-Methods':'POST, OPTIONS'}
def fn(route):
    rq=route.request
    if rq.method=='OPTIONS':return route.fulfill(status=200,headers=CORS,body='ok')
    if ST['mode']=='down':return route.abort()
    b=json.loads(rq.post_data or '{}');a=b.get('action')
    R=lambda o,s=200:route.fulfill(status=s,headers=CORS,content_type='application/json',body=json.dumps(o))
    norm=lambda c:''.join(ch for ch in str(c).upper() if ch.isalnum());fmt=lambda n:n[:4]+'-'+n[4:8]
    if a=='check':
        c=fmt(norm(b.get('code','')));x=ST['codes'].get(c)
        if not x:return R({'ok':False,'reason':'bad'})
        if x['disabled']:return R({'ok':False,'reason':'off'})
        if b['device'] in x['devs']:return R({'ok':True,'code':c})
        if len(x['devs'])>=3:return R({'ok':False,'reason':'limit'})
        x['devs'].append(b['device']);return R({'ok':True,'code':c})
    if b.get('pass')!='PASS-WORD-TEST-0000':return R({'ok':False,'reason':'pass'},403)
    if a=='list':return R({'ok':True,'codes':[{'code':k,'label_enc':v['label'],'created_at':'2026-10-24T05:00:00Z','disabled':v['disabled'],'max_devices':3} for k,v in ST['codes'].items()],
        'devices':[{'code':k,'device':d,'kind':'компьютер, Chrome','last_at':'2026-10-24T05:10:00Z'} for k,v in ST['codes'].items() for d in v['devs']],'attempts':[]})
    if a=='issue':ST['codes']['WXYZ-6789']={'disabled':False,'label':b['label'],'devs':[]};return R({'ok':True,'code':'WXYZ-6789'})
    if a in('disable','enable'):ST['codes'][b['code']]['disabled']=(a=='disable');return R({'ok':True})
    return R({'ok':True})
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-proxy-server'])
    ctx=b.new_context(viewport={'width':1280,'height':800});ctx.route('https://qughzpirpovjwxjttcyv.supabase.co/**',fn)
    pg=ctx.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('dialog',lambda d:d.accept())
    pg.goto(U);pg.wait_for_timeout(1200)
    vis=lambda:pg.evaluate("!document.getElementById('accscr').hidden")
    ok('без кода кабинет закрыт окном «Введите код доступа»',vis() and 'Введите код доступа' in pg.text_content('#acc-title'))
    ok('кнопки «Скачать записи» на первом входе нет',pg.evaluate("document.getElementById('acc-save').hidden"))
    pg.fill('#acc-in','ABC');pg.click('#acc-go');pg.wait_for_timeout(300)
    ok('короткий код: подсказка о формате','8 знаков' in pg.text_content('#acc-msg'))
    pg.fill('#acc-in','QQQQ-QQQQ');pg.click('#acc-go');pg.wait_for_timeout(600)
    ok('неверный код не пускает','Такого кода нет' in pg.text_content('#acc-msg') and vis())
    pg.fill('#acc-in','abcd 2345');pg.press('#acc-in','Enter');pg.wait_for_timeout(800)
    ok('верный код (маленькими буквами, с пробелом) пускает',not vis())
    pg.reload();pg.wait_for_timeout(1500)
    ok('после перезапуска код не спрашивается',not vis())
    # пример, чтобы были записи, затем отключение
    pg.evaluate("(()=>{const b=document.createElement('button');b.dataset.act='demoOn';document.body.appendChild(b);b.click();b.remove()})()");pg.wait_for_timeout(800)
    ST['codes']['ABCD-2345']['disabled']=True
    pg.reload();pg.wait_for_timeout(1800)
    ok('отключённый код: «Доступ закрыт»',vis() and 'Доступ закрыт' in pg.text_content('#acc-title') and 'закрыт' in pg.text_content('#acc-note'))
    ok('при закрытом доступе можно скачать свои записи',not pg.evaluate("document.getElementById('acc-save').hidden"))
    ST['codes']['ABCD-2345']['disabled']=False
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))");pg.reload();pg.wait_for_timeout(1800)
    ok('включённый снова код открывает кабинет сам',not vis())
    ST['mode']='down';pg.reload();pg.wait_for_timeout(1800)
    ok('без интернета, но с недавней проверкой — кабинет работает',not vis())
    pg.evaluate("(()=>{const a=JSON.parse(localStorage.getItem(KEY+'-acc'));a.ok=new Date(Date.now()-20*864e5).toISOString();localStorage.setItem(KEY+'-acc',JSON.stringify(a))})()")
    pg.reload();pg.wait_for_timeout(1800)
    ok('без интернета 20 дней — нужна проверка доступа',vis() and 'проверка' in pg.text_content('#acc-title'))
    ST['mode']='ok';pg.click('#acc-go');pg.wait_for_timeout(800)
    ok('появился интернет — «Войти» открывает кабинет',not vis())
    # лимит устройств
    for i in range(3):
        c2=b.new_context();c2.route('https://qughzpirpovjwxjttcyv.supabase.co/**',fn);q=c2.new_page();q.goto(U);q.wait_for_timeout(900)
        q.fill('#acc-in','ABCD-2345');q.click('#acc-go');q.wait_for_timeout(700)
        last=q.text_content('#acc-msg');hid=q.evaluate("document.getElementById('accscr').hidden");c2.close()
    ok('четвёртое устройство с тем же кодом не пускается','других устройствах' in last and not hid)
    ok('ошибок в коде кабинета нет',not errs)
    # страница управления
    a=ctx.new_page();aerr=[];a.on('pageerror',lambda e:aerr.append(str(e)));a.on('dialog',lambda d:d.accept())
    a.goto('http://127.0.0.1:8765/v11/upravlenie.html');a.wait_for_timeout(600)
    a.fill('#pw','wrong');a.click('#go');a.wait_for_timeout(600)
    ok('управление: чужой пароль не пускает','не подошёл' in a.text_content('#lmsg'))
    a.fill('#pw','pass-word-test-0000');a.click('#go');a.wait_for_timeout(1200)
    ok('управление: свой пароль пускает, виден список',not a.evaluate("document.getElementById('app').hidden") and 'ABCD-2345' in a.text_content('#list'))
    a.fill('#nm','Мария Иванова');a.click('#issue');a.wait_for_timeout(2500)
    ok('выдан код и готово сообщение',a.text_content('#new-code')=='WXYZ-6789' and 'WXYZ-6789' in a.input_value('#new-msg') and 'innaodincova-finpro.github.io/tochka-opory' in a.input_value('#new-msg'))
    ok('имя на сервер уходит закрытым','Мария' not in ST['codes']['WXYZ-6789']['label'] and ST['codes']['WXYZ-6789']['label'].startswith('v1.'))
    ok('в списке имя читается','Мария Иванова' in a.text_content('#list'))
    a.click('button[data-a=disable][data-c="WXYZ-6789"]');a.wait_for_timeout(1500)
    ok('отключение кода',ST['codes']['WXYZ-6789']['disabled'] and 'отключён' in a.text_content('#list'))
    a.set_viewport_size({'width':390,'height':844});a.wait_for_timeout(300);a.screenshot(path='../adm_ph.png',full_page=True)
    a.set_viewport_size({'width':1280,'height':800});a.screenshot(path='../adm_pc.png',full_page=True)
    pg.close();q2=ctx.new_page();ctx.clear_cookies();q2.goto('http://127.0.0.1:8765/v11/index.html?gate=1');q2.evaluate("localStorage.clear()");q2.reload();q2.wait_for_timeout(1000);q2.screenshot(path='../acc_pc.png')
    q2.set_viewport_size({'width':390,'height':844});q2.wait_for_timeout(300);q2.screenshot(path='../acc_ph.png')
    ok('ошибок на странице управления нет',not aerr)
    b.close()
print(len(OK),'ok',len(BAD),'fail');sys.exit(1 if BAD else 0)
