# ADC 3.0.5 — архитектурен обзор и MVP roadmap

## Текуща архитектура

### Общ изглед

Репото е разделено на две реалности:

1. **Исторически/изследователски слой** — `README.md` и `ADC_3_0_5.ipynb` пазят Colab/ноутбук наследството: yfinance зареждане, индикатори, LSTM, RL, mock broker, email/notification идеи и MQL4-подобна order логика.
2. **SaaS monorepo слой** — `saas/` е по-чистата посока за продуктова разработка. В него има backend FastAPI приложение, frontend React/Vite приложение, начална инфраструктура, docs и празни/placeholder shared packages.

Практическият MVP трябва да се гради върху `saas/`, а notebook-ът да остане архив/референтен материал, от който вече са извадени части в стабилни Python модули.

### Backend

Backend-ът е във `saas/apps/api` и е FastAPI приложение с ясна начална слоеста структура:

- `app/main.py` — основен FastAPI entry point; създава app-а, регистрира CORS, създава таблици през SQLAlchemy и включва API router под `/api/v1`.
- `app/api/v1/api.py` — централен router composer за endpoint families: auth, dashboard, indicators, signals, trades, trade journal, orders, RL, LSTM, sessions, settings, market data, market stream, notifications, strategy и simulations.
- `app/api/v1/endpoints/` — HTTP слой, смесващ стабилни CRUD endpoint-и, demo/readiness endpoint-и и wrapper-и върху експериментални services.
- `app/schemas/` — Pydantic request/response contracts за повечето endpoint-и.
- `app/models/__init__.py` — SQLAlchemy модели за потребители, настройки, сигнали, сделки и equity snapshots.
- `app/db/session.py` — SQLAlchemy engine/session/base конфигурация.
- `app/security.py` — password hashing, JWT token creation и current user dependency.
- `app/services/` — основната бизнес/експериментална логика: data loading, simulations, strategy settings, trade journal, order management/mock broker, trading sessions, market stream, RL trainer и notifications.
- `core/` — технически индикатори и LSTM модел; това е реално домейн/core логика, но е извън `app/`, което създава втори “core” слой до `app/core/config.py`.
- `tests/` — сравнително богати unit/contract/API тестове, включително статичен route contract test.

Има работеща локална опаковка:

- `saas/docker-compose.yml` дефинира Postgres, Redis, backend, Celery worker и web.
- `saas/.env.example` съдържа базови env променливи, но frontend ключът е `NEXT_PUBLIC_API_BASE_URL`, докато Vite app-ът използва `VITE_API_URL`.
- `saas/apps/api/Dockerfile` и `saas/apps/web/Dockerfile` съществуват.

### Frontend

Frontend-ът е във `saas/apps/web` и е Vite + React + TypeScript приложение:

- `src/main.tsx` — React bootstrap.
- `src/app/App.tsx` — routing и protected layout flow.
- `src/api/client.ts` — Axios client с `VITE_API_URL`, default `http://localhost:8000/api/v1`, и bearer token interceptor.
- `src/api/*.ts` — frontend API clients за auth, dashboard, signals, trades, orders, sessions, settings, indicators, market data, market stream, trade journal, simulations, RL, LSTM и notifications.
- `src/pages/` — UI страници за login/register, dashboard, signals, trades, sessions, trade journal, simulations, AI controls, market data, notifications и settings.
- `src/components/` — shared UI shell, protected route, feature guard, stat cards, loading/page states и live market widget.
- `src/store/authStore.ts` — Zustand auth state.

Frontend-ът вече има желания SaaS flow skeleton: login/register → protected app shell → dashboard/signals/history/metrics/settings. Част от страниците обаче са по-широки от MVP и обслужват експериментални features.

### Data, scripts и инфраструктура

