"""Transit real-time data — ⏸️ 보류 (2026-06-12).

거주지(경상북도 구미시)의 실시간 버스 도착 API가 노후화되어 사용 불가 판단,
연동을 보류한다. 항상 빈 배열을 반환하며 프론트 위젯은 "보류" 안내를 표시한다.

재개 조건: 구미시(또는 경북) 신규 실시간 도착 API가 확인되면
  1. 키를 secrets/transit_api_key 패턴으로 추가 (core/config.py _read_secret)
  2. 이 모듈에 호출 구현
  3. frontend TransitCard의 보류 안내 분기 제거
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def get_transit() -> list[dict[str, Any]]:
    """Return transit arrivals. 보류 상태 — 항상 []."""
    return []
