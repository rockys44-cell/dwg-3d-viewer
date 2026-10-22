"""Build the analysis report from this run's exported DXF inventory."""
from pathlib import Path
from collections import Counter
import json, shutil
R=Path(__file__).resolve().parents[1]
def read(name):return json.loads((R/'analysis'/name).read_text())
def cell(s):return str(s).replace('|','\\|').replace('\n',' / ')
def table(headers,rows):
 return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join('---' for _ in headers)+' |']+['| '+' | '.join(cell(x) for x in row)+' |' for row in rows])
s=read('summary.json');layers=read('layers.json');blocks=read('blocks.json');devices=read('devices.json');entities=read('entities.json');audit=read('audit.json');texts=read('texts.json')
texttypes=Counter(t['type'] for t in texts)
fixes=Counter(e['code'] for e in audit['fixes'])
report=f'''# 湖南宝峰配料工艺图 T6 · DXF 解析报告

## 结论与识别数量

已实际使用 **GNU LibreDWG 0.13.4** 将 AutoCAD 2004–2006 DWG 转换为 `converted.dxf`（AC1018），并由 **ezdxf 1.4.4** 成功读取。原图单位为毫米，中文编码为 GBK/ANSI_936。

{table(['项目','数量','统计口径'],[
['设备候选符号实例',s['deviceSymbols'],'模型空间顶层 INSERT，按明确设备名或型号白名单匹配；不是设备实物数'],
['其中类别可由名称识别',s['namedDeviceSymbols'],'阀门、储料、输送、筛分、破碎、混合、除尘'],
['其中仅型号可识别',s['modelCodeSymbols'],'SCNZ、LFHBF 型号，类别待核'],
['其中基础图/底座实例',s['foundationSymbols'],'已包含在上述总数，不另加计'],
['已确认的真实管线','无法确定','没有管线语义图层或足够的连接拓扑证据；不等于 0 条管线'],
['候选线实体',s['candidatePaths'],'1-设备轮廓 层的 59 条 LINE + 11 条 LWPOLYLINE；也可能只是设备边线'],
['模型空间文字',s['directTexts'],'491 TEXT + 156 MTEXT，不包含块内文字'],
['全库文字定义记录',s['textDefinitions'],'含块定义及非顶层文字，不按插入次数重复计数'],
['块展开后的文字出现次数',s['expandedTexts'],'包含块插入复制、尺寸文字；不是独立人工标注数'],
['图层',s['layers'],'LAYER 表'],['块定义',s['blocks'],'含模型/图纸空间块、匿名块、尺寸块和未插入块'],
['模型空间块引用',s['blockReferences'],'全部顶层 INSERT，不全部视为设备'],
['模型空间图元',s['modelEntities'],'包含 INSERT、尺寸、文字、几何等'],
['DXF 全库记录',s['entityDatabase'],'图元、表项、对象等 entitydb 记录，不能当成设备数']])}

图中可读到多层面平面布置、剖面及设备基础定位图。同一设备可能出现在平面、立面、侧视和基础图中；目前没有可靠唯一设备编号与跨视图对应关系，**无法据此给出独立设备实物总数**。

## 实际转换与数据质量

- Linux 检查未发现 dwg2dxf、dwgread、ODAFileConverter 或 LibreOffice；gcc、make、Python 和 Node 可用，ezdxf 已预装。见 `logs/tool-inventory.json`。
- 使用官方发布归档：https://github.com/LibreDWG/libredwg/releases/download/0.13.4/libredwg-0.13.4.tar.xz 。HTTPS 校验保持启用；安装脚本记录并核对本次下载归档的 SHA-256。
- 原 DWG SHA-256：`{s['originalSha256']}`。
- 转换命令退出码为 0，输出保存在 `converted.dxf`，日志见 `logs/conversion.log`，版本见 `logs/converter-version.txt`。
- 转换器出现 Unknown object 警告，可能跳过未知对象的 EED/reactors/扩展字典。转换成功**不代表与 AutoCAD 完全无损等价**。
- ezdxf 审计进行了 **{s['auditFixes']} 项内存修复**，修复后剩余错误 **{s['auditErrors']}**；未将修复回写到 `converted.dxf`。完整 DXF entitydb 导出发生在审计之前，场景使用审计后的内存模型。
- 审计修复代码分布：`{dict(fixes)}`，具体实体句柄与原因见 `analysis/audit.json`。
- DXF 图元导出失败 **{len(audit['export_failures'])}** 项。仍无法保证转换器已保留原 DWG 的所有专用对象。
- 原图全部 17 个图层均处于关闭状态。网页为检查用途默认显示它们，并允许分别关闭；原 DXF 图层设置没有改写。

实际执行：

```bash
./scripts/install_converter.sh
./scripts/convert.sh
XDG_CACHE_HOME=/workspace/.cache python3 scripts/analyze_drawing.py
XDG_CACHE_HOME=/workspace/.cache python3 scripts/build_scene.py
python3 scripts/write_report.py
cd web
npm ci --cache /workspace/.cache/npm --no-audit --no-fund
npm run build
npm run dev -- --port 5173 --strictPort
```

工具首次编译使用 `--disable-python --disable-bindings --disable-shared`，4 路 make。复用构建与依赖可避免每次重新编译。未使用需要授权的商业转换器。

## 设备识别规则及数量

仅对模型空间**顶层**块引用计数，不将 1,543 个 INSERT 全部认定为设备；也不将嵌套零件重复算作设备。匹配规则实现于 `scripts/build_scene.py` 的 `kind()`，可审计的逐个设备记录见 `analysis/devices.json`，包含原始句柄、块名、图层、插入位置、边界框及基础视图标志。

{table(['类别','实例数'],s['categories'].items())}

规则：阀门匹配闸门/闸阀/对夹阀/DN；储料匹配缓冲罐/吨袋/缓冲仓；输送匹配螺旋输送机/NE50/B400/B600；筛分匹配振动筛；破碎匹配对辊机/PE/PEX/2PG；混合匹配混合机；除尘匹配收尘器/DMC。SCNZ/LFHBF 单列型号待核。匿名块、随机名块及无可靠命名的设备可能漏识别，本次不是完整人工设备清点。

{table(['匹配块名','实例数','类别'],[(name,n,next(d['category'] for d in devices if d['name']==name)) for name,n in Counter(d['name'] for d in devices).most_common()])}

## 管线识别边界

原图图层主要为设备轮廓、钢构、建筑轮廓、标注、护栏、中心线等，没有管线语义层。不能将所有 LINE/LWPOLYLINE、中心线、轴线或设备轮廓认定为管线。

为人工复核导出了 **70 个候选线实体**，规则固定为顶层 `1-设备轮廓` 上的 LINE/LWPOLYLINE；`analysis/pipeline_candidates.json` 保留其句柄和原始坐标。它们未做设备端口连接、线网合并或流向确认，因此无法统计真实管段、回路或工艺流量。网页中的虚线与流动动画是**按设备类别编排的推演示意**，不代表图纸已确认的连接顺序。

## 文字

模型空间直接文字 647 条；全库定义计数 {dict(texttypes)}，共 1,428 条。递归展开模型空间 INSERT 与 DIMENSION 后得到 2,635 次文字出现。全量原始文字在 `analysis/texts.json`，经块变换的文字在 `analysis/expanded_texts.json`。

部分视图标题：

{chr(10).join('- '+cell(t['text']) for t in read('expanded_texts.json') if any(k in t['text'] for k in ['层面布置','层面布局','剖面图','基础定位','基础开挖']) and len(t['text'])<65)}

## 全部图层

{table(['图层','颜色索引','原始关闭','冻结'],[(l['name'],l['attributes'].get('color'),l['off'],l['frozen']) for l in layers])}

## 图元统计

模型空间：

{table(['类型','数量'],s['types'].items())}

全库（含块定义、对象和表项）：

{table(['DXF 类型','记录数'],Counter(e['type'] for e in entities).most_common())}

## 全部块定义

以下包含空间块、匿名块、尺寸块和普通块。块成员句柄与类型分布完整保存在 `analysis/blocks.json`；所有实体的 DXF 属性、文字和导出组码在 `analysis/entities.json`，不能与模型空间计数相加。

{table(['块名','直接成员数','类型'],[(b['name'],len(b['entities']),', '.join(f'{k}:{v}' for k,v in b['types'].items())) for b in blocks])}

## Three.js 网页实现与限制

- `web/` 使用 Three.js + Vite，本地打包依赖，不依赖第三方 CDN 或 API。
- 图纸空间：递归展开块，沿曲线采样，使用原始 XY 坐标投影显示几何，并为识别符号提供可点击的半透明体块。场景可旋转、平移、缩放、俯视、图层开关、搜索文字及设备、查看原始句柄与坐标。
- 原图单位 mm。网页转换到相对坐标以保证 GPU 精度。不同视图在原图中横向排布，不能当成真实厂房布局；体块厚度是示意，不是实际设备高度。原始 Z 范围 `{s['zRange']}` 保留于解析资料，不用作设备标高。
- 工艺示意：以已识别块为来源，为储料/输送/筛分/破碎/混合/除尘/阀门显示代表外形。可查看来源、定位原图和播放流动。类别间顺序、外形、尺寸和连线**未经工程验证**。
- 可视化跳过项：`{s['skipRender']}`。这些对象仍在原 DXF 与全量图元导出中。MLINE 的内存绘制遇到空线型错误，因此使用明确的跳过清单；未为显示而篡改 DXF 或隐藏解析错误。HATCH 不做填充渲染；代理对象没有专用 CAD 对象解析器。
- 浏览器曲线采样容差为 {s['browserCurveToleranceMm']} mm，投影线段按图层去除重合线，生成 {s['browserSegments']:,} 段；仅影响显示，原 DXF 和全量图元导出不受影响。
- 网页标注按钮显示视图标题；全部 2,635 次文字均可搜索，列表一次最多展示 250 条匹配结果，可继续输入缩小范围。

## 产物与复现

- `converted.dxf`：实际转换输出。
- `analysis/entities.json`、`layers.json`、`blocks.json`、`layouts.json`、`texts.json`：完整解析导出。
- `analysis/audit.json`、`summary.json`、`devices.json`、`pipeline_candidates.json`、`expanded_texts.json`：审计和分类依据。
- `web/public/drawing.json` 与 `geometry.bin`：仅用于网页的场景数据。
- `scripts/`：转换、解析、报告和浏览器测试脚本。检查结果见 `logs/`，网页截图见 `analysis/viewer-*.png`。

验证结果由实际测试脚本写入 `logs/validation.json` 和 `logs/browser-test.json`；报告并不把尚未运行的检查标记为通过。原始 DWG 保持不变。
'''
for filename,label in [('validation.json','数据验证'),('browser-test.json','浏览器交互验证')]:
 p=R/'logs'/filename
 if p.exists():
  result=json.loads(p.read_text());report+=f"\n### {label}\n\n状态：{result['status']}，共 {result['count']} 项。\n\n"+table(['检查','结果'],[(x['name'],x['status']) for x in result['checks']])+"\n"
(R/'drawing_analysis.md').write_text(report,encoding='utf8')
shutil.copyfile(R/'drawing_analysis.md',R/'web/public/drawing_analysis.md')
print('Report written:',len(report),'characters')
