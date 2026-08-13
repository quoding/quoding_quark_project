# QUARK — 개인 자비스 통합관제 시스템

> N100 미니PC + ESP32 + AI 에이전트로 집을 제어하고 하루를 관리하는 개인 비서.
> **실제 작업 루트는 `quark/`** — 별도 git 저장소 (origin: `github.com/quoding/quoding_quark_project`).
> `2.agent_page/`는 그 상위 폴더이며 자체 git 저장소가 아님.

> 📚 초기 기획·구상 문서는 `guide_file/`에 있음 (QUARK_Agent_Conception.md 등). **구상 단계 자료이며 실제 구현과 다를 수 있음** — 기술 선택의 "왜"를 알고 싶을 때만 참고.

## 스택 — 실제 적용된 것 (계획과 달라진 부분 위주)

- **에이전트**: 단일 `quark_agent.py` (Pydantic AI) + 등록형 도구(`tools/assistant.py`, `tools/home.py`).
  ⚠️ 초기 구상의 "에이전트별 분리"(command/conversation/idea/summary)는 **채택되지 않음** — 단일 에이전트 + 도구로 통합됨.
- **모델 라우팅**: `agents/routing.py`가 메시지 길이·복잡도 키워드로 nano↔mini 자동 선택. 모델 ID는 항상 `settings`에서 가져옴 (하드코딩 금지).
- **알림/스케줄**: 자체 PostgreSQL polling loop (10초 주기) — `reminder_service.py`. APScheduler는 asyncpg와 비호환 확인 후 폐기.
- **DB**: PostgreSQL + pgvector (`AgentMemory` 테이블, RAG), Alembic 마이그레이션 (`alembic/versions/`).
- **Discord**: `discord.py` 2.7 `commands.Bot` + Cogs, 슬래시 커맨드, `DynamicItem` 영속 버튼.
- **MQTT**: asyncio-mqtt + `mqtt_bridge.py`; `rule_router.py`가 정규식으로 LLM 이전 1차 처리.
- **프론트**: React 19 + TS, Zustand (`deviceStore`/`homeStore`/`uiStore`/`bridge`), shadcn/ui.

## 디렉토리 — 실제 구조 (guide_file 계획과 명칭/구성이 다름)

```
backend/app/
  agents/    quark_agent.py(단일 에이전트), routing.py(모델 선택), deps.py
  tools/     assistant.py, home.py            ← 새 기능은 여기에 등록형 함수로 추가
  services/  mqtt_bridge, rule_router, scheduler, memory, reminder_service,
             discord_bot, github_stats, weather, news, market, transit, rag, docker_stats, ...
  models/    agenda, automation, device, memory(AgentMemory/pgvector), reminder
  discord/cogs/  reminder.py
frontend/src/
  pages/   Dashboard, IotScreen, AgendaScreen, AutomationScreen, MonitorScreen
  stores/  deviceStore, homeStore, uiStore, bridge
```

## 핵심 컨벤션

- **시크릿**: `secrets/<name>` 파일 → Docker Secret 또는 `.env` fallback (`core/config.py`의 `_read_secret()`). 새 키 추가 시 이 패턴을 따를 것. (단, OpenAI 키는 예외로 `.env`의 `OPENAI_API_KEY`만 사용)
- **에이전트 확장**: 새 능력은 `tools/`에 `register_*_tools(agent, deps)` 형태로 추가 — 별도 에이전트를 새로 만들지 않는다.
- **테스트**: OpenAI/Discord/GitHub 등 외부 호출은 전부 `unittest.mock.patch`로 모킹. 실제 네트워크 호출 절대 금지.
- **DB 변경**: Alembic 마이그레이션으로만 (raw SQL 지양 — pgvector 유사도 검색은 예외).
- **MQTT 토픽**: `quark/{type}/{device-id}/{metric}`.

## 자주 쓰는 명령

```bash
docker compose up -d
docker compose logs -f quark-api
docker compose exec quark-postgres psql -U quark quark_db
docker compose exec quark-api alembic upgrade head
cd backend && pytest -q
```

- **`quark-api`와 `quark-discord-bot`은 같은 이미지(`quoding-quark-backend:latest`)를 공유** — 둘 다 `backend/` 소스로 빌드되고 `command`만 다름. `docker compose build quark-api` (또는 `up -d --build quark-api`) 한 번이면 두 컨테이너 다 최신 이미지를 쓰게 됨. 예전엔 서비스별로 이미지가 따로 빌드돼서 한쪽만 재빌드하면 다른 쪽(주로 discord-bot)이 옛날 코드로 계속 도는 문제가 있었음 — `image:` 태그를 맞춰서 구조적으로 막음. 새 backend 서비스를 compose에 추가할 때도 같은 이미지를 공유시킬지 고려할 것.

## 절대 하지 않는 것

- ❌ **APScheduler** — asyncpg와 비호환 확인됨, 자체 polling loop 사용
- ❌ **에이전트 다중 분리** — 단일 `quark_agent` + `tools/` 등록 패턴 유지
- ❌ Celery / Home Assistant / Chroma — 오버엔지니어링·RAM 낭비, pgvector로 충분
- ❌ 동기 코드 in FastAPI — 모든 IO `async`, DB는 `AsyncSession`
- ❌ API 키·토큰을 대화창에 붙여넣기 — 노출 시 즉시 재발급, `secrets/` 파일을 직접 편집
