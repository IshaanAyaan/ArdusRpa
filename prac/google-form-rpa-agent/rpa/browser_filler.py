import re
from playwright.async_api import async_playwright

async def prefill_form(config, headless=False, keep_open=True, fast=False, default_timeout_ms=10000):
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=headless)
        c = await b.new_context()

        # Optional fast mode: block heavy resources to speed up navigation
        if fast:
            async def _block(route):
                req = route.request
                rt = req.resource_type
                if rt in ("image","media","font"):
                    await route.abort()
                else:
                    await route.continue_()
            await c.route("**/*", _block)

        pg = await c.new_page()
        pg.set_default_timeout(default_timeout_ms)
        await pg.goto(config['form_url'], wait_until='domcontentloaded')
        for f in config.get('fields',[]):
            t=f.get('type'); eid=f.get('entry_id'); lbl=f.get('question_label'); val=f.get('value')
            if t in ('text','paragraph') and eid:
                # Prefer visible editable inputs or textarea, avoid hidden/sentinel
                sel=f'input[name="entry.{eid}"]:not([type="hidden"]), textarea[name="entry.{eid}"]'
                loc = pg.locator(sel)
                if await loc.count()>0:
                    try:
                        await loc.first.fill(str(val))
                    except Exception:
                        pass
            elif t=='date' and eid:
                m=re.match(r"(\d{4})-(\d{2})-(\d{2})$", str(val))
                if m:
                    y,mo,d=m.groups()
                    for suf,v in (('_year',y),('_month',str(int(mo))),('_day',str(int(d)))):
                        sel=f'[name="entry.{eid}{suf}"]';
                        if await pg.locator(sel).count()>0: await pg.fill(sel, v)
            elif t=='time' and eid:
                m=re.match(r"(\d{2}):(\d{2})$", str(val))
                if m:
                    hh,mm=m.groups()
                    for suf,v in (('_hour',str(int(hh))),('_minute',f"{int(mm):02d}")):
                        sel=f'[name="entry.{eid}{suf}"]';
                        if await pg.locator(sel).count()>0: await pg.fill(sel, v)
            elif t=='dropdown' and eid:
                sel=f'select[name="entry.{eid}"]'
                if await pg.locator(sel).count()>0:
                    await pg.select_option(sel, label=str(val))
            elif t=='choice':
                r = pg.get_by_role('radio', name=re.compile(rf'^{re.escape(str(val))}$', re.I))
                if await r.count()>0:
                    try:
                        await r.first.scroll_into_view_if_needed()
                        await r.first.check()
                    except Exception:
                        pass
            elif t=='checkbox':
                vals=val if isinstance(val, list) else [str(val)]
                for o in vals:
                    cb = pg.get_by_role('checkbox', name=re.compile(rf'^{re.escape(o)}$', re.I))
                    if await cb.count()>0:
                        try:
                            await cb.first.scroll_into_view_if_needed()
                            await cb.first.check()
                        except Exception:
                            pass
        print('✅ Prefill done.' + (' Browser left open. (No submit).' if keep_open else ''))
        if keep_open:
            try:
                while True:
                    await pg.wait_for_timeout(60000)
            except KeyboardInterrupt:
                pass
            except Exception:
                # If page or browser closed externally, exit gracefully
                pass
        await c.close(); await b.close()
