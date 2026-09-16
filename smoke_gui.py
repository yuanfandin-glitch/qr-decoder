"""GUI 冒烟测试：
阶段一：建窗 -> 载入图片 -> 校验解码结果
阶段二：框选取屏（模拟鼠标拖拽）-> 校验抓图与回调
全程自动关闭窗口。
"""
import importlib.util
import os
import sys
import tkinter as tk

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("qr_gui", os.path.join(HERE, "qr_gui.pyw"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

IMG = r"C:/Users/Yuan Fanding/.workbuddy-ai/clipboard-images/clipboard-2026-09-16T14-57-58-514Z-9545122a.png"

root = tk.Tk()
app = mod.App(root)
state = {}


# ---------- 阶段一 ----------
def run1():
    try:
        app.load_path(IMG)
    except Exception as exc:
        print("load_path 异常:", exc, flush=True)
    root.after(2500, check1)


def check1():
    state["text"] = app.text.get("1.0", "end").strip()
    state["status"] = app.status.cget("text")
    state["copy"] = str(app.btn_copy.cget("state"))
    state["open"] = str(app.btn_open.cget("state"))
    state["photo"] = app.photo is not None
    root.after(100, run2)


# ---------- 阶段二：框选取屏 ----------
def run2():
    def on_capture(img):
        state["snip_size"] = img.size
        state["snip_ok"] = img.size[0] > 100 and img.size[1] > 100
        root.after(100, finish)

    def on_cancel(msg):
        state["snip_msg"] = msg
        root.after(100, finish)

    try:
        snip = mod.Snipper(root, on_capture, on_cancel)
        state["snip_created"] = True
    except Exception as exc:
        state["snip_error"] = f"{type(exc).__name__}: {exc}"
        root.after(100, finish)
        return

    def drag():
        try:
            snip.canvas.event_generate("<ButtonPress-1>", x=120, y=120)
            snip.canvas.event_generate("<B1-Motion>", x=420, y=420)
            snip.canvas.event_generate("<ButtonRelease-1>", x=420, y=420)
        except Exception as exc:
            state["snip_error"] = f"事件模拟失败: {exc}"

    root.after(300, drag)
    root.after(4000, finish)  # 兜底


def finish():
    try:
        root.destroy()
    except tk.TclError:
        pass


root.after(200, run1)
root.after(12000, finish)
root.mainloop()

print("预览已生成:", state.get("photo"))
print("状态栏:", state.get("status"))
print("复制/打开按钮:", state.get("copy"), "/", state.get("open"))
print("解码结果:", repr(state.get("text")))
print("取屏窗口创建:", state.get("snip_created"), "| 抓图尺寸:", state.get("snip_size"),
      "| 异常:", state.get("snip_error") or state.get("snip_msg") or "无")

ok1 = state.get("text", "").startswith("https://pan.quark.cn") and state.get("photo")
ok2 = state.get("snip_created") and state.get("snip_ok")
print("PHASE1:", "PASS" if ok1 else "FAIL")
print("PHASE2:", "PASS" if ok2 else "FAIL")
sys.exit(0 if (ok1 and ok2) else 1)
