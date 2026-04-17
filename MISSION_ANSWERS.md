Tên sinh viên: Lưu Thị Ngọc Quỳnh
Mã sinh viên: 2A202600122
Ngày: 17/04/2026

# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Các anti-pattern tìm được trong `01-localhost-vs-production/develop/app.py`

1. API key bị hardcode trong source code.
2. `DATABASE_URL` bị hardcode trong source code.
3. Các config như `DEBUG`, `MAX_TOKENS`, `PORT` không lấy từ environment variables.
4. Dùng `print()` để log thay vì structured logging.
5. Log làm lộ secret: code in cả `OPENAI_API_KEY` ra terminal.
6. Không có health check endpoint cho platform/orchestrator kiểm tra.
7. Server bind vào `localhost` nên không phù hợp khi chạy trong container/cloud.
8. Port bị cố định là `8000`.
9. `reload=True` chỉ phù hợp cho development, không nên dùng trong production.
10. Không có xử lý graceful shutdown rõ ràng.

### Exercise 1.2: Kết quả chạy basic version

- Chạy local thành công.
- Endpoint hoạt động khi gọi theo đúng kiểu mà code đang nhận:

```powershell
POST /ask?question=Hello
```

- Kết quả quan sát được là request trả về `200 OK` và JSON có field `answer`.
- Lưu ý: file lab đang gợi ý gửi JSON body, nhưng code `develop/app.py` lại nhận `question` như query parameter, nên nếu gửi body JSON nguyên văn theo lab có thể bị `422`.
- Trên Windows PowerShell cần bật UTF-8 để chữ tiếng Việt hiển thị đúng:

```powershell
chcp 65001
$env:PYTHONUTF8="1"
```

### Exercise 1.3: So sánh `basic/app.py` và `production/app.py`

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode trong code | Đọc từ environment variables | Dễ đổi giữa dev/staging/prod, an toàn hơn |
| Secrets | Lưu trực tiếp trong source | Tách khỏi code | Giảm nguy cơ lộ key khi push Git |
| Health check | Không có | Có `/health` và `/ready` | Giúp platform biết khi nào restart hoặc route traffic |
| Logging | `print()` | JSON structured logging | Dễ parse log, giám sát và debug trong production |
| Shutdown | Đột ngột | Graceful shutdown qua lifespan + SIGTERM | Tránh mất request đang xử lý |
| Host/Port | Cứng `localhost:8000` | Lấy từ config/env | Phù hợp Docker, Railway, Render |
| Debug | `reload=True` luôn bật | Chỉ bật khi `DEBUG=true` | Tránh overhead và rủi ro production |
| Validation | Gần như không có | Có check `question` rỗng, readiness flag | Ổn định hơn khi nhận request thật |

### Checkpoint 1

- [x] Hiểu tại sao hardcode secrets là nguy hiểm
- [x] Biết cách dùng environment variables
- [x] Hiểu vai trò của health check endpoint
- [x] Biết graceful shutdown là gì

---

## Part 2: Docker Containerization

### Exercise 2.1: Trả lời về `02-docker/develop/Dockerfile`

1. Base image là `python:3.11`.
2. Working directory là `/app`.
3. `COPY requirements.txt` trước để tận dụng Docker layer cache. Nếu code đổi mà dependencies không đổi thì Docker không phải cài lại toàn bộ packages.
4. `CMD` là lệnh mặc định khi container start và dễ bị override khi `docker run`. `ENTRYPOINT` cố định hơn, thường dùng khi muốn container luôn hoạt động như một executable cụ thể.

### Exercise 2.2: Build và run basic image

- Lệnh build đúng phải chạy từ project root:

```powershell
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
```

- Lệnh run:

```powershell
docker run -p 8000:8000 my-agent:develop
```

- Lưu ý thực tế của repo:
  - `02-docker/develop/app.py` nhận `question` như query parameter, không phải JSON body.
  - Test ổn định hơn bằng:

```powershell
curl.exe -X POST "http://localhost:8000/ask?question=What%20is%20Docker"
```

- Kết quả kiểm tra trên máy hiện tại:
  - Docker CLI có cài.
  - `docker build` chưa chạy được vì Docker daemon báo lỗi:

