"""二维码/条码本地解码器（命令行 + GUI 后端）。

用法:
    python decode_qr.py <图片路径> [<图片路径> ...]   # 人类可读输出
    python decode_qr.py --json <图片路径>             # GUI 调用，输出 JSON
不传参数时，默认解析最新的剪贴板图片。
依赖: opencv-python-headless, numpy
注意: 本脚本运行在托管 venv（Python 3.13，已装 cv2），GUI 通过子进程调用它。
"""
import glob
import json
import os
import sys

import cv2

CLIP_DIR = r"C:/Users/Yuan Fanding/.workbuddy-ai/clipboard-images"


def decode(path):
    img = cv2.imread(path)
    if img is None:
        return None, "无法读取图片"
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    det = cv2.QRCodeDetector()

    data, _, _ = det.detectAndDecode(gray)
    if data:
        return data, "QRCodeDetector"

    try:
        curved = cv2.QRCodeDetectorCurved()
        data, _, _, _ = curved.detectAndDecodeCurved(gray)
        if data:
            return data, "QRCodeDetectorCurved"
    except Exception:
        pass

    ok, infos = det.detectAndDecodeMulti(gray)
    if ok and infos:
        return " | ".join(infos), "detectAndDecodeMulti"

    # 退化情况：放大 + Otsu 二值化重试
    for scale in (2, 3, 4):
        big = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        data, _, _ = det.detectAndDecode(big)
        if data:
            return data, f"upscale x{scale}"
        _, bw = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        data, _, _ = det.detectAndDecode(bw)
        if data:
            return data, f"upscale x{scale} + otsu"

    return None, "未识别到二维码"


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    if as_json:
        args = [a for a in args if a != "--json"]

    if not args:
        pngs = sorted(glob.glob(os.path.join(CLIP_DIR, "*.png")), key=os.path.getmtime)
        args = [pngs[-1]] if pngs else []
    if not args:
        print("用法: python decode_qr.py [--json] <图片路径>")
        return 1

    if as_json:
        p = args[0]
        data, how = decode(p)
        print(json.dumps({"ok": bool(data), "data": data, "how": how},
                         ensure_ascii=False))
        return 0

    for p in args:
        data, how = decode(p)
        print(f"[{os.path.basename(p)}] via {how}")
        print(data if data else "  -> 失败")
    return 0


if __name__ == "__main__":
    sys.exit(main())
