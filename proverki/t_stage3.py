from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8765/v11/index.html'; R=[]
def ok(n,c,i=''): R.append(bool(c)); print(('OK  ' if c else 'FAIL'),n,i)
def act(pg,a,**kw):
    pg.evaluate("""([a,kw])=>{const b=document.createElement('button');b.dataset.act=a;Object.entries(kw).forEach(([k,v])=>b.dataset[k]=v);b.hidden=true;document.body.appendChild(b);b.click();b.remove()}""",[a,kw]); pg.wait_for_timeout(350)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-proxy-server']); ctx=b.new_context(viewport={'width':390,'height':844})
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('dialog',lambda d:d.accept())
    pg.goto(U); pg.wait_for_timeout(900)
    ok('первый вход — пустой кабинет', pg.evaluate("S.clients.length===0&&S.sessions.length===0"))
    pg.get_by_role('button',name='Выбрать').first.click(); pg.wait_for_timeout(300)
    ok('экран «С чего начать»', pg.locator('text=С чего начать').count()==1)
    act(pg,'demoOn'); ok('пример открыт и отмечен полосой', pg.evaluate("S.clients.length>5") and pg.is_visible('#demobar'))
    act(pg,'demoOff'); ok('выход из примера — пусто', pg.evaluate("S.clients.length===0") and not pg.is_visible('#demobar'))
    pg.reload(); pg.wait_for_timeout(900); ok('после перезапуска пусто, без вопроса о подходе', pg.evaluate("S.clients.length===0") and pg.locator('text=Как вы работаете').count()==0)
    # клиент с постоянным временем
    act(pg,'newClient'); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)"); pg.fill('#c-name','Ирина Тестова'); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)"); pg.select_option('#c-sd','3'); pg.wait_for_timeout(100)
    pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)"); pg.fill('#c-st','11:00'); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)"); pg.select_option('#c-status','в работе'); pg.click('[data-act=saveClient]'); pg.wait_for_timeout(600)
    ok('после сохранения предложено расставить встречи', pg.locator('#modal h3').inner_text()=='Расставить встречи')
    pg.click('[data-act=seriesGo]'); pg.wait_for_timeout(300)
    n=pg.evaluate("S.sessions.length"); ok('встречи на 4 недели расставлены по средам', n in (4,5) and pg.evaluate("S.sessions.every(v=>pd(v.date).getDay()===3&&v.time==='11:00')"), str(n))
    cid=pg.evaluate("S.clients[0].id")
    n_before=pg.evaluate("S.sessions.length"); act(pg,'series',id=cid); ok('повторная расстановка не задваивает', pg.locator('#toast:has-text("все встречи уже стоят")').count()==1 and pg.evaluate("S.sessions.length")==n_before); act(pg,'closeModal')
    # пересечение
    d0=pg.evaluate("S.sessions[0].date")
    act(pg,'newClient'); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)"); pg.fill('#c-name','Олег Второй'); pg.click('[data-act=saveClient]'); pg.wait_for_timeout(400)
    act(pg,'newSess',date=d0,time='11:30',cid=pg.evaluate("S.clients[1].id"))
    pg.fill('#s-t','11:30'); pg.dispatch_event('#s-t','change'); pg.wait_for_timeout(150)
    ok('предупреждение о занятом времени видно в окне', pg.is_visible('#s-busy') and 'Ирина' in pg.inner_text('#s-busy'), pg.inner_text('#s-busy'))
    pg.click('[data-act=createSess]'); pg.wait_for_timeout(300)
    ok('записать можно после подтверждения', pg.evaluate("S.sessions.length")==n+1)
    # перенос
    sid=pg.evaluate("S.sessions[0].id"); act(pg,'openSess',id=sid)
    ok('кнопка «Перенести» в карточке', pg.locator('[data-act=moveSess]').count()==1)
    pg.click('[data-act=moveSess]'); pg.wait_for_timeout(300)
    nd=pg.evaluate("D(30)"); pg.fill('#mv-d',nd); pg.fill('#mv-t','15:00'); pg.click('[data-act=moveGo]'); pg.wait_for_timeout(300)
    v=pg.evaluate("id=>{const v=sess(id);return [v.date,v.time,v.status,(cl(v.cid)||{}).debt||0]}",sid)
    ok('перенос: новая дата и время, статус тот же, долга нет', v[0]==nd and v[1]=='15:00' and v[2]=='запланирована' and v[3]==0, str(v))
    # удаление встречи и отмена
    k=pg.evaluate("S.sessions.length"); act(pg,'delSess',id=sid)
    ok('встреча удалена', pg.evaluate("S.sessions.length")==k-1)
    pg.evaluate("doUndo()"); pg.wait_for_timeout(300); ok('удаление отменяется', pg.evaluate("S.sessions.length")==k)
    # платёж
    pg.evaluate("S.pays.push({id:'pp1',cid:S.clients[0].id,date:D(0),sum:3000,method:'СБП',sid:'',check:false,purpose:'Консультация'});save()")
    act(pg,'delPay',id='pp1'); ok('платёж удалён', pg.evaluate("!S.pays.some(p=>p.id==='pp1')"))
    # клиент
    act(pg,'editClient',id=cid); ok('кнопка «Удалить клиента» в карточке', pg.locator('[data-act=delClient]').count()==1)
    pg.click('[data-act=delClient]'); pg.wait_for_timeout(300)
    ok('клиент и его встречи удалены', pg.evaluate("id=>!S.clients.some(c=>c.id===id)&&!S.sessions.some(v=>v.cid===id)",cid))
    # отпуск
    pg.evaluate("S.sessions.push({id:'o1',cid:S.clients[0].id,date:D(3),time:'10:00',dur:50,status:'запланирована',type:'регулярная',fmt:'очно',price:1000});save()")
    act(pg,'offNew'); pg.fill('#of-a',pg.evaluate("D(2)")); pg.fill('#of-b',pg.evaluate("D(5)")); pg.click('[data-act=offGo]'); pg.wait_for_timeout(300)
    ok('отпуск: встреча в эти дни отменена', pg.evaluate("sess('o1').status")=='отменена специалистом')
    pg.evaluate("go('sched')"); pg.wait_for_timeout(300); ok('отпуск виден в календаре', pg.locator('.cal .d.off').count()==4)
    # второй участник в карточке встречи
    pg.evaluate("S.sessions.push({id:'pp',cid:S.clients[0].id,date:D(8),time:'12:00',dur:50,status:'запланирована',type:'регулярная',fmt:'очно',price:1000});save()")
    act(pg,'openSess',id='pp'); pg.evaluate("document.querySelectorAll('#modal details').forEach(d=>d.open=true)"); pg.select_option('#v-type','парная'); pg.wait_for_timeout(100)
    ok('поле второго участника появляется в карточке', pg.is_visible('#v-partner'))
    ok('ошибок страницы нет', not errs, str(errs[:2]))
    b.close()
print('ИТОГ',sum(R),'из',len(R))
