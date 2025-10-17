# Prop Bot Super Spec — v6.3 (интегрированная)
**Статус:** готово к передаче Codex (Implementation Mode).  
**Важно:** Разделы v6.3 **имеют приоритет** над пересекающимися пунктами в v6.2. Если встретятся дубликаты/расхождения, считать верными требования из v6.3.

## Changelog v6.3
- Вшиты 7 «обязательных релиз‑гейтов» (P0‑закрытие, TCA/атрибуция, Regime→Policy→Sizing, Fee‑tier & Cash Planner, Exception‑budget/SLO, Микро‑латентность, Альфа‑фабрика/A‑B).
- Добавлен большой список «обязательных доп. требований», чтобы бот был серьёзным на рынке (но запускался сначала на обычном ПК с Python 3.12, затем на VPS).
- Уточнены SLI/SLO‑метрики, пороги, проверочные тесты и порядок раскатки (canary → shadow → micro‑live).
- Добавлены секции по Recon/Exactly‑Once/DR‑дрилам, Security/RBAC/HSM, Compliance/GDPR, CI/CD и Release‑политикам.
- Закреплены совместимость и пути развертывания под окружение Дениса (локально → VPS), не ломая текущие эндпоинты.

---

## 0. Обязательные Release‑Gates (запрещена широкая раскатка, если не выполнено)
> Каждый релиз должен проходить эти гейты. Codex обязан внедрить логику гейтов, метрики и отчёты.

### RG‑1. Жёсткое закрытие P0 (Safety/Integrity)
**Состав P0:** Durable Order Journal/Outbox (exactly‑once), HA/DR (leader‑election + fencing), Invariants (state/limits), Guarded Startup (health/snapshot/recon ok), Conformance‑симулятор бирж, Key‑Security (HSM/YubiKey/TPM), Compliance (WORM‑экспорт, аудит).  
**DoD:**  
- [ ] Все торговые события фиксируются в журнале с идемпотентными ключами; повтор запуска не создаёт дублей/потерю состояния.  
- [ ] DR‑дрилы проходят: имитация падения лидера/разрыва сети, split‑brain=0 (фенсинг), RPO≈0, RTO≤60s (локально), ≤120s (VPS).  
- [ ] Guarded startup: запуск в «hold», пока не пройдут health‑пробы MD/REST, позиционный recon, ключевые инварианты.  
- [ ] Conformance‑suite на каждую биржу: типы ордеров, отмены, rate‑limiter, частные каналы, edge‑кейсы.  
- [ ] Ключи в аппаратном хранилище/агенте; ротация и политики доступа документированы; секреты не в коде.  
**SLI/SLO (минимум):** split_brain_incidents=0/30д; journal_gap=0; recon_mismatch=0 в конце дня; RPO≤1s.  

### RG‑2. TCA и атрибуция как релиз‑гейт
**Суть:** ни один функциональный апгрейд не идёт в широкую раскатку без отчёта «до/после» по издержкам.  
**Показатели (обязательные):**  
- [ ] taker_impact_bps ↓, maker_fill_rate ↑, avg_slippage_bps ↓, reject_rate ↓, cancel_fail_rate ↓, комиссия_bps ↓.  
- [ ] PnL‑атрибуция по корзинам: fees, slippage, rebates, funding, inventory, model alpha.  
**Гейт:** апгрейд допускается в canary только если ≥3 ключевых метрики улучшены/не хуже baseline.

### RG‑3. Regime → Policy → Sizing
**Суть:** для каждого рыночного режима своя политика входа/выхода, flip maker↔taker, лимиты воздействия и размер позиции.  
**DoD:**  
- [ ] Классификатор режимов (range/trend/volatile/liquidity shock …) с довериями.  
- [ ] Policy‑матрица (по режимам): пороги сигналов, допустимый impact, maker/taker flip‑условия, тайм‑гварды.  
- [ ] Sizing‑правила: per‑venue caps, per‑instrument caps, VaR/MaxDD; auto‑de‑risk при дрейфе/всплеске волы.  
**SLI/SLO:** pnl_volatility_day ↓ 20–40% против baseline; overfill_impact_events ↓.

### RG‑4. Fee‑tier & Cash Planner
**Суть:** активное достижение VIP/fee‑tiers, плановая ребалансировка кэша/маржи по биржам ради bps.  
**DoD:**  
- [ ] Модель экономик комиссий/ребейтов на биржу/символ; таргеты по обороту и симулятор «что будет после апгрейда».  
- [ ] Планировщик ребалансировки средств (min‑fee‑cost subject to risk/latency); триггеры переключения.  
**SLI/SLO:** комиссия_bps ↓ 3–8 bps относительно baseline без ухудшения риска/латентности.

### RG‑5. Exception‑Budget / SLO‑гейты
**Суть:** автоматическая дисциплина остановок/hold/restart при деградации.  
**SLI/SLO (минимум):**  
- [ ] ws_gap_ms_p95 ≤ 400ms (локально), ≤ 600ms (VPS);  
- [ ] order_cycle_ms_p95 ≤ 200ms (локально), ≤ 300ms (VPS);  
- [ ] reject_rate ≤ 0.5%; cancel_fail_rate ≤ 0.3%;  
- [ ] max_day_drawdown ≤ планового лимита; при превышении → HOLD до ручного «двухключевого» разрешения.  
**DoD:** авто‑холды и авто‑ремедиации включены, алерты/он‑колл уведомления отправляются.

### RG‑6. Микро‑латентность там, где это окупается
**Суть:** без колокации/FPGA, но выжимаем «жир» из клиента.  
**DoD:**  
- [ ] zero‑copy парс для L2, минимизация allocations; batch‑amend/склейка ордеров; fewer hops в hot‑path; lock‑free очереди.  
- [ ] md_to_order_path_ms_p95 ↓; maker_queue_position_estimator внедрён.  
**Эффект:** maker‑fill +5–15%; taker‑impact −10–20%.

### RG‑7. Альфа‑фабрика и A/B
**Суть:** постоянная программа экспериментов: champion↔challenger, дрейф‑детекторы, offline/online A‑B.  
**DoD:**  
- [ ] Эксп‑реестр (гипотеза, метрики, длительность, результат), автоблок неудачных;  
- [ ] Online‑A/B на малой доле риска с auto‑rollback;  
- [ ] Drift‑алерты (feature/label drift).

---

## 1. Обязательные доп. требования (того, чего часто нет, но нужно «по‑взрослому»)
> Эти пункты нужно внедрить, даже если частично перекрываются с v6.2. Они критичны для «серьёзности» на рынке.

### 1.1 Runbooks & Incident Response
- Единый **Runbook**: как запускать, останавливать, переводить в HOLD, как вручную хеджировать, как делать DR‑фейловер.
- **Инцидент‑процедуры**: SEV‑классификация, RFO/RCA шаблоны, тайминги, «двухключевое» снятие HOLD.
- **ChatOps**: команды паузы/резюма/режимов через Telegram/веб (с подтверждением 2‑мя операторами при критических действиях).

### 1.2 Staging/Testnet/Replay
- Профили: **local‑paper → testnet → shadow‑live → micro‑live**; **conformance‑suite** на каждую биржу.
- **Deterministic replay** (Parquet/SQLite WAL); golden‑тесты на случаи падений/рестартов/дублирующих событий.

### 1.3 Reconciliation & Ledger
- **Позиции/балансы/комиссии/ребейты/фандинг** — детальная сверка по концам сессий/дня; отклонения → алерт+HOLD.
- **WORM‑экспорт** для аудита/налогов (SE/EU); сводный **Tax‑Ledger** (realized/unrealized PnL, fees, funding).

### 1.4 Security/RBAC/Keys
- **RBAC/Least‑Privilege**, секреты только в секрет‑сторе; **HSM/YubiKey/TPM**; ротация ключей; доступы по ролям.
- **Audit‑лог** административных действий; **2‑man rule** на опасные операции (resume после красного холда, смена лимитов).

### 1.5 Compliance/GDPR
- Политики хранения/удаления данных; Privacy‑нотсы в UI; экспорт истории по запросу; защита персональных данных.

### 1.6 CI/CD & Supply‑Chain
- Pinned deps, SBOM, SAST/DAST; **канареечные релизы**, авто‑rollback по SLO; freeze‑окна для high‑risk апдейтов.
- Эфемерные окружения для PR (по возможности), smoke‑и acceptance‑тесты обязательны.

### 1.7 Observability/SRE
- Prometheus‑метрики: ws_gap_ms, order_cycle_ms, maker_fill_rate, taker_impact_bps, reject_rate, cancel_fail_rate, pnl_buckets, recon_mismatch.
- Дашборды (RU‑UI), алерты (он‑колл), **SLO‑дашборд** с exception‑budget.

### 1.8 Economic & Risk Calculators
- Funding/basis/ADL‑риск; cost‑of‑carry; стресс‑тест профилей; auto‑off при негативной экономике.
- Per‑venue caps, per‑symbol caps, VaR/MaxDD; **kill‑switch** и **safe_mode**.

### 1.9 Fee Modeling & VIP Planner
- Унифицированная модель комиссий/ребейтов по биржам; целевые VIP‑уровни; симулятор «что даёт ребейт».
- Планировщик ребалансировок средств с ограничениями риска/латентности.

### 1.10 Telegram/UX
- Команды: /status, /hold, /resume, /risk, /limits, /fees, /config‑apply (с валидацией и soft‑reload).
- RU‑интерфейс, хелпы и предупреждения на русском, понятные ошибки/подсказки.

### 1.11 DR/HA
- Active‑passive с leader‑election, fencing‑tokens; периодические **DR‑дрилы** (раз в неделю); RPO≈0, RTO≤ целевых.
- Readiness‑эндпоинт `/live-readiness` с проверками зависимостей и состояния.

### 1.12 Performance/Hot‑Path
- Lock‑free очереди; минимизация hop’ов; batch‑операции; CPU‑пиннинг (VPS); компилируемые модели (pydantic‑compiled) там, где уместно.
- (Опционально) вынос критичных участков в Rust/С++ модуль при доказанной выгоде (через TCA).

### 1.13 Storage/DB
- SQLite WAL + Alembic локально; опция Postgres на VPS; **Outbox/Inbox** семантика для exactly‑once.
- Periodic VACUUM/анализ, резервные копии, проверка целостности журналов.

### 1.14 Legal/Disclaimers
- Баннеры в UI: риски, режимы (paper/testnet/live), предупреждения о пределах стратегии/юрисдикции.

---

## 2. API/Эндпоинты (минимум, не ломая текущие)
- `/api/health`, `/live-readiness` (новый), `/api/ui/control-state`, `/api/ui/{execution,pnl,exposure}`
- `/api/ui/recon/*` (позиции/балансы/комиссии), `/api/ui/stream` (WS/SSE), `/api/ui/config/{validate,apply,rollback}`
- `/api/opportunities`, `/metrics`, `/metrics/latency`

---

## 3. Метрики, Пороги и Алерты (ядро)
| Метрика | Цель локально | Цель VPS | Алерт/Действие |
|---|---:|---:|---|
| ws_gap_ms_p95 | ≤ 400ms | ≤ 600ms | HOLD при 3× превышении 5 минут |
| order_cycle_ms_p95 | ≤ 200ms | ≤ 300ms | HOLD + auto‑remediate |
| maker_fill_rate | ≥ baseline +5% | ≥ baseline +5% | Investigate/Tune |
| taker_impact_bps | ↓ к baseline | ↓ к baseline | Gate в canary |
| reject_rate | ≤ 0.5% | ≤ 0.5% | Rate‑limit tuning/Backoff |
| cancel_fail_rate | ≤ 0.3% | ≤ 0.3% | Venue quarantine |
| recon_mismatch | 0 | 0 | HOLD до исправления |
| max_day_drawdown | ≤ лимита | ≤ лимита | HOLD, 2‑man resume |

---

## 4. Release‑политика и Порядок раскатки
1) **Local‑paper**: закрыть RG‑1 → RG‑2 (TCA baseline) → RG‑3/4/5/6/7 на синтетике/реплее.  
2) **Testnet**: conformance‑suite на каждую биржу + smoke.  
3) **Shadow‑live**: 0 риск, mirror‑поток, TCA/атрибуция; сравнение с baseline.  
4) **Micro‑live**: маленькие лимиты/капы + exception‑budget; auto‑rollback по SLO.  
5) **Ramp‑up**: VIP‑планёр/ребаланс; A/B челленджеры включаются малыми долями риска.  

---

## 5. Совместимость и запуск (окружение Дениса)
- Python **3.12**, venv, macOS → VPS (Debian/Ubuntu).  
- Директории: `PROJECT="/Users/denis/Desktop/cryptobot new"`, логи, PID, БД — как в текущем проекте.  
- Профиль по умолчанию: `paper`; ключевые эндпоинты не ломать.  
- ENV при локальном запуске:  
```
APP_ENV=local
DEFAULT_PROFILE=paper
API_HOST=127.0.0.1
API_PORT=8000
PYTHONPATH="$PROJECT${PYTHONPATH:+:$PYTHONPATH}"
```
- При переносе на VPS: systemd‑юнит, health‑пробы, резервные копии БД/журналов, защищённые секреты.

---

## 6. Acceptance Tests (минимальный набор «зелёного запуска»)
- **AT‑P0**: падение лидера/сеть → split‑brain=0, RPO≈0, повторный подъём в HOLD, recon=OK.  
- **AT‑TCA**: отчёт до/после апгрейда, ≥3 метрики улучшены/не хуже.  
- **AT‑SLO**: выдержаны пороги ws_gap/order_cycle/reject/cancel_fail в течение ≥60 минут.  
- **AT‑RECON**: конец дня — ноль расхождений по позициям/балансам/фандингу/комиссиям.  
- **AT‑CONFIG**: `/api/ui/config/{validate,apply,rollback}` — работает без простоя (soft‑reload).  
- **AT‑STREAM**: `/api/ui/stream` отдаёт realtime‑метрики, алерты.  
- **AT‑HOLD/KILL**: пауза/резюм с 2‑man rule, auto‑remediation сценарии пройдены.

---

## 7. Глоссарий (сжатый)
- **Exactly‑once** — каждая сделка фиксируется один раз, перезапуски не создают дубликатов.  
- **Conformance‑suite** — батарея тестов на поведение адаптера биржи/ордер‑менеджера.  
- **Exception‑budget** — допустимый объём ошибок/деградации до остановки.  
- **TCA** — анализ издержек исполнения (комиссии, проскальзывание, ребейты, impact).

---




## 8. VPS Handoff & Zero‑Downtime Upgrade (Codex: implement end‑to‑end)

> Цель: чтобы Денис мог **без правки кода** перенести бота на VPS, безопасно подключаться к UI/метрикам и обновлять версии **без простоя и без поломок**.

### 8.1 Security posture по умолчанию (закрыто всё)
- Сервис API/UIs **биндится на 127.0.0.1** на VPS, наружу порты не торчат.
- **UFW**: `deny incoming`, `allow outgoing`, `allow 22/tcp`. Ничего, кроме SSH, не открывать.
- Секреты не в коде: `.env`/секрет‑стор, ротация ключей, аудит админ‑действий, **2‑man rule** на опасные операции.

**DoD:**
- [ ] UFW включен, входящие порты (кроме 22/tcp) закрыты.
- [ ] Uvicorn/ASGI слушает `127.0.0.1:8000`.
- [ ] Secrets backend подключён; audit‑лог активен.

### 8.2 Подключение к UI без открытия портов (SSH‑туннель)
- Сценарий для macOS:  
  `ssh -N -L 8000:127.0.0.1:8000 ubuntu@<VPS_IP>` → UI доступен на `http://127.0.0.1:8000` локально.  
- Аналогично проксировать метрики (например, 8001).

**DoD:**
- [ ] В `docs/runbooks/vps.md` есть раздел «SSH‑туннель» с примерами и скриншотами.
- [ ] Проверка: UI открывается через туннель, без открытия портов наружу.

### 8.3 Опционально: HTTPS через Nginx (не по умолчанию)
- Реверс‑прокси + HTTPS (Let’s Encrypt), **HTTP basic или mTLS**. Включать только по команде (feature flag).

**DoD:**
- [ ] В `docs/runbooks/vps.md` описана настройка HTTPS‑варианта.
- [ ] Флаги/конфиги позволяют включить/выключить реверс‑прокси без изменения бизнес‑кода.

### 8.4 Архитектура релизов (zero‑downtime, быстрый rollback)
- Директория релизов: `/opt/crypto-bot/releases/<ts>/` (код+виртуалка+зависимости).  
- Активный симлинк: `/opt/crypto-bot/current` → выбранный релиз.  
- `systemd` сервис запускает из `current`.  
- **Canary**: второе приложение на порту `9000` для smoke/AT/TCA перед переключением симлинка.  
- **Rollback**: мгновенная смена симлинка на предыдущий релиз + `systemctl restart`.

**Deliverables:**
- [ ] `scripts/deploy/release.sh` — сборка нового релиза, smoke‑запуск на `:9000`, переключение симлинка при успехе.  
- [ ] `scripts/deploy/rollback.sh` — возврат симлинка на предыдущий релиз.  
- [ ] `systemd` юнит(ы): `crypto-bot.service` (prod на 8000) и шаблон `crypto-bot@.service` (canary на 9000).

