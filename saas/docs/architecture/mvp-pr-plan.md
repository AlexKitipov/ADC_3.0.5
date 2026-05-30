# ADC 3.0.5 — подробен план от Pull Request-и за SaaS MVP

Този документ разбива `mvp-roadmap.md` на малки, атомарни и изпълними Pull Request-и. Редът е подбран така, че всеки PR да може да се тества самостоятелно, без да чупи текущия FastAPI + Vite flow, и да използва максимално съществуващите endpoint-и, schemas, services и страници.

## Етап 1: Изчистване и подреждане

### PR 1: Подравняване на MVP scope, env и локални run инструкции

- **Описание**
  - Фиксира текущия SaaS runtime като официална посока за MVP.
  - Подравнява frontend env ключа към Vite (`VITE_API_URL`) и оставя ясни бележки, че notebook/root legacy слой остава само архив/референция.
  - Не променя runtime логика; целта е безопасна основа за следващите PR-и.
- **Промени по backend**
  - Документира canonical start command: `cd saas/apps/api && uvicorn app.main:app --reload`.
  - Описва core MVP endpoint-ите, без още да премахва readiness/demo endpoint-и.
- **Промени по frontend**
  - Документира canonical Vite env: `VITE_API_URL=http://localhost:8000/api/v1`.
  - Проверява, че `src/api/client.ts` продължава да чете `import.meta.env.VITE_API_URL` с fallback към локалния backend.
- **Промени по services**
  - Няма промени по service код в този PR.
- **Промени по модели/схеми**
  - Няма промени.
- **Промени по инфраструктура**
  - Редактира `saas/.env.example`: добавя/подрежда `APP_ENV`, `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `CORS_ORIGINS`, `VITE_API_URL`, `MARKET_DATA_PROVIDER`, `BROKER_PROVIDER`, `AI_PROVIDER`.
  - Редактира `saas/README.md` и `saas/apps/api/README.md` с единен local run flow.
- **Файлове за създаване**
  - Няма.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest tests/test_api_contracts.py`
  - `cd saas/apps/web && npm run build`
  - Ръчно: frontend build използва `VITE_API_URL`, а документацията не сочи друг backend entry point.

### PR 2: Маркиране и ограничаване на Lab/Advanced features в навигацията

- **Описание**
  - Прави MVP навигацията чиста: Dashboard, Signals, Trades/History, Settings.
  - Advanced/Lab страниците остават в кода и routing-а, но вече не са част от основния SaaS shell.
  - Не изтрива AI, simulations, sessions, market data, notifications или trade journal функционалност.
- **Промени по backend**
  - Няма backend runtime промени.
  - Документира, че `/rl`, `/lstm`, `/simulations`, `/sessions`, `/trade-journal`, `/notifications`, `/market-stream` са lab/advanced endpoint families.
