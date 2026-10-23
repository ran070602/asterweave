"""意见箱：把邮箱二维码离线生成成内联 data URI（不引入任何外部引用）。

读 `tools/feedback.json` → 写 `tools/feedback_qr.json`：
  { email, show, mailto, qr, form_url, form_qr, version, subject }
其中 qr / form_qr 是 `data:image/png;base64,...`，可直接作为 <img src> 内联进单文件。
"""
import base64, io, json, os, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "feedback.json")
OUT = os.path.join(ROOT, "tools", "feedback_qr.json")


def qr_data_uri(text, box_size=8, border=2):
    import qrcode
    q = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                      box_size=box_size, border=border)
    q.add_data(text)
    q.make(fit=True)
    img = q.make_image(fill_color="#0b1020", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii"), len(q.modules)


def obfuscate(email):
    """防爬变形：只用于页面显示，复制按钮里仍是真实地址。"""
    user, _, domain = email.partition("@")
    dom = domain.replace(".", " [dot] ")
    return f"{user} [at] {dom}"


def main():
    cfg = json.load(open(SRC, encoding="utf-8"))
    email = (cfg.get("email") or "").strip()
    subject = cfg.get("subject") or "星织 Asterweave 试玩反馈"
    form_url = (cfg.get("formUrl") or "").strip()
    if not email:
        print("!! feedback.json 里没有 email"); sys.exit(1)

    # 邮件正文模板尽量短；正文由页面「复制反馈」带出
    body = "关卡：\n问题：\n"
    mailto = ("mailto:" + email + "?subject=" + urllib.parse.quote(subject) +
              "&body=" + urllib.parse.quote(body))
    # v2.3：界面已移除「扫码提交」（QQ/微信扫码器不认 mailto: 协议），二维码默认不再生成。
    # 需要时用 `python tools/build_feedback.py --qr` 重新开启，产物仍是内联 data URI。
    want_qr = ("--qr" in sys.argv)
    qr, modules = (qr_data_uri(mailto) if want_qr else ("", 0))
    out = {
        "email": email,
        "show": obfuscate(email),
        "mailto": mailto,
        "qr": qr,
        "version": cfg.get("version") or "",
        "subject": subject,
        "form_url": form_url,
        "form_qr": "",
        "modules": modules,
    }
    if form_url and want_qr:
        fqr, fmod = qr_data_uri(form_url)
        out["form_qr"] = fqr
        out["form_modules"] = fmod
        print(f"表单二维码：{fmod}×{fmod} 模块")
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    if want_qr:
        print(f"意见箱配置已生成：邮箱 {email}｜邮件二维码 {modules}×{modules} 模块｜"
              f"内联 data URI {len(qr)//1024} KB（内联 PNG，不产生外部引用）")
    else:
        print(f"意见箱配置已生成：邮箱 {email}｜未生成二维码（界面已改为「查看作者邮箱」；"
              f"如需二维码请加 --qr）")


if __name__ == "__main__":
    main()