- `saas/apps/api/app/services/data_loader.py` централизира yfinance daily data и Alpha Vantage intraday data.
- `saas/apps/api/app/services/order_management.py` съдържа MQL4-подобни order constants, error mapping и `MockBrokerAPI`.
- `saas/apps/api/app/services/market_stream.py` съдържа mock websocket/SSE tick stream.
- `saas/apps/api/app/services/trade_journal.py` работи с CSV/JSON/PNG artifacts, което е полезно за миграция от notebook към SaaS, но не е идеално като дългосрочно primary persistence.
- `saas/scripts/` е само placeholder README; няма реални maintenance scripts.
- `saas/infra/` има README placeholders за Docker, Nginx и Terraform.
- `saas/packages/` има placeholder packages за contracts/config/ui, но не изглежда реално използвано от web или api.

## Основни модули

### Entry points

- Backend runtime: `saas/apps/api/app/main.py` чрез `uvicorn app.main:app --reload`.
- Backend router: `saas/apps/api/app/api/v1/api.py`.
- Frontend runtime: `saas/apps/web/src/main.tsx`, с routing във `saas/apps/web/src/app/App.tsx`.
- Local stack: `saas/docker-compose.yml`.
- Research archive: `ADC_3_0_5.ipynb` и root `README.md`.

### Ядро на продуктовата логика

- **Auth и SaaS основа:** `app/api/v1/endpoints/auth.py`, `app/security.py`, `app/models/User`, `UserSettings`.
- **Signals:** `app/models/Signal`, `app/schemas/signals.py`, `app/api/v1/endpoints/signals.py`. Това е persistence/API слой за сигнали, но липсва отделен signal generation engine service.
- **Trades/metrics:** `app/models/Trade`, `EquitySnapshot`, `app/api/v1/endpoints/trades.py`, `app/api/v1/endpoints/dashboard.py`.
- **Data provider:** `app/services/data_loader.py`.
- **Indicators:** `core/indicators.py` и `/indicators/calculate` endpoint.
- **Simulation pipeline:** `app/services/simulation_runner.py`, `app/services/strategy_settings.py`, `app/services/pivot_env.py`, `app/services/rl_trainer.py`, `core/lstm_model.py`.
- **Mock broker/order layer:** `app/services/order_management.py`, `app/api/v1/endpoints/orders.py`.
- **Live/demo market stream:** `app/services/market_stream.py`, `app/api/v1/endpoints/market_stream.py`.
- **Trade journal artifacts:** `app/services/trade_journal.py`, `app/api/v1/endpoints/trade_journal.py`.
- **Notifications:** `app/services/notifications.py`, `app/api/v1/endpoints/notifications.py`.

### Demo/prototype части

- `ADC_3_0_5.ipynb` и code-in-README съдържат изследователски notebook стил и не трябва да са production entry point.
- `GET /signals`, `GET /trades`, `GET /settings`, `GET /dashboard/summary` са readiness/demo payload-и, не продуктови read models.
- RL/LSTM training endpoint-и са ценни за research, но са тежки за MVP SaaS и трябва да останат зад feature flag или да бъдат извадени от основния user flow.
- `trade_journal` CSV/JSON/PNG artifact layer е полезен за import/export и симулации, но не трябва да бъде единственият източник на истина за SaaS историята.
- `saas/packages/*`, `saas/infra/*` и `saas/scripts/` са предимно placeholders.
- Mock broker, mock websocket и in-memory job/session stores са прототипна инфраструктура, която трябва да се изолира зад интерфейси.

## Силни страни

- Има вече оформен `saas/` monorepo, което позволява да се продължи итеративно без тотално пренаписване.
- Backend-ът има версия на API (`/api/v1`), отделени endpoints, Pydantic schemas и SQLAlchemy модели.
- Frontend-ът вече има protected routing, auth store, API clients и страници за основните SaaS сценарии.
- Има тестова база за backend и frontend clients/pages; route contract test-ът е особено полезен за предотвратяване на frontend/backend drift.
- Data loader, indicators, simulation runner, RL trainer, LSTM generator и mock broker вече са извадени от notebook логика в преизползваеми модули.
- Docker Compose вече описва локален stack с Postgres, Redis, API, Celery и web.