- **Промени по frontend**
  - Редактира `saas/apps/web/src/components/AppShell.tsx`: основният `navItems` показва само Dashboard, Signals, Trades/History и Settings.
  - Добавя вторичен collapsed/secondary Lab section или скрива lab links зад feature flag/config константа.
  - Редактира текстовете в `AIControlsPage.tsx`, `SimulationPage.tsx`, `SessionsPage.tsx`, `NotificationsPage.tsx`, `TradeJournalPage.tsx`, `MarketDataPage.tsx`, така че да показват “Advanced/Lab”.
  - Запазва route definitions в `saas/apps/web/src/app/App.tsx`, за да не се счупят директни URL-и и тестове.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - По избор: `saas/apps/web/src/config/features.ts` за `showLabNavigation`/`labRoutes`, ако няма съществуващ config.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/web && npm test -- --run`
  - `cd saas/apps/web && npm run build`
  - Ръчно: след login sidebar/mobile nav показват само MVP links; директен `/simulations` URL още се зарежда.

### PR 3: Добавяне на празни MVP service фасади без refactor на стара логика

- **Описание**
  - Създава стабилни места за новия bounded-context слой, без да мести старата логика наведнъж.
  - Всеки фасаден service има минимални функции/classes и unit tests, но endpoint-ите все още може да използват стария код.
- **Промени по backend**
  - Не променя API responses.
  - Добавя imports само където са нужни за tests; не сменя router behavior.
- **Промени по frontend**
  - Няма.
- **Промени по services**
  - Създава `app/services/signal_engine.py` с `SignalDecision` dataclass/Pydantic-compatible DTO и placeholder deterministic `generate_signal_decision(...)`.
  - Създава `app/services/metrics.py` с чисти функции `win_rate(...)`, `calculate_monthly_pnl(...)`, `latest_equity_snapshot(...)`.
  - Създава `app/services/data/__init__.py`, `app/services/data/providers.py`, `app/services/data/mock_provider.py`, `app/services/data/yahoo_provider.py`, `app/services/data/alpha_vantage_provider.py`.
  - Създава `app/services/broker/__init__.py`, `app/services/broker/base.py`, `app/services/broker/mock_broker.py`.
  - Старите `data_loader.py` и `order_management.py` остават непреместени и работещи.
- **Промени по модели/схеми**
  - Няма DB migration.
  - По избор добавя lightweight schema exports само ако tests изискват serializable DTO.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - `saas/apps/api/app/services/signal_engine.py`
  - `saas/apps/api/app/services/metrics.py`
  - `saas/apps/api/app/services/data/__init__.py`
  - `saas/apps/api/app/services/data/providers.py`
  - `saas/apps/api/app/services/data/mock_provider.py`
  - `saas/apps/api/app/services/data/yahoo_provider.py`
  - `saas/apps/api/app/services/data/alpha_vantage_provider.py`
  - `saas/apps/api/app/services/broker/__init__.py`
  - `saas/apps/api/app/services/broker/base.py`
  - `saas/apps/api/app/services/broker/mock_broker.py`
  - `saas/apps/api/tests/test_signal_engine.py`
  - `saas/apps/api/tests/test_metrics_service.py`
  - `saas/apps/api/tests/test_data_providers.py`
  - `saas/apps/api/tests/test_broker_interface.py`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма в този PR; преместванията са по-късно.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest tests/test_signal_engine.py tests/test_metrics_service.py tests/test_data_providers.py tests/test_broker_interface.py`
  - `cd saas/apps/api && python -m pytest tests/test_api_contracts.py`

## Етап 2: Backend стабилизация

### PR 4: Изолиране на data providers зад MarketDataProvider contract

- **Описание**
  - Прави `DataLoader` фасада, която избира provider по `MARKET_DATA_PROVIDER`.
  - Запазва yfinance daily data като default no-budget provider, Alpha Vantage като optional intraday provider и mock/static provider за tests/offline demo.
- **Промени по backend**
  - `GET /api/v1/market-data/ohlcv` запазва същия HTTP contract, но използва provider factory вместо директна логика.
  - `POST /api/v1/indicators/calculate` може да продължи да работи със същите schemas, но тестовете трябва да могат да използват mock provider.
- **Промени по frontend**
  - Няма промяна по UI.
  - `src/api/marketData.ts` остава със същия contract.
- **Промени по services**
  - Редактира `app/services/data/providers.py`: `MarketDataProvider` Protocol с `get_ohlcv(symbol, timeframe, start, end)`.
  - Редактира `app/services/data/mock_provider.py`: връща deterministic OHLCV DataFrame за unit/API tests.
  - Редактира `app/services/data/yahoo_provider.py`: премества yfinance daily логиката от `data_loader.py`.
  - Редактира `app/services/data/alpha_vantage_provider.py`: премества Alpha Vantage intraday логиката и чете key само ако provider е активен.
  - Редактира `app/services/data_loader.py`: оставя backward-compatible фасада и `get_market_data_provider()` factory.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - `saas/.env.example`: документира `MARKET_DATA_PROVIDER=yahoo` и optional `ALPHA_VANTAGE_API_KEY=`.