**DoD:**
- [ ] Smoke `/api/health` и `/live-readiness` для canary зелёные ≥ X минут перед переключением.
- [ ] Переключение релиза не рвёт соединения (допустимая деградация ≤ 1 рестарт цикла).

### 8.5 Управление конфигом из UI
- Реализовать `/api/ui/config/{validate,apply,rollback}` с **soft‑reload** и токеном отката.  
- В UI: форма редактирования YAML+ENV с валидацией и кнопками **Применить**/ **Откатить**.

**DoD:**
- [ ] Конфиг‑правки не требуют рестарт процесса, либо downtime ≤ 1–2 сек.  
- [ ] Валидатор ловит ошибки схемы/ограничений; rollback всегда доступен.

### 8.6 Профиль сети VPS (sysctl)
- Применить профиль (см. `vps-sysctl.conf`) для снижения хвостовых задержек: `somaxconn`, `tcp_*`, `rmem/wmem` и пр.

**DoD:**
- [ ] Файл установлен в `/etc/sysctl.d/99-crypto-bot.conf`; `sysctl --system` успешен.
- [ ] В `docs/runbooks/vps.md` есть раздел «Network tuning» с целевыми SLO улучшений.

### 8.7 Бэкапы и миграции БД
- Перед миграциями — snapshot SQLite/Postgres.  
- Alembic‑миграции **идемпотентны**, есть `downgrade`.  
- При провале миграции — auto‑rollback релиза.

**DoD:**
- [ ] `scripts/db/backup.sh`, `scripts/db/restore.sh`.  
- [ ] AT‑кейс провала миграции приводит к безопасному откату.

### 8.8 Мониторинг и алерты
- Prometheus‑метрики и SLO‑дашборд.  
- Алерты (Telegram): `slo_breach`, `hold_activated`, `recon_mismatch`, `dr_event`.  
- **Auto‑HOLD/auto‑remediation** при SLO breach.

**DoD:**
- [ ] Триггеры алертов настроены; он‑колл получает уведомления.
- [ ] Auto‑HOLD реально срабатывает и документирован в Runbook.

### 8.9 UI: Remote API Profiles (переключатель «Локально/VPS‑1/VPS‑2»)
- В UI добавить профиль удалённого API (baseURL, имя, способ подключения: SSH‑туннель/HTTPS).  
- Список профилей хранить в конфиг‑хранилище, видимый в UI; безопасный переключатель активного профиля.

**DoD:**
- [ ] Компонент UI показывает активный профиль, latency до него и `/live-readiness` статус.  
- [ ] Переключение профиля не требует перезагрузки приложения.

### 8.10 Acceptance для раздела 8
- **AT‑VPS‑SEC:** UFW/localhost биндинг, порты закрыты.  
- **AT‑VPS‑SSH:** UI доступен через SSH‑туннель.  
- **AT‑VPS‑REL:** релиз на 9000 проходит `/live-readiness` ≥ 10 мин, затем без‑простойный свитч на 8000.  
- **AT‑VPS‑CFG:** редактирование конфига через UI с валидацией и rollback.  
- **AT‑VPS‑DB:** миграция с принудительным fail триггерит rollback и восстановление снапшота.  
- **AT‑VPS‑SLO:** алерты и auto‑HOLD срабатывают при нарушении порогов.

---

## 9. Artefacts, которые должен создать Codex
- `docs/runbooks/vps.md` — пошаговая инструкция (SSH‑туннель, HTTPS‑вариант, sysctl, бэкапы, релизы).  
- `scripts/deploy/release.sh`, `scripts/deploy/rollback.sh` — релиз/откат.  
- `scripts/db/backup.sh`, `scripts/db/restore.sh` — бэкапы БД.  
- `systemd/crypto-bot.service`, `systemd/crypto-bot@.service` — сервисы.  
- `configs/config.v6.3.attributes.yaml` влит в боевой YAML профиля.  
- UI‑компонент «Remote API Profiles» + страницы `/live-readiness`, конфиг‑редактор.

**Примечание:** всё это — часть Definition of Done раздела 8. Codex обязан закоммитить артефакты в ветку `epic/indie-pro-upgrade-v2` и приложить к PR скриншоты/логи прохождения Acceptance‑кейсов.





## 10. System Status Dashboard (Codex: implement end-to-end)

> Цель: единая панель **P0/P1/P2/P3** со статусами всех функций бота. Денис открывает UI и видит: что работает, что «красное», почему, куда кликнуть за логами/метриками, какие SLO/алерты и сколько осталось exception‑budget.

### 10.1 API (обязательно)
Встроить новый модуль статусов и подключить роутер с префиксом **`/api/ui/status`**:
- `GET /api/ui/status/overview` → агрегированный снимок статуса.
- `GET /api/ui/status/components` → список компонентов (карточек) и скорингов по группам.
- `GET /api/ui/status/slo` → SLO‑снапшот (p95 ws_gap, p95 order_cycle, reject_rate, cancel_fail_rate, recon_mismatch, max_day_drawdown_bps, budget_remaining).
- (WS) `GET /api/ui/stream/status` → поток обновлений статусов (можно объединить с существующим stream).

**Контракт ответа (минимум):**
```jsonc
{
  "ts": "ISO8601 UTC",
  "overall": "OK|WARN|ERROR|HOLD",
  "scores": { "P0": 0.0..1.0, "P1": 0.0..1.0, "P2": 0.0..1.0, "P3": 0.0..1.0 },
  "slo": {
    "ws_gap_ms_p95": number,
    "order_cycle_ms_p95": number,
    "reject_rate": number,
    "cancel_fail_rate": number,
    "recon_mismatch": number,
    "max_day_drawdown_bps": number,
    "budget_remaining": number
  },
  "components": [{
    "id": "string",
    "title": "string",
    "group": "P0|P1|P2|P3",
    "status": "OK|WARN|ERROR|HOLD",
    "summary": "string",
    "metrics": { "any": "numbers" },
    "links": [{ "title": "string", "href": "string" }]
  }],
  "alerts": [ { "severity": "info|warn|error|critical", "title": "string", "msg": "string", "since": "ISO8601", "component_id": "string" } ]
}
```

> Примечание: Полная схема приложена как `status_contract.json` и должна соблюдаться в автотестах.

### 10.2 Реестр проверок (backend)
Реализовать **реестр** компонент‑проверок. Каждый компонент регистрирует функцию, которая возвращает статус и краткое описание.
**Обязательные компоненты:**
- **P0:** Journal/Outbox (gap=0), Guarded Startup, Leader/Fencing (split‑brain=0), Conformance (per‑venue), Recon (mismatch=0), Keys/Security (backend OK, audit on), Compliance/WORM.
- **P1:** Live Readiness, Recon API, Config {validate|apply|rollback}, Stream, TCA Gate, Regime Engine, Policy Matrix, Sizing/De‑risk, Fee Planner.
- **P2:** QPE, Batch Amend/Skleyka, Lock‑free Queues, Zero‑copy L2, Multi‑Region MD.
- **P3:** A/B Factory, Research Kit, Reports/Replay.

Скоринг групп P0..P3 рассчитывать детерминировано (правила в коде), а статусы OK/WARN/ERROR/HOLD раскрашивать по **порогам**.

### 10.3 Пороговые/цели
Добавить конфиг **`status_thresholds.yaml`** с порогами OK/WARN для P0..P3, и SLO‑целями для профиля (local/VPS). Поддержать override из основного YAML конфигурации.

### 10.4 UI — System Status
Создать страницу «**System Status**»:
- Шапка: Overall (цвет), активный профиль (Local/VPS‑1/..), кнопки HOLD/RESUME (2‑man rule).
- Вкладки: **P0 / P1 / P2 / P3**. Внутри — грид карточек с цветом, summary, метриками и ссылками на метрики/логи.
- Боковая панель: **SLO & Alerts**, остаток **exception‑budget**, таймлайн событий (HOLD/RESUME/Deploy/DR‑дрилы/SEV инциденты).
- Поддержать live‑обновления через WS‑стрим.

### 10.5 Интеграция SLO/OBS
- Источники SLO брать из уже имеющихся метрик Prometheus/внутреннего мониторинга.
- При breach порогов — генерировать алерт и (если настроено) переводить бота в HOLD (auto‑remediation).

### 10.6 Deliverables (создать в репозитории)
- Backend: модуль реестра проверок (`status_registry.py` или эквивалент), роутер `status_endpoints` с подключением к FastAPI.
- Config: `status_thresholds.yaml` с дефолтами; интеграция overrides.
- UI: страница «System Status», компоненты карточек и SLO/Alerts‑панель.
- Tests: автотесты на контракт `overview`, на пороговую раскраску и на реакцию HOLD при breach.

### 10.7 Acceptance
- `/api/ui/status/overview` соответствует контракту; ≥ 20 компонентов в списке, верно фильтруются по вкладкам.
- Изменение одной проверки в «симулированный ERROR» подсвечивает карточку, создаёт алерт и (если включено) переводит в HOLD.
- SLO‑боковина показывает актуальные значения и остаток exception‑budget; при ухудшении в течение ≥ X минут — алерт.
- UI обновляется в реальном времени (через WS) без перезагрузки страницы.

---

## 11. Codex Handoff (1‑pager, вставить в описание PR)

**Режим:** IMPLEMENTATION MODE — не описывай, а внедряй по этой спецификации.  
**Ветка:** `epic/indie-pro-upgrade-v2`. Коммиты батчами ≤ ~300 LOC, каждый с тестами, метриками и отчётом TCA/SLO.  
**Порядок:** P0 → P1 → SLO/OBS → Status Dashboard → VPS Handoff (раздел 8).  
**Гейты:** Ни один PR не мержится, пока не зелёные Acceptance из соответствующего раздела.  
**Артефакты к PR:** скриншоты UI (System Status), логи автотестов, выдержки из `/live-readiness`, графики SLO, TCA «до/после».





## 12. P0 Hardening Addenda (включить как обязательные требования)

> Эти пункты НЕ лишние. Они закрепляют «боевую» надёжность и должны быть явным текстом в P0. Codex обязан внедрить и закрыть DoD ниже.

### 12.1 Что уже покрыто в v6.3 (уточнить/проверить DoD)
- **Session fencing / leader-election** — есть в HA/DR (раздел 8); уточнить C-o-D per-venue.  
- **Zero‑downtime релиз (blue/green)** — есть (порт 9000→8000), `release.sh/rollback.sh`, health-гейты (раздел 8.4).  
- **DB‑бэкапы + миграции с откатом** — есть (`backup.sh/restore.sh`, Alembic downgrade, AT-rollback; раздел 8.7).  
- **VPS sysctl профиль** — есть (раздел 8.6).  
- **Remote API Profiles + /live‑readiness монитор** — есть (раздел 8.9).  
- **SLO/Alerts + Auto‑HOLD (Telegram)** — есть (раздел 8.8).  
- **Закрытая поверхность (127.0.0.1, UFW, SSH‑туннель)** — есть (раздел 8.1–8.2).  
- **Node‑гигиена (chrony, logrotate, watchdog)** — частично описано в 8/Runbooks; требуется формализовать DoD.

### 12.2 Что добавить явным текстом (встроить в P0, с DoD)
**Cancel‑on‑Disconnect / Session fencing per‑venue**  
Включить авто‑cancel при обрыве сессии (WS/API) и при смене лидера (fencing‑epoch).  
**DoD:** эмуляция обрыва → открытые ордера отменены, split‑brain=0, нет «зависших» заявок.

**Rate‑Limit Governor (централизованный)**  
Единый лимитер на процесс: приоритет **cancel/replace > place**, экспоненциальный backoff, штраф проблемным маршрутам.  
**DoD:** при 429/пике — нет «штормов», показатели reject/cancel_fail в пределах SLO.

**Clock‑skew guard**  
Chrony/NTP + мониторинг смещения; при |skew| > X мс — **HOLD** (иначе ломаются таймауты/подписи).  
**DoD:** симулированный skew триггерит HOLD, алерт уходит.

**Snapshot+Diff continuity checks**  
Инициализация книги с валидацией `seq/lastUpdateId`; abort при gap/рассинхроне.  
**DoD:** на сломанных снапшотах бот уходит в HOLD, ресабскрайб/реинициализация проходит зелёно.

**Hard Risk Kill‑caps**  
Абсолютные дневные/помесячные лимиты по notional/убытку, вне зависимости от стратегий.  
**DoD:** при превышении — немедленный HOLD/flatten, 2‑man resume.

**Runaway‑loop breakers**  
Лимит «N place/min», «N cancel/min»; анти‑flip post‑only; quarantine маршрута/символа при токсичном поведении.  
**DoD:** синтетический «разгон» не выводит систему из SLO, триггеры срабатывают и гасят цикл.

**Exchange maintenance calendar**  
Календарь плановых окон бирж; auto‑HOLD/route‑off, ранние оповещения.  
**DoD:** правила календаря выключают venue заранее, алерт виден в UI.

**Break‑glass & key‑escrow**  
Аварийный доступ по 2‑man; оффлайн‑хранение recovery‑ключей.  
**DoD:** регламент в Runbook, тех. проверка «печати» (seal), журнал действий в audit‑логе.

**At‑rest шифрование БД/журналов**  
LUKS/encfs том для SQLite/Postgres и ключевого кеша.  
**DoD:** файлы БД/журналов на зашифрованном томе; документирован процесс монтирования/бэкапа.

**Service надёжность на узле**  
`systemd` Watchdog, `Restart=on-failure`, StartLimit, logrotate, дисковая квота/alerts.  
**DoD:** имитация падений → auto‑restart, нет log‑bloat, дисковая квота ловит переполнение.

### 12.3 Интеграция в Acceptance
- **AT-P0-FENCE:** обрыв сессии/смена лидера → C‑o‑D работает, split‑brain=0, «хвостов» нет.  
- **AT-P0-RLG:** стресс по 429 → лимитер держит reject/cancel_fail в SLO, backoff активен.  
- **AT-P0-SKEW:** clock‑skew > X мс → HOLD + алерт.  
- **AT-P0-SNAPDIFF:** битый снапшот/пропуск diff → HOLD + реинициализация → нормальная работа.  
- **AT-P0-KILLCAP:** превышение kill‑cap → HOLD/flatten.  
- **AT-P0-RUNAWAY:** «разгон» ордеров → триггеры гасят цикл, SLO не сорваны.  
- **AT-P0-MAINT:** наступило окно биржи → venue выключен по правилам, алерт.  
- **AT-P0-ENC:** база/журналы на шифрованном томе; бэкап/restore рабочие.  
- **AT-P0-SVC:** сервис падает/лог‑спам/диск фулл → watchdog/rotate/квоты спасают, алерты приходят.






## 13. P1 Enhancements (Codex: implement, gated by TCA/SLO)

> Эти пункты НЕ лишние — они усиливают исполнение и устойчивость. Внедрять после полного закрытия P0, с релиз-гейтами TCA/SLO и A/B (раздел 0).

### 13.1 Drop‑Copy / Trade‑Capture per‑venue
**Зачем:** зеркальный пост‑трейд поток для безошибочного recon (дубликаты fill, пропуски WS, «призраки»).  
**DoD:** отдельный коннектор; сверка drop‑copy vs основной поток; `recon_gap=0`; отчёт расхождений за 7 дней.  
**Acceptance:** AT‑P1‑DC: разрыв основного WS → drop‑copy покрывает, mismatch=0 в конце дня.

### 13.2 Maker Quoting Core (отдельный модуль)
**Зачем:** самостоятельный котировщик: inventory‑skew, правила join/step/refresh, post‑only guard, «кочевник» по тикам, реакция на токсичность.  
**DoD:** сервис `quoting-core` с YAML‑профилями; метрики: `maker_fill_rate`, `quote_refresh_latency_ms`, `adverse_pickoff_rate`; A/B vs текущий вход.  
**Acceptance:** AT‑P1‑MQC: maker_fill_rate ≥ baseline+5%, adverse_pickoff_rate ↓.

### 13.3 Bulk‑API (batch new/cancel/amend)
**Зачем:** снижает p95 цикла и давление на лимиты при массовых апдейтах.  
**DoD:** поддержка batch по биржам; `bulk_success_rate ≥ 99.5%`; деградация в одиночные вызовы при фейлах.  
**Acceptance:** AT‑P1‑BATCH: под нагрузкой order_cycle_ms_p95 ↓ vs baseline.

### 13.4 Maintenance‑Calendar Ingest (машиночитаемые окна)
**Зачем:** авто‑HOLD/route‑off заранее, планирование релизов.  
**DoD:** фидер ics/json/rss → `/api/system/maintenance` с будущими окнами; алерты за 24h/1h.  
**Acceptance:** AT‑P1‑MC: наступление окна → venue снимается заранее, алерт в UI.

### 13.5 Multi‑homing сети / ISP‑диверсификация
**Зачем:** уменьшить риск «чёрных дыр» провайдера/RTT‑шипов.  
**DoD:** второй аплинк или WireGuard‑туннель до альтернативного VPS; health‑пробы путей; авто‑фейловер; `path_failover_time_ms` в отчёте.  
**Acceptance:** AT‑P1‑MH: симуляция падения основного пути → фейловер ≤ целевого времени.