## Слаби страни

- Има два “core” смисъла: `app/core/config.py` за инфраструктурна конфигурация и top-level `core/` за indicators/LSTM domain logic.
- `services/` е твърде широк слой: съдържа data access, domain logic, broker simulation, ML training, notifications, artifacts и session orchestration без ясни bounded contexts.
- Липсва явен `signal_engine` service, въпреки че сигналите са централният продукт. В момента signal API може да записва сигнали, но generation/scoring/explanation логиката е разпръсната между indicators, simulations и AI/RL/LSTM части.
- Някои endpoint-и са readiness/demo, други са production-like, което прави API contract-а нееднороден.
- Част от frontend API clients очакват маршрути, които трябва да се валидират внимателно срещу backend contract-а при всяка промяна.
- ML dependencies (`tensorflow`, `stable-baselines3`) са тежки за минимален SaaS runtime и увеличават friction-а за локално стартиране/деплой.
- Auto `Base.metadata.create_all()` в app startup е удобно локално, но не е добра production migration стратегия.
- Няма ясен provider interface за broker/data/AI; mock имплементациите са реални класове, но не са капсулирани като сменяеми adapters.
- `.env.example` използва `NEXT_PUBLIC_API_BASE_URL`, а Vite frontend-ът използва `VITE_API_URL`.

## Рискове

- **Tight coupling:** endpoint-и извикват директно services и DB модели; при растеж ще стане трудно да се сменят persistence/provider/AI имплементации.
- **ML тежест в основния backend:** ако TensorFlow/RL останат задължителни dependencies, cloud deploy ще е по-скъп, по-бавен и по-чуплив.
- **Неясен product core:** без отделен signal engine MVP-то може да изглежда като набор от експерименти, а не като SaaS за trading signals.
- **State fragmentation:** част от състоянието е SQL, част е in-memory job store, част е файлови artifacts. Това е приемливо за демо, но рисковано за реални потребители.
- **Frontend/backend drift:** много API clients и страници означават висок шанс някой UI flow да сочи към endpoint, който е демо, незавършен или с различен contract.
- **Deployment risk:** placeholders в infra/packages създават впечатление за готовност, но реално липсват минимални deployment runbooks и env alignment.

# Целева архитектура (MVP)

## Backend

Целта е да се запази текущият FastAPI backend, но да се подреди около няколко стабилни bounded contexts. Не е нужно масивно пренаписване; първо се добавят/преместват тънки фасади, после постепенно се мести логика.

### Предложена структура

```text
saas/apps/api/app/
  main.py
  api/
    deps.py
    v1/
      api.py
      endpoints/
        auth.py
        dashboard.py
        signals.py
        trades.py
        settings.py
        market_data.py
        broker.py или orders.py
        simulations.py        # feature-flag/research
        ai.py                 # explanations/scoring, not training
  core/
    config.py
    security.py               # по-късно може да премести app/security.py тук
    logging.py
  db/
    session.py
    repositories/
  models/
    users.py
    settings.py
    signals.py
    trades.py
    metrics.py
  schemas/
  services/
    signal_engine.py
    metrics.py
    trade_service.py
    data/
      providers.py
      yahoo_provider.py
      alpha_vantage_provider.py
      mock_provider.py
    broker/
      base.py
      mock_broker.py
    ai/
      explanations.py
      scoring.py
    research/
      simulation_runner.py
      rl_trainer.py
      lstm_model.py
      pivot_env.py
    notifications.py
```

### Какво да остане

