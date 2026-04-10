"""
core/email_sender.py — EA Auto Master v6.0
===========================================
SMTP 이메일 발송. email.json 설정 파일 사용.
"""
import os
import json
import datetime
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from core.config import HERE


def send_email_report(results, subject="EA AutoMaster 라운드 완료 보고"):
    """SMTP 이메일 발송.
    results: list of dict (round, grade, score, profit, pf)
    Returns (success: bool, message: str)
    """
    cfg_path = os.path.join(HERE, "email.json")
    if not os.path.exists(cfg_path):
        return False, "email.json 없음 -- 설정탭에서 저장 필요"

    try:
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        return False, f"email.json 읽기 실패: {e}"

    smtp_host = cfg.get("smtp_host", "smtp.naver.com")
    smtp_port = int(cfg.get("smtp_port", 587))
    sender = cfg.get("sender_email", "")
    password = cfg.get("app_password", "")
    receivers = [r.strip() for r in cfg.get("receiver_email", "").split(",") if r.strip()]

    if not sender or not password or not receivers:
        return False, "이메일 설정 불완전 (sender/password/receiver 확인)"

    body_lines = [f"EA AutoMaster 라운드 최적화 완료 -- {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n"]
    for r in results:
        body_lines.append(
            f"R{r.get('round', '?'):>2} | 등급:{r.get('grade', '?')} | "
            f"점수:{r.get('score', 0):>3} | 수익:${r.get('profit', 0):>8.2f} | "
            f"PF:{r.get('pf', 0):.2f}"
        )
    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(receivers)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(sender, password)
            s.sendmail(sender, receivers, msg.as_string())
        return True, f"전송 완료 -> {', '.join(receivers)}"
    except Exception as e:
        return False, f"전송 실패: {e}"
