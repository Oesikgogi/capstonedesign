import os
import socket
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()


class IPv4SMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        last_error = None
        for family, socktype, proto, _, address in socket.getaddrinfo(
            host,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM,
        ):
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                sock.settimeout(timeout)
                sock.connect(address)
                return sock
            except OSError as exc:
                last_error = exc
                if sock is not None:
                    sock.close()
        if last_error is not None:
            raise last_error
        raise OSError(f"Could not resolve SMTP host: {host}")


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM_EMAIL"))


def is_email_delivery_configured() -> bool:
    return _smtp_configured()


def _send_email(to_email: str, subject: str, body: str) -> bool:
    if not _smtp_configured():
        return False

    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    smtp_force_ipv4 = os.getenv("SMTP_FORCE_IPV4", "true").lower() == "true"
    smtp_timeout = int(os.getenv("SMTP_TIMEOUT_SECONDS", "10"))
    from_email = os.getenv("SMTP_FROM_EMAIL")
    from_name = os.getenv("SMTP_FROM_NAME", "Boo키우기")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((from_name, from_email))
    message["To"] = to_email
    message.set_content(body)

    smtp_client = IPv4SMTP if smtp_force_ipv4 else smtplib.SMTP
    with smtp_client(smtp_host, smtp_port, timeout=smtp_timeout) as server:
        if smtp_use_tls:
            server.starttls()
        if smtp_username and smtp_password:
            server.login(smtp_username, smtp_password)
        server.send_message(message)

    return True


def send_signup_verification_code(to_email: str, code: str) -> bool:
    body_lines = [
        "Boo키우기 회원가입 인증번호입니다.",
        "",
        f"인증번호: {code}",
        "",
        "이 인증번호를 회원가입 화면에 입력해주세요.",
    ]
    return _send_email(
        to_email=to_email,
        subject="Boo키우기 학교 이메일 인증번호",
        body="\n".join(body_lines),
    )


def send_password_reset(to_email: str, token: str) -> bool:
    password_reset_url = os.getenv("PASSWORD_RESET_URL", "").rstrip("/")
    app_base_url = os.getenv("APP_BASE_URL", "").rstrip("/")
    reset_url_base = password_reset_url or (
        f"{app_base_url}/password-reset" if app_base_url else ""
    )
    reset_url = f"{reset_url_base}?token={token}" if reset_url_base else None

    body_lines = [
        "Boo키우기 비밀번호 재설정 요청이 접수되었습니다.",
        "",
    ]
    if reset_url:
        body_lines.extend(
            [
                "아래 링크에서 새 비밀번호를 설정해주세요.",
                reset_url,
            ]
        )
    else:
        body_lines.extend(
            [
                "아래 재설정 토큰을 앱의 비밀번호 재설정 화면에 입력해주세요.",
                token,
            ]
        )
    body_lines.extend(
        [
            "",
            "본인이 요청하지 않았다면 이 메일을 무시해도 됩니다.",
        ]
    )
    return _send_email(
        to_email=to_email,
        subject="Boo키우기 비밀번호 재설정",
        body="\n".join(body_lines),
    )