- `app/main.py`, `app/api/v1/api.py`, `app/api/v1/endpoints/auth.py`, `settings.py`, `dashboard.py`, `signals.py`, `trades.py`, `market_data.py`.
- `app/models/User`, `UserSettings`, `Signal`, `Trade`, `EquitySnapshot` като начални SQL модели.
- `app/schemas/*` като API contracts.
- `app/services/data_loader.py`, `order_management.py`, `simulation_runner.py`, `strategy_settings.py`, `trade_journal.py`, `notifications.py`, `market_stream.py` — но част от тях трябва да се преместят/групират постепенно.
- `core/indicators.py` и `core/lstm_model.py`, но е по-добре да се преместят под `app/services/research/` или `app/domain/` в по-късен етап.

### Какво да се премести постепенно

- `saas/apps/api/core/indicators.py` → `saas/apps/api/app/services/indicators.py` или `app/domain/indicators.py`.
- `saas/apps/api/core/lstm_model.py` → `saas/apps/api/app/services/research/lstm_model.py`.
- `app/services/order_management.py` → `app/services/broker/mock_broker.py` плюс `app/services/broker/base.py`.
- `app/services/data_loader.py` → `app/services/data/providers.py` + provider implementations.
- `app/services/simulation_runner.py`, `pivot_env.py`, `rl_trainer.py`, `strategy_settings.py` → `app/services/research/`, защото са ценни, но не са minimal SaaS runtime.
- `app/security.py` → `app/core/security.py` само ако това не счупи много imports; иначе остави alias/wrapper.

### Какво да се слее или изолира

- `trades.py` и `orders.py` трябва ясно да се разграничат:
  - `trades` = потребителска история/позиции/PnL в SaaS.
  - `orders` или `broker` = изпълнение през mock/real broker adapter.
- `dashboard.py` трябва да използва `services/metrics.py`, вместо да изчислява метрики директно в endpoint-а.
- `signals.py` трябва да използва `services/signal_engine.py`, вместо само да създава записи по подаден payload.
- `market_stream.py` да остане demo/live widget feature, но да не блокира MVP.
- `notifications.py` да остане optional; не трябва да е задължително за локален MVP.

### Слоеве

- **Signal engine:** нов `app/services/signal_engine.py` с функции/класове:
  - `generate_signal(symbol, timeframe, strategy_settings) -> SignalDecision`
  - `generate_signals_for_user(user_id) -> list[SignalDecision]`
  - използва `DataProvider`, `TechnicalIndicators`, прост ruleset и записва през repository/service.
- **Data layer:** `DataProvider` protocol/interface с метод `get_ohlcv(symbol, timeframe, start, end)`. Първи adapters: Yahoo daily, Alpha Vantage intraday, mock/static provider for tests.
- **Metrics layer:** `app/services/metrics.py` с `calculate_dashboard_stats(user_id)`, `equity_curve(user_id)`, `drawdown_curve(user_id)`, `win_rate(trades)`.
- **AI layer:** за MVP да бъде explain/scoring слой, не training платформа:
  - `explain_signal(signal, indicators, market_context) -> explanation`
  - `score_signal(...) -> confidence/risk_notes`
  - RL/LSTM training остава research/advanced feature.
- **API layer:** endpoint-и да са тънки: validate request → call service → return schema.

## Frontend

### Да остане

- `src/app/App.tsx` protected routing skeleton.
- `src/store/authStore.ts`.
- `src/api/client.ts` и API modules за auth, dashboard, signals, trades, settings, market data.
- `src/components/AppShell.tsx`, `ProtectedRoute.tsx`, `FeatureGuard.tsx`, `StatCard.tsx`, `PageState.tsx`, `LoadingState.tsx`.
- `DashboardPage.tsx`, `SignalsPage.tsx`, `TradesPage.tsx`, `SettingsPage.tsx`, `AuthPage.tsx`.

### Да се ограничи за MVP

- `AIControlsPage.tsx`, `SimulationPage.tsx`, `SessionsPage.tsx`, `NotificationsPage.tsx`, `TradeJournalPage.tsx`, `MarketDataPage.tsx` могат да останат, но да бъдат “Advanced/Lab” секция или временно скрити зад feature flags.
- MVP навигацията трябва да показва само:
  - Login/Register
  - Dashboard
  - Signals
  - Signal History
  - Trades/History
  - Metrics
  - Settings

