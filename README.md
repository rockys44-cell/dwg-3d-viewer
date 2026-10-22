# 宝峰配料工艺图 · DWG / DXF / Three.js

原始文件：`湖南宝峰配料工艺图T6.dwg`（AutoCAD 2004–2006）。使用 LibreDWG 0.13.4 实际转换，ezdxf 1.4.4 提取，Three.js 展示。

解析结果见 [drawing_analysis.md](drawing_analysis.md)。243 个设备候选符号（含重复视图、150 个类别待核型号），647 条模型空间文字。70 条设备轮廓线是人工复核候选，不能据此确认真实管线数量。三维外形、符号高度与工艺示意连线未经工程验证。

## 启动网页

```bash
cd /workspace/dwg-3d-viewer/web
npm ci --cache /workspace/.cache/npm --no-audit --no-fund
npm run dev -- --port 5173 --strictPort
```

需要 Node.js 20.19+ 或 22.12+；本环境验证使用 Node.js 24.19.0。页面支持设备与文字搜索定位、原图图层开关、旋转/平移/缩放/俯视、图元来源查看和工艺推演动画。网页不依赖 CDN 或外部 API。

## 重新转换与解析

```bash
cd /workspace/dwg-3d-viewer
python3 -m venv --system-site-packages /workspace/.venvs/dwg-viewer
source /workspace/.venvs/dwg-viewer/bin/activate
python -m pip install --cache-dir /workspace/.cache/pip -r requirements.txt
./scripts/install_converter.sh
./scripts/convert.sh
XDG_CACHE_HOME=/workspace/.cache python scripts/analyze_drawing.py
XDG_CACHE_HOME=/workspace/.cache python scripts/build_scene.py
python scripts/write_report.py
```

转换脚本只覆盖生成的 `converted.dxf`，不改动源 DWG。LibreDWG 默认构建路径为 `/workspace/tools/libredwg-0.13.4`；可用 `DWG2DXF` 指定已有转换器。源码构建工具需 gcc/make，使用 4 路并行，首次编译约数分钟，后续复用。安装脚本通过 TLS 下载官方发布归档并校验记录的 SHA-256。

导出文件在 `analysis/`：图层、全部块、布局、全库实体属性与组码、文字、审计日志、设备及候选线记录。`web/public/geometry.bin` 是简化的相对坐标 XY 投影几何，不是可编辑 CAD 模型。源 DWG、转换 DXF 和图元导出保留原始精度。

## 验证

```bash
cd /workspace/dwg-3d-viewer
XDG_CACHE_HOME=/workspace/.cache /workspace/.venvs/dwg-viewer/bin/python scripts/validate_analysis.py
# 先启动上述 Vite 服务；浏览器测试依赖系统 Chromium、Playwright 与 Pillow。
XDG_CACHE_HOME=/workspace/.cache /workspace/.venvs/dwg-viewer/bin/python scripts/browser_test.py
python scripts/write_report.py
cd web && npm run build
```

实际结果见 `logs/validation.json`、`logs/browser-test.json`，截图在 `analysis/viewer-*.png`。完整限制、识别规则和全部块列表见解析报告。转换器存在未知对象警告、ezdxf 内存审计修复 869 项；代理实体、填充和多线未在网页中渲染。不能将转换成功当成与原 AutoCAD 专用对象无损等价。

各云任务已有隔离环境，直接使用现有 checkout，无需创建 Git worktree。进程在环境恢复后需要按启动步骤重新运行。

## GitHub Pages 发布

静态发布目录为 `docs/`。在 GitHub 仓库打开 **Settings → Pages**，将 **Source** 选为 **Deploy from a branch**，将分支和目录选为 **main /docs**，点击 **Save**。GitHub 完成部署后，预期地址为 `https://rockys44-cell.github.io/dwg-3d-viewer/`；以 Pages 设置中显示的成功发布地址为准。

更新网页后，执行 `./scripts/build_pages.sh` 并提交 `docs/`。该脚本使用项目子路径 `/dwg-3d-viewer/` 构建。首次打开会加载约 51 MB 的几何数据，请稍等。网页左键拖动旋转，滚轮缩放，左侧搜索设备；点击“工艺示意”，再点击“流动”播放示意动画。
