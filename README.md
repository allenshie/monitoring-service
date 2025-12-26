# Monitoring Service

提供邊緣端／整合端上報心跳與事件的 FastAPI 服務，並可在非 k8s 環境下啟用內建的 heartbeat watcher，監測服務是否失聯。若部署於 k8s，可將 `MONITOR_HEARTBEAT_ENABLED=0` 僅保留 HTTP 介面與 Prometheus metrics。

## 功能與範疇
- `/heartbeat`：邊緣/整合服務每隔數秒呼叫，更新最後心跳時間。
- `/events`：傳送異常或業務事件（例如推論失敗、整合錯誤、任務成功）。
- `/metrics`：Prometheus 可抓取心跳與事件的 Gauge/Counter，包含 `monitoring_service_status`、`monitoring_service_last_seen_seconds`、`monitoring_events_total` 等。
- 背景 `heartbeat_watcher`（可關閉）會在 FastAPI 啟動時自動啟動、關閉時優雅停止，定期檢查心跳是否逾時，若逾時自動標記為 down。

> ⚠️ 本服務定位為 **sidecar metrics exporter**：所有狀態與事件僅存在記憶體，重啟後即清空，並假設 Prometheus 會定期抓取 `/metrics`。如需歷史查詢/告警，請透過 Prometheus + Alertmanager/Grafana 完成，或自行實作 Webhook/persistence。

## 環境變數
`monitoring/.env.example` 已列出常用參數，可複製後調整：

| 變數 | 預設 | 說明 |
| --- | --- | --- |
| `MONITOR_HOST` | `0.0.0.0` | FastAPI 監聽位址。|
| `MONITOR_PORT` | `9400` | FastAPI 監聽 port。|
| `MONITOR_HEARTBEAT_ENABLED` | `1` | 是否啟用背景 heartbeat watcher（K8s 若交由外部監控，可關閉）。|
| `MONITOR_HEARTBEAT_TIMEOUT` | `30` | 若超過此秒數未收到心跳，Watcher 會將服務標記為 down。|
| `MONITOR_HEARTBEAT_CHECK_INTERVAL` | `5` | Watcher 檢查心跳的間隔秒數。|

> 其他設定（log level、Prometheus path 等）可透過 `uvicorn` 參數或容器 orchestrator 控制。

## 執行方式
```bash
cd monitoring
cp .env.example .env      # 複製後依需求調整 MONITOR_* 參數
pip install -r requirements.txt
set -a; source .env; set +a  # 或以其他方式載入 .env
python main.py
```

## Docker 部署

### 單一 monitoring 服務

```bash
cd monitoring
cp .env.example .env  # 視需求調整環境變數
cd deployments/monitoring-only
docker compose up --build
```

> 網路連線：compose 會將服務加入外部 `smartware_net` network，以便與 edge/integration/streaming 互通。若尚未透過 streaming 組態建立該網路，請先執行 `docker network create smartware_net`。

### Monitoring + Prometheus 堆疊

```bash
cd monitoring
cp .env.example .env
cd deployments/stack-with-prometheus
docker compose up --build
```

Prometheus 會預設在 `http://localhost:9090` 監聽，並抓取 monitoring 容器的 `/metrics`；可於 `prometheus/prometheus.yml` 與 `rules/` 內調整 scrape 頻率與告警。

## 心跳/事件 payload 範例
```bash
curl -X POST http://localhost:9400/heartbeat -H 'Content-Type: application/json' \
     -d '{"service": "edge-cam01", "phase": "edge_loop"}'

curl -X POST http://localhost:9400/events -H 'Content-Type: application/json' \
     -d '{"service": "edge-cam01", "event_type": "error", "detail": "model timeout"}'
```

- `phase` 為可選欄位，用於寫入當下 pipeline 狀態（例如 `working_phase`、`edge_loop`），方便監控端檢視服務最新狀態。
- `event_type` 可自訂（例如 `failure`、`success`、`warning`），若同時提供 `component`，會在 `monitoring_task_failures_total` / `monitoring_task_success_total` 這兩個 counter 上遞增，便於追蹤各 Task 成功/失敗次數。

API 會依 FastAPI 自動產生 OpenAPI 規格，可在啟動後拜訪 `http://<host>:<port>/docs` 或 `/redoc` 查看參數說明。

> 如果你的 workflow/Task 是使用 `smart-workflow` 套件（edge/integration 預設架構），則只要於 `.env` 或服務設定中提供 `MONITOR_ENDPOINT=http://<monitor-host>:<port>`，系統就會自動呼叫 `/heartbeat` 與 `/events` 報告狀態，開發者無需額外撰寫呼叫邏輯。其他服務若想直接整合，也可依上述 payload 範例手動呼叫。

## 與其他環境整合
- **k8s**：設定 `MONITOR_HEARTBEAT_ENABLED=0`，由 sidecar/Prometheus 負責監控，監控服務僅提供 `/events` 與 `/metrics` 接口。
- **非 k8s (如 Orin)**：保持 `heartbeat` 功能開啟，服務會自動標記超時的節點，用於通知或上游告警。

## Logging 與監控
- `main.py` 會在啟動時使用 `logging.basicConfig` 設為 `INFO` 級別，`heartbeat_watcher` 遇到超時時也會輸出 warning；若需更細節可在啟動前設定 `LOG_LEVEL` 或覆寫 `uvicorn` 的 `--log-level`。
- 推薦搭配 `deployments/stack-with-prometheus` 觀察 `/metrics`，再由 Prometheus/Alertmanager 建立告警，避免倚賴服務本身保留狀態。
