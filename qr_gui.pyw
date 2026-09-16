# -*- coding: utf-8 -*-
"""二维码解码器 GUI（Windows / tkinter，本地离线）。

运行架构：
  - 本文件跑在 Python 3.14（系统 Python，带 tkinter），只依赖 Pillow 做预览与剪贴板；
  - 解码通过子进程委托给 Python 3.13 托管环境（已装 opencv + numpy）执行 decode_qr.py。
    原因：3.14 目前没有 opencv/numpy 的二进制轮子，装会走源码编译。

启动：双击 启动二维码解码器.bat
"""
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageGrab, ImageTk

HERE = os.path.dirname(os.path.abspath(__file__))
DECODER_SCRIPT = os.path.join(HERE, "decode_qr.py")


def resolve_decoder():
    """找到能跑 decode_qr.py 的解释器（需要 opencv + numpy）。

    顺序：环境变量 QR_DECODER_PY > 当前解释器自带 cv2 > 项目内常见 venv > 放弃。
    找不到返回 None，界面会提示怎么配，而不是写死某台机器的路径。
    """
    env_py = os.environ.get("QR_DECODER_PY")
    if env_py and os.path.exists(env_py):
        return env_py

    try:
        import importlib.util
        if importlib.util.find_spec("cv2") is not None:
            return sys.executable
    except (ImportError, ValueError):
        pass

    for rel in ("venv", ".venv", "backend", os.path.join("backend", "venv")):
        for sub in ("Scripts", "bin"):
            cand = os.path.join(HERE, rel, sub, "python.exe" if sub == "Scripts" else "python")
            if os.path.exists(cand):
                return cand
    return None


DECODER_PY = resolve_decoder()

BG = "#f5f6f8"
CARD = "#ffffff"
TEXT = "#1f2026"
MUTED = "#6b7280"
ACCENT = "#2563eb"
BORDER = "#e3e5ea"

IMG_TYPES = [("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tif *.tiff"), ("所有文件", "*.*")]
IMG_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tif", ".tiff")


HINT = "设置环境变量 QR_DECODER_PY，指向装了 opencv-python-headless 与 numpy 的 python.exe"


