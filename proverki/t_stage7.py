from playwright.sync_api import sync_playwright
R=[]
def ok(n,c,i=''): R.append(c); print(('OK  ' if c else 'FAIL'),n,i)
def act(pg,a,**d):
    pg.evaluate("([a,d])=>{const b=document.createElement('button');b.dataset.act=a;Object.assign(b.dataset,d);b.hidden=true;document.body.appendChild(b);b.click();b.remove()}",[a,d]); pg.wait_for_timeout(250)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-proxy-server']); pg=b.new_page(viewport={'width':1300,'height':900}); e=[]; pg.on('pageerror',lambda x:e.append(str(x))); pg.on('dialog',lambda d:d.accept())
    pg.goto('http://127.0.0.1:8765/v11/index.html'); pg.wait_for_timeout(900); pg.get_by_role('button',name='Выбрать').first.click(); pg.wait_for_timeout(300); act(pg,'demoOn'); pg.wait_for_timeout(500)
    # пакет списывается сам
    vid=pg.evaluate("(()=>{const v=S.sessions.find(v=>v.cid==='c1'&&v.status==='подтверждена');return v.id})()")
    u0=pg.evaluate("pack('c1')[0].used")
    pg.evaluate(f"sessModal('{vid}')"); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)")
    pg.select_option('#v-status','состоялась'); pg.select_option('#v-pay','пакет'); act(pg,'saveSess',id=vid)
    ok('встреча из пакета списана сама',pg.evaluate("pack('c1')[0].used")==u0+1)
    pg.evaluate(f"sessModal('{vid}')"); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)")
    act(pg,'saveSess',id=vid)
    ok('повторное сохранение не списывает второй раз',pg.evaluate("pack('c1')[0].used")==u0+1)
    pg.evaluate(f"sessModal('{vid}')"); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)")
    pg.select_option('#v-status','подтверждена'); act(pg,'saveSess',id=vid)
    ok('снятие отметки возвращает встречу в пакет',pg.evaluate("pack('c1')[0].used")==u0)
    # пауза
    pg.evaluate("(()=>{const c=S.clients.find(c=>c.status==='в работе');S.sessions=S.sessions.filter(v=>!(v.cid===c.id&&v.date>=D(0)));doneSess(c.id).forEach(v=>v.date=D(-40));save();S.ui.tab='clients';S.ui.client=c.id;render()})()"); pg.wait_for_timeout(300)
    ok('подсказка о паузе в карточке',pg.locator('#view [data-act=setPause]').count()==1)
    pg.click('#view [data-act=setPause]'); pg.wait_for_timeout(200)
    ok('статус пауза',pg.evaluate("cl(S.ui.client).status")=='пауза')
    # город клиента
    act(pg,'newClient'); pg.fill('#c-name','Тест Городов'); pg.select_option('#c-city','Новосибирск'); act(pg,'saveClient')
    ok('разница во времени посчитана',pg.evaluate("(()=>{const c=S.clients.find(c=>c.name==='Тест Городов');return c.tzOff===7-myUtc()&&/^К-\\d{3}$/.test(c.code)})()"))
    ok('нет поля долга в форме',(act(pg,'newClient') or True) and pg.locator('#c-debt').count()==0); pg.evaluate("closeModal()")
    pg.evaluate("go('help')"); ok('версия в справке','в36' in pg.text_content('#view'))
    ok('в Настройках нет запроса данных и выхода из примера',pg.locator('#view summary:has-text("Запрос клиента")').count()==0 and pg.locator('#view [data-act=demoOff]').count()==0)
    pg.evaluate("go('superv')"); ok('кнопки вопроса супервизору нет',pg.locator('[data-act=aiSuperv]').count()==0)
    ok('ошибок нет',not e,str(e)); b.close()
print('ИТОГ',sum(R),'из',len(R))