### Минимален flow

1. **Register/Login:** създаване на потребител и JWT login.
2. **Settings onboarding:** избор на symbols, timeframe, risk, initial balance; default values са достатъчни.
3. **Dashboard:** cards за balance/equity/drawdown/win rate/monthly PnL + equity/drawdown chart.
4. **Signals:** latest signals, filter by symbol, generate/refresh signal button.
5. **History:** списък от сигнали и trades; за MVP може да бъде една Signals page с tabs или отделна Trades page.
6. **Metrics:** може да е част от dashboard, не отделна страница в първия MVP.

## Data & Broker

### Data

- Запази yfinance daily data като default no-budget provider.
- Изолирай Alpha Vantage intraday зад optional provider с env key.
- Добави mock/static data provider за tests и offline demos.
- Създай един service contract:

```python
class MarketDataProvider(Protocol):
    def get_ohlcv(self, symbol: str, timeframe: str, start: str | None, end: str | None) -> pd.DataFrame: ...
```

- `DataLoader` може първо да стане фасада, която избира provider по `MARKET_DATA_PROVIDER`.

### Mock broker

- `MockBrokerAPI` остава MVP broker.
- Премести го зад `BrokerClient` protocol:
  - `place_order()`
  - `close_order()`
  - `get_open_orders()`
  - `get_account_snapshot()`
- API endpoint-ите не трябва да знаят дали broker-ът е mock или реален.
- Запази MQL4-like error mapping като полезен compatibility layer, но го дръж в broker adapter-а.

### Persistence

- За MVP използвай SQLite локално по default и Postgres през Docker Compose.
- SQL трябва да е source of truth за users, settings, signals, trades, equity snapshots.
- CSV/JSON artifacts да останат import/export/simulation output, не primary SaaS state.

## AI слой

За реален MVP AI слой не трябва да означава задължително TensorFlow/RL training в production request path. Предложение:

- **MVP AI explanations:** deterministic или LLM-ready service, който обяснява защо сигналът е BUY/SELL/HOLD според RSI/MACD/pivot/drawdown/risk.
- **Signal scoring:** confidence score и risk score, изчислени от индикатори и volatility.
- **Research features:** LSTM/RL/simulation да останат в `/simulations`, `/rl`, `/lstm`, но да са извън основния SaaS flow и по възможност feature-flagged.
- **Future:** ако добавиш LLM endpoint, той трябва да е adapter (`AIProvider`) с mock/local implementation за no-budget режим и cloud provider по env.

# Roadmap от текущото състояние до MVP

## Етап 1 — Изчистване и подреждане

Цел: без голям refactor, да се маркира кое е product core и кое е lab/research.

### Конкретни действия

1. Добави архитектурна документация:
   - `saas/docs/architecture/mvp-roadmap.md` — този документ.
2. Актуализирай env alignment:
   - в `saas/.env.example` добави `VITE_API_URL=http://localhost:8000/api/v1`;
   - запази `NEXT_PUBLIC_API_BASE_URL` само ако планираш Next.js, иначе го премахни по-късно.
3. Създай празни/минимални service фасади, без да местиш стара логика наведнъж:
   - `saas/apps/api/app/services/signal_engine.py`
   - `saas/apps/api/app/services/metrics.py`
   - `saas/apps/api/app/services/data_providers.py` или папка `app/services/data/`
   - `saas/apps/api/app/services/broker.py` или папка `app/services/broker/`
4. Маркирай lab features в документация и navigation:
   - `AIControlsPage.tsx`, `SimulationPage.tsx`, `SessionsPage.tsx`, `NotificationsPage.tsx`, `TradeJournalPage.tsx`, `MarketDataPage.tsx` → “Advanced/Lab”.