- **Файлове за създаване**
  - Ако PR 3 не е създал тестове: `saas/apps/api/tests/test_market_data_provider_selection.py`.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Логически се пренася код от `app/services/data_loader.py` към `app/services/data/*.py`, но файлът `data_loader.py` остава като compatibility фасада.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && MARKET_DATA_PROVIDER=mock python -m pytest tests/test_market_data.py tests/test_indicators.py tests/test_market_data_provider_selection.py`
  - `cd saas/apps/api && python -m pytest tests/test_api_contracts.py`

### PR 5: Изолиране на MockBrokerAPI зад BrokerClient interface

- **Описание**
  - Разграничава `trades` като SaaS history/PnL от `orders` като broker execution adapter.
  - API endpoint-ите вече не трябва да знаят дали broker-ът е mock или реален.
- **Промени по backend**
  - Редактира `app/api/v1/endpoints/orders.py`: използва `get_broker_client()` dependency/factory.
  - Запазва текущите `/api/v1/orders/*` endpoint paths и response schemas.
  - Не променя `/api/v1/trades/*` в този PR.
- **Промени по frontend**
  - `src/api/orders.ts` остава със същия public API.
  - Няма UI промяна.
- **Промени по services**
  - Редактира `app/services/broker/base.py`: `BrokerClient` Protocol с `place_order`, `close_order`, `get_open_orders`, `get_account_snapshot`.
  - Редактира `app/services/broker/mock_broker.py`: премества/обвива `MockBrokerAPI` от `order_management.py`.
  - Редактира `app/services/order_management.py`: compatibility imports за MQL4 constants/error mapping и deprecated wrapper, ако тестове все още го import-ват.
  - Добавя provider factory по `BROKER_PROVIDER=mock`.
- **Промени по модели/схеми**
  - Няма DB промени.
  - Ако schemas са твърде broker-specific, добавя минимални aliases, без breaking changes.
- **Промени по инфраструктура**
  - `saas/.env.example`: документира `BROKER_PROVIDER=mock`.
- **Файлове за създаване**
  - `saas/apps/api/tests/test_broker_orders_api.py` или разширяване на съществуващите order tests.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Логически пренася mock broker implementation от `app/services/order_management.py` към `app/services/broker/mock_broker.py`; старият файл остава compatibility layer.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && BROKER_PROVIDER=mock python -m pytest tests/test_orders.py tests/test_broker_orders_api.py`
  - `cd saas/apps/api && python -m pytest tests/test_api_contracts.py`
  - `cd saas/apps/web && npm test -- --run src/api/orders.test.ts`

### PR 6: Изваждане на dashboard metrics в services/metrics.py

- **Описание**
  - Прави `dashboard.py` тънък API слой: validate/auth/db dependency → call metrics service → return schema.
  - Подготвя frontend dashboard за реални SaaS metrics: balance, equity, drawdown, win rate, monthly PnL, equity curve, drawdown curve.
- **Промени по backend**
  - Редактира `app/api/v1/endpoints/dashboard.py`: премахва директните агрегиращи изчисления от endpoint-а.
  - `GET /api/v1/dashboard/stats` връща същия `DashboardStats` contract.
  - `GET /api/v1/dashboard/equity-curve` и `GET /api/v1/dashboard/drawdown-curve` връщат същите response models, но се изчисляват през service.
  - `GET /api/v1/dashboard/summary` остава readiness endpoint, но се маркира като не-MVP data endpoint.
- **Промени по frontend**
  - Няма нужда от промяна; `src/api/dashboard.ts` остава съвместим.
  - Ако frontend очаква различно fallback поведение, обновява tests в `src/api/dashboard.test.ts`.
- **Промени по services**
  - Редактира `app/services/metrics.py`: добавя `calculate_dashboard_stats(db, user_id)`, `get_equity_curve(db, user_id)`, `get_drawdown_curve(db, user_id)`, `win_rate(trades)`.
  - Добавя unit tests за edge cases: no trades, no snapshots, only open trades, monthly PnL only closed trades.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - `saas/apps/api/tests/test_dashboard_metrics_service.py`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest tests/test_dashboard.py tests/test_dashboard_metrics_service.py`
  - `cd saas/apps/web && npm test -- --run src/api/dashboard.test.ts src/pages/DashboardPage.test.tsx`

### PR 7: Създаване на реален MVP signal_engine ruleset

- **Описание**
  - Имплементира deterministic ruleset за BUY/SELL/HOLD на база RSI, MACD trend/histogram и volatility/risk proxy.
  - Не включва TensorFlow/RL/LSTM в production request path.
- **Промени по backend**
  - Няма нов endpoint още; PR-ът е service-first, за да е лесен за unit тестване.
- **Промени по frontend**
  - Няма.
- **Промени по services**
  - Редактира `app/services/signal_engine.py`: добавя `generate_signal(symbol, timeframe, strategy_settings, data_provider) -> SignalDecision`.
  - Използва `MarketDataProvider` за OHLCV.
  - Използва съществуващите indicator helpers от `saas/apps/api/core/indicators.py` или текущия indicators service, без да мести `core/` в този PR.
  - BUY rule: RSI < 30 и MACD line/histogram показва подобрение.
  - SELL rule: RSI > 70 и MACD показва отслабване.
  - HOLD rule: default.
  - Confidence score: 0–1, базиран на дистанция от RSI thresholds, trend alignment и volatility.
  - Explanation: кратък текст с RSI/MACD/risk reasons.
- **Промени по модели/схеми**
  - Редактира `app/schemas/signals.py`: добавя request schema за generate endpoint, напр. `SignalGenerateRequest(symbol: str | None, timeframe: str | None)` и response schema/fields, ако съществуващият `Signal` не покрива `confidence`/`explanation`.
  - Ако DB моделът `Signal` няма `confidence`/`explanation`, в този PR може да ги върне само в response DTO или да добави nullable columns само ако project вече няма migration constraint. За атомарност предпочитаният вариант е response DTO без DB schema break.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - `saas/apps/api/tests/test_signal_engine_rules.py`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && MARKET_DATA_PROVIDER=mock python -m pytest tests/test_signal_engine.py tests/test_signal_engine_rules.py`
  - Unit cases: oversold → BUY, overbought → SELL, neutral → HOLD, missing/short data → safe HOLD.

### PR 8: Добавяне на POST /api/v1/signals/generate и запис в DB

- **Описание**
  - Свързва `signal_engine` с SaaS API.
  - Endpoint-ът генерира сигнал за текущия потребител, записва го в `Signal` таблицата и връща създадения signal/decision.
- **Промени по backend**
  - Редактира `app/api/v1/endpoints/signals.py`: добавя `POST /generate`.
  - Endpoint flow: current user → load user settings → choose symbol/timeframe from request or settings defaults → call `signal_engine.generate_signal(...)` → persist `Signal(user_id, symbol, action, price, rsi, macd, timestamp)` → return schema.
  - `GET /api/v1/signals/latest` и `GET /api/v1/signals/by-symbol/{symbol}` остават без breaking changes.
  - `POST /api/v1/signals/create` остава за manual/test compatibility, но не е основният MVP generate flow.
- **Промени по frontend**
  - Няма UI промяна в този PR, но contract се подготвя за следващия PR.
- **Промени по services**
  - Редактира `app/services/signal_engine.py`: добавя helper за DB persistence или връща достатъчно данни за endpoint-а.
  - Използва `app/services/data_loader.py`/provider factory и settings service/model.
- **Промени по модели/схеми**
  - Редактира `app/schemas/signals.py`: добавя `SignalGenerateRequest` и `SignalGenerateResponse` или разширява съществуващите schemas без да чупи response на existing endpoints.
  - Не изисква non-null нови DB columns.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - `saas/apps/api/tests/test_signals_generate_api.py`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && MARKET_DATA_PROVIDER=mock python -m pytest tests/test_signals.py tests/test_signals_generate_api.py tests/test_api_contracts.py`
  - Smoke API: register/login → `POST /api/v1/signals/generate` → `GET /api/v1/signals/latest` показва новия запис.

### PR 9: Стабилизиране на trades MVP endpoints и отделяне от orders/broker execution

- **Описание**
  - Финализира SaaS trade history flow: open trades, closed trades, open trade, close trade.
  - Оставя broker execution в `/orders`, но `/trades` става source of truth за потребителската история/PnL.
- **Промени по backend**
  - Редактира `app/api/v1/endpoints/trades.py`: гарантира stable contracts за `GET /open`, `GET /closed`, `POST /open`, `POST /close/{trade_id}`.
  - Проверява authorization: потребителят може да вижда/затваря само свои trades.
  - `POST /close/{trade_id}` изчислява/запазва `pnl`, `exit_price`, `exit_time`, `status=closed`.
  - Не извиква директно `MockBrokerAPI`; ако се прави broker order, това трябва да е чрез adapter или да остане out of scope.
- **Промени по frontend**
  - `src/api/trades.ts`: подравнява methods към stable endpoints (`getOpen`, `getClosed`, `openTrade`, `closeTrade`).
  - `src/pages/TradesPage.tsx`: гарантира, че UI не разчита на `/orders` за history.
- **Промени по services**
  - По избор създава `app/services/trade_service.py` с `open_trade(...)`, `close_trade(...)`, `list_open_trades(...)`, `list_closed_trades(...)`, ако endpoint-ът съдържа твърде много логика.
  - Ако service се създаде, endpoint-ът става тънък wrapper.
- **Промени по модели/схеми**
  - Редактира `app/schemas/trades.py`, ако липсват ясни `TradeOpenRequest`/`TradeCloseRequest` schemas.
  - Не прави breaking DB промени.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - По избор: `saas/apps/api/app/services/trade_service.py`
  - `saas/apps/api/tests/test_trades_mvp_api.py`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest tests/test_trades.py tests/test_trades_mvp_api.py`
  - `cd saas/apps/web && npm test -- --run src/api/trades.test.ts src/pages/TradesPage.test.tsx`
  - Smoke API: open trade → appears in `/trades/open` → close trade → appears in `/trades/closed` with PnL.

### PR 10: Изчистване на readiness/demo endpoint contracts от MVP frontend dependency

- **Описание**
  - Оставя readiness/demo endpoint-и налични, но ги маркира и тества отделно, за да не се ползват като product data endpoints.
  - Целта е MVP frontend да разчита само на стабилните `/auth`, `/settings/user-settings`, `/dashboard/stats`, `/dashboard/*-curve`, `/signals/latest`, `/signals/by-symbol`, `/signals/generate`, `/trades/*`, `/market-data/ohlcv`, `/indicators/calculate`.
- **Промени по backend**
  - Редактира docstrings/tags или schemas за readiness endpoints: `GET /signals`, `GET /trades`, `GET /settings`, `GET /dashboard/summary`.
  - Добавя/обновява static API contract tests, които ясно различават MVP core от readiness/demo routes.
  - Не премахва endpoints в този PR, за да няма breaking change.
- **Промени по frontend**
  - Проверява и премахва usage на readiness endpoints от `src/api/*.ts` и pages, ако има такова.
  - Frontend API clients трябва да сочат stable MVP endpoint-и.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - По избор: `saas/apps/api/tests/test_mvp_route_contracts.py`, ако съществуващият contract test не е достатъчно ясен.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest tests/test_api_contracts.py tests/test_mvp_route_contracts.py`
  - `cd saas/apps/web && npm test -- --run src/api`
  - Manual route audit: MVP pages не извикват readiness routes.

## Етап 3: Frontend интеграция

### PR 11: Добавяне на signalsAPI.generate и Generate/Refresh UI

- **Описание**
  - Свързва новия backend generate endpoint с Signals page.
  - Потребителят вече може да генерира сигнал от UI и веднага да види резултата в latest/history.
- **Промени по backend**
  - Няма backend промяна, освен ако contract test от PR 8 открие несъответствие.
- **Промени по frontend**
  - Редактира `saas/apps/web/src/api/signals.ts`: добавя `generate(payload?: { symbol?: string; timeframe?: string })`.
  - Редактира `saas/apps/web/src/pages/SignalsPage.tsx`: добавя Generate/Refresh button, loading state, error state и optimistic или refetch flow.
  - Ако Signals page има symbol filter, generate използва избрания symbol; иначе backend settings default.
  - Обновява `src/pages/SignalsPage.test.tsx` и/или добавя `src/api/signals.test.ts`.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Frontend types: редактира `saas/apps/web/src/types/index.ts`, ако `Signal` трябва да включва optional `confidence`/`explanation`.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - По избор: `saas/apps/web/src/api/signals.test.ts`, ако липсва.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/web && npm test -- --run src/api/signals.test.ts src/pages/SignalsPage.test.tsx`
  - `cd saas/apps/web && npm run build`
  - E2E manual: login → Signals → Generate → latest list обновява нов сигнал.

### PR 12: Подравняване на Settings onboarding flow към MVP defaults

- **Описание**
  - Гарантира, че нов потребител получава usable defaults за symbols, timeframe, risk и initial balance.
  - Settings page става първото място за MVP configuration, без да блокира dashboard ако липсват настройки.
- **Промени по backend**
  - Редактира `app/api/v1/endpoints/settings.py`: `GET /user-settings` връща default settings, ако user още няма запис.
  - `PUT /user-settings` валидира symbols/timeframe/risk и запазва за текущия user.
- **Промени по frontend**
  - Редактира `src/pages/SettingsPage.tsx`: показва defaults, save state и clear validation errors.
  - Редактира `src/api/settings.ts`, ако method names/paths не съвпадат със stable contract.
  - `FeatureGuard` трябва да третира default symbols като валидни след успешно load-ване.
- **Промени по services**
  - По избор добавя `app/services/settings_service.py` само ако endpoint-ът съдържа дублирана default логика; иначе оставя endpoint simple.
- **Промени по модели/схеми**
  - Редактира `app/schemas/settings.py`: ясни defaults и validation bounds.
  - Frontend types в `src/types/index.ts` се подравняват към backend schema.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - `saas/apps/api/tests/test_settings_defaults.py`
  - По избор: `saas/apps/web/src/api/settings.test.ts`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest tests/test_settings.py tests/test_settings_defaults.py`
  - `cd saas/apps/web && npm test -- --run src/api/settings.test.ts`
  - Manual: new user → Dashboard loads → Settings shows default symbols/timeframe/risk → save works.

### PR 13: Dashboard page подравнен към metrics service и empty states

- **Описание**
  - Dashboard показва работещи cards и curves дори при нов потребител без trades/snapshots.
  - Empty states обясняват следващата стъпка: configure settings → generate signal → open trade.
- **Промени по backend**
  - Няма endpoint промени; използва стабилизираните metrics endpoints.
- **Промени по frontend**
  - Редактира `src/pages/DashboardPage.tsx`: гарантира calls към `dashboardAPI.getStats`, `getEquityCurve`, `getDrawdownCurve`.
  - Добавя graceful empty chart state за празни arrays.
  - Добавя CTA към `/signals` за generate signal, ако няма signals/trades.
  - Обновява `src/pages/DashboardPage.test.tsx`.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Frontend types се подравняват, ако `DashboardStats` fields са nullable/zero defaults.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - Няма, освен ако се добави малък shared chart empty-state component.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/web && npm test -- --run src/api/dashboard.test.ts src/pages/DashboardPage.test.tsx`
  - `cd saas/apps/web && npm run build`
  - Manual: new user dashboard не показва crash/NaN.

### PR 14: Trades page интеграция с MVP trade lifecycle

- **Описание**
  - Trades page става реална History страница за open/closed trades.
  - Позволява отваряне/затваряне на mock trade през SaaS `/trades` endpoints, без директна зависимост от broker `/orders`.
- **Промени по backend**
  - Няма, освен малки schema fixes ако frontend разкрие mismatch.
- **Промени по frontend**
  - Редактира `src/pages/TradesPage.tsx`: отделя Open и Closed tabs/sections.
  - Използва `tradesAPI.getOpen`, `tradesAPI.getClosed`, `tradesAPI.openTrade`, `tradesAPI.closeTrade`.
  - Добавя loading/error states и PnL display.
  - По избор добавя action от signal към open trade, ако Signals page вече връща достатъчно price/action.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Frontend `Trade` type в `src/types/index.ts` се подравнява към backend schema.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - Няма.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/web && npm test -- --run src/api/trades.test.ts src/pages/TradesPage.test.tsx`
  - `cd saas/apps/web && npm run build`
  - Manual: open trade → appears in Open → close → moves to Closed with PnL.

### PR 15: Финален MVP shell flow и route cleanup без изтриване на Lab код

- **Описание**
  - Подрежда frontend flow: login/register → dashboard → settings/signals/trades.
  - Lab routes остават директно достъпни или feature-flagged, но не са видими в основния MVP shell.
- **Промени по backend**
  - Няма.
- **Промени по frontend**
  - Редактира `src/app/App.tsx`: проверява redirects и protected route order.
  - Редактира `src/components/AppShell.tsx`: финализира desktop/mobile MVP nav.
  - Редактира `src/components/FeatureGuard.tsx`: гарантира, че settings defaults не блокират Signals/Trades без нужда.
  - Проверява `AuthPage.tsx`: register/login redirects са към `/dashboard`.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Няма.
- **Файлове за създаване**
  - По избор: `saas/apps/web/src/config/navigation.ts`, ако навигацията трябва да бъде централизирана.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/web && npm test -- --run src/store/authStore.test.ts src/pages/DashboardPage.test.tsx src/pages/SignalsPage.test.tsx src/pages/TradesPage.test.tsx`
  - `cd saas/apps/web && npm run build`
  - Manual: unauthenticated user redirects to login; authenticated user lands on dashboard; nav is MVP-only.

## Етап 4: Локално тестване

### PR 16: Backend smoke сценарии и test data helpers

- **Описание**
  - Добавя програмируеми smoke tests за основния MVP API flow.
  - Целта е всеки бъдещ PR да може да докаже register → login → settings → generate signal → dashboard → trade lifecycle.
- **Промени по backend**
  - Добавя integration tests, които използват test DB и mock market data provider.
  - Проверява auth token flow, settings defaults, signal generation persistence, dashboard stats и trades lifecycle.
- **Промени по frontend**
  - Няма.
- **Промени по services**
  - Ако е нужно, добавя fixtures/helper factories за mock provider и user settings.
- **Промени по модели/схеми**
  - Няма runtime schema промени.
- **Промени по инфраструктура**
  - Редактира `saas/apps/api/pyproject.toml` или pytest config, ако трябва `MARKET_DATA_PROVIDER=mock` за smoke tests.
  - Документира smoke командата в `saas/apps/api/README.md`.
- **Файлове за създаване**
  - `saas/apps/api/tests/test_mvp_smoke_flow.py`
  - По избор: `saas/apps/api/tests/factories.py`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && MARKET_DATA_PROVIDER=mock python -m pytest tests/test_mvp_smoke_flow.py`
  - `cd saas/apps/api && python -m pytest`

### PR 17: Frontend API/client smoke coverage за MVP flow

- **Описание**
  - Добавя frontend tests за API clients и ключови страници с mocked backend responses.
  - Целта е build/test да хваща contract drift между frontend и backend.
- **Промени по backend**
  - Няма.
- **Промени по frontend**
  - Добавя/обновява tests за `auth.ts`, `settings.ts`, `dashboard.ts`, `signals.ts`, `trades.ts`.
  - Добавя page tests за Signals generate button, Dashboard empty state и Trades lifecycle UI.
  - Проверява Axios bearer token interceptor в `src/api/client.ts` чрез съществуващите auth tests.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Ако frontend types са разпръснати, централизира само минимално в `src/types/index.ts` без голям refactor.
- **Промени по инфраструктура**
  - Ако липсва test setup, добавя/коригира `vitest` setup в рамките на текущия frontend tooling.
- **Файлове за създаване**
  - `saas/apps/web/src/api/signals.test.ts`, ако още липсва.
  - `saas/apps/web/src/api/settings.test.ts`, ако още липсва.
  - По избор: `saas/apps/web/src/pages/SettingsPage.test.tsx`.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/web && npm test -- --run`
  - `cd saas/apps/web && npm run build`

### PR 18: Local Docker Compose MVP profile и docs smoke commands

- **Описание**
  - Подготвя локален Docker Compose flow, който стартира MVP без да изисква lab training jobs в request path.
  - Celery/Redis остават налични, но MVP smoke docs не зависят от RL/LSTM jobs.
- **Промени по backend**
  - Няма application logic промяна.
  - Проверява backend container start command: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Промени по frontend**
  - Проверява web container build args/env за `VITE_API_URL`.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Редактира `saas/docker-compose.yml`: env vars са консистентни с `.env.example`; `MARKET_DATA_PROVIDER`, `BROKER_PROVIDER`, `AI_PROVIDER` имат safe defaults.
  - Редактира `saas/README.md`: добавя `docker compose up --build` и smoke curl сценарии.
  - По избор добавя `saas/scripts/smoke-api.sh` за health/register/login/settings/signals/dashboard smoke flow.
- **Файлове за създаване**
  - По избор: `saas/scripts/smoke-api.sh`.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas && docker compose config`
  - `cd saas && docker compose up --build`
  - `cd saas && ./scripts/smoke-api.sh` ако script е добавен.

## Етап 5: Подготовка за деплой

### PR 19: Production-ready env contract и cheap deploy documentation

- **Описание**
  - Подготвя Render/Railway backend + Vercel/static frontend deployment без overengineering.
  - Документира кои env променливи са задължителни и кои са optional/lab.
- **Промени по backend**
  - Проверява, че backend приема `PORT` чрез deploy start command, без да променя local dev command.
  - Проверява CORS config с `CORS_ORIGINS` за deployed frontend domain.
- **Промени по frontend**
  - Документира `VITE_API_URL=https://<backend-domain>/api/v1` за build-time env.
- **Промени по services**
  - Няма.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Редактира `saas/.env.example`: final MVP env block.
  - Създава `saas/docs/deployment/cheap-mvp-deploy.md` с Render/Railway backend, managed Postgres, Vercel/static frontend и notes за Redis/Celery като optional.
  - Редактира `saas/infra/README.md`: линк към deploy doc и яснота, че Terraform/Nginx са future.
- **Файлове за създаване**
  - `saas/docs/deployment/cheap-mvp-deploy.md`
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas && docker compose config`
  - `cd saas/apps/api && python -m pytest tests/test_api_contracts.py`
  - `cd saas/apps/web && npm run build`

### PR 20: Runtime hardening за MVP deploy без lab dependencies в critical path

- **Описание**
  - Финален малък hardening PR преди deploy.
  - Гарантира, че MVP backend може да стартира като single FastAPI service, дори ако Redis/Celery/RL/LSTM не са активни.
- **Промени по backend**
  - Проверява imports в `app/main.py` и `app/api/v1/api.py`: lab routers могат да останат регистрирани, но не трябва да стартират тежки training dependencies на import.
  - Ако някой lab endpoint import-ва тежка зависимост eager, премества я вътре в function/service call или зад feature flag, без try/catch around imports.
  - Добавя health/readiness smoke check за `/api/v1/health`, ако вече съществува; ако не съществува, добавя минимален health endpoint в подходящия router само ако съвпада с текущия routing style.
- **Промени по frontend**
  - Няма UI промени.
- **Промени по services**
  - Research services (`rl_trainer.py`, `simulation_runner.py`, `pivot_env.py`, LSTM wrappers) остават lab; production MVP path не ги извиква.
  - Optional notifications/market stream не трябва да блокират app startup.
- **Промени по модели/схеми**
  - Няма.
- **Промени по инфраструктура**
  - Docker/README docs уточняват, че Celery worker е optional за MVP deploy.
  - Ако compose има hard dependency от web/backend към worker, премахва я.
- **Файлове за създаване**
  - По избор: `saas/apps/api/tests/test_app_startup.py`.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -c "from app.main import app; print(app.title)"`
  - `cd saas/apps/api && python -m pytest tests/test_app_startup.py tests/test_api_contracts.py`
  - `cd saas && docker compose config`

### PR 21: Финален MVP acceptance smoke и release checklist

- **Описание**
  - Последният PR не добавя нова архитектура; само заключва acceptance checklist и smoke commands за MVP release.
  - Потвърждава, че последователността от PR-и е довела до работещ SaaS MVP: auth, settings, dashboard, signal generation, trades history и deploy docs.
- **Промени по backend**
  - Няма feature промени; само fixes ако smoke тестовете открият дребен contract mismatch.
- **Промени по frontend**
  - Няма feature промени; само fixes ако build/test открият дребен contract mismatch.
- **Промени по services**
  - Няма feature промени.
- **Промени по модели/схеми**
  - Няма planned schema промени.
- **Промени по инфраструктура**
  - Създава или редактира release checklist doc с точните команди за локално и Docker тестване.
  - По избор добавя Makefile targets, ако `saas/Makefile` вече има подходяща структура: `test-api`, `test-web`, `build-web`, `smoke-api`.
- **Файлове за създаване**
  - `saas/docs/architecture/mvp-acceptance-checklist.md` или `saas/docs/deployment/mvp-release-checklist.md`.
- **Файлове за изтриване**
  - Няма.
- **Файлове за преместване**
  - Няма.
- **Какво да се тества след PR-а**
  - `cd saas/apps/api && python -m pytest`
  - `cd saas/apps/web && npm test -- --run`
  - `cd saas/apps/web && npm run build`
  - `cd saas && docker compose config`
  - Manual acceptance: register → login → settings defaults/save → generate signal → latest signals → open trade → close trade → dashboard metrics update.

## Препоръчителна зависимост между PR-ите

- PR 1–3 са foundation и трябва да влязат първи.
- PR 4 и PR 5 са независими един от друг след PR 3 и могат да се разработват паралелно, но merge редът може да остане 4 → 5 за по-лесен review.
- PR 6 трябва да влезе преди PR 13.
- PR 7 трябва да влезе преди PR 8, а PR 8 преди PR 11.
- PR 9 трябва да влезе преди PR 14.
- PR 10 е cleanup/contract guard и е най-полезен след backend стабилизацията, преди frontend финализацията.
- PR 16–18 заключват локалното качество преди deploy подготовката.
- PR 19–21 са deploy/release hardening и не трябва да добавят нови product features.
