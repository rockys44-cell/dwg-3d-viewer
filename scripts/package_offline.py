from pathlib import Path
import base64,re,zipfile,json
r=Path(__file__).resolve().parents[1];dist=r/'web/dist';out=r/'downloads';out.mkdir(exist_ok=True)
h=(dist/'index.html').read_text()
script=re.search(r'<script type="module" crossorigin src="([^"]+)"></script>',h)
style=re.search(r'<link rel="stylesheet" crossorigin href="([^"]+)">',h)
assert script and style
js=(dist/script[1].lstrip('/')).read_text();css=(dist/style[1].lstrip('/')).read_text()
assert not re.search(r'\bimport\s*\(',js),'Unexpected external dynamic import'
data=(dist/'drawing.json').read_text();geom=base64.b64encode((dist/'geometry.bin').read_bytes()).decode()
report=base64.b64encode((r/'drawing_analysis.md').read_bytes()).decode()
bootstrap='''<script>
const drawingPayload=JSON.parse(document.getElementById('drawing-payload').textContent);
const originalFetch=window.fetch.bind(window);
window.fetch=async function(resource,options){
 const name=String(resource).split('/').pop().split('?')[0];
 if(name==='drawing.json')return new Response(JSON.stringify(drawingPayload),{headers:{'Content-Type':'application/json'}});
 if(name==='geometry.bin'){
  const raw=atob(document.getElementById('geometry-payload').textContent.trim());
  const bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);
  return new Response(bytes,{headers:{'Content-Type':'application/octet-stream'}});
 }
 throw new Error('离线版不需要网络：'+name);
};
</script>'''
h=h.replace(script[0],'<script type="module">'+js.replace('</script','<\\/script')+'</script>')
h=h.replace(style[0],'<style>'+css+'</style>')
h=h.replace('href="./drawing_analysis.md" target="_blank"','href="data:text/markdown;charset=utf-8;base64,'+report+'" download="drawing_analysis.md"')
h=h.replace('<div id="app">','<script id="drawing-payload" type="application/json">'+data.replace('</','<\\/')+'</script><script id="geometry-payload" type="application/octet-stream">'+geom+'</script>'+bootstrap+'<div id="app">')
path=out/'双击打开三维网页.html';path.write_text(h,encoding='utf8')
instructions='''宝峰工艺三维网页 · 离线版\n\n1. 解压 ZIP。\n2. 双击“ 双击打开三维网页.html ”，使用 Chrome 或 Edge 打开。\n3. 第一次读取图纸数据需要稍等，文件较大。无需联网、安装或输入命令。\n\n鼠标左键拖动：旋转；右键拖动：平移；滚轮：缩放。\n左侧输入设备名称（例如“缓冲罐”）可搜索，点击结果会定位原图。\n点击“工艺示意”，再点击右下角“流动”，播放工艺示意动画。\n点击“图纸空间”返回源图，点击“总览”恢复视角。\n\n注意：设备外形、高度与流程连线均为示意，不能用于施工。\n原始图纸解析报告附在压缩包内，网页右上角也可下载报告。\n'''
(out/'打开说明.txt').write_text(instructions,encoding='utf8')
with zipfile.ZipFile(out/'宝峰三维网页_解压后双击打开.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 z.write(path,path.name);z.write(out/'打开说明.txt','打开说明.txt');z.write(r/'drawing_analysis.md','drawing_analysis.md')
print(json.dumps({'html_bytes':path.stat().st_size,'zip_bytes':(out/'宝峰三维网页_解压后双击打开.zip').stat().st_size}))
