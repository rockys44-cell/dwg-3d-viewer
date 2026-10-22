from pathlib import Path
import json
from playwright.sync_api import sync_playwright,expect
r=Path(__file__).resolve().parents[1];checks=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 context=b.new_context(offline=True,viewport={'width':1512,'height':982})
 page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route('http://127.0.0.1:5173/offline-viewer.html',lambda route:route.fulfill(path=str(r/'downloads/双击打开三维网页.html'),content_type='text/html; charset=utf-8'))
 page.goto('http://127.0.0.1:5173/offline-viewer.html',wait_until='load',timeout=120000)
 page.wait_for_function('window.__viewer?.ready || window.__viewer?.error',timeout=120000)
 assert page.evaluate('window.__viewer.ready'),page.evaluate('window.__viewer.error');checks.append('离线 HTML 在断网浏览器中通过本地响应注入加载，WebGL 渲染成功')
 expect(page.locator('#device-count')).to_have_text('243');checks.append('完整图纸数据无需网络加载')
 page.locator('#search').fill('缓冲罐');expect(page.locator('#list-count')).to_have_text('5');page.locator('.item').first.click();expect(page.locator('#detail-name')).to_have_text('缓冲罐');checks.append('中文设备搜索和原图定位')
 page.locator('#mode-process').click();page.wait_for_function('window.__viewer.mode === "process" && window.__viewer.camera[1] < 40')
 page.locator('#toggle-flow').click();expect(page.locator('#toggle-flow')).to_have_attribute('aria-pressed','true');n=page.evaluate('window.__viewer.renders');page.wait_for_function(f'window.__viewer.renders > {n+2}');checks.append('流程动画实际绘制')
 rect=page.locator('#canvas-host').bounding_box();old=page.evaluate('window.__viewer.camera');page.mouse.move(rect['x']+300,rect['y']+200);page.mouse.down();page.mouse.move(rect['x']+400,rect['y']+250,steps=6);page.mouse.up();page.wait_for_timeout(500);assert old!=page.evaluate('window.__viewer.camera');checks.append('鼠标拖动旋转')
 old=page.evaluate('window.__viewer.camera');page.mouse.wheel(0,-400);page.wait_for_timeout(500);assert old!=page.evaluate('window.__viewer.camera');checks.append('滚轮缩放')
 assert not errors,errors;checks.append('无未捕获 JavaScript 错误')
 page.screenshot(path=str(r/'analysis/viewer-offline.png'))
 (r/'logs/offline-test.json').write_text(json.dumps({'status':'passed','network':'offline','harness':'Playwright route.fulfill supplies the HTML without network; managed Chromium blocks file:// navigation, so direct local-file navigation was not validated in this cloud machine','checks':checks,'pageErrors':errors},ensure_ascii=False,indent=2))
 print('PASS offline:',len(checks),'checks',flush=True);b.close()
