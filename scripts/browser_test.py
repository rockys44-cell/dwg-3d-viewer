"""Exercise WebGL rendering and the actual viewer UI in Chromium."""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright, expect
from PIL import Image,ImageChops,ImageStat
R=Path(__file__).resolve().parents[1]
url=os.environ.get('VIEWER_TEST_URL','http://127.0.0.1:5173')
checks=[]
def passed(name):checks.append({'name':name,'status':'passed'});print('PASS',name,flush=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1512,'height':982},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 response=page.goto(url,wait_until='networkidle',timeout=120000);assert response.status==200
 page.wait_for_function('window.__viewer?.ready || window.__viewer?.error',timeout=120000)
 assert page.evaluate('window.__viewer.ready'),page.evaluate('window.__viewer.error')
 assert page.locator('#device-count').inner_text()=='243';assert page.locator('#text-count').inner_text()=='647'
 page.wait_for_function('window.__viewer.frame > 5');passed('Data load and actual WebGL draw frames')
 rect=page.locator('#canvas-host').bounding_box();assert 300<rect['height']<1000
 page.screenshot(path=str(R/'analysis/viewer-drawing.png'));passed('Canvas fits viewport and original drawing screenshot captured')
 page.locator('#search').fill('缓冲罐');expect(page.locator('#list-count')).to_have_text('5');page.locator('.item').first.click()
 expect(page.locator('#detail-name')).to_have_text('缓冲罐');assert page.locator('#focus-selected').is_enabled();passed('Device name search, source inspector and focus')
 page.locator('#tab-texts').click();page.locator('#search').fill('基础开挖');assert int(page.locator('#list-count').inner_text())>0
 page.locator('.item').first.click();assert '基础开挖' in page.locator('#detail-name').inner_text();passed('Chinese annotation search and transformed position focus')
 page.locator('#search').fill('');page.locator('#tab-layers').click();cb=page.locator('input[data-layer="1-设备轮廓"]');cb.uncheck();assert not cb.is_checked();cb.check();assert cb.is_checked();passed('Layer visibility controls')
 page.locator('#toggle-labels').click();assert page.locator('#toggle-labels').get_attribute('aria-pressed')=='true';passed('Drawing title annotation toggle')
 page.locator('#mode-process').click();page.wait_for_function('window.__viewer.mode === "process" && window.__viewer.camera[1] < 40')
 assert page.locator('#process-note').is_visible();assert '未经原图拓扑确认' in page.locator('#process-note').inner_text();passed('Process mode carries explicit topology limitation')
 page.locator('#toggle-flow').click();assert page.locator('#toggle-flow').get_attribute('aria-pressed')=='true';frame=page.evaluate('window.__viewer.frame');page.wait_for_function(f'window.__viewer.frame > {frame+3}');passed('Flow animation renders advancing frames')
 # Hit real meshes through the canvas rather than the DOM inventory.
 page.locator('#tab-devices').click();page.locator('#search').fill('')
 before=page.locator('#detail-name').inner_text();hit=False
 rect=page.locator('#canvas-host').bounding_box()
 for fx,fy in [(.40,.37),(.38,.40),(.42,.48),(.51,.52),(.64,.60),(.52,.67),(.70,.50)]:
  page.mouse.click(rect['x']+rect['width']*fx,rect['y']+rect['height']*fy)
  if page.locator('#focus-selected').is_enabled() and page.locator('#detail-name').inner_text()!=before:hit=True;break
 assert hit,'Canvas raycast did not select any rendered device'
 passed('Canvas raycast selects a real rendered equipment mesh')
 page.locator('#reset').click();page.wait_for_timeout(900);page.screenshot(path=str(R/'analysis/viewer-process.png'))
 # Distinct screenshots guard against accepting a completely blank canvas as readiness.
 a=Image.open(R/'analysis/viewer-drawing.png').convert('RGB');b=Image.open(R/'analysis/viewer-process.png').convert('RGB')
 crop=(int(rect['x']+80),int(rect['y']+100),int(rect['x']+rect['width']-80),int(rect['y']+rect['height']-80))
 assert sum(ImageStat.Stat(ImageChops.difference(a.crop(crop),b.crop(crop))).mean)>3
 passed('Drawing and process modes produce distinct visible canvas content')
 # Orbit, zoom and top-view controls change the actual camera.
 previous=page.evaluate('window.__viewer.camera');page.mouse.move(rect['x']+300,rect['y']+200);page.mouse.down();page.mouse.move(rect['x']+400,rect['y']+230,steps=6);page.mouse.up();page.wait_for_timeout(300)
 assert page.evaluate('window.__viewer.camera')!=previous
 page.locator('#top-view').click();page.wait_for_timeout(900);assert page.evaluate('window.__viewer.camera[1]')>40
 passed('Orbit and top-view camera controls')
 report=page.request.get(url+'/drawing_analysis.md');assert report.ok and '243' in report.text();passed('Analysis report is served successfully')
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(300)
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1');assert page.locator('#canvas-host').bounding_box()['height']>=370
 page.screenshot(path=str(R/'analysis/viewer-mobile.png'));passed('Mobile viewport has usable canvas and no horizontal overflow')
 assert not errors,errors;passed('No uncaught browser JavaScript errors')
 result={'status':'passed','url':url,'checks':checks,'count':len(checks),'pageErrors':errors,'renderer':page.evaluate('window.__viewer')}
 (R/'logs/browser-test.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 browser.close()
print(f'PASS: {len(checks)} browser checks')
