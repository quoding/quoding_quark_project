#!/usr/bin/env bash
# QUARK host helper — one-time install (run with sudo from this directory).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

install -m 0440 -o root -g root "$HERE/quark-reboot-sudoers" /etc/sudoers.d/quark-reboot
visudo -cf /etc/sudoers.d/quark-reboot

install -m 0644 "$HERE/quark-host-helper.service" /etc/systemd/system/quark-host-helper.service
systemctl daemon-reload
systemctl enable --now quark-host-helper.service

echo "✅ quark-host-helper 설치 및 기동 완료"
systemctl status quark-host-helper.service --no-pager | head -5