```text
Docker Desktop is unable to start
```

- Vì vậy chưa đo được image size thực tế bằng `docker images my-agent:develop`.

### Exercise 2.3: Multi-stage build trong `02-docker/production/Dockerfile`

- Stage 1 (`builder`) dùng để cài dependencies và build tools như `gcc`, `libpq-dev`.
- Stage 2 (`runtime`) chỉ copy những gì cần để chạy app:
  - packages từ builder
  - source code
  - non-root user
  - healthcheck
  - `uvicorn`

Tại sao image nhỏ hơn:

1. Dùng `python:3.11-slim` thay vì `python:3.11`.
2. Final image không chứa build tools.
3. Chỉ copy runtime artifacts thay vì toàn bộ môi trường build.

Ghi chú khi đối chiếu repo:

- `02-docker/production/Dockerfile` đang `COPY 02-docker/production/requirements.txt`, nhưng file này hiện không tồn tại trong repo.
- `02-docker/production/docker-compose.yml` cũng tham chiếu `.env.local`, nhưng file này chưa có.
- Nghĩa là phần production Docker trong repo hiện chưa chạy nguyên xi được nếu chưa bổ sung các file thiếu.

### Exercise 2.4: Docker Compose stack

Services được định nghĩa trong `02-docker/production/docker-compose.yml`:

1. `agent` - FastAPI AI agent
2. `redis` - cache/session/rate limiting
3. `qdrant` - vector database cho RAG
4. `nginx` - reverse proxy + load balancer

Architecture diagram:

```text
Client
  |
  v
Nginx
  |
  v
Agent
 |   \
 |    \
 v     v
Redis  Qdrant
```

Cách chúng communicate:

- Client chỉ gọi vào `nginx`.
- `nginx` reverse proxy request sang `agent`.
- `agent` gọi `redis` để cache/session/rate limiting.
- `agent` gọi `qdrant` để phục vụ vector search/RAG.
- Tất cả service nằm trên network nội bộ `internal`.

Kết quả xác minh:

- Chưa khởi động stack được trong môi trường hiện tại do:
  - Docker daemon chưa chạy
  - compose production còn thiếu file tham chiếu

### Checkpoint 2

- [x] Hiểu cấu trúc Dockerfile
- [x] Biết lợi ích của multi-stage builds
- [x] Hiểu Docker Compose orchestration
- [x] Biết cách debug container bằng `docker logs`, `docker exec`
- [ ] Chưa verify build/run Docker thực tế trên máy này vì Docker Desktop chưa start

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway

Phân tích từ `03-cloud-deployment/railway/app.py` và `railway.toml`:

- App đọc `PORT` từ environment variable, đúng với cách Railway inject cổng runtime.
- Health check endpoint là `/health`.
- `startCommand` là:

```text
uvicorn app:app --host 0.0.0.0 --port $PORT
```

- Railway config có:
  - `healthcheckPath = "/health"`
  - restart policy khi crash

Kết quả thực tế:

- Chưa deploy thật trong môi trường hiện tại vì cần Internet, Railway CLI login, và account cloud.
- Vì vậy chưa có public URL thật để điền.

### Exercise 3.2: So sánh `render.yaml` và `railway.toml`

| Tiêu chí | `railway.toml` | `render.yaml` |
|---------|----------------|---------------|
| Mục tiêu | Cấu hình deploy cho 1 app Railway | Infrastructure as Code cho Render |
| Build | `builder = "NIXPACKS"` hoặc Dockerfile auto-detect | `buildCommand`/`runtime` khai báo rõ |
| Start command | `startCommand` | `startCommand` |
| Health check | `healthcheckPath` | `healthCheckPath` |
| Env vars | Thường set qua CLI/dashboard | Có thể khai báo trực tiếp trong YAML |
| Multi-service | Không mô tả đầy đủ nhiều service trong file này | Có thể định nghĩa web service và Redis add-on trong cùng một file |
| Auto deploy | Chủ yếu qua Railway workflow | Có `autoDeploy: true` |

Kết luận:

