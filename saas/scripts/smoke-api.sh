#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000/api/v1}"
RUN_ID="${RUN_ID:-$(date +%s)}"
USERNAME="${SMOKE_USERNAME:-smoke_${RUN_ID}}"
EMAIL="${SMOKE_EMAIL:-smoke_${RUN_ID}@example.com}"
PASSWORD="${SMOKE_PASSWORD:-correct-horse-battery-staple}"

request() {
  local method="$1"
  local path="$2"
  shift 2
  curl --fail --show-error --silent --request "$method" "${API_URL}${path}" "$@"
}

extract_token() {
  python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
}

printf 'Smoke API base: %s\n' "$API_URL"

printf '1/8 health...\n'
request GET /health >/dev/null

printf '2/8 register user...\n'
request POST /auth/register \
  --header 'Content-Type: application/json' \
  --data "{\"email\":\"${EMAIL}\",\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" >/dev/null

printf '3/8 login user...\n'
TOKEN="$(request POST /auth/login \
  --header 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=${USERNAME}" \
  --data-urlencode "password=${PASSWORD}" | extract_token)"
AUTH_HEADER="Authorization: Bearer ${TOKEN}"

printf '4/8 read default user settings...\n'
request GET /settings/user-settings --header "$AUTH_HEADER" >/dev/null

printf '5/8 update user settings...\n'
request PUT /settings/user-settings \
  --header "$AUTH_HEADER" \
  --header 'Content-Type: application/json' \
  --data '{"symbols":["EURUSD","BTCUSD"],"timeframe":"1h","balance":10000,"risk_per_trade":0.01,"grid_levels":5,"grid_step_pct":0.0025,"martingale_factor":1.05,"enable_trading":false,"email_notifications":false}' >/dev/null

printf '6/8 create and read signals...\n'
request POST /signals/create \
  --header "$AUTH_HEADER" \
  --header 'Content-Type: application/json' \
  --data '{"symbol":"EURUSD","action":"BUY","price":1.085,"rsi":44.2,"macd":0.15}' >/dev/null
request GET /signals/latest --header "$AUTH_HEADER" >/dev/null
request GET /signals/by-symbol/EURUSD --header "$AUTH_HEADER" >/dev/null

printf '7/8 read dashboard stats...\n'
request GET /dashboard/stats --header "$AUTH_HEADER" >/dev/null
request GET /dashboard/equity-curve --header "$AUTH_HEADER" >/dev/null
request GET /dashboard/drawdown-curve --header "$AUTH_HEADER" >/dev/null

printf '8/8 readiness placeholders...\n'
request GET /dashboard/summary >/dev/null
request GET /settings >/dev/null
request GET /signals >/dev/null

printf 'Smoke API flow passed for user %s.\n' "$USERNAME"
