# qr-decoder

本地离线的二维码解码器，带 Windows 桌面 GUI。图片不上传，全部在本机完成识别。

## 功能

- **选择图片…**：打开本地图片文件
- **粘贴剪贴板**（`Ctrl+V`）：截图后直接粘，无需先存盘
- **截图解码**（`Ctrl+S`）：屏幕蒙上遮罩，拖拽框选区域，松手即解
- 左侧缩略图预览，右侧结果区
- 解码成功自动复制到剪贴板；结果是 http(s) 链接时可直接用浏览器打开
- 识别失败会自动升级策略：曲面校正 → 多码识别 → 放大 ×2/×3/×4 → 二值化重试

## 文件

| 文件 | 说明 |
|---|---|
| `qr_gui.pyw` | GUI 前端（tkinter）。只依赖 Pillow |
| `decode_qr.py` | 解码后端（OpenCV）。支持命令行与 `--json` 两种模式 |
| `smoke_gui.py` | 冒烟测试：模拟建窗、载入、拖拽取屏并校验结果 |
| `启动二维码解码器.bat` | 双击启动 |

## 为什么拆成两个 Python

- GUI 跑在 **Python 3.14**（Windows 系统 Python 自带 tkinter 9.0）；托管精简版的 Python 3.13 **没有 tkinter**。
- 但 **Python 3.14 目前没有 numpy / opencv 的二进制轮子**，直接 `pip install` 会转源码编译，耗时且易失败。
- 因此：界面在 3.14 上跑，解码通过子进程委托给**装了 opencv + numpy 的 3.13 环境**，结果以 JSON 回传。

如果你只有一套 Python，且它同时具备 tkinter 与 opencv（例如官方安装版 3.12/3.13 + `pip install opencv-python-headless pillow`），可以把 `qr_gui.pyw` 里的 `DECODER_PY` 直接指向该解释器即可，无需改动其他代码。

## 安装

```bat
REM 1) 解码后端环境（需 opencv + numpy）
python -m venv <venv-backend>
<venv-backend>\Scripts\pip install opencv-python-headless numpy pillow

REM 2) GUI 前端环境（需 tkinter + pillow，Windows 官方安装包自带 tkinter）
<py314> -m venv <venv-gui>
<venv-gui>\Scripts\pip install pillow
```

在 `qr_gui.pyw` 中设置：

```python
DECODER_PY = r"<venv-backend>\Scripts\python.exe"
```

或设置环境变量 `QR_DECODER_PY` 覆盖，不改代码。

然后按实际路径修改 `启动二维码解码器.bat` 中的 `pythonw.exe` 路径，双击即可运行。

## 命令行用法

```bat
python decode_qr.py <图片路径>            REM 人类可读输出
python decode_qr.py                        REM 解析最新一张剪贴板图片
python decode_qr.py --json <图片路径>      REM 输出 JSON，供 GUI 调用
```

中文路径已处理（用 `np.fromfile` + `cv2.imdecode` 读文件，规避 `cv2.imread` 的限制）。

## 测试

```bat
python smoke_gui.py
```

自动建窗、载入测试图、模拟鼠标拖拽取屏，最后输出 `PHASE1: PASS / PHASE2: PASS` 并自行关闭窗口。

## 许可

MIT