- Railway đơn giản hơn cho prototype.
- Render mô tả hạ tầng chi tiết hơn, hợp với GitOps/IaC style.

### Exercise 3.3: GCP Cloud Run

`cloudbuild.yaml` mô tả CI/CD pipeline:

1. Chạy test
2. Build Docker image
3. Push image lên container registry
4. Deploy lên Cloud Run

`service.yaml` mô tả service runtime:

- `minScale: 1`, `maxScale: 10`
- `containerConcurrency: 80`
- CPU/memory limits
- env vars và secrets từ Secret Manager
- `livenessProbe` dùng `/health`
- `startupProbe` dùng `/ready`

Kết luận:

- Đây là mô hình production-grade hơn Railway/Render.
- Có CI/CD rõ ràng, secret management tốt hơn, scale control tốt hơn.

### Checkpoint 3

- [ ] Chưa deploy thành công lên platform thật trong môi trường hiện tại
- [ ] Chưa có public URL hoạt động để xác minh
- [x] Hiểu cách set environment variables trên cloud
- [x] Hiểu cách xem logs và health checks qua platform config

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

Vị trí check API key:

- Nằm trong hàm `verify_api_key()` ở `04-api-gateway/develop/app.py`.
- Header được dùng là `X-API-Key`.

Điều gì xảy ra nếu sai key:

- Không có key: trả `401 Unauthorized`
- Có key nhưng sai: trả `403 Forbidden`

Rotate key:

- Đổi giá trị `AGENT_API_KEY` trong environment variable
- Restart/redeploy service để app dùng key mới
- Không nên hardcode key trong code

Kết quả test local:

- Không có key: `401`
- Có key đúng: request thành công, nhận được `answer`

### Exercise 4.2: JWT authentication

JWT flow trong `04-api-gateway/production/auth.py`:

1. Client gửi `username/password` đến endpoint login
2. Server gọi `authenticate_user()`
3. Nếu hợp lệ, server tạo JWT qua `create_token()`
4. Client gửi token bằng header:

```text
Authorization: Bearer <token>
```

5. Protected endpoint dùng dependency `verify_token()` để:
  - decode JWT
  - kiểm tra expiry
  - lấy `username`, `role`

Lưu ý khi đối chiếu lab và code:

- Lab ghi `/token`
- Code thực tế dùng `/auth/token`

Kết quả test runtime:

- Chưa test live được vì Python environment hiện tại thiếu package `PyJWT`, nên app production của Part 4 không import được `jwt`.
- Tuy vậy flow và logic đã đọc/đối chiếu đầy đủ từ code.

### Exercise 4.3: Rate limiting

Algorithm được dùng:

- Sliding Window Counter
- Cài bằng `deque` timestamps theo từng user

Limit:

- User thường: `10 req/min`
- Admin: `100 req/min`

Bypass limit cho admin:

- Không phải bypass hoàn toàn
- Admin được route sang limiter khác là `rate_limiter_admin` với quota cao hơn

Khi hit limit:

- Trả `429 Too Many Requests`
- Có các header:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
  - `Retry-After`

### Exercise 4.4: Cost guard

Repo hiện tại có `CostGuard` trong `04-api-gateway/production/cost_guard.py` với đặc điểm:

- In-memory
- Budget theo ngày
- Có global budget và per-user budget
- Tính cost dựa trên input/output tokens

Tuy nhiên, nếu bám đúng yêu cầu trong `CODE_LAB.md` thì bài 4.4 mong muốn:

- Budget `$10/tháng mỗi user`
- Lưu trong Redis
- Reset theo tháng

Phiên bản logic đúng theo đề bài:

```python
import redis
from datetime import datetime

r = redis.Redis()

def check_budget(user_id: str, estimated_cost: float) -> bool:
    month_key = datetime.now().strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"

    current = float(r.get(key) or 0)
    if current + estimated_cost > 10:
        return False

    r.incrbyfloat(key, estimated_cost)
    r.expire(key, 32 * 24 * 3600)
    return True
```

### Checkpoint 4

- [x] Implement API key authentication
- [x] Hiểu JWT flow
- [x] Implement rate limiting
- [ ] Cost guard trong repo chưa bám đúng 100% yêu cầu Redis + monthly budget của đề

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

