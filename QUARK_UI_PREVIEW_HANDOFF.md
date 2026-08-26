# Quark 새 UI 프리뷰 작업 요약

## 작업 경로

- 프로젝트 루트: `/home/muya98/quoding`
- 프론트엔드: `/home/muya98/quoding/frontend`
- 새 UI 컴포넌트: `frontend/src/pages/QuarkPreview.tsx`
- 새 UI 스타일: `frontend/src/pages/QuarkPreview.css`
- 프리뷰 진입 분기: `frontend/src/App.tsx`

## 접속 경로

- 기존 UI: `https://quark.quoding.com/`
- 새 UI: `https://quark.quoding.com/preview`
- 하위 경로:
  - `/preview/iot`
  - `/preview/agenda`
  - `/preview/monitor`
  - `/preview/automation`
  - `/preview/research`

기존 UI는 교체하지 않았으며 `/`에 그대로 남아 있다.

## 작업 내용

- 밝은 웜 그레이 배경과 딥 그린·세이지 중심의 새 디자인 시스템 적용
- 홈, 스마트 홈, 일정, 모니터링, 자동화, 연구 아카이브 화면 구현
- 모바일 반응형 사이드바와 페이지별 URL 이동 구현
- 기존 SSE 채팅 훅 연결
- 기존 Zustand 홈 상태 및 MQTT 명령 연결
- 날씨, Google Calendar, 할 일, 습관, 아이디어, 알림 API 연결
- 시스템 상태, 서비스, Docker, GitHub, OpenAI 사용량 API 연결
- 재부팅, WoL, RAG 임베딩 토글 연결
- 자동화 조회·생성·토글·삭제 연결
- 연구 조회·실행 및 논문 링크 연결
- 빠른 메모, 물 섭취, D-Day, 시세, 포모도로 기능 추가
- 날씨 예보·일출·일몰, 뉴스 API 위젯 추가
- 기분·수면·주간 수면·카페인 기록 API 연결
- 캘린더 일간·주간·월간 보기 전환 추가
- 카메라 모의 화면과 세계 시계 추가
- Quark 채팅 전체 히스토리 펼치기 추가
- `quark-dash-v2` 기반 위젯 표시·순서·크기 편집 및 저장 복원 추가
- 대중교통은 기존 보류 방침에 따라 제외

## 검증 및 배포 상태

- `npm run build` 성공
- Vitest 13개 테스트 통과
- 백엔드 주요 조회 API 18개 응답 `200` 확인
- `quark-frontend` 이미지 재빌드 및 컨테이너 재생성 완료
- `quark-nginx` 재시작으로 오래된 API upstream 문제 해결
- Cloudflare 외부 도메인에서 `/`, `/preview`, `/api/system/stats` 응답 `200` 확인

## 참고

- 아직 새 UI를 기본 `/` 경로로 승격하지 않았다.
- 실제 물리 기기 MQTT 제어와 미니PC 재부팅·WoL은 운영 화면에서 수동 확인이 필요하다.
- 현재 변경 사항은 Git 커밋되지 않은 상태다.
