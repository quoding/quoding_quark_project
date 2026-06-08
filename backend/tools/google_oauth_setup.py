#!/usr/bin/env python3
"""1회성 Google Calendar OAuth 인증 — refresh_token 발급용.

호스트(미니PC)에서 직접 실행한다 (Docker 불필요, secrets/ 파일을 그대로 읽고 씀).
브라우저가 없는 헤드리스 서버이므로, 맥 등 다른 기기에서 SSH 포트 포워딩으로
로컬 콜백 서버에 접속해 인증을 완료하는 방식을 사용한다.

사용법:
    cd backend && python tools/google_oauth_setup.py

    (다른 터미널에서, 맥 등에서)
    ssh -L 8765:localhost:8765 <user>@<minipc-host>

    그 다음 안내된 URL을 맥의 브라우저에서 열어 로그인·동의 → 자동으로 토큰 저장됨.
"""
from __future__ import annotations

import json
import secrets as _secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SECRETS_DIR = REPO_ROOT / "secrets"

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPE = "https://www.googleapis.com/auth/calendar"
AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"


def _read_secret(name: str) -> str:
    path = SECRETS_DIR / name
    if not path.exists():
        print(f"[오류] {path} 없음 — google_oauth_client_id / google_oauth_client_secret 먼저 채워주세요.")
        sys.exit(1)
    value = path.read_text().strip()
    if not value:
        print(f"[오류] {path} 가 비어 있습니다.")
        sys.exit(1)
    return value


_auth_code: str | None = None


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if code:
            _auth_code = code
            self.wfile.write("<h1>인증 완료 — 이 창은 닫으셔도 됩니다.</h1>".encode("utf-8"))
        else:
            self.wfile.write("<h1>인증 코드가 없습니다. 다시 시도해주세요.</h1>".encode("utf-8"))

    def log_message(self, fmt: str, *args: object) -> None:  # silence default request logging
        pass


def main() -> None:
    client_id = _read_secret("google_oauth_client_id")
    client_secret = _read_secret("google_oauth_client_secret")

    state = _secrets.token_urlsafe(16)
    auth_url = AUTH_ENDPOINT + "?" + urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",  # refresh_token 발급에 필수
            "prompt": "consent",  # 항상 refresh_token을 다시 받도록 강제
            "state": state,
        }
    )

    print("=" * 70)
    print("1) 다른 기기(맥)에서 이 미니PC로 SSH 포트 포워딩을 여세요:")
    print(f"   ssh -L {REDIRECT_PORT}:localhost:{REDIRECT_PORT} <user>@<이 서버 호스트>")
    print()
    print("2) 그 기기의 브라우저에서 아래 URL을 여세요:")
    print(auth_url)
    print("=" * 70)
    print(f"\n[대기 중] localhost:{REDIRECT_PORT} 에서 콜백을 기다립니다 ...")

    httpd = HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    httpd.handle_request()  # 콜백 1번만 받고 종료

    if _auth_code is None:
        print("[오류] 인증 코드를 받지 못했습니다.")
        sys.exit(1)

    print("[완료] 인증 코드 수신 — 토큰 교환 중 ...")

    body = urllib.parse.urlencode(
        {
            "code": _auth_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = urllib.request.Request(TOKEN_ENDPOINT, data=body, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"[오류] 토큰 교환 실패: {exc.code} {exc.read().decode('utf-8')}")
        sys.exit(1)

    refresh_token = payload.get("refresh_token")

    if not refresh_token:
        print("[오류] refresh_token이 응답에 없습니다 — 이미 한 번 동의한 계정이면")
        print("       Google 계정 설정에서 앱 액세스를 제거(revoke)한 뒤 다시 시도하세요.")
        print(f"       응답: {payload}")
        sys.exit(1)

    out_path = SECRETS_DIR / "google_calendar_refresh_token"
    out_path.write_text(refresh_token)
    out_path.chmod(0o600)
    print(f"[저장 완료] {out_path}")
    print("\nDocker 컨테이너가 새 secret을 읽도록 재시작하세요:")
    print("   docker compose restart quark-api")


if __name__ == "__main__":
    main()