Trong `05-scaling-reliability/develop/app.py` đã có:

- `GET /health` cho liveness
- `GET /ready` cho readiness

Kết quả test local:

```json
{"health_status":"ok","ready":true,"uptime":3.6}
```

Ý nghĩa:

- `/health` cho biết process còn sống
- `/ready` cho biết instance đã sẵn sàng nhận traffic

### Exercise 5.2: Graceful shutdown

Cách triển khai:

1. Dùng `lifespan()` để quản lý startup/shutdown
2. Có biến `_is_ready` để dừng nhận request mới khi shutdown
3. Có middleware đếm `_in_flight_requests`
4. Khi shutdown, app chờ tối đa 30 giây cho request đang chạy xong
5. Bắt `SIGTERM` và `SIGINT`
6. `uvicorn.run(..., timeout_graceful_shutdown=30)`

Ý nghĩa:

- Khi orchestrator gửi `SIGTERM`, app không tắt đột ngột mà cố hoàn thành request đang xử lý.

### Exercise 5.3: Stateless design

Trong `05-scaling-reliability/production/app.py`:

- Session được lưu bằng `save_session()` và `load_session()`
- Nếu có Redis, dữ liệu lưu dưới key `session:{session_id}`
- Conversation history được append qua `append_to_history()`
- Có TTL mặc định 3600 giây

Tại sao đúng tinh thần stateless:

- Agent instance không phụ thuộc vào memory cục bộ của riêng nó
- Bất kỳ instance nào cũng có thể đọc tiếp session từ Redis

Lưu ý:

- Nếu Redis không có sẵn, code fallback sang in-memory store
- Fallback này chạy được để demo nhưng không scalable

### Exercise 5.4: Load balancing

Kiến trúc mong muốn trong `05-scaling-reliability/production`:

```text
Client
  |
  v
Nginx :8080
  |
  v
agent_cluster
  |
  +--> agent replica 1
  +--> agent replica 2
  +--> agent replica 3
  |
  v
Redis
```

Chi tiết:

- `nginx.conf` cấu hình `upstream agent_cluster`
- Có header `X-Served-By` để quan sát instance xử lý request
- `proxy_next_upstream` giúp chuyển request sang instance khác nếu lỗi

Nhưng khi đối chiếu repo, có 2 blocker:

1. `docker-compose.yml` tham chiếu `05-scaling-reliability/advanced/Dockerfile`, nhưng file này không tồn tại
2. `env_file: .env.local` nhưng file này cũng chưa có

Vì vậy demo scale bằng Docker Compose hiện chưa chạy nguyên xi được.

### Exercise 5.5: Test stateless

`test_stateless.py` thực hiện:

1. Tạo session mới
2. Gửi 5 requests liên tiếp
3. In `served_by` để xem request được xử lý bởi instance nào
4. Đọc lại history để chứng minh conversation vẫn còn

Kết luận mong muốn của test:

- Nếu nhiều instance cùng phục vụ mà history vẫn giữ nguyên, thiết kế stateless với Redis đang hoạt động đúng.

Kết quả thực tế:

- Chưa chạy được end-to-end vì stack Docker production của Part 5 còn lỗi tham chiếu file như đã nêu ở trên.

### Checkpoint 5

- [x] Implement health và readiness checks
- [x] Implement graceful shutdown
- [x] Refactor stateless bằng Redis-backed session storage
- [x] Hiểu load balancing với Nginx
- [ ] Chưa chạy được test stateless end-to-end do Docker/compose blocker

---

## Part 6: Final Project

### Đánh giá `06-lab-complete`

Những gì đã có trong code/config:

- `Dockerfile` multi-stage, base image slim, non-root user, `HEALTHCHECK`
- `.dockerignore`, `.env.example`, `requirements.txt`
- `app/config.py` đọc config từ environment variables
- `app/main.py` có:
  - API key authentication
  - rate limiting
  - cost guard
  - health/readiness endpoints
  - structured JSON logging
  - graceful shutdown signal handler