5. Не трий веднага notebook-а:
   - `ADC_3_0_5.ipynb` остава archive/reference.
   - root `README.md` трябва по-късно да се съкрати до project overview + линк към `saas/`.

### Очевидни dead/placeholder части

Не ги трий в първата стъпка, но ги третирай като cleanup candidates:

- `saas/packages/ui/README.md`, `saas/packages/contracts/README.md`, `saas/packages/config/README.md` — placeholder packages.
- `saas/infra/docker/README.md`, `saas/infra/nginx/README.md`, `saas/infra/terraform/README.md` — placeholder infra docs.
- `saas/scripts/README.md` — placeholder без реални scripts.
- readiness endpoint-и: `GET /signals`, `GET /trades`, `GET /settings`, `GET /dashboard/summary` — могат да останат за health/readiness, но не трябва frontend MVP да разчита на тях като data endpoints.

## Етап 2 — Backend стабилизация

Цел: един ясен backend entry point, тънки endpoint-и и стабилен MVP API.

### Entry point

- Остави canonical start:

```bash
cd saas/apps/api
uvicorn app.main:app --reload
```

- В `saas/README.md` и `saas/apps/api/README.md` документирай това като единствения backend dev entry point.

### MVP endpoint-и

Стабилизирай тези endpoint-и като “core MVP”:

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/settings/user-settings`
- `PUT /api/v1/settings/user-settings`
- `GET /api/v1/dashboard/stats`
- `GET /api/v1/dashboard/equity-curve`
- `GET /api/v1/dashboard/drawdown-curve`
- `GET /api/v1/signals/latest`
- `GET /api/v1/signals/by-symbol/{symbol}`
- `POST /api/v1/signals/generate` — нов MVP endpoint, който извиква `signal_engine` и записва сигнал.
- `GET /api/v1/trades/open`
- `GET /api/v1/trades/closed`
- `POST /api/v1/trades/open`
- `POST /api/v1/trades/close/{trade_id}`
- `GET /api/v1/market-data/ohlcv`
- `POST /api/v1/indicators/calculate`

### Изваждане на логика от endpoints

1. `dashboard.py`:
   - премести изчисленията в `app/services/metrics.py`.
2. `signals.py`:
   - добави `POST /generate`;
   - използвай `DataLoader` + indicators + simple strategy rules;
   - записвай `Signal` в DB.
3. `market_data.py`:
   - остави endpoint-а да извиква data provider service.
4. `orders.py`:
   - използвай broker interface, не директно `MockBrokerAPI` в endpoint-а.
5. `trade_journal.py`:
   - третирай като import/export/simulation artifact, не като primary MVP history.

### Минимални rules за signal engine

Първи MVP ruleset, достатъчен за реален demo product:

- BUY ако RSI < 30 и MACD histogram/line показва подобрение.
- SELL ако RSI > 70 и MACD показва отслабване.
- HOLD иначе.
- Confidence score: 0–1 на база distance от RSI thresholds, volatility/ATR и trend alignment.
- Explanation: кратък текст с използваните индикатори.

## Етап 3 — Frontend интеграция

Цел: минимален работещ UI flow без lab clutter.

### Компоненти и endpoint-и

- `AuthPage.tsx` → `authAPI.register`, `authAPI.login`, `authAPI.getCurrentUser`.
- `SettingsPage.tsx` → `settingsAPI.getUserSettings`, `settingsAPI.updateUserSettings`.
- `DashboardPage.tsx` → `dashboardAPI.getStats`, `getEquityCurve`, `getDrawdownCurve`.
- `SignalsPage.tsx` → `signalsAPI.getLatest`, `signalsAPI.getBySymbol`, нов `signalsAPI.generate`.
- `TradesPage.tsx` → `tradesAPI.getOpen`, `getClosed`, `openTrade`, `closeTrade`.
- `MarketDataPage.tsx` → optional/lab, ползва `marketDataAPI.getOHLCV`.

### Навигация за MVP

В `AppShell.tsx` остави видими:

- Dashboard
- Signals
- Trades / History
- Settings

Скрий или групирай като `Lab`:

- Sessions
- Trade Journal
- Simulations
- AI Controls
- Market Data
- Notifications

### UX flow

1. Потребителят се регистрира.
2. След login отива на Dashboard.
3. Ако няма settings, backend връща defaults.
4. User отваря Signals и натиска Generate/Refresh.
5. Backend генерира сигнал, записва го, UI го показва в Latest.
6. User може да отвори mock trade от сигнала.
7. Dashboard показва базови metrics.

## Етап 4 — Локално тестване

### Стартиране без Docker

Backend:

```bash
cd saas/apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp ../../.env.example ../../.env
uvicorn app.main:app --reload
```

Frontend:

```bash
cd saas/apps/web
npm install
VITE_API_URL=http://localhost:8000/api/v1 npm run dev
```

### Стартиране с Docker Compose

```bash
cd saas
docker compose up --build
```

### Basic test scenarios

1. Health:

```bash
curl http://localhost:8000/api/v1/health
```

2. Register:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","username":"demo","password":"password123"}'
```