### 13.6 Единая Self‑Trade‑Prevention (STP)
**Зачем:** унифицировать биржевую STP‑семантику (моды/IDs) и валидацию per‑venue.  
**DoD:** таблица STP‑режимов; автотесты на «склейку»/отмену; `stp_blocked_self_match_total` метрика.  
**Acceptance:** AT‑P1‑STP: self‑match блокируется везде, отчёт по метрике.

### 13.7 Intent‑Arbiter (глобальный арбитр конфликтов стратегий)
**Зачем:** не каннибалить ликвидность/лимиты, соблюсти бюджеты.  
**DoD:** сервис `intent-arbiter`: приоритеты (budget/alpha/impact), лимиты; метрика `conflict_resolved_total`; отсутствие «переезда» notional‑лимитов.  
**Acceptance:** AT‑P1‑IA: в конфликтных кейсах соблюдаются лимиты и приоритеты, TCA не ухудшается.

### 13.8 Автоматизированные Game‑Days (DR/CHAOS)
**Зачем:** регулярный прогон хаос‑кейсов со скор‑картой/PDF.  
**DoD:** еженедельный сценарий (WS‑обрыв, rate‑limit, clock‑skew, venue down); auto‑scorecard и PDF в `reports/`.  
**Acceptance:** AT‑P1‑GD: отчёт с баллами; все триггеры сработали, SLO удержаны/auto‑HOLD корректно.

### 13.9 Secrets‑Vault с авто‑ротацией (поверх HSM)
**Зачем:** TTL/lease‑политики и алерты об истечении.  
**DoD:** интеграция (напр., Vault); политики rotation; Runbook «break‑glass»; алерты expiry.  
**Acceptance:** AT‑P1‑SECR: эмуляция истечения → авто‑ротация/алерт; доступы логируются.

### 13.10 Per‑venue Heartbeat Kill‑Guard
**Зачем:** мгновенный cancel‑all при hb‑miss/md_gap.  
**DoD:** метрики `hb_miss_total`, события `auto_cancel_on_hb`; время до cancel ≤ N мс (задать в конфиге).  
**Acceptance:** AT‑P1‑HB: пропажа hb → cancel‑all ≤ N мс, алерт в UI.



## 14. P2 Advanced / Scale (Codex: implement selectively, feature‑flagged)

> Пункты расширяют масштабируемость/ресёрч. Внедрять после стабилизации P1. Все — за флагами/конфигами.

### 14.1 «Black‑Swans» сценарная библиотека + one‑click replay
**DoD:** `scenarios/` с метаданными (FTX collapse, Terra, Binance outage, USDT depeg); CLI `scenario run <name>`; отчёт сравнения до/после.  
**Acceptance:** AT‑P2‑SWAN: запуск сценария, валидный отчёт, безошибочный replay.

### 14.2 Fallback оповещения (Email/SMS/Voice)
**DoD:** провайдеры + эскалации по времени; журнал доставок; при fail Telegram — уход на fallback.  
**Acceptance:** AT‑P2‑ALERT: тест эскалаций с журналом доставок.

### 14.3 Property‑based / Fuzz‑тесты
**DoD:** Hypothesis‑пакеты для парсеров/ордер‑машины; отчёт о покрытии граничных кейсов (NaN, дубли, seq‑drift, skew).  
**Acceptance:** AT‑P2‑FUZZ: найденные граничные случаи фиксируются, регресс‑тесты добавлены.

### 14.4 Latency‑Lab
**DoD:** `latency_lab.py` + md‑отчёт: p50/p99 place/cancel, DNS, TCP‑handshake, TLS‑resume, WS‑ping; исторический трекер регрессий.  
**Acceptance:** AT‑P2‑LAT: отчёт в репозитории, тревоги при регрессе.

### 14.5 Data‑Lake / Retention‑политики
**DoD:** S3/облако с lifecycle; `cold_storage_bytes_total`; monthly restore‑drill.  
**Acceptance:** AT‑P2‑LAKE: успешный restore и верификация контрольных сумм.

### 14.6 VPIN / Order‑Flow Toxicity
**DoD:** онлайн‑оценка VPIN; флаг `avoid_toxic_flow`; корреляция со slippage в TCA.  
**Acceptance:** AT‑P2‑VPIN: при высоком VPIN входы ограничиваются, TCA улучшение ≥ целевого.

### 14.7 UI Offline Snapshot (read‑only)
**DoD:** периодический dump состояния; статическая страница snapshot при падении сети/бэкенда.  
**Acceptance:** AT‑P2‑OFF: доступен offline snapshot, данные актуальны в пределах интервала.

### 14.8 Event‑Streaming Backbone (Kafka/NATS)
**DoD:** топики/сабжекты для md‑gw, risk, pnl, research; backpressure‑алерты; схема событий; отключаемо.  
**Acceptance:** AT‑P2‑ESB: нагрузочный тест, отсутствие потерь/задержек > целевых.

### 14.9 Онбординг Market‑Maker Programs
**DoD:** чек‑листы соответствия; авто‑экспорт метрик (объём/спрэд/онлайн); напоминания по SLA.  
**Acceptance:** AT‑P2‑MM: сформирован пакет заявки на программу, метрики соответствуют.

### 14.10 Tax/Accounting экспорты по странам
**DoD:** CSV/XLSX выгрузки (двойная запись, PnL bridge); валидаторы сумм с выписками бирж.  
**Acceptance:** AT‑P2‑TAX: сверки сходятся, отчёт формируется без ручных правок.



---

# Приложение: Полный текст v6.2 (для контекста и обратной совместимости)

# PROP_BOT_SUPER_SPEC v6.2 — All-In Consolidated (Python 3)
**Date:** 2025-10-15  
**Filename remains:** `prop_bot_super_spec_v6.2.md`  
**Note:** This file **консолидирует** всё содержимое v6 → v6.1 → v6.2 + последние дополнения (v6.3 ideas), дедуплицировано и отсортировано для Codex.

**Runtime:** CPython **3.12.x** (pinned), Linux x86_64; унифицированные профили для локального запуска и **VPS**.  
**Mode:** IMPLEMENTATION MODE — не описывать, а **внедрять**. Каждый пункт → код + метрики + тесты + артефакты.

---

## Priority Legend — Prop Priority Scale (PPS)
- **P0 — Blocker / Safety-Critical** — без этого нельзя торговать (безопасность денег/данных/закона).
- **P1 — Production-Required** — обязательно для устойчивой live-торговли (доходность/устойчивость).
- **P2 — Important / Perf-Reliability** — ускоряет, повышает надёжность и эксплуатацию.
- **P3 — Nice-to-Have / Research** — полезно, но не блокирует.

Assignment Criteria: Safety/Legal/Integrity → P0; HA/DR/Availability → P0–P1; PnL/Impact → P1–P2; SLO/Latency → P2; UX/Research → P3.

---

# P0 — Blocker / Safety-Critical (делать первыми)

## Исполнение & целостность
1. **Durable Order Journal / Outbox (exactly-once)** — идемпотентные ключи, детерминированный replay.  
2. **HA/DR актив-пассив с leader-election + fencing** — **RPO=0** (журнал ордеров), **RTO ≤ целевого**; split-brain=0.  
3. **Guarded Startup & Venue-Halt Detection** — старт/торговля запрещены при холтах/деградации venue и/или stale-фидах.  
4. **Kill-Switch & Auto-Remediation** — безопасные автоматические действия на красных метриках (throttle / hold / kill-window).  
5. **Exchange Conformance-Simulator** — покрытие edge-кейсов (partial, reject, amend→cancel-replace, rate-limit storms, funding/ADL).

## Риск & казначейство
6. **Risk-Budget Governor (intraday VaR/MaxDD)** — бюджеты риска с cooldown/gradual-unlock.  
7. **State Invariants & Self-Healing** — инварианты cash/position/PNL + авто-починка/карантин расхождений.  
8. **Funding/Borrow/ADL Risk + Stablecoin Depeg** — детекторы/лимиты; hedging/exit правила.  
9. **Margin Orchestrator (cross/isolated, subaccounts)** — безопасные переключения/переводы между саб-аккаунтами.

## Маркет-данные & латентность
10. **Multi-view WS + Staleness Quorum** — k-вьюпойнтов; auto-quarantine lagging feeds; auto-failover.  
11. **Stale-Update Guard** — торгуем только при `Δt_last_update ≤ SLO`, анти flip-flop top-of-book.  
12. **Time/Latency Determinism** — chrony/PTP, CPU pinning/isolcpus, IRQ affinity, отдельные event-loops (md vs execution).

## Анти-HFT микроструктура
13. **QPE + Anti-Adverse-Selection** — вход только при приемлемой ожидаемой очереди/проскальзывании.  
14. **Capacity/Impact Controller** — кривые ёмкости; запрет overshoot; учёт maker-rebate vs токсичность.  
15. **Min Fill-Quality / Last-Look Proxy** — пороги качества заливки; отмена/снижение объёма при микро-пиле.

## Безопасность & supply-chain
16. **Hermetic Builds + Golden Images + SBOM/Attestations** — воспроизводимые образы; supply-chain подписи.  
17. **Egress Firewall (allow-list), Withdraw-OFF, HSM/YubiKey** — защита средств/ключей.  
18. **Two-Man Rule & Change-Control** — двойное одобрение risk/SOR/keys; полный аудит-трейл.  
19. **Geo/Sanctions/Jurisdiction Gate (EU/SE)** — соответствие нормам.  
20. **Compliance/Tax Pack + WORM** — экспорт ledger/PNL/fees/funding + README импорта.

## Python 3 Runtime Hardening
21. **Pinned CPython 3.12.x; venv; constraints + --require-hashes**; свои manylinux wheels.  
22. **Async-safety повсюду** — таймауты/`TaskGroup`/cancel-shielding; watchdog зависших задач.  
23. **Hot-path вне event loop** — native (Rust/C++) или `to_thread()`/процессы; без блокирующих операций в корутинах.  
24. **faulthandler / ulimit / лог-ротация / backpressure**; только `time.monotonic()`; фиксированный RNG-seed в тестах.

---

# P1 — Production-Required (доходность и устойчивость)

1. **Regime Engine 2.0 (HMM/cluster)** — режим-aware сетапы и SOR-политики.  
2. **Maker↔Taker Flip (latency/queue aware)** — динамическая смена роли по ситуации.  
3. **Real-Time Venue Router (fee-tier + latency)** — оптимальный выбор места исполнения.  
4. **Cash & Fee-Tier Planner 2.0** — удержание выгодных комиссий (без withdraw).  
5. **Multi-Region MD Aggregator (active-active)** — устойчивость региона.  
6. **Opportunity Normalizer** — нормализация выгодности по биржам/микроструктуре.  
7. **Dual Protocol Stack (WS + FIX/ITCH; REST-degrade)** — альтернативный стек и cancel-on-disconnect гарантии.  
8. **Online-TCA + PnL Attribution** — пост-трейд разбор издержек и источников прибыли.  
9. **Seasonality / Session Bias** — корректировки размеров и порогов по времени.  
10. **Inventory/Exposure Guard (Portfolio-Hedger)** — авто-сведение перп/спот; «no-overnight».  
11. **Exception-Budget мониторинг** — ошибки/мин; SLO-гейты релизов.

---

# P2 — Important / Perf-Reliability

1. **Native Hot-Path (Rust/C++)** — zero-copy L2, QPE, кодеки, lock-free очереди.  
2. **What-If & Stress Sandbox** — реплей/синтетика перед включением.  
3. **Human-in-the-Loop Knobs + instant rollback** — безопасные «ручки».  
4. **DocOps & Auto-gen (OpenAPI/арх-диаграммы)** — актуальная документация из кода.  
5. **RL-Offline Harness** — безопасная оценка decision-политик.  
6. **Cost-of-Alpha Scoreboard** — где «съедает» маржу (фиды/fees/latency/impact).

---

# P3 — Nice-to-Have / Research

1. **Execution-Replay Viewer (UI)** — визуальный проигрыватель сделок/LOB.  
2. **Voice/Push Alerts** — мгновенные уведомления.  
3. **Post-Trade Storytelling** — авто-разбор ключевых сессий.  
4. **Colo-Ready Profile (впрок)** — NUMA/NIC-offload, белые списки.

---

## API/Endpoints (новые/расширенные)
- `/api/ui/recon/orders` — `exactly_once_state`, ссылки на journal entries.  
- `/api/ui/execution` — `expected_queue_pos`, `expected_slippage_bps`, `fill_quality`.  
- `/live-readiness` — `leader`, `fencing_token`, `venue_halt`, `data_quorum`.  
- `/api/ui/ops/flags` — подписанные feature-flags + freeze windows.  
- `/api/ui/risk/{budget,funding_adl}` — лимиты и индикаторы funding/ADL.  
- `/api/ui/ops/{invariants,latency,changes,margin}` — инварианты, p50/p95/p99/p99.9 латентность, аудит изменений, статус маржи.  
- `/api/ui/md/regions` — состояние multi-region MD.  
- `/api/ui/what-if` — запуск песочницы.

---

## Метрики (ядро)
- **Execution/Integrity:** `order_exactly_once_gaps_total`, `duplicate_suppressed_total`, `recon_drift_bps`.  
- **HA/DR:** `leader_switchovers_total`, `split_brain_incidents_total=0`, `dr_drills_passed_total`, `rpo_violations_total=0`.  
- **Latency/MD:** `feed_lag_ms`, `latency_p99_9_ms_*`, `quarantine_events_total`, `md_region_failover_time_ms`.  
- **Risk:** `intraday_drawdown_pct`, `var95`, `liquidation_risk_score`, `funding_risk_score`, `adl_risk_level`, `depeg_alerts_total`.  
- **Microstructure:** `expected_slippage_bps`, `alpha_after_impact_bps`, `fill_quality_score`, `overslip_reduction_bps`.  
- **Routing/Alpha:** `ab_champion_winrate`, `venue_route_regrets_bps`, `regime_switch_profit_bps`, `fee_savings_bps`, `seasonality_uplift_bps`.  
- **Ops/Security:** `auto_remediation_actions_total`, `feature_flag_toggles_total`, `freeze_window_violations_total`, `supplychain_attestations_total`.  
- **Runtime:** `exception_budget_rate`, `watchdog_task_resets_total`.

---

## Acceptance / Deliverables
- **Чек-листы:** см. `DoD v2.4` + Addendum в этом файле ниже.  
- **Артефакты:** сим-логи, failover-drill, tax-pack, SBOM/attestations, A/B-отчёты, latency-бенчи, отчёты surveillance/venue-routing/fee-tiers, what-if сценарии.  
- **CI/CD:** атомарные коммиты по блокам P0→P3; feature-flags; canary → shadow → limited live; freeze windows соблюдать.

---

## Repo / Branch / Conventions
- **BRANCH:** `epic/indie-pro-upgrade-v2`  
- Python 3.12.x pinned; `ruff/black/mypy --strict`; `pydantic v2 (strict)`; `orjson/msgspec` сериализация.  
- Нативные модули: manylinux wheels; fallback на pure-python; ABI-чек в CI.  
- Логи с `CLOCK_MONOTONIC` и trace-id (OTel). Все критические пути покрыты p99.9 метриками.

---

## Codex Kickoff (для исполнителя)
- Внедрить P0 целиком (по подпунктам), затем P1, далее P2→P3.  
- Каждый подпункт = отдельный PR: **код + тесты + метрики + артефакты**.  
- В CI включить: hermetic build, SBOM/attestations, doc-autogen, what-if/симы.  
- Релиз через feature-flags: canary → shadow → limited live; freeze windows.

---

## 📜 Legacy: предыдущая версия (v6.2, сохранена ниже)
# PROP_BOT_SUPER_SPEC v6.2 — “All-In Baseline”
**Date:** 2025-10-15  
**Extends:** v6.1 (Annex) — без ломания обратной совместимости

**Цель v6.2:** Сразу собрать сверхмощный baseline без колокации: ввести риск-бюджеты, инварианты/самовосстановление, управляющий маржой,
герметичные сборки и золотые образы, подписанные feature-flags, geo/санкции-гейты; добавить P1 усилители доходности (regime 2.0,
maker↔taker flip, cash/fee-tier planner 2.0, seasonality, multi-region MD), P2 эксплуатацию (what-if, human-in-the-loop, DocOps, RL-offline),
и P3 R&D/UX. Все пункты заданы в режиме IMPLEMENTATION MODE (не описывать — внедрять) с задачами, метриками и артефактами.

---

## 🔁 Changelog v6.2 (добавки к v6.1)

### P0 — Blocker / Safety-Critical
**P0.18 Risk-Budget Governor (intraday VaR/MaxDD)**
- Design: лимиты бюджета риска по дню/сессии/аккаунту (VaR, MaxDD, loss buckets) + cool-down/gradual-unlock.
- Tasks: risk/budget_governor.py; конфиги thresholds; интеграция с kill-window и auto-remediation.
- Metrics: intraday_drawdown_pct, var95, budget_lock_events_total.
- Tests: синтетические просадки/рывки; отчёт: reports/risk_budget_abuse.md.

**P0.19 State Invariants & Self-Healing**
- Design: инварианты: cash = sum(fills)+fees+funding; position = Σfills; pnl = realized+unrealized; журнал несоответствий.
- Tasks: recon/invariants.py, sre/self_heal.py; триггеры safe actions.
- Metrics: invariants_violations_total=0, self_heal_actions_total.
- Tests/Artifacts: артефакты нарушений + auto-fix логи.