- Có `railway.toml` và `render.yaml`
- Code-based checker `check_production_ready.py` chạy pass `20/20`

### Kết quả chạy checker

Lệnh:

```powershell
$env:PYTHONUTF8="1"
python check_production_ready.py
```

Kết quả:

```text
Result: 20/20 checks passed (100%)
```

### Smoke test runtime thực tế

Khi chạy local, mình gặp 2 vấn đề quan trọng:

1. `06-lab-complete/app/main.py` import `utils.mock_llm`, nhưng `utils/` nằm ở repo root chứ không nằm trong `06-lab-complete`, nên chạy local trực tiếp sẽ lỗi:

```text
ModuleNotFoundError: No module named 'utils'
```

2. Sau khi thêm `PYTHONPATH` để app import được `utils`, request đến `/health` vẫn trả `500` vì middleware có dòng:

```python
response.headers.pop("server", None)
```

Trong runtime này, `MutableHeaders` không có method `pop`, nên phát sinh:

```text
AttributeError: 'MutableHeaders' object has no attribute 'pop'
```

### Đối chiếu với checklist của đề bài

| Requirement | Trạng thái | Ghi chú |
|------------|------------|---------|
| Agent trả lời qua REST API | Có | `POST /ask` |
| Support conversation history | Chưa rõ/thiếu | `06-lab-complete` chưa lưu history cho `/ask` |
| Streaming responses | Chưa có | Optional |
| Dockerized multi-stage build | Có | Dockerfile đạt yêu cầu |
| Config từ env vars | Có | `app/config.py` |
| API key authentication | Có | `X-API-Key` |
| Rate limiting | Có | Nhưng là in-memory |
| Cost guard | Có | Nhưng là global daily in-memory, chưa phải per-user monthly Redis |
| Health endpoint | Có | `/health` defined, nhưng runtime hiện lỗi middleware |
| Readiness endpoint | Có | `/ready` defined |
| Graceful shutdown | Có | `SIGTERM` + lifespan |
| Stateless design với Redis | Chưa đạt trọn vẹn | `06-lab-complete` chưa dùng Redis cho history/rate/cost |
| Structured JSON logging | Có | `logging.basicConfig(... JSON ...)` |
| Deploy Railway hoặc Render | Có config | Chưa deploy thật trong môi trường hiện tại |
| Public URL hoạt động | Chưa verify | Không có URL thật để test |
| Nginx load balancer + scale 3 agent | Chưa có trong final compose | `06-lab-complete/docker-compose.yml` chỉ có `agent + redis` |

### Kết luận cho Part 6

`06-lab-complete` là một template production-oriented khá tốt và pass toàn bộ code-based checklist, nhưng chưa bám 100% yêu cầu vận hành thực tế của đề bài vì:

1. Runtime local còn bug ở middleware headers
2. Import `utils` phụ thuộc repo root
3. Chưa có Nginx load balancer trong final compose
4. Chưa có Redis-backed stateless conversation history đúng như yêu cầu cuối bài
5. Public deployment chưa được verify

Nếu chấm theo góc nhìn code structure, project này mạnh.
Nếu chấm theo góc nhìn "chạy thật end-to-end đúng toàn bộ checklist", vẫn còn một số gap cần sửa.

---

## Tổng kết cá nhân

Sau khi đối chiếu toàn bộ `CODE_LAB.md` với repo hiện tại:

- Part 1 hoàn chỉnh và đã chạy local.
- Part 2 hiểu rõ lý thuyết, nhưng Docker runtime chưa verify được do Docker Desktop chưa start và một số file production còn thiếu.
- Part 3 đã phân tích đầy đủ config cloud, nhưng chưa deploy thật nên chưa có public URL.
- Part 4 đã xác minh được API key auth bằng runtime test; JWT/rate-limit/cost-guard được hiểu rõ từ code nhưng chưa test live hoàn toàn do thiếu dependencies trong Python env.
- Part 5 đã verify local được health/readiness; phần scale/load balancing bằng Docker còn blocker do compose tham chiếu file thiếu.
- Part 6 pass checker 20/20 nhưng runtime thực tế vẫn cần sửa để thật sự production-ready.