3. Login:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=demo&password=password123'
```

4. Settings:

```bash
curl http://localhost:8000/api/v1/settings/user-settings \
  -H "Authorization: Bearer $TOKEN"
```

5. Latest signals:

```bash
curl http://localhost:8000/api/v1/signals/latest \
  -H "Authorization: Bearer $TOKEN"
```

6. Dashboard:

```bash
curl http://localhost:8000/api/v1/dashboard/stats \
  -H "Authorization: Bearer $TOKEN"
```

### Programmatic checks

Backend:

```bash
cd saas/apps/api
python -m pytest
```

Frontend:

```bash
cd saas/apps/web
npm test
npm run build
```

Contract-specific:

```bash
cd saas/apps/api
python -m pytest tests/test_api_contracts.py
```

## Етап 5 — Подготовка за деплой

Цел: евтин cloud-ready MVP без overengineering.

### Env

Добави/подреди `saas/.env.example`:

```env
APP_ENV=local
DATABASE_URL=sqlite:///./adc_saas.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me
CORS_ORIGINS=["http://localhost:5173"]
VITE_API_URL=http://localhost:8000/api/v1
MARKET_DATA_PROVIDER=yahoo
BROKER_PROVIDER=mock
AI_PROVIDER=mock
```

### Docker

- Запази текущите Dockerfile-и.
- За MVP може първо да деплойнеш backend като single FastAPI service без Celery, ако RL/LSTM jobs са изключени.
- Redis/Celery стават нужни само ако оставиш async training/simulation jobs.

### Render/Railway

Минимална конфигурация:

- Backend service:
  - root: `saas/apps/api`
  - build: `pip install -e .`
  - start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - env: `DATABASE_URL`, `SECRET_KEY`, `CORS_ORIGINS`, provider vars.
- Postgres managed DB.
- Frontend:
  - root: `saas/apps/web`
  - build: `npm ci && npm run build`
  - publish: `dist`
  - env: `VITE_API_URL=https://<backend-domain>/api/v1`.

### Vercel

- Подходящо само за frontend Vite static hosting.
- Backend трябва да остане Render/Railway/Fly.io/VM, защото FastAPI + ML deps не са удобни за Vercel serverless.

## Минимална последователност за един човек

1. Документирай MVP scope и маркирай lab features.
2. Подравни env и local run docs.
3. Добави `signal_engine.py` с прост deterministic ruleset.
4. Добави `POST /signals/generate` и frontend button.
5. Извади dashboard metrics в service.
6. Скрий lab navigation от MVP shell.
7. Направи e2e smoke flow: register → login → settings → generate signal → dashboard.
8. Пусни backend contract tests и frontend build.
9. Подготви Render/Railway backend + Vercel frontend deployment docs.
10. Едва след това мисли за real broker, paid data provider, Stripe и advanced AI.