**P0.20 Margin Orchestrator (cross/isolated, subaccounts)**
- Design: автоматический свитчер маржи, лимиты заимствований, перевод свободных средств между саб-аккаунтами.
- Tasks: risk/margin_orchestrator.py; интеграция с venue adapters.
- Metrics: margin_switch_events_total, liquidation_risk_score.
- Tests: стресс-сценарии ликвидаций; отчёт: reports/margin_scenarios.md.

**P0.21 Guarded Startup & Venue Halt Detection**
- Design: preflight-гейт: биржа в норме, фиды свежие, креденшелы валидны, withdraw=off; детектор холтов/техработ.
- Tasks: infra/startup_guard.py, data/venue_halt_detector.py.
- Metrics: startup_block_events_total, venue_halt_events_total.
- Tests: имитация частичной деградации venue.

**P0.22 Hermetic Builds & Golden Images**
- Design: репродьюсибл сборки, зафиксированные зависимости, sbom+attestations, золотые образы VPS.
- Tasks: ci/hermetic.yml, infra/images/golden.Dockerfile; supply-chain подписания.
- Metrics: hermetic_rebuild_reproducibility_pct, supplychain_attestations_total.
- Artifacts: artifacts/images/*, attestations/*.

**P0.23 Signed Feature-Flags + Freeze Windows**
- Design: service feature-flags (подписанные), окна заморозки перед релизами/ивентами; аудит всех переключений.
- Tasks: infra/feature_flags/*, api/ui/ops/flags; интеграция в risk/execution.
- Metrics: feature_flag_toggles_total, freeze_window_violations_total=0.
- Artifacts: reports/feature_flags_audit.md.

**P0.24 Geo/Sanctions/Jurisdiction Gate**
- Design: allow/deny по IP/аккаунту/паре; политика по санкциям и локальным правилам (EU/SE).
- Tasks: compliance/geo_gate.py, policies/*.yaml.
- Metrics: geo_gate_blocks_total; Tests: списки тест-кейсов.

### P1 — Production-Required (доходность и устойчивость)
**P1.23 Regime Engine 2.0 (HMM/кластеризация)**
- Tasks: research/regime2/{hmm.py, cluster.py}, online-инференс.
- Metrics: regime_switch_profit_bps, regime_accuracy.
- Artifacts: reports/regime2_eval.md.

**P1.24 Maker↔Taker Flip (latency/queue aware)**
- Tasks: exec/role_flip.py (ввязка с QPE/latency), политики SOR.
- Metrics: flip_roi_bps, overslip_reduction_bps.
- Tests: AB на live-replay; отчёт: reports/flip_ab.md.

**P1.25 Cash & Fee-Tier Planner 2.0**
- Tasks: treasury/fee_tier_planner.py; прогноз тиров, внутренние переводы (без withdraw).
- Metrics: fee_savings_bps, tier_uptime_pct.
- Artifacts: reports/fee_tier_effect.md.

**P1.26 Vol-Seasonality & Session Bias**
- Tasks: research/seasonality/*.ipynb, runtime корректировки sizing/thresholds.
- Metrics: seasonality_uplift_bps.

**P1.27 Multi-Region MD Aggregator (active-active)**
- Tasks: data/md_agg_active_active.py, балансировщик потоков.
- Metrics: md_region_failover_time_ms, md_drop_dups_total.

**P1.28 Opportunity Normalizer**
- Tasks: research/opportunity_normalizer.py — приводить метрику «выгодности» к бирже/микроструктуре.
- Metrics: false_entry_drop_pct, normalized_sharpe_delta.

### P2 — Important / Perf-Reliability
**P2.29 What-If & Stress Sandbox (on-demand)**
- Tasks: tools/what_if_sandbox.py, сим-пресеты.
- Artifacts: reports/what_if/*.md.

**P2.30 Human-in-the-Loop Knobs**
- Tasks: ui/knobs/* с аудитом и rollback; Telegram подтверждения.
- Metrics: manual_interventions_total, rollback_success_pct.

**P2.31 DocOps & Arch Auto-Gen**
- Tasks: ci/docops.yml, scripts/gen_arch_diagrams.py, openapi автоген.
- Artifacts: docs/arch/*.svg, api/openapi.json.

**P2.32 RL-Offline Harness**
- Tasks: research/rl_offline_harness.py; оффлайн оценка политик.
- Metrics: policy_offline_score, risk_violations_offline.

### P3 — Nice-to-Have / Research
**P3.33 Execution-Replay Viewer (UI)** — tools/replay_viewer/*.
**P3.34 Voice/Push Alerts** — ops/alerts_voice_push/*.
**P3.35 Post-Trade Storytelling** — reports/storyteller/* авто-отчёты.

---

## 🔌 API/Endpoints (новые в v6.2)
- `/api/ui/ops/flags` — подписанные feature-flags и окна заморозки.
- `/api/ui/risk/budget` — текущие лимиты/использование VaR/MaxDD.
- `/api/ui/ops/invariants` — состояние инвариантов и self-heal действия.
- `/api/ui/ops/margin` — статус маржи/саб-аккаунтов.
- `/api/ui/md/regions` — статус multi-region MD.
- `/api/ui/what-if` — запуск сценариев песочницы.

## 📈 Метрики (добавки)
- intraday_drawdown_pct, var95, budget_lock_events_total
- invariants_violations_total, self_heal_actions_total
- margin_switch_events_total, liquidation_risk_score
- startup_block_events_total, venue_halt_events_total
- hermetic_rebuild_reproducibility_pct, supplychain_attestations_total
- feature_flag_toggles_total, freeze_window_violations_total
- regime_switch_profit_bps, flip_roi_bps, fee_savings_bps, seasonality_uplift_bps
- md_region_failover_time_ms, false_entry_drop_pct, normalized_sharpe_delta
- manual_interventions_total, rollback_success_pct, policy_offline_score

## 🧭 Repo/Branch
- BRANCH: epic/indie-pro-upgrade-v2 (продолжаем). Коммиты атомарные по блокам P0→P3.
- Артефакты обязательны к каждому пункту (reports/, artifacts/, docs/).

---

## 📜 Legacy: v6.1 (preserved below)
# PROP_BOT_SUPER_SPEC v6.1 — “Prop Lock-in v1 — Annex”
**Date:** 2025-10-15  
**Replaces/extends:** v6 (не ломая обратную совместимость)

**Цель v6.1:** Дожать платформу до ~92–94% prop-grade без колокации, добавив детерминизм времени/задержек, ускорение hot-path, двойной протокольный стек, market-surveillance, Funding/ADL risk, Two-Man Rule, retention/DR KPI и расширения P1/P2.

---

## 🔁 Changelog v6.1 (добавки к v6)

### P0 (обязательно в v6.1)
1. **Time/Latency Determinism**
   - Синхронизация времени: chrony/PTP, единый CLOCK_MONOTONIC в трейсе/логах.
   - CPU pinning/isolcpus, IRQ affinity, фиксированные квантовые таймеры для execution-петель.
   - Отдельные event-loops: market-data vs execution.
   - **Метрика:** latency_p99_9_ms по каждому критическому пути; цель — снижение ×2–×5.

2. **Hot-Path Native (Rust/C++ bindings)**
   - Zero-copy парсинг L2 diff, кодирование ордеров, QPE/impact в native, lock-free очереди.
   - FFI только на границах; fallback на Python при деградации.
   - **API:** те же; **Артефакты:** latency-бенчмарки, flamegraphs.

3. **Dual Protocol Stack per Venue**
   - Пара WS-коннекторов (native + альтернативный) + FIX/ITCH где возможно; REST-degrade.
   - Гарантии cancel-on-disconnect, re-login с верификацией позиций/ордера.
   - **Метрики:** protocol_failover_total, state_resync_time_ms.

4. **Trade Surveillance / Market Conduct**
   - Детекторы: spoofing/layering/self-match/quote-stuffing, лимиты на частоту отмен, штрафы.
   - Автокилл-свитч и отчёт-плейбук.
   - **Артефакты:** reports/surveillance_incidents.md.

5. **Funding / Borrow / ADL Risk Manager**
   - Прогнозы funding spikes, ADL-термометр; кэпсы на перенос, borrow-rate учёт.
   - Depeg-монитор стейблкоинов → auto-hedge/exit.
   - **Метрики:** funding_risk_score, adl_risk_level.

6. **Two-Man Rule & Change Control**
   - Для risk-лимитов, SOR-политик, ключей, withdraw-параметров — двойное одобрение.
   - Полный аудит-трейл изменений.

7. **Retention & Legal Export (EU/SE)**
   - Политики хранения/ретенции; auto-purge за сроком, «чёрный ящик» на инциденты.
   - Документация по экспорту (в т.ч. для бух. систем).

8. **DR Targets & Drills**
   - KPI: RPO=0 для журнала ордеров, RTO ≤ N сек; квартальные «чёрные» учения.
   - Автосбор контекста инцидента в артефакты.

### P1 (сильно укрепляет)
9. **Colo-Ready Profile** — отдельный профиль конфигов «colo-mode»: NIC-offload, NUMA, IP-allowlist.
10. **Model-Ops+ для SOR-политик** — A/B шампион/челленджер не только для альф, но и для правил исполнения.
11. **Real-time Venue Selection** — планировщик маршрутов с учётом текущих fee-tier/ребейтов и замеренной задержки.
12. **Reg-Pack (MiCA/MAR style)** — витрина отчётов: манипуляции/инциденты, выгрузки для аудиторов/налогов.
13. **Portfolio Hedger** — авто-сведение перп/спот/кросс-venue; режим «без ночного риска».

### P2 (повышает «оперативку» и удобство)
14. **Cost-of-Alpha Scoreboard** — где «съедается» маржа: фиды, комиссии, latency, capacity.
15. **Quant-Research UX** — шаблоны ноутов, автоген отчётов в PR, единый каталог фичей.
16. **Аппаратный “Big Red Button”** — внеполосный kill-all (USB-кнопка/педаль).

---

## 📐 Scope v6.1 (IMPLEMENTATION MODE)
Каждый пункт описан как Design → Tasks → API/UI → Метрики → Тесты → Артефакты.

### P0.11 Time/Latency Determinism
- **Tasks:** infra/latency/ptp.md, infra/latency/cpu_pinning.md; сервисы chrony/PTP; скрипты pinning/IRQ; отдельные event-loops.
- **Метрики:** latency_p50/p95/p99/p99_9_ms по: md→strategy, strategy→place, place→ack, ack→fill.
- **Тесты:** бенч-ран до/после; цель p99.9↓ ×2–×5.
- **Артефакты:** artifacts/latency/bench_DATE.csv, flamegraphs.

### P0.12 Hot-Path Native
- **Tasks:** native/book, native/qpe, native/codec; bindings/py; CI manylinux.
- **API/UI:** без изменений.
- **Тесты:** корректность против Python-референса; деградация → авто-fallback.
- **Артефакты:** reports/native_speedup.md.

### P0.13 Dual Protocol Stack
- **Tasks:** venues/*/{ws_alt, fix}; state-resync после reconnect.
- **Метрики:** protocol_failover_total, state_resync_time_ms, cancel_on_disconnect_ok_total.
- **Тесты:** отключение канала → cancel/ресинк успешны.

### P0.14 Trade Surveillance
- **Tasks:** risk/surveillance/rules.py, limits.yaml; алерты + автокилл.
- **Тесты:** симуляции spoof/layer/self-match; false positive rate.
- **Артефакты:** reports/surveillance_incidents.md.

### P0.15 Funding/Borrow/ADL Risk
- **Tasks:** risk/funding_hedger.py, risk/adl_meter.py, risk/stablecoin_depeg.py.
- **Метрики:** funding_risk_score, adl_risk_level, depeg_alerts_total.
- **Тесты:** исторические всплески funding/ADL; edge-кейсы depeg.