def call_decoder(path):
    """调用后端解码，返回 (内容, 解码方式)。"""
    if not DECODER_PY:
        return None, f"未找到解码后端；{HINT}"
    if not os.path.exists(DECODER_SCRIPT):
        return None, f"找不到解码脚本：{DECODER_SCRIPT}"
    try:
        out = subprocess.run(
            [DECODER_PY, DECODER_SCRIPT, "--json", path],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return None, "解码超时"
    except Exception as exc:
        return None, f"解码失败：{exc}"

    if out.returncode != 0 or not out.stdout.strip():
        return None, f"解码失败：{(out.stderr or '').strip()[:200]}"
    try:
        res = json.loads(out.stdout.strip().splitlines()[-1])
    except json.JSONDecodeError:
        return None, "解码输出无法解析"
    return res.get("data"), res.get("how", "未知")


class Snipper(tk.Toplevel):
    """全屏半透明遮罩，拖拽框选屏幕区域后截图。"""

    def __init__(self, master, on_capture, on_cancel=None):
        super().__init__(master)
        self.on_capture = on_capture
        self.on_cancel = on_cancel
        self.attributes("-fullscreen", True)
        self.attributes("-alpha", 0.35)
        self.attributes("-topmost", True)
        self.configure(bg="#000000")
        self.overrideredirect(True)

        self.canvas = tk.Canvas(self, cursor="crosshair", highlightthickness=0, bg="#000000")
        self.canvas.pack(fill="both", expand=True)
        self.start = None
        self.rect = None

        w = self.winfo_screenwidth()
        self.canvas.create_text(w // 2, 28, text="拖拽框选二维码区域 · Esc 取消",
                                fill="#ffffff", font=("Microsoft YaHei UI", 12))

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Escape>", self.cancel)
        self.canvas.focus_set()

    def on_press(self, event):
        self.start = (event.x, event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y,
                                                 outline=ACCENT, width=2, fill="#2563eb")
        self.canvas.itemconfigure(self.rect, stipple="gray25")

    def on_drag(self, event):
        if not self.start:
            return
        self.canvas.coords(self.rect, self.start[0], self.start[1], event.x, event.y)

    def on_release(self, event):
        if not self.start:
            return
        x1, y1 = self.start
        x2, y2 = event.x, event.y
        box = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
        self.destroy()
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            if self.on_cancel:
                self.on_cancel("框选区域过小，已取消")
            return
        # 等遮罩真正消失再抓屏，否则会把半透明层拍进去
        self.master.after(180, lambda: self._grab(box))

    def _grab(self, box):
        try:
            img = ImageGrab.grab(bbox=box, all_screens=True)
        except Exception as exc:
            if self.on_cancel:
                self.on_cancel(f"截图失败：{exc}")
            return
        self.on_capture(img)

    def cancel(self, event=None):
        self.destroy()
        if self.on_cancel:
            self.on_cancel("已取消截图")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("二维码解码器")
        self.root.geometry("780x540")
        self.root.minsize(680, 470)
        self.root.configure(bg=BG)
        self.photo = None
        self._build_ui()
        self.root.bind("<Control-v>", lambda e: self.from_clipboard())
        self.root.bind("<Control-V>", lambda e: self.from_clipboard())
        self.root.bind("<Control-s>", lambda e: self.snip())
        self.root.bind("<Control-S>", lambda e: self.snip())
        if not DECODER_PY:
            self.status.configure(text="未配置解码后端 · " + HINT)
        if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
            self.load_path(sys.argv[1])

    # ---------- 界面 ----------
    def _build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=BG)
        style.configure("TButton", padding=(12, 6), background=CARD, foreground=TEXT)
        style.configure("Accent.TButton", padding=(12, 6), background=ACCENT, foreground="#ffffff")
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        style.configure("TLabel", background=BG, foreground=TEXT)

        top = ttk.Frame(self.root, padding=(16, 14, 16, 8))
        top.pack(fill="x")
        ttk.Button(top, text="选择图片…", command=self.pick_file).pack(side="left")
        ttk.Button(top, text="粘贴剪贴板 (Ctrl+V)", style="Accent.TButton",
                   command=self.from_clipboard).pack(side="left", padx=8)
        ttk.Button(top, text="截图解码 (Ctrl+S)", command=self.snip).pack(side="left")
        ttk.Button(top, text="清空", command=self.clear).pack(side="left", padx=(8, 0))
        ttk.Label(top, text="本地解码 · 图片不上传", foreground=MUTED).pack(side="right")

        body = ttk.Frame(self.root, padding=(16, 4, 16, 12))
        body.pack(fill="both", expand=True)

        left = tk.Frame(body, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        left.pack(side="left", fill="y")
        self.preview = tk.Label(left, bg=CARD, text="预览区\n\n选图或 Ctrl+V 粘贴",
                                fg=MUTED, width=34, height=18, justify="center")
        self.preview.pack(padx=14, pady=14)

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))
        ttk.Label(right, text="解码结果", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")

        box = tk.Frame(right, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        box.pack(fill="both", expand=True, pady=(6, 0))
        self.text = tk.Text(box, wrap="word", relief="flat", bg=CARD, fg=TEXT,
                            insertbackground=TEXT, padx=10, pady=10,
                            font=("Consolas", 10), undo=True)
        sb = ttk.Scrollbar(box, command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        bar = ttk.Frame(right, padding=(0, 8, 0, 0))
        bar.pack(fill="x")
        self.btn_copy = ttk.Button(bar, text="复制结果", command=self.copy_result, state="disabled")
        self.btn_copy.pack(side="left")
        self.btn_open = ttk.Button(bar, text="打开链接", command=self.open_link, state="disabled")
        self.btn_open.pack(side="left", padx=8)

        self.status = ttk.Label(self.root, text="就绪", foreground=MUTED,
                                padding=(16, 0, 16, 12), anchor="w")
        self.status.pack(fill="x")

    # ---------- 动作 ----------
    def snip(self):
        self.root.withdraw()
        self.root.update_idletasks()

        def restore(msg=None):
            self.root.deiconify()
            if msg:
                self.status.configure(text=msg)

        def on_capture(img):
            restore()
            self.show_image(img)
            tmp = os.path.join(os.environ.get("TEMP", HERE), "_qr_gui_snip.png")
            try:
                img.convert("RGB").save(tmp)
            except Exception as exc:
                self.status.configure(text=f"截图保存失败：{exc}")
                return
            self.run_decode(tmp, "屏幕截图")

        Snipper(self.root, on_capture, restore)

    def pick_file(self):
        path = filedialog.askopenfilename(title="选择含二维码的图片", filetypes=IMG_TYPES)
        if path:
            self.load_path(path)

    def from_clipboard(self):
        self.status.configure(text="读取剪贴板…")
        self.root.update_idletasks()
        try:
            item = ImageGrab.grabclipboard()
        except Exception as exc:
            messagebox.showerror("剪贴板", f"读取剪贴板失败：{exc}")
            self.status.configure(text="就绪")
            return

        if item is None:
            self.status.configure(text="剪贴板里没有图片")
            return
        if isinstance(item, list):  # 复制的是文件
            path = item[0]
            if path.lower().endswith(IMG_EXTS):
                self.load_path(path)
            else:
                self.status.configure(text=f"剪贴板是文件而非图片：{os.path.basename(path)}")
            return
        if isinstance(item, Image.Image):
            tmp = os.path.join(os.environ.get("TEMP", HERE), "_qr_gui_clip.png")
            try:
                item.convert("RGB").save(tmp)
            except Exception as exc:
                self.status.configure(text=f"剪贴板图片保存失败：{exc}")
                return
            self.show_image(item)
            self.run_decode(tmp, "剪贴板图片")
            return
        self.status.configure(text=f"剪贴板内容不支持：{type(item).__name__}")

    def load_path(self, path):
        try:
            img = Image.open(path)
            img.load()
        except Exception as exc:
            self.status.configure(text=f"无法读取：{os.path.basename(path)}（{exc}）")
            return
        self.show_image(img)
        self.run_decode(path, os.path.basename(path))

    def run_decode(self, path, label):
        self.status.configure(text=f"解码中…（{label}）")
        self.root.update_idletasks()

        def work():
            data, how = call_decoder(path)
            self.root.after(0, lambda: self.on_result(data, how, label))

        threading.Thread(target=work, daemon=True).start()

    def on_result(self, data, how, label):
        self.text.delete("1.0", "end")
        if not data:
            self.btn_copy.configure(state="disabled")
            self.btn_open.configure(state="disabled")
            self.status.configure(text=f"{label}：{how}")
            self.text.insert("1.0", f"（{how}）")
            return

        self.text.insert("1.0", data)
        self.btn_copy.configure(state="normal")
        is_url = data.strip().lower().startswith(("http://", "https://"))
        self.btn_open.configure(state="normal" if is_url else "disabled")
        tail = f"{label} → {how}，共 {len(data)} 字符"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            tail += "（已自动复制）"
        except tk.TclError:
            pass
        self.status.configure(text=tail)

    def show_image(self, img):
        thumb = img.copy()
        thumb.thumbnail((300, 300), Image.LANCZOS)
        self.photo = ImageTk.PhotoImage(thumb)
        self.preview.configure(image=self.photo, text="")

    def copy_result(self):
        data = self.text.get("1.0", "end").strip()
        if data:
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            self.status.configure(text="已复制到剪贴板")

    def open_link(self):
        url = self.text.get("1.0", "end").strip().split()[0]
        if url.lower().startswith(("http://", "https://")):
            try:
                os.startfile(url)
            except Exception:
                subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)

    def clear(self):
        self.text.delete("1.0", "end")
        self.preview.configure(image="", text="预览区\n\n选图或 Ctrl+V 粘贴")
        self.photo = None
        self.btn_copy.configure(state="disabled")
        self.btn_open.configure(state="disabled")
        self.status.configure(text="就绪")


def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
