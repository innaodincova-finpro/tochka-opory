from playwright.sync_api import sync_playwright
U='http://127.0.0.1:8765/v11/index.html'; O='/tmp/claude-0/-home-claude/871422d8-68b2-5fc8-b99e-a6edeea11466/scratchpad/stage1/out/'; R=[]
def ok(n,c,i=''): R.append(bool(c)); print(('OK  ' if c else 'FAIL'),n,i)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-proxy-server'])
    for vp,tag in [((1300,850),'pc'),((390,844),'ph')]:
        ctx=b.new_context(viewport={'width':vp[0],'height':vp[1]},accept_downloads=True); pg=ctx.new_page(); e=[]
        pg.on('pageerror',lambda x:e.append(str(x))); pg.on('dialog',lambda d:d.accept())
        pg.goto(U); pg.wait_for_timeout(900); pg.get_by_role('button',name='Выбрать').first.click(); pg.wait_for_timeout(300)
        pg.evaluate("(()=>{const b=document.createElement('button');b.dataset.act='demoOn';b.hidden=true;document.body.appendChild(b);b.click();b.remove()})()"); pg.wait_for_timeout(300); pg.evaluate("S.settings.spec.name='Анна Ремизова';save()")
        pg.evaluate("go('docs')"); pg.wait_for_timeout(300)
        pg.locator('summary:has-text("Шаблоны документов")').click(); pg.wait_for_timeout(200)
        pg.locator('tr[data-act=tplOpen]').first.click(); pg.wait_for_timeout(400)
        ok(tag+' шаблон открывается с текстом', 'ДОГОВОР-ОФЕРТА' in pg.input_value('#tp-text'))
        pg.screenshot(path=O+f'tpl-{tag}.png')
        if tag=='pc':
            pg.select_option('#tp-c','c1')
            with pg.expect_download() as d: pg.click('[data-act=tplWord]')
            d.value.save_as(O+'tpl.doc'); t=open(O+'tpl.doc',encoding='utf-8-sig').read()
            ok('в Word подставлены клиент и специалист', 'Марина Соколова' in t and 'Анна Ремизова' in t and '[Клиент]' not in t)
            pg.fill('#tp-text', pg.input_value('#tp-text')+'\nДобавлено.'); pg.click('[data-act=tplSave]'); pg.wait_for_timeout(300)
            ok('сохранение текста поднимает версию', pg.evaluate("tpl('t1').ver")=='3.2')
            pg.locator('tr[data-act=tplOpen]').first.click(); pg.wait_for_timeout(300); pg.select_option('#tp-c','c2'); pg.click('[data-act=tplSign]'); pg.wait_for_timeout(300)
            ok('«Отметить подписание» с выбранными документом и клиентом', pg.input_value('#dc-t')=='t1' and pg.input_value('#dc-c')=='c2')
        ok(tag+' ошибок нет', not e, str(e[:1])); ctx.close()
    b.close()
print('ИТОГ',sum(R),'из',len(R))