### P0.16 Two-Man Rule
- **Tasks:** infra/change_control/* + UI подтверждения (Telegram/веб) с журналом.
- **Тесты:** попытка одиночного изменения → отказ; журнал полон.

### P0.17 Retention/Legal/DR KPI
- **Tasks:** infra/retention_policies.yaml, auto-purge; экспортные конвейеры.
- **Тесты:** выборочные проверки сроков; DR-дриллы по расписанию.
- **Артефакты:** runbooks/dr_drills.md, artifacts/drill_*.

### P1.18 Colo-Ready Profile
- **Tasks:** configs/profiles/colo.yaml, проверка NIC/NUMA, offload.
- **Артефакты:** reports/colo_readiness.md.

### P1.19 Model-Ops+ для SOR
- **Tasks:** A/B переключатель SOR-политик, отчёт сравнений.
- **Артефакты:** reports/sor_policy_ab.md.

### P1.20 Real-time Venue Selection
- **Tasks:** exec/venue_router.py с fee-tier/latency; self-tests.
- **Метрики:** venue_route_regrets_bps.
- **Артефакты:** reports/venue_routing.md.

### P1.21 Reg-Pack
- **Tasks:** витрина отчётов (+ API), шаблоны выгрузок.
- **Артефакты:** artifacts/regpack/*.

### P1.22 Portfolio Hedger
- **Tasks:** risk/hedger.py, правила «no overnight», кросс-venue netting.
- **Артефакты:** reports/hedger_effect.md.

### P2.23 Cost-of-Alpha Scoreboard
- **Tasks:** dashboards/cost_of_alpha/*.
- **Артефакты:** скриншоты/экспорты.

### P2.24 Quant-Research UX
- **Tasks:** research/templates/*, автоген отчётов в CI.
- **Артефакты:** пример PR с отчётом.

### P2.25 Big Red Button
- **Tasks:** infra/oob_kill_switch.md, драйвер/утилита.
- **Тесты:** эмуляция на staging.

---

## 🔌 API/Endpoints (добавки v6.1)
- `/api/ui/ops/changes` — аудит изменений (Two-Man Rule).
- `/api/ui/risk/funding_adl` — индикаторы funding/ADL.
- `/api/ui/ops/latency` — агрегаты p50/p95/p99/p99.9.
- `/api/ui/venue/routing` — текущие маршруты/регреты.

## 📈 Ключевые метрики (добавки)
- latency_p99_9_ms_*, protocol_failover_total, state_resync_time_ms
- surveillance_alerts_total, auto_kill_switch_total
- funding_risk_score, adl_risk_level, depeg_alerts_total
- venue_route_regrets_bps
- dr_drills_passed_total, rpo_violations_total=0

## 🧭 Repo/Branch
- BRANCH: epic/indie-pro-upgrade-v2 (продолжаем); подпапки как в списке Tasks.
- Атомарные коммиты по пунктам; артефакты и отчёты обязательны.

---

## 📜 Legacy: v6 (preserved below)
# PROP_BOT_SUPER_SPEC v6 — “Prop Lock‑in v1”
**Date:** 2025-10-15  
**Replaces:** v5  
**Purpose:** Довести платформу до **prop‑grade**: exactly‑once исполнение, HA/DR, анти‑adverse‑selection, capacity‑aware sizing, кворум свежести данных, conformance‑симулятор, alpha‑factory, строгая секьюрность ключей, compliance‑пакет, auto‑remediation.

---

## 🔁 Changelog v6 → (новое относительно v5)
**P0 (обязательно к внедрению в этом релизе):**
1. **Durable Order Journal / Outbox** для *exactly‑once* закрытия сделок (идемпотентные ключи, детерминированный replay).
2. **HA/DR актив‑пассив** с leader‑election и **fencing tokens**, split‑brain тесты, горячий standby (другая зона/VPS).
3. **Queue‑Position Estimator (QPE)** + **anti‑adverse‑selection** фильтры на вход (динамический вход только при приемлемой ожидаемой очереди/проскальзывании).
4. **Capacity/Impact Controller**: кривые ёмкости по символам/биржам, adaptive sizing, maker‑rebate vs токсичность потока.
5. **Multi‑view market data**: параллельные WS‑вьюпойнты, **staleness quorum**, auto‑quarantine «хромающих» фидов.
6. **Exchange Conformance‑Simulator**: батарея edge‑кейсов (partial, reject, amend→cancel‑replace, burst rate‑limit, funding/ADL).
7. **Alpha‑Factory & Model‑Governance**: MLflow/registry, оффлайн/онлайн паритет фичей, drift/decay‑детекторы, champion↔challenger A/B.
8. **Key Security & Network**: HSM/YubiKey, per‑env права (withdraw=off), egress allow‑list, bastion, IP‑binding.
9. **Compliance/Tax Pack (EU/SE)**: WORM‑журнал, экспорт ledger/PnL/fees/funding (CSV) + README c импортом.
10. **Auto‑remediation runbooks**: для каждой красной метрики — безопасное автоматическое действие (throttle/hold/kill).

**P1 (желательно в v6, допускается частичный скоп):**
- Canary/shadow rollout расширения (A/B α‑моделей), weekly kill/keep.
- Online‑TCA расширение: пост‑трейд атрибуция по символам/временам суток.
- VIP/fee planner апдейт: прогноз тиров и рентабельности на горизонте недели.

---

## 🎯 Scope v6 (IMPLEMENTATION MODE — не описывать, а ВНЕДРЯТЬ)
Ниже — **конкретные задачи для исполнения** (под Codex и обычный PR‑флоу). Разделы дают: *Design кратко → Tasks → API/UI → Метрики → Тесты/Сим → Артефакты*.

### P0.1 Durable Order Journal / Outbox (exactly‑once)
- **Design:** Outbox‑паттерн + WORM‑журнал событий: `place|ack|partial|fill|cancel|reject` с reason‑codes, idempotency keys (per venue+clOrdId), deterministic replay.
- **Tasks:**
  - `app/execution/outbox.py` — продюсер/консьюмер; транзакционная запись до сетевого вызова.
  - `app/db/migrations/*` — `order_journal` (+ индексы по (venue, cl_ord_id), (parent_order_id, ts)).
  - Обработчик рестартов: re‑emit только незавершённые шаги.
  - Интеграция с `/api/ui/execution`, `/api/ui/recon/*`.
- **API/UI:** `/api/ui/recon/orders` добавляет поле `exactly_once_state`.
- **Метрики:** `order_exactly_once_gaps_total`, `outbox_replay_time_ms`, `duplicate_suppressed_total`.
- **Тесты/Сим:** kill ‑9 во время place/ack/fill — ни двойных ордеров, ни потерянных fill’ов.
- **Артефакты:** `reports/order_exactly_once.md` (с лог‑треками).

### P0.2 HA/DR актив‑пассив, leader‑election + fencing
- **Design:** Lease в KV (sqlite‑fallback/redis/zookeeper) + fencing‑token; горячий standby синхронизирует outbox и состояние.
- **Tasks:** `infra/leader.py`, health‑pings, safe‑drain на демоушн.
- **API/UI:** `/live-readiness` включает поля `leader`, `fencing_token`.
- **Метрики:** `leader_switchovers_total`, `split_brain_incidents_total=0`.
- **Тесты:** принудительный fail master → takeover ≤ N секунд; split‑brain сим.
- **Артефакты:** `runbooks/failover.md`, `artifacts/failover_drill_{date}.zip`.

### P0.3 Queue‑Position Estimator (QPE) + anti‑adverse‑selection
- **Design:** Оценка позиции в очереди на best‑bid/ask, фильтр входа при токсичных окнах.
- **Tasks:** `exec/qpe.py`, `risk/adverse_filter.py`; wiring в sizing/entry‑policy.
- **API/UI:** Добавить в `/api/ui/execution` поля `expected_queue_pos`, `expected_slippage_bps`.
- **Метрики:** hit‑rate до/после фильтра, net‑alpha after fees.
- **Тесты:** AB‑тест с фиксированной seed‑логикой.
- **Артефакты:** `reports/adverse_selection_ab.md`.

### P0.4 Capacity/Impact Controller
- **Design:** кривые ёмкости per symbol×session; adaptive size; «не лезем» при насыщении; maker‑rebate учёт.
- **Tasks:** `risk/capacity.py` + конфиг `configs/capacity/*.yaml`; санкционированные лимиты.
- **Метрики:** `capacity_utilization_pct`, `impact_cost_bps`, `alpha_after_impact_bps`.
- **Тесты:** стресс‑симы с кривыми; защита от overshoot.
- **Артефакты:** `reports/capacity_curves.pdf`.

### P0.5 Multi‑view market data & staleness quorum
- **Design:** несколько WS‑вьюпойнтов/регионов; голосование свежести; quarantine lagging feeds.
- **Tasks:** `data/freshness_quorum.py`, маршрутизация в consumers.
- **Метрики:** `feed_lag_ms`, `quarantine_events_total`, failover time.
- **Тесты:** деградация одного из фидов → авто‑переключение.
- **Артефакты:** `artifacts/feeds_failover_logs/`.

### P0.6 Exchange Conformance‑Simulator
- **Design:** дискретный сим‑движок edge‑кейсов venue.
- **Tasks:** `sim/exchange_conformance.py` + json‑наборы сценариев.
- **Тесты:** partial‑fill bursts, reject trees, amend→cancel‑replace, rate‑limit storms, funding/ADL.
- **Артефакты:** `artifacts/conformance/*`, отчёт coverage.

### P0.7 Alpha‑Factory & Governance
- **Design:** MLflow/registry; оффлайн↔онлайн паритет фичей; drift detectors; weekly council.
- **Tasks:** `research/alpha_registry.md`, `research/drift.py`, A/B wiring; champion/challenger launcher.
- **Метрики:** `alpha_decay_days`, `ab_champion_winrate`.
- **Артефакты:** weekly отчёт `reports/alpha_council_{iso_week}.md`.

### P0.8 Key Security & Network
- **Design:** HSM/YubiKey для ключей; egress firewall (allow‑list), bastion, IP‑binding/обфускация.
- **Tasks:** `infra/secrets/README.md`, политики ansible/terraform; runtime checks `withdraw=off`.
- **Тесты:** red‑team smoke (безопасное имитационное).
- **Артефакты:** `artifacts/security/sbom.spdx`, `attestations/`.

### P0.9 Compliance/Tax Pack (EU/SE)
- **Tasks:** `export/tax_pack.py` генерирует `tax_pack_{YYYYMM}.zip` (ledger.csv, pnl.csv, fees.csv, funding.csv, README).
- **Гейты:** валидаторы форматов; spot‑проверка 3 случайных дней.
- **Артефакты:** `artifacts/tax/*`.

### P0.10 Auto‑remediation runbooks
- **Design:** mapping «красная метрика → безопасное действие».
- **Tasks:** `sre/auto_remediation.py`, конфиги; dry‑run режим сначала.
- **Метрики:** сколько раз сработало; MTTR снижение.
- **Артефакты:** `runbooks/*`, `reports/mttr_delta.md`.

---

## P1 Дополнения (можно частично)
1) Расширить canary/shadow на уровень α‑моделей и SOR‑политик.  
2) Online‑TCA: атрибуция по времени суток и режиму рынка.  
3) VIP/fees planner: неделя вперёд с вероятностными интервалами.

---

## 🔌 API/Endpoints (добавления)
- `/api/ui/recon/orders` — `exactly_once_state`, ссылки на journal entries.
- `/api/ui/execution` — `expected_queue_pos`, `expected_slippage_bps`.
- `/live-readiness` — `leader`, `fencing_token`, кворум дат. 
- Логи/трейсы: OTel span от place→ack→fill→recon (расширить атрибутами outbox_id, fencing_token).

---

## 📈 Метрики (новые ключевые)
- `order_exactly_once_gaps_total`, `duplicate_suppressed_total`
- `leader_switchovers_total`, `split_brain_incidents_total`
- `expected_slippage_bps`, `alpha_after_impact_bps`
- `feed_lag_ms`, `quarantine_events_total`
- `ab_champion_winrate`, `alpha_decay_days`
- `auto_remediation_actions_total`

---

## ✅ Acceptance & Gates
Смотри **DoD v2.2** — v6 добавляет новые гейты для Outbox, HA/DR, QPE, Capacity, Feeds‑Quorum, Conformance‑Sim, Alpha‑Gov, Security, Compliance, Auto‑remediation.

---

## 🧭 Repo/Branch/PR (для Codex)
- **BRANCH:** `epic/indie-pro-upgrade-v2`
- Коммиты атомарные, по разделам P0.  
- Каждый раздел обязан положить артефакты и обновить метрики/тесты.

---

## 📁 Приложение A — файлы/директории (рекомендуемо)
```
app/execution/outbox.py
app/execution/qpe.py
risk/capacity.py
data/freshness_quorum.py
sim/exchange_conformance.py
research/{alpha_registry.md, drift.py}
sre/auto_remediation.py
export/tax_pack.py
infra/{leader.py, secrets/README.md}
runbooks/{failover.md, *.md}
reports/{order_exactly_once.md, capacity_curves.pdf, alpha_council_*.md}
artifacts/{conformance, feeds_failover_logs, tax, security, failover_drill_*}
```

---

## 📜 Legacy: v5 content (preserved for reference)
> Ниже — неизменённый текст предыдущей версии (v5), сохранён для полной совместимости и контекста.

---

# PROP_BOT_SUPER_SPEC_ONE — v5 (2025-10-15)

## Changelog (вставлено 2025-10-15)
Добавлены критически важные разделы уровня prop (P0) и важные улучшения (P1):

**P0**
1. Жизненный цикл ордеров (derivs): post-only, reduce-only, close-on-trigger, STP режимы по биржам, cancel-replace, идемпотентность маршрутизации.
2. Сквозная трассировка и корреляция: OpenTelemetry-трейсы (place→ack→fill→recon), correlation-id в логах/алертах, p50/p95/p99 по шагам пайплайна.
3. Supply-chain security: SBOM (syft), подпись артефактов (sigstore), lockfile/constraints, secret-scanner, редакция логов, ротация ключей.
4. Backfill/repair для фич-стора: политика поиска/заполнения дыр, детерминированные reprocess jobs, отчёты.
5. Капитал-аллокатор между стратегиями: бюджеты риска per-alpha, кластеризация корреляций, авто-делеверидж при co-move.
6. Стресс‑тесты/Expected Shortfall: сценарии flash-crash/funding-spike/ликвидность, отчёты ES/DD и поведение kill-switch.
7. Subaccounts/маржин-режимы: cross/isolated, переключатели плеча per‑инструмент, совместимость с reconcile.
8. Производственная оркестрация: systemd-юниты, restart-policy, graceful drain/shutdown hooks, health‑timeouts.
9. Feature toggles/rollout: shadow→canary→prod, canary‑лимиты риска, авто‑rollback по SLO.
10. Incident/postmortem: шаблоны и автосбор контекста (trace-id, top-errors, latencies).

**P1**
- Пер-эндпоинт rate-limit budgeter; cancel-on-disconnect нюансы; расширенный Linux/NIC тюнинг; справочник market‑status по биржам; портфельный VaR/ES‑kill; расширенная атрибуция по маршрутам SOR.



---

## §8.x Исполнение: жизненный цикл ордеров (P0)

### Требования
- **post_only** с защитой от проскальзывания (staleness_ms) и автоматическим cancel-replace при изменении цены шага.
- **reduce_only** строго для закрывающих ордеров; запрет flip-а позиции за счёт RO.
- **close_on_trigger** для стопов/триггеров на деривативах, где доступно.
- **Self‑Trade Prevention (STP)** c режимами по биржам (в т.ч. CANCEL_NEWEST/CANCEL_OLDEST/REJECT_NEW).
- **cancel_replace** вместо cancel+new там, где это быстрее/дешевле; идемпотентность (client_oid).
- **Индикаторы** ошибок маршрутизации и автоматические «обходы» (fallback routes).

### Конфигурация (пример YAML)
```yaml
execution:
  order_lifecycle:
    post_only: { enabled: true, staleness_ms: 500 }
    reduce_only: { enforce_on_close: true }
    close_on_trigger: { enabled: true }
    stp:
      mode_by_venue:
        binance: CANCEL_NEWEST
        okx: CANCEL_OLDEST
        bybit: REJECT_NEW
    cancel_replace:
      enabled: true
      max_latency_ms: 25
      idempotency: true
```

### DoD
- STP‑rejects < 0.1%/сутки; **0** незапланированных flip-ов из‑за RO.
- На maker‑ветке post_only проскальзывание = 0 на N≥1000 ордеров.
- Отчёт `reports/execution_lifecycle.md` с p50/p95/p99 на place→ack и cancel_replace.

---

## §4.x Observability/Tracing (P0)

### Требования
- **OpenTelemetry** трейсинг для этапов: ingest→signal→route→place→ack→fill→recon.
- **correlation_id** в логах/алертах, линк «jump‑to‑trace» в уведомлениях.
- Метрики p50/p95/p99, top‑N «медленных» спанов/сутки.

### Конфигурация
```yaml
observability:
  tracing:
    enabled: true
    exporter: otlp
    span_attrs: [venue, symbol, side, coid, route, env]
  logging:
    redact: [api_key, secret, passphrase, tokens]
    correlation_id: propagate
```

### DoD
- Дашборд с распределениями задержек на **каждом** шаге пайплайна.
- Алерт указывает trace‑id и ссылку на трейс.

---

## §2.x Supply-chain / CI Security (P0)

### Требования
- **SBOM** (syft) и **подпись артефактов** (sigstore) на релизах.
- **Lockfiles** (uv.lock/constraints.txt) — воспроизводимые сборки.
- **Secret‑scanner** в CI; **маскирование секретов** в логах; **ротация** ключей ≤90 дней.

### Конфигурация
```yaml
supply_chain:
  sbom: syft
  artifact_signing: sigstore
  lockfiles: [uv.lock, constraints.txt]
  secret_scanner: true
  key_rotation_days: 90
```

### DoD
- Релиз блокируется без SBOM и подписи; в логах отсутствуют секреты (юнит‑тест проверяет).

---

## §3.x Data Backfill / Repair (P0)

```yaml
data_backfill:
  gaps_policy: detect->queue->fill->audit
  reprocess_jobs: { deterministic: true, idempotent: true }
  reports: { daily: gaps_filled.md }
```
**DoD:** Реплей на историке совпадает с live‑метриками ±ε; отчёт `reports/gaps_filled.md` присутствует.

---

## §5.x Capital Allocator (P0)

```yaml
risk_allocator:
  budgets:
    per_alpha: {max_notional, max_dd, max_var}
  correlation:
    cluster_method: "spearman+ward"
    co_move_cooldown_min: 30
  auto_deleverage_on_cluster_dd: true
```
**DoD:** Автоматическое урезание размера при кластерном DD; отчёт о перераспределениях в `reports/risk_budgets.md`.

---

## §11.x Stress / ES (P0)

Сценарии: flash‑crash, funding‑spike, divergence mark/index, неделя низкой ликвидности.  
Метрики: **ES(x%)**, maxDD, время/порог срабатывания throttle/kill.

**DoD:** `reports/stress.md` на каждый релиз; триггеры kill/throttle подтверждены.

---

## §6.x Subaccounts / Маржин‑профили (P0)

Профили per‑venue: subaccount, cross/isolated, плечо per‑инструмент.  
**DoD:** Смена режима не ломает reconcile; повышение плеча — под Two‑Man Rule.

---

## §2.y Оркестрация (systemd) (P0)

- service‑юниты с restart=always, watchdog‑heartbeats.
- **graceful drain/shutdown hooks**, health‑timeouts.
- Атомарные релизы (symlink‑switch), авто‑rollback по SLO.

**DoD:** crash‑loop не приводит к зомби; safe‑mode автозадействуется.

---

## §11.y Feature toggles / Rollout (P0)

- Фич‑флаги: **shadow → canary → prod**; canary‑лимиты риска.
- Авто‑rollback по SLO/ошибкам.

**DoD:** Доказанный путь активации без правок кода; отчёт `reports/rollout.md`.

---

## §2.z Incident / Postmortem Templates (P0)

Автогенерация `incidents/incident-YYYYMMDD-HHMM.md` и `postmortems/pm-…md` c trace‑id, top‑errors, p50/p95/p99 и кратким таймлайном.



---

## §9.x Улучшения P1

- Пер‑эндпоинт **rate‑limit budgeter** + токен‑бакеты.
- **Cancel‑on‑disconnect** нюансы per‑venue и автоперевыставление флага.
- Расширенный **Linux/NIC** тюнинг: rps/xps, ethtool coalesce.
- Справочник **market‑status** (maintenance, degrade, post‑only windows).
- Портфельные **VaR/ES‑kill‑switch** (кластерный DD).
- Расширенная **PnL‑атрибуция по SOR‑маршрутам** (до/после ребейтов).



---


<!-- Auto-augmented on 2025-10-15 04:28 UTC -->

# PROP‑BOT SuperSpec v3 (RU, Unified)

**Что это:** единая, структурированная спецификация, объединяющая твою **Супер‑Спеку v2** (полностью русская, с подсказками, шкалой риска, лимитами, финансами и жёсткой безопасностью) и **Полную спецификацию** (архитектурная карта, дерево проекта, конфиги, API, метрики, CI/CD и приёмка).

— Все тексты и подсказки — **на русском языке**.  
— Встроены **info‑точки “i”** с «что это» и «на что влияет».  
— Управление из UI: **validate → apply → rollback**, безопасные дефолты, **Two‑Man Rule** для опасных действий.  

---

## 0) Язык и помощь (из v2, дополнено)
- ru‑RU — язык по умолчанию, en‑US — фолбэк.  
- «Простые объяснения» (ВКЛ/ВЫКЛ), info‑точки, интерактивный тур и `USER_GUIDE_RU.md`.  
- Быстрые подсказки (≤100 мс), не перекрывают важные элементы.

---

## 1) Архитектура (объединено)
- **Сервисы v2:** md‑gw · feature‑svc · strategy‑core · risk‑svc · exec‑svc (SOR/live) · treasury‑svc · recon‑svc · pnl‑svc · research‑kit · ui‑api · authz/audit · obs/chaos.  
- **Хранилища:** Parquet (данные/фичи), SQL (состояние), Redis (кэш). Контракты схем и интеграционные проверки.  
- **Синхронизация времени:** chrony/PTP, латентностный бюджет по стадиям.  
- **Подробное дерево проекта (из Полной спецификации):**
## 2) Архитектура и дерево проекта
```
crypto-bot/
  app/
    bot/                      # оркестрация стратегий
      arb_live_bot.py
      arb_paper_bot.py
    execution/
      base.py                 # контракты и общие типы
      live.py                 # live‑исполнение (deadlines, идемпотентность, cancel-all)
      paper.py                # бумажное исполнение (p_fill)
      sor.py                  # маршрутизация (scoring)
      guardrails.py           # ценовые коридоры, notional/qty caps, rate-limits, cool-off
    exchanges/
      binance_native.py       # WS+REST (perp) + testnet
      okx_native.py
      bybit_native.py
      adapters.py             # унификация моделей (OB/trades/mark/funding)
    data/
      orderbook.py            # snapshot+diff, seq/gap, stale-detector
      funding.py              # ставки funding/OI/basis
      recorder.py             # запись Parquet
    replay/
      engine.py               # оффлайн‑движок через тот же decision/exec‑путь
      store.py                # чтение/партиции (Parquet)
      lob_micro.py            # L2/L3 микросимулятор (очередь)
      tca.py                  # online‑TCA + expected_slippage_bps()
    risk/
      limits.py               # дневные капы per symbol/family, time-of-day budgets
      sizing.py               # размер, Q‑скейлинг
      quantizer.py            # price/qty шаги
      policy.py               # режимы maker/taker, reduceOnly, position‑mode
    pnl/
      reconcile.py            # сверка с биржей (fees/funding/realized)
      attribution.py          # alpha vs slippage vs fees vs funding
    recon/
      daemon.py               # reconciliation daemon (orders/positions/balances)
      api.py                  # /api/ui/recon/*
    ui/
      server_ws.py            # FastAPI маршруты + /dashboard
      streams.py              # /api/ui/stream (WS / SSE fallback)
      config_apply.py         # validate/apply + soft‑reload + rollback
      security.py             # RBAC, approvals (Two‑Man Rule), authN/Z
      telegram_bot.py         # опционально
    infra/
      readiness.py            # /live-readiness + SLO/safe_mode
      leader_lock.py          # single‑trader lock + fencing tokens
      state.py                # чекпоинтинг inflight/exposure, идемпотентный рестарт
      metrics.py              # Prometheus регистраторы
      logging.py              # структурные логи + audit trail
  configs/
    config.paper.yaml
    config.live.yaml
    config.dev.yaml
    secrets.example.yaml
  scripts/
    accept.sh
    load_test.sh
  reports/
  tests/                      # pytest (unit/integration/e2e/chaos)
  .github/workflows/
    ci.yml
    acceptance.yml
  Makefile
  pyproject.toml
  README.md
  OPS.md
  RUNBOOKS.md
  DASHBOARD.md
  CONFIG_EDITING.md
  RESEARCH.md
  API.md
  FINAL_REPORT.md
```

---

## 2) Среды, НФ‑требования, OS/VPS тюнинг
- Python 3.12, линт/типизация (`ruff`, `black`, `mypy --strict`), Docker, SBOM.  
- Профили: paper, testnet, live, dev; feature‑flags.  
- SLO‑целевые p95: `order_cycle≤500ms`, `ws_gap≤200ms`, `book_freshness≤250/300ms`, `cancel_all≤1500ms`.  
## 8) Надёжность: /live‑readiness, SLO, Single‑Trader Lock, DR
- `/live-readiness` → `{ ok: bool, reasons: [], metrics: {...} }`, учитывает p95 `ws_gap_ms`, `book_freshness_ms`, `order_cycle_ms`, fill‑ratio, backlog.  
- SLO‑гвардейцы: авто **safe_mode** по порогам YAML.  
- Single‑Trader Lock: лидер‑элекция (Redis/etcd) + **watchdog‑kill** двойника.  
- DR/Checkpointing: периодические снимки (экспозиции, inflight, квоты) → идемпотентный рестарт **без дублей**.

---

## 3) Маркет‑данные и качество (объединено)
- Binance UMFutures, OKX v5, Bybit v5: native WS + REST‑snapshots, схема snapshot+diff с `seqId`, gap‑recovery, stale‑детектор.  
- Метрики качества: `ws_gap_ms`, `snapshot_age_ms`, `book_freshness_ms`; watermarks, dedup, late‑data.  
- Fallback ccxt(pro) при деградации.  

---

## 4) Фичи, режимы и аналитика
- OFI, Imbalance, CVD, microprice, vol/skew/kurtosis, funding/basis, OI/liquidations, корреляции, liquidity map.  
- Классификатор режимов (эвристика+ML) + drift‑детект; fallback Range.  
- Online‑TCA, LOB‑микросим для калибровки `p_fill`.  
- **Advisory‑mode** (read‑only советы; не приказы):  
## 14) Advisory‑mode (подсказки, не приказы)
- Флаг `center.advisory.enabled=false` и `crypto_bot.advisory.consume=false` (бот **читает и логирует**, ордеров не ставит).  
- Формат `Advice` с полями: `symbol`, `side`, `tf`, `confidence`, `rationale`, `drivers[]`, `risk`, `valid_until`.
- WS topic `"advice"` + REST `GET /api/ui/advice`.

---

## 5) Шкала риска 0–100% + Safe‑mode (из v2)
- Переключатель ВКЛ/ВЫКЛ; `level∈[0..100]` → таргет‑риск/дневной кап/размеры/тайминги/микс maker‑taker/лимиты конкуренции/плечо*.  
- Caps per env (paper/testnet/live), Two‑Man на повышение в live; auto safe‑mode при SLO/Recon проблемах.  
- UI показывает «человеческое резюме» изменений.

---

## 6) Плечо (маржин) (из v2)
- Тумблер **Плечо: ВКЛ/ВЫКЛ**, потолок плеча (напр. 2×/3×).  
- В live поднятие потолка — только по Two‑Man.

---

## 7) Лимиты/коридоры и pre‑trade guards (из v2 + FULL)
- Правила Global/By‑Venue/By‑Symbol, `min/max_notional_usd`, `side_caps(LONG/SHORT)`, `max_concurrent_positions`, `max_inflight_orders`.  
- `price_bands`: ±bps от mid/mark или [min,max] абсолютом; блокируем ордера вне коридоров с понятной причиной.  
- Проверка против `minQty/stepSize/minNotional/precision`, авто‑rollback невалидных настроек.

---

## 8) Исполнение, SOR и live‑hardening (объединено)
- Идемпотентность (clientOrderId+fencing), строгие дедлайны, cancel‑all≤1500мс, STP, postOnly stale‑guard, cancel‑on‑disconnect.  
- Token‑Bucket REST (429/418), maintenance/quarantine awareness, leader‑lock.  
- **SOR**: скоринг venues по `cycle_time_p95`, `p_fill`, fees/VIP, impact, queue‑pos, reliability; `route_reason` и ожидаемый `slippage_bps`.  

---

## 9) Финансы и казначейство (из v2 + FULL)
- Балансы/эквити/маржа/Unrealized PnL по биржам (и суммарно, в USD).  
- PnL дневной/недельный/месячный; комиссии, funding; графики/экспорт CSV/Parquet.  
- Ledger: депозиты/выводы/переводы/комиссии/funding. VIP/fees planner, ребалансер.

---

## 10) Сверка и PnL‑атрибуция (объединено)
- Recon‑демон (orders/positions/balances) → diffs=0; orphan‑fix.  
- PnL‑атрибуция: alpha vs slippage vs fees vs funding; **дневной дрейф ≤0.1%** к отчётам биржи.

---

## 11) Replay/Backtest/LOB (объединено)
- Record‑and‑Replay через тот же decision/exec путь; KPI‑отчёты; сценарии событий.  
- LOB‑микросим (очередь L2/L3), калибровка p_fill; Online‑TCA рефит.

---

## 12) PRO/HFT‑панели (из v2)
- Latency‑waterfall; Circuit‑breakers; A/B & Shadow; What‑If Risk Sandbox; VIP/Fees Planner; Incident Timeline; Trade Replay; Change‑Mgmt; Rate‑Limit Monitor; Data‑Quality Board; Compliance Export.

---

## 13) Управление биржами из UI (из v2)
- «+ Добавить биржу», ключи, testnet/live, **Проверить подключение** → **Сохранить**.  
- Если коннектора нет — профиль сохраняется (status: `connector missing`), горячая подгрузка позже.

---

## 14) Безопасность и «вывод невозможен» (из v2 + FULL)
- На биржах: суб‑аккаунты, API только Read/Trade, IP‑whitelist, Withdrawal whitelist, 2FA+FIDO2, anti‑phish.  
- В боте: **нет кода withdraw/transfer**, egress‑firewall (allow‑list доменов/SNI), HTTP‑санитайзер путей (вид withdraw/transfer/address → блок+алерт+стоп), RBAC+Two‑Man, WORM‑аудит, секреты в хранилище, non‑root/ro‑FS/seccomp, tripwire‑агент.  
- E2E‑тест «withdraw невозможен» обязателен.

---

## 15) Observability & Readiness (объединено)
- `/live-readiness` → ok/degraded/fail, авто safe‑mode при fail.  
## 16) Метрики (Prometheus)
Минимум:
- `ws_gap_ms`, `book_freshness_ms`, `order_cycle_ms`, `cancel_time_ms` (p50/p95/p99, per venue/symbol/side/size-bucket)
- `fill_ratio_real`, `expected_vs_real_slippage_bps`
- `venue_health{venue}`, `risk_trips_total`, `cancel_all_total`, `exec_mode_info`
- `orders_inflight`, `route_reason_count{reason}`, `advice_count`
- Ошибки по классам: `ws_errors_total`, `rest_errors_total`, `rate_limit_hits_total`

---

## 16) API (сводная выжимка)
- **UI‑API (ru‑интерфейс):** i18n/tooltips, stream(SSE), settings(risk‑profile/limits), treasury(balances/ledger), pnl, config(validate/apply/rollback), approvals (Two‑Man).  
- **REST/прочие (из Полной спецификации):**  
## 13) API (REST)
Минимальный набор (расширяем по мере внедрения):
- `GET /api/health` → `{status, version, ts}`
- `GET /live-readiness` → `{ ok, reasons[], metrics{} }`
- `GET /api/opportunities`
- `GET /api/ui/execution`, `GET /api/ui/pnl`, `GET /api/ui/exposure`
- `POST /api/control` → `{action: "pause|resume|kill|hedge"}` (Two‑Man Rule на опасные действия)
- `GET /api/ui/stream` (WS) | `/api/ui/stream-sse` (SSE) — topics: `health`, `opportunities`, `execution`, `risk`, `pnl`, `latency`, `logs`, `advice`
- `POST /api/ui/config/validate` → `{ valid: bool, errors[] }`
- `POST /api/ui/config/apply` → `{ applied: bool, message, rollback_token }`
- `POST /api/ui/profile/switch` → `{ profile }`
- Recon: см. раздел 9
- Analytics center:  
  `GET /api/ui/regimes`, `/api/ui/signals`, `/api/ui/liquidity`, `/api/ui/derivatives`, `/api/ui/risk`, `/api/ui/channels`
- Advisory‑mode:  
  `GET /api/ui/advice?symbols=...&tf=...&limit=100` (см. схему `schemas/Advice.json`)

**Схемы (прикладные, pydantic v2) описать в `API.md`.**

---

## 17) Конфигурация и флаги (включая пример YAML)
## 3) Конфигурация и feature‑flags
- Все параметры в `configs/*.yaml` + переопределения через ENV.
- **Минимальный пример `configs/config.paper.yaml`:**
```yaml
profile: paper
server:
  host: 127.0.0.1
  port: 8000
symbols: ["BTC/USDT", "ETH/USDT"]
venues:
  binanceusdm:
    api_key: ${BINANCE_KEY}
    secret: ${BINANCE_SECRET}
    testnet: true
  okx:
    key: ${OKX_KEY}
    secret: ${OKX_SECRET}
    passphrase: ${OKX_PASSPHRASE}
    testnet: true
  bybit:
    key: ${BYBIT_KEY}
    secret: ${BYBIT_SECRET}
    testnet: true
market_data:
  ws:
    reconnect_jitter_ms: [500, 2000]
    stale_ms: 1200
  rest_snapshot_sec: 1
execution:
  mode: paper             # paper|live
  maker_taker: hybrid     # maker|taker|hybrid
  deadlines_ms:
    place: 400
    cancel: 300
  retry:
    attempts: 3
    backoff_ms: [50, 150, 300]
  price_bands_bps: 6
  per_order_notional_cap: 50        # USDT
  rate_limits_per_symbol_per_min: 20
  cool_off_on_errors_sec: 5
risk:
  notional_caps:
    per_symbol:
      BTC/USDT: 200
      ETH/USDT: 200
    per_venue:
      binanceusdm: 500
      okx: 500
      bybit: 500
  daily_drawdown_cap_pct: 2.5
sor:
  weights:
    cycle_time_p95: 0.25
    p_fill: 0.25
    fees_vip: 0.15
    impact: 0.15
    queue_pos: 0.10
    reliability: 0.10
readiness:
  slo:
    order_cycle_ms_p95: 500
    ws_gap_ms_p95: 200
    book_freshness_ms_p95: 250
  safe_mode_on_breach: true
advisory:
  enabled: false
ui:
  rbac: true
  approvals_two_man_rule: true
  stream_hz: 4
logging:
  level: INFO
  audit: true
storage:
  db_url: sqlite+aiosqlite:///./data/crypto_bot.db
  parquet_dir: ./data/parquet
```
- **Секреты** вне репо: ENV/Keychain/Vault. Пример шаблона: `configs/secrets.example.yaml`.

---

## 18) CI/CD, Makefile и приёмка
## 21) Makefile цели (обязательны и зелёные)
```
make install
make lint
make mypy
make test
make run
make db-init
make backtest
make replay FILE=...
make live-dryrun
make micro-live
make acceptance
```
Все цели обязаны корректно работать с путём `"/Users/denis/Desktop/cryptobot new"`.

## 22) Примеры SLO и финальная приёмка
- SLO (paper/micro-live): `order_cycle_ms p95 ≤ 500ms`, `ws_gap_ms p95 ≤ 200ms`, `fill_ratio_real ≥ 60%`.  
- Команды приёмки:
  ```bash
  make install && make lint && make mypy && make test
  make backtest           # KPI → reports/
  make live-dryrun        # /live-readiness -> { ok: true }
  make micro-live         # min-size, строгие капы
  ```
- Итоговый артефакт: **`FINAL_REPORT.md`** (ссылки на PR/CI, скрины UI/метрик, readiness/SLO‑вердикт, PnL‑сверка ≤0.1%, отчёты backtest, результаты chaos, список обновлённых зависимостей с планом тестов, чек‑лист Go‑Live).

---

## Глоссарий ключевых JSON‑форматов (кратко)
- **Advice**: `{ "symbol": "BTC/USDT", "side": "long|short|flat", "tf": "1m|5m|...", "confidence": 0..1, "rationale": "...", "drivers": ["funding_down", "liq_spike"], "risk": "low|med|high", "valid_until": "ISO8601" }`
- **Readiness**: `{ "ok": true, "reasons": [], "metrics": { "ws_gap_ms_p95": 180, "book_freshness_ms_p95": 210, "order_cycle_ms_p95": 420, ... } }`
- **Route decision**: `{ "venue": "okx", "mode": "maker|taker", "route_reason": "p95_cycle_better|vip_fee|impact_low|...", "expected_slippage_bps": 3.2 }`

---

## Правила реализации
- Строгая типизация; явные pydantic‑схемы для всех публичных API.  
- Идемпотентность и **exactly‑once** завершение для ордеров при рестартах.  
- Все потенциально опасные действия через RBAC + Two‑Man Rule.  
- Никаких “магических” констант — всё в YAML/ENV.  
- Обязательная телеметрия (метрики/логи/трейсы) для разбора инцидентов.

```

### Приложение B — crypto-bot-analytic-center-spec-v1 (исходник, включено дословно)
```
# SPEC — Полный Аналитический Центр + Advisory‑mode (для crypto-bot)  
**Версия:** v1.0 • **Совместимость:** не ломать существующие API/UI • **Цель:** уровень инди‑про/малый проп (операционное качество, наблюдаемость, исполнение, риск)

---

## 0) Инварианты и область
- **Не ломать** текущие эндпоинты (`/api/health`, `/api/ui/*`) и схемы.
- **Добавлять** новые API/флаги/WS топики с SemVer‑версированием.
- **Конфиг‑флаги** управляют всеми функциями (feature‑flags, безопасные дефолты).
- **Definition of Done** в конце файла — обязательные проверки.

---

## 1) Источники данных (ингест) и микроструктура
- **CEX перпетуалы:** Binance UMFutures, OKX v5, Bybit v5.  
  **Native WS** (trades/books/tickers/funding/OI/liquidations) + **REST‑snapshots**.  
  Контроль `seqId`/gap‑fill/ресинк, параллельно **CCXT** как резерв.
- **Деривативы:** funding (live+history), **Open Interest**, **basis**, **long/short ratio**, **ликвидации**.
- **Микроструктура:**
  - **OFI/Imbalance**, **CVD**, **Liquidity map** (depth densities), **impact‑кривая (Kyle/λ)**.
  - Разделение цен **mark/index/last**, отслеживание делистингов/alias и **изменений правил funding**.
- **Метаданные контрактов (`/api/md/meta`):** tick/lot/minNotional, множители, комиссии, расписания funding, ID/aliases, версия правил.

---

## 2) Время, метки и водяные метки
- **Time sync:** NTP/chrony; (опц.) **PTP/PHC** и hardware timestamping. Метрики `clock_skew_ms`, `phc_locked`.
- **Watermarks:** event‑time vs processing‑time; политика **late‑data** и **dedup** по `(symbol, seqId, ts, venue)`.

---

## 3) Хранилища и фичи
- **Feature‑store:** Parquet (partitioned by `dt/symbol/tf`) + **KV‑кэш** (TTL).  
  **Lineage/versioning** (DVC), **retention/compaction** (горячее/тёплое/архив).
- **Data contracts:** Great Expectations на сырьё/фичи (диапазоны, монотонность `seqId`, уникальность).
- **Архив:** шардируемые jsonl/pcap WS‑потоки; **replay** для восстановления рынка.

---

## 4) Режимы/ML/сигналы
- **Классификатор режимов:** эвристики + ML; **fallback=Range**. Метки: тренд/вола/ликвидность/funding‑режим.
- **Drift‑детект:** PSI/KS, алерт/флаг **auto‑fallback** до эвристик.
- **Сигналы:** Long/Short/Flat с `confidence∈[0,1]`, **TTL/expiry**, условия **инвалидации** (funding flip, вола>порог).
- **Explainability:** reason‑codes и топ‑фичи.
- **Калибровка вероятностей:** Brier/ECE, reliability‑диаграммы.

---

## 5) Execution‑sim (paper) и честность моделирования
- Алгоритмы: **IOC/FOK**, **TWAP/VWAP**, **POV**; лимиты доли объёма/минуты.
- **Очередь/проска:** impact‑кривая, adverse‑selection, **latency injection**, **queue‑position estimator**, Monte‑Carlo.
- **What‑if:** пересимуляция исторических сигналов при альтернативных latency/fees.

---

## 6) Advisory‑mode (подсказки, не приказы)
- **REST:** `GET /api/ui/advice?symbols=…&tf=…&limit=100`  
- **WS:** топик `"advice"` в `/api/ui/stream`.
- **Схемы:** `schemas/Advice.json`, `Signal.json`, `Regime.json`, `MarketMetrics.json`, `AdviceWhy.json`.
- **Пояснимость советов:**  
  `GET /api/ui/advice/why?id=…` — причины, контекст (режим/ликвидность/funding), ожидаемая просадка, **рекоменд. макс‑размер** (не приказ).  
  `GET /api/ui/advice/perf?lookback=…&by=regime|liq` — эффективность советов по режимам/ликвидности.
- **Флаги/безопасность:**  
  `center.advisory.enabled=false` (по умолчанию), **read‑only токены**, rate‑limit, аудит включений/чтений.  
  Для бота: `crypto_bot.advisory.consume=true|false` — читает/сравнивает, **не исполняет**.

---

## 7) UI (операционный и исследовательский)
- Доски: **Signals vs Advice**, **Regimes**, **Liquidity Map**, **Liquidations Heatmap**, **Imbalance/OFI**, **CVD & Volume Profile**,  
  **Quality & Latency**, **Correlation & Clusters**, **Ops/SLO**, (опц.) **News** (тумблер).
- Интерактив: фильтры по ликвидности/vol/funding, мульти‑ТФ, **explain** карточки, аннотации событий.

---

## 8) Риск, исполнение и ордерный контур
- **Pre‑trade risk server:** `max_notional`, `max_order_size`, **price bands** (±Xσ/ref), **orders/sec throttle**, **STP**, **cancel‑on‑disconnect**.
- **Kill‑switch** (two‑man rule), **daily loss cap**, **max drawdown**, **cool‑off** окна.
- **Idempotency:** ключи на ордера, **ОКО** (источник idempotency), maker/taker‑switch, **post‑only staleness guard**.
- **Журнализация (drop‑copy surrogate):** WORM‑лог всех ордерных событий, меркле‑хеши по часам, **crash‑recovery** + **cancel‑all**.
- **Состояния venue/symbol:** maintenance/cancel‑only/degraded; список **quarantine**.

---

## 9) Казначейство, экспозиции и комиссии
- **Net/Gross exposure** per venue/symbol, **ребалансер** капиталов, **funding optimizer**.
- **VIP/tiers:** учёт **maker rebates**, эскалация уровней комиссий, симуляция экономии.

---

## 10) PnL и атрибуция
- Разложение PnL: **carry/funding**, **fees/rebates**, **market impact**, **slippage vs model**, **timing**.  
  REST: `/api/ui/pnl/attribution`.

---

## 11) Наблюдаемость, SLO и алерты
- **Качество данных:** свежесть, пропуски, seq‑gaps, clock‑skew, drop‑ratio.  
  REST: `/api/ui/quality`, `/api/ui/slo`.  
- **Латентность:** WS/REST latency, reconnects/resubscribe, p95/p99 и **stage‑by‑stage** (`tick→feature→signal→advice`).  
  REST: `/api/ui/latency`.
- **Алерты:** stale data, seq‑gap, funding fetch fail, drift>threshold, latency breach, **backpressure trips**, **clock‑skew**.
- **Телеметрия:** Prometheus/VictoriaMetrics, контроль **кардинальности метрик**.

---

## 12) Исследования/ML и управление версиями
- **Лейблинг:** triple‑barrier, event‑based sampling; **meta‑labeling**.  
- **Валидация:** walk‑forward, purged k‑fold, leakage‑checks.  
- **Регистр моделей:** MLflow (registry/artifacts/params).  
- **Shadow/Canary:** теневая модель (логируем, не показываем), canary‑трафик 5–10%; A/B «show vs holdout».  
- **Калибровка advice:** ECE/Brier по режимам/ликвидности.

---

## 13) Тестируемость и воспроизводимость
- **Record‑and‑replay** (jsonl/pcap), **golden‑tests** для фич/режимов/сигналов.  
- Property‑based тесты критичных трансформаций.  
- **Chaos/Fault‑injection:** latency spikes, packet loss, disconnects, stale snapshots, reject/partial‑fill эмуляция.

---

## 14) Производительность и ОС‑тюнинг
- **Pinned CPU/IRQ**, `ulimit`, TCP‑тюнинг, GC, `uvloop`/asyncio.  
- Warm‑up кешей/соединений, pre‑subscribe + snapshot‑prefetch.  
- **Tail shaving** p99/p999.

---

## 15) Топология, лидерство и восстановление
- **Single‑trader lock** (leader‑election), hot‑standby, watchdog‑рестарты.  
- Разделение процессов: ingest/risk/execution/UI.  
- **DR/Backups:** снапшоты feature‑store, offsite, тест восстановления раз в спринт.

---

## 16) Безопасность и комплаенс
- RBAC (`viewer/analyst/admin`) со скоупами, **IP‑allowlist**, секреты в KMS/HSM, ротация ключей, секрет‑скан в CI.  
- **WS‑подпись/HMAC**, **replay‑protection**, CORS allowlist.  
- Журналы WORM N‑дней, **двухфактор** на критичные действия.  
- **Compliance/Tax Export** (CSV/Parquet), privacy‑scrub.

---

## 17) Операционный контур
- **Runbooks:** `/api/ui/ops/runbooks`, SOD/EOD чек‑листы, go/no‑go, on‑call, **error‑budget**.  
- Инциденты: шаблон постмортема, SLA/SLO‑политика, страница совместимости/депрекейтов.

---

## 18) API — существующие и новые (REST)
**Сохранить:**  
`GET /api/health`  
`GET /api/ui/regimes`  
`GET /api/ui/signals`  
`GET /api/ui/liquidity`  
`GET /api/ui/derivatives`  
`GET /api/ui/risk`  
`GET /api/ui/pnl`  
`GET /api/ui/execution`  
`GET /api/ui/channels`  
`GET /api/ui/news?limit=…` → `{enabled:false}` если выключено

**Добавить (аналитика/качество/пояснимость):**  
`GET /api/ui/quality` — свежесть, seq‑gap, clock‑skew, drop‑ratio  
`GET /api/ui/latency` — p95/p99 + stage‑latency  
`GET /api/ui/liquidations` — поток и аггрегаты  
`GET /api/ui/imbalance` — OFI/LOB imbalance  
`GET /api/ui/cvd` — CVD по символам/ТФ  
`GET /api/ui/correlation` — матрица/кластеры  
`GET /api/ui/alpha` — важности/дрейф фич  
`GET /api/ui/model` — версии/параметры моделей  
`GET /api/ui/slo` — SLO/SLA центра  
`GET /api/md/meta` — метаданные/версии правил  
`GET /api/ui/advice` — советы (TTL/confidence)  
`GET /api/ui/advice/why` — объяснение  
`GET /api/ui/advice/perf` — эффективность/разбиения  
`GET /api/ui/pnl/attribution` — атрибуция PnL  
`GET /api/ui/recon/orders` / `…/positions` — сверка  
`GET /api/ui/treasury` — капитал/ребаланс  
`GET /api/ui/ops/runbooks` — плейбуки  
`POST /api/risk/kill‑switch` — аварийная остановка (two‑man)

**Версионирование:** `X‑API‑Version`, SemVer, заголовок Deprecation + страница совместимости.

---

## 19) WebSocket‑топики (`/api/ui/stream`)
`"quotes"`, `"trades"`, `"funding"`, `"oi"`, `"liquidations"`, `"imbalance"`, `"cvd"`, `"advice"`, `"quality"`, `"alerts"`.

---

## 20) Конфигурационные флаги (минимальный набор)
```yaml
center:
  advisory:
    enabled: false
  degrade:
    on_overload: true
  news:
    enabled: false
  liquidations:
    enabled: true
  cvd:
    enabled: true
  imbalance:
    enabled: true

quality:
  max_clock_skew_ms: 2000
  max_seq_gap: 0
  freshness:
    max_staleness_ms: 2000

advice:
  calibration:
    enabled: true
  max_recs_per_min: 120
  default_ttl_s: 900
  break_on_drift: true

model:
  shadow:
    id: null
  canary:
    traffic_pct: 0

risk:
  max_notional: 0
  max_order_size: 0
  price_band_bps: 100
  daily_loss_cap: 0
  cool_off_minutes: 60
  stp: true
  cancel_on_disconnect: true

exec:
  idempotency:
    enabled: true
  post_only:
    staleness_ms: 500
  maker_taker_switch: true

treasury:
  rebalance:
    enabled: true
funding:
  optimizer:
    enabled: true

security:
  ws_signature:
    required: true
  keys:
    rotation_days: 30
  ip_allowlist: []

backup:
  retention_days: 30
```
Для бота‑клиента: `crypto_bot.advisory.consume=true|false`.

---

## 21) Новости
- Тумблер в UI; `GET /api/ui/news?limit=…` возвращает `{enabled:false}`, если выключено.
- Источники/анализ новостей — **опционально**, с возможностью отключения.

---

## 22) Стоимость и метрики
- Политика кардинальности метрик, лимиты на label‑space.
- S3/Parquet lifecycle, метрика `metrics_cardinality_*`.

---

— Финальное **DoD**: SLO‑гейт зелёный 24ч; Recon==0; PnL‑дрейф ≤0.1%; Security/Chaos/CI e2e — зелёные; Soak: testnet 3–7д → micro‑live 7–14д.

---

## 19) Приложения
- Глоссарии JSON‑схем (Advice/Why/Signal/Regime/MarketMetrics).  
- Полные исходники исходных спецификаций доступны в истории.



---

## 20) Память и обучение (Experience & Auto‑Calibration, RU)
**Цель:** бот целенаправленно работает на прибыль и **учится на опыте**, но в безопасных рамках (капы, SLO‑гейт, откаты, Two‑Man).

### 20.1 Что запоминаем
- **Сделки и контекст**: цена, слиппедж, спред, глубина, задержки, маршрут SOR, «почему вошли/вышли» (Why/Advice).
- **Ошибки/инциденты**: 429/418, stale/gap, crossed‑book, таймауты, рассинхроны сверки.
- **Режимы рынка**: тренд/флэт/волатильность и результативность в каждом режиме.
- **Здоровье площадок**: надежность WS/REST, фактический слиппедж, funding/basis, де‑пеги.
- **Твои действия**: включения/выключения функций, изменения риска/лимитов с результатом.

### 20.2 Как «учимся» (безопасные контуры)
- **Автокалибровка исполнения (онлайн)**: SOR‑веса, ожидания слиппеджа, тайминги лимиток — малыми шагами, с границами и авто‑откатом.
- **Регуляторы риска (онлайн)**: лёгкая корректировка размера/тейкерности в рамках **шкалы риска** и твоих капов.
- **Инцидент → Правило**: повторяющиеся сбои автоматически предлагаются как guard‑правила (включаются после твоего ОК/Two‑Man).
- **Оффлайн‑обучение стратегий**: дневные/недельные бэч‑апдейты через **shadow (champion/challenger)** → отчёт → ручной апгрейд.

### 20.3 Режимы обучения
- **Strict (дефолт):** память ведётся, **без** автоприменения параметров.
- **Advisory:** в UI подсказки «что улучшить» (например, снизить тейкерность на конкретной бирже).
- **Auto‑calibration P0:** разрешены только безопасные автоподстройки (SOR/тайминги/микро‑лимиты).

### 20.4 Хранилища и трассировка
- **Experience Store** (Parquet/DB) · **Anomaly Registry** · **Venue Health** · **Model Registry** (версии/метрики/откаты).

### 20.5 UI/События
- SSE: `learn.advice`, `learn.applied`, `model.promoted`, `model.rolled_back`.
- В каждом изменении — **человеческое резюме** и кнопка **Откатить**.

### 20.6 Acceptance (минимум)
- Онлайн‑калибровки не выходят за капы; любые изменения логируются и откатываются одной кнопкой.
- Shadow‑версии сравниваются по PnL/слиппеджу, апгрейд только после «зелёного» отчёта.
- При инцидентах формируются guard‑правила, включаются только после подтверждения.

---

## 21) Целевая функция прибыли (Profit‑First Objectives)
**Главная цель:** **зарабатывать деньги** при контроле риска.
- **Оптимизируем**: risk‑adjusted PnL (например, дневной Sharpe/Sortino, net PnL после комиссий и фандинга).
- **Ограничения**: дневной кап убытка, макс. просадка (intraday), SLO/качество данных (без них агрессия ограничивается).
- **Онлайн‑монитор**: KPI‑панель «Цель/Факт/Отклонение», алерты при уходе от траектории (например, перевышение слиппеджа).
- **What‑If**: песочница показывает, как изменение риска/лимитов повлияет на цель при текущих условиях.

---

## 22) Управление вселенной рынков (Universe) — расширено
- **Manual Allowlist** (дефолт) · **Rule‑Based Discovery** · **Draft → Review → Approve** (Two‑Man в live — опционально).
- **Канонические ID**: `VENUE:TYPE:BASE-QUOTE[:KIND]` (исключает коллизии по тикерам между биржами/типами).
- **Анти‑двойник**: «есть однофамильцы» → требуется явное подтверждение; исключаем префиксы (`1000`, `3L/3S`) по умолчанию.
- **Acceptance**: без allowlist пара **не торгуется**; одинаковый тикер на разных биржах → разные UID и независимые лимиты.

---

## 23) Анти‑ловушки (Guardrails) — расширено
**Качество данных:** stale/gap‑детект, кросс‑проверка mid/mark/last и/или 2 провайдеров, wick/outlier‑фильтр.  
**Микроструктура:** anti‑spoof/microburst, locked/crossed‑guard, trade‑through, price‑protection.  
**Биржи:** maintenance/quarantine, delist/migrate watcher, cancel‑on‑disconnect, rate‑limit health.  
**Перпы/стейблы:** funding‑кламп, basis‑аномалии перп‑спот, depeg‑детект (USDT/USDC).  
**Риск/частота:** throttles, drawdown‑гейты, портфельные корреляционные капы.

**Таблица реакций (примеры):**
| Условие | Порог | Действие |
|---|---:|---|
| `book_freshness_ms` | > 300 мс | Пауза символа, ресинх |
| `ws_gap_ms` | p95 > 200 мс | Safe‑mode, снижение агрессии |
| Crossed/locked | любой | Запрет тейкера, ждать норму |
| Anchor diverge (mid/mark/last) | > 10 bps | HOLD/только maker |
| Funding forecast | > 50 bps/8ч | Снизить размер/запретить сторону |
| Basis perp‑spot | > 100 bps | HOLD/уменьшить агрессию |
| 429/418 серия | > N/мин | Backoff, SOR на другие биржи |
| Limits breached | ≥ M за T | Понизить уровень риска |
| Intraday DD | > 2% | Step‑down риска, затем пауза |

**Конфиг (пример):**
```json
{
  "guards": {
    "stale_book_ms_max": 300,
    "anchor_divergence_bps": 10,
    "locked_crossed_action": "DISABLE_TAKER",
    "max_slippage_bps": 20,
    "throttle_orders_per_sec": 5
  },
  "perp": {
    "funding_bps_cap_8h": 50,
    "basis_bps_cap": 100
  },
  "universe": {
    "autodiscovery": false,
    "require_approval": true,
    "exclude_prefix": ["1000","3L","3S"]
  }
}
```

**Acceptance:** триггеры правильно срабатывают; ордера вне коридоров блокируются с понятной причиной; события в SSE.

---

## 24) UI/UX на русском — расширение
- **Info‑точки “i”** и hover‑подсказки у всех ключевых элементов (что это + на что влияет), ≤100 мс.  
- **«+ Добавить биржу/пару»**: проверка совместимости (tick/step/minNotional), предупреждение про однофамильцев.  
- **What‑If Risk Sandbox**: примерить изменения без применения; кнопки **Проверить → Применить → Откатить**.  
- **Incident Timeline** и **Trade Replay**: разбор полётов в один клик.

---

## 25) API/События — расширение
- `GET/PUT /api/ui/universe` (поиск/черновик/одобрить/удалить),  
  `GET/PUT /api/ui/limits`, `GET/PUT /api/ui/settings/risk-profile`, `POST /api/ui/approvals`.  
- SSE: `universe.changed`, `limits.breached`, `learn.advice`, `learn.applied`, `model.promoted`, `model.rolled_back`, `readiness.changed`, `alerts.*`.

---

## 26) Acceptance — расширение (перечень 1–47 в группах)
**(A) Universe/анти‑двойники:** белый список обязателен; UID уникальны; авто‑добавление ВЫКЛ; требуются подтверждения.  
**(B) Guardrails:** все таблицы триггеров покрыты тестами; safe‑mode и hold срабатывают корректно.  
**(C) Риск/Плечо:** слайдер меняет параметры в заявленных границах; потолок плеча соблюдается; Two‑Man на повышение.  
**(D) Лимиты/Коридоры:** min/max/side‑caps/price‑bands/конкуренция соблюдены; валидация против биржи, auto‑rollback.  
**(E) Финансы:** балансы/PnL/ledger сверяются; экспорт работает; дневной дрейф PnL ≤ 0.1%.  
**(F) Безопасность средств:** withdraw невозможен (на биржах и в боте); логи в WORM‑аудите; e2e‑кейс проходит.  
**(G) Память/Обучение:** автокалибровки в капах, с отчётами и откатом; shadow‑тесты champion/challenger.  
**(H) Целевая прибыль:** KPI‑панель сходится с метриками; алерты по отклонениям; what‑if коррелирует с фактом.



---

## Телеграм‑управление — обязательные команды и безопасность {#telegram-control}
**Назначение:** безопасный старт/стоп и базовые операции без входа на сервер.  
**Архитектура:** внешний сервис `tele-bridge` (webhook) → RBAC/Two‑Man → внутренние UI‑API (`/api/control`, `/api/ui/status`, `/api/ui/settings/*`).

### Команды (обязательно реализовать ровно так)
| Команда | Описание (RU) |
|---|---|
| `/status` | Показать состояние: run/pause/safe_mode, readiness(SLO), дневной PnL, активные биржи/пары. |
| `/start` | Запустить торговлю (только если `/live-readiness` зелёный). |
| `/pause` | Пауза торговли (позиции удерживаются по политике). |
| `/kill` | Аварийный стоп: `cancel_all` + безопасное свёртывание. |
| `/safe_on` | Включить безопасный режим. |
| `/safe_off` | Выключить безопасный режим (**только с Two‑Man в live**). |
| `/risk <0..100>` | Установить уровень риска; не превышать `env_caps`. |
| `/leverage off|on <max>` | Вкл/выкл плечо и задать потолок (напр. `3`). |
| `/limits` | Показать лимиты: max_notional, price_bands, concurrency caps. |
| `/addpair VENUE:TYPE:BASE-QUOTE[:KIND]` | Предложить пару в черновик universe (включение — через ревью/Two‑Man). |
| `/alerts on|off` | Вкл/выкл уведомления об инцидентах в Telegram. |

**Безопасность:** allowlist `chat_id`; при необходимости 2‑фактор (одноразовый код); все опасные действия — через Two‑Man в `live`; команды и результаты — в WORM‑аудит.  
**События:** `health.changed`, `component.failed/recovered`, `safe_mode activated`, `limits.breached`, `model.promoted/rolled_back`, дневной PnL‑дайджест.


---

## Панель здоровья (Health) — API‑контур и формат {#health-api}
**Цель:** видеть зелёный/жёлтый/красный статус по компонентам и общий % работоспособности.
### Эндпоинты (реализовать буквально)
- `GET /api/ui/health/summary` → `{ "score_pct": 95.0, "overall": "YELLOW", "counts": {"GREEN": 42, "YELLOW": 3, "RED": 1, "GRAY": 4}, "ts": "..." }`
- `GET /api/ui/health/components?scope=all|venue|symbol&type=service|connector|function|storage|security` → список с полями:  
  `component_id`, `status ∈ {GREEN,YELLOW,RED,GRAY}`, `weight`, `reason_code`, `reason_text_ru`, `hint_ru`, `last_error_at`.
- `GET /api/ui/health/history?from&to&bucket=5m` → временной ряд `score_pct` и статусов.
- **SSE:** `/api/ui/stream` → события `health.changed`, `component.failed`, `component.recovered`.

**Подсчёт процента:**  
`score_pct = 100 * (Σ weight_GREEN + 0.5 * Σ weight_YELLOW) / Σ weight_ENABLED`.  
**Связь с безопасностью:** при `overall=RED` или SLO‑провале — авто `safe_mode` и снижение агрессии.

**Пример элемента:**
```json
{"component_id":"exec-svc","status":"RED","reason_code":"EXCHANGE_REJECTS","reason_text_ru":"Биржа отклоняет заявки (429/5xx)","hint_ru":"Включён backoff и SOR перенаправляет трафик на другие площадки","last_error_at":"2025-10-14T10:22:03Z"}
```


---

## Примечание по нумерации разделов {#numbering}
В тексте встречается повторная нумерация заголовков. Для избежания двусмысленностей исполнение следует вести **по названиям разделов** и якорям (`#telegram-control`, `#health-api`, и т. п.), а не по номерам. В коде и документации использовать эти якоря.


---

## PR‑гейт и Auto‑merge (только «зелёные» PR) {#pr-gate-automerge}
**Цель:** в ветку `main` попадает только проверенный (зелёный) код; при желании PR сливается автоматически.

### Требования к репозиторию
- **Branch protection** для `main`:
  - ✓ Require a pull request before merging
  - ✓ Require status checks to pass before merging — добавить обязательные проверки CI (self‑check/e2e)
  - (опц.) ✓ Require approvals (минимум 1 ревью)
  - ✓ Do not allow bypassing the above settings
- **Allow auto‑merge** — включено в настройках репозитория
- Метки: `automerge`, `green`, `needs-fix`

### CI‑процесс
- Workflow `.github/workflows/pr-selfcheck.yml` прогоняет: `make install → lint → mypy → test → acceptance (e2e)`.
- При успехе: добавляет метку `green`, снимает `needs-fix`. Если на PR есть метка `automerge` и все чеки зелёные — включает **auto‑merge (squash)**.
- При сбое: вешает `needs-fix`, снимает `green`. Мерж **запрещён** правилами защиты ветки.
- Дополнительно: `.github/workflows/selfcheck.yml` можно запускать на `push` в `main` для периодических прогона/отчётов.
- Скрипт `scripts/selfcheck.sh` — единая локальная проверка (используется и в CI).

### Поведение «до кнопки Merge»
- Пока хотя бы один статус **красный** — PR **не может** быть смёржен (гейт).
- Когда все статусы **зелёные**:
  - если у PR стоит метка `automerge` — он сливается **автоматически**;
  - если метки нет — ты нажимаешь **Merge** вручную.

### Acceptance для этого раздела
1) Правила защиты ветки настроены; невозможен merge «красного» PR.
2) При успешном прогоне CI ставит `green`; при провале — `needs-fix`.
3) Метка `automerge` приводит к авто‑слиянию после «позеленения».
4) Логи и артефакты прогонов доступны в GitHub Actions.


---

# ✳️ Дополнительные критические улучшения для выхода в лайв (P0→P2)

Ниже — интегрированный список улучшений, который дополняет твою спецификацию. Структура: **Что / Зачем / Критерии готовности / Артефакты**. Это сформулировано так, чтобы его мог напрямую исполнять Codex/разработчик в виде эпиков и задач.

## P0 — Обязательные перед лайвом (без этого — нельзя)

### 1) Живой SOR + дедлайны (idempotent place/cancel)
**Что:** clientOrderId+fencing, per-venue quotas, hard-timeouts на place/cancel, cancel-on-disconnect, fail-fast при staleness.  
**Зачем:** снижает риск «залипаний», двойных исполнений и избыточного проскальзывания.  
**Критерии:** `place_latency_p95`, `cancel_latency_p95`, `%timeouts<0.5%`; автопереход в `safe_mode` при превышении порогов.  
**Артефакты:** модуль `execution/live.py`, `execution/sor.py`, метрики Prometheus:
```
exec_place_latency_ms{venue=,type=} p50|p95|p99
exec_cancel_latency_ms{venue=} p50|p95|p99
exec_timeouts_total{venue=,op=}
exec_route_reason_total{venue=,reason=}
```

### 2) /live-readiness + health-панель с причинами
**Что:** агрегатор статусов (WS staleness, seq-gap, rate-limit, cancel-latency, balances/funding), SSE-события.  
**Зачем:** не даёт стратегии стартовать на «полумёртвом» контуре.  
**Критерии:** 24h soak без false-green; алерты приходят <5с.  
**Артефакты:** эндпоинт:
```http
GET /live-readiness
200 OK
{
  "ready": false,
  "reasons": [{"code":"WS_STALE","detail":"BTCUSDT 3500ms"}],
  "advice_ru": "Перезапустите WS для OKX; включён safe_mode"
}
```

### 3) Online‑TCA (реальные издержки)
**Что:** arrival/decision/fill, `slippage_bps`, attribution по сигналу/исполнению; алерты на регресс.  
**Зачем:** мгновенно показывает, где утекает edge.  
**Критерии:** дашборд «Издержки», auto-throttle при деградации.  
**Артефакты:** `tca/online.py`, отчёт Parquet/CSV.

### 4) PnL‑атрибуция + recon‑демон
**Что:** разложение PnL: signal/fees/slippage/funding/borrow/rebates/errors; ежедневная сверка.  
**Зачем:** понимаем вклад каждого слоя и сравниваем с отчётами биржи.  
**Критерии:** расхождение ≤0.1% к отчётам; ежедневный отчёт.  
**Артефакты:** `pnl/attrib.py`, `recon/daemon.py`, `/api/ui/recon/*`.

### 5) LOB‑реплей + микросим
**Что:** офлайн‑прогон через тот же decision→exec пайплайн; оценка p_fill/impact/очереди.  
**Зачем:** безрисковая калибровка стратегий и стопов.  
**Критерии:** acceptance‑тест каждого релиза на реплее.  
**Артефакты:** `sim/lob.py`, `replay/runner.py`.

### 6) UI‑стрим (/api/ui/stream) + SLO‑алерты
**Что:** SSE/WS события `data.stale`, `opps/sec=0`, `cancel_p95>thr`, `recon.failed`, `ws.reconnect`.  
**Зачем:** «живые» деградации видно сразу.  
**Критерии:** алерты в UI/Telegram, понятные RU‑советы.  
**Артефакты:** сервер SSE/WS, Telegram‑нотификатор.

### 7) VIP/ребейт‑планировщик
**Что:** fee‑tiers/ребейты per‑venue, маршрутизация по **чистой** доходности.  
**Зачем:** на деривативах комиссии решают исход.  
**Критерии:** отчёт «до/после ребейтов», рост net‑alpha.  
**Артефакты:** `fees/vip_planner.py`.

### 8) Профили {paper,testnet,live} + конвейер допусков
**Что:** жёсткие DoD‑гейты, запрет skip, чек‑листы.  
**Зачем:** безопасная эскалация риска.  
**Критерии:** журнал прохождения; артефакты тестов в релизе.  
**Артефакты:** `configs/config.paper.yaml`, `configs/config.testnet.yaml`, `configs/config.live.yaml`.

### 9) Регим‑классификатор рынка
**Что:** эвристики/ML (range/trend/liquidity/vola/funding); авто‑вкл/выкл алф; no‑trade зоны.  
**Критерии:** отчёт performance по режимам; throttle при неблагоприятном.  
**Артефакты:** `risk/regime.py`.

### 10) Chaos/latency‑тесты + watchdog
**Что:** инъекция задержек/дропов WS/REST, 429‑бури, seq‑gap; авто‑деградация.  
**Критерии:** сценарии «биржа тормозит/падает/фрагментируется» — зелёные.  
**Артефакты:** `tests/chaos/*.py`, `ops/watchdog.py`.

---

## P0+ — Анти‑ловушки микроструктуры

11) **Data‑gates & sanity‑checks** — staleness, crossed/locked, mark/index‑дивергенции, funding‑roll окна, outliers.  
12) **Execution‑Quality Score (EQS)** — скоринг входа (спред/глубина/impact/очередь/волн.).  
13) **Kelly‑throttle/дневные капы** — дробный Келли, дневной loss‑cap, cool‑off после серий отмен/проска.  
14) **Fail‑safe старта** — при рестарте: cancel_all → загрузка позиций/ордеров → reconcile → trade‑enable.  
15) **Tick/step/minNotional валидатор** — reduce‑only/close‑on‑trigger где нужно.

---

## P1 — Надёжность/эксплуатация

16) **Leader‑lock/fencing** на уровне процессов/узлов.  
17) **Time‑sync (NTP) + монотоника** для дедлайнов.  
18) **Rate‑limit & backoff‑jitter** — централизованный лимитер.  
19) **Kill‑switch** — ручной/авто стоп стратегий и закрытие позиций.  
20) **Долговременные логи/трассинг** — ретро‑анализ 90 дней.  
21) **Runbooks** — плейбуки «что делать, если…».  
22) **DR/Backups (RPO/RTO)** — снапшоты состояния, восстановление ≤10 мин.

---

## P1 — Исполнение/производительность

23) **Очередь in‑flight ордеров** — журнал, дедупликация, ретраи по idempotency.  
24) **Latency‑профилировка** — p50/p95/p99 place/cancel/query, GC, RTT.  
25) **Оптимизация критического пути** — async I/O, batching, без горячих аллокаций.

---

## P1 — Управление стратегиями/алфами

26) **Feature‑store + versioning** — воспроизводимость бэктест/лайв.  
27) **A/B‑тесты и канарейки** — shadow/canary deploy.  
28) **Drift‑детектор** — мониторинг распределений и доходности.  
29) **Событийные окна** — листинги, ADL‑риски, спец‑режим.

---

## P1 — Риск/капитал

30) **Многоуровневые лимиты** — per‑instrument/venue/day caps, max concurrent orders, exposure caps.  
31) **Netting/hedge‑политики** — единообразный неттинг, `hedge` action с дедлайнами.  
32) **Расширенная модель комиссий** — maker/taker, rebates, borrow, funding spikes.

---

## P1 — Безопасность/доступ

33) **Secrets‑management + ротация ключей**, принцип наименьших привилегий.  
34) **RBAC/Two‑Man Rule** на опасные действия (pause/kill/withdraw/config‑apply).

---

## P2 — Качество кода/релизы/CI

35) **Strict typing & static analysis** — Python 3.12, mypy strict, ruff/black.  
36) **Acceptance‑наборы по стратегиям** — от сигнала до отчёта на реплее.  
37) **Версии конфигов и rollback** — `/api/ui/config/{validate,apply,rollback}`.

---

## P2 — Прозрачность/отчётность

38) **Месячный аудит‑отчёт** — Sharpe/MAR, hit‑rate net‑fees, maxDD, cancel‑latency, fill‑ratio, capacity, издержки.  
39) **Телеметрия «качество возможности»** — `opps_per_sec`, спред/глубина, токсичность потока.

---

# 📦 Endpoints/файлы/метрики (чтобы Codex мог сразу впиливать)

## Новые эндпоинты
- `GET /live-readiness`
- `GET /api/ui/stream` (SSE)
- `POST /api/ui/config/validate|apply|rollback`
- `GET /api/ui/recon/status|diffs`
- `GET /api/ui/costs/tca/summary`

## Файлы/модули
```
app/execution/sor.py
app/execution/live.py
app/tca/online.py
app/pnl/attrib.py
app/recon/daemon.py
app/sim/lob.py
app/replay/runner.py
app/fees/vip_planner.py
app/risk/regime.py
app/tests/chaos/*.py
```

## Профили
```
configs/config.paper.yaml
configs/config.testnet.yaml
configs/config.live.yaml
```

## Метрики (пример)
```
opps_per_sec
data_staleness_ms{symbol=}
ws_reconnects_total{venue=}
slippage_bps_bucket{strategy=}
pnl_attrib_usd{component=}
recon_mismatch_total
```

---

# ✅ Acceptance/DoD кратко
- Все P0 зеленые на 24h soak (paper→testnet), затем микролот live.  
- Отчёт Online‑TCA и PnL‑атрибуции приложен к релизу.  
- Chaos‑сценарии проходят.  
- `/live-readiness` не даёт false-green.  
- Разрешён автоматический rollback конфигов.



