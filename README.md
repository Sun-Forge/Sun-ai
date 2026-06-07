# SUN AI - Distributed AI System

Hệ thống AI phân tán sử dụng Telegram Bot, GitHub Actions, và Ollama.

## 🏗️ Kiến Trúc

```
Telegram Bot
    ↓
VPS Gateway (Flask API)
    ↓
GitHub Actions Job
    ↓
Ollama (AI Model)
    ↓
Kết quả trả về VPS
    ↓
Telegram Bot / API Client
```

## ✨ Tính Năng

- ✅ **Telegram Bot Interface** - Menu đơn giản, dễ sử dụng
- ✅ **OpenAI Compatible API** - Hỗ trợ client OpenAI
- ✅ **Rate Limiting** - 100 requests/phút per API Key
- ✅ **Model Support** - 8 models khác nhau
- ✅ **Heartbeat System** - Giám sát trạng thái nodes
- ✅ **Usage Statistics** - Theo dõi sử dụng
- ✅ **GitHub Actions Integration** - CI/CD automation
- ✅ **Tailscale Security** - VPN private network

## 📋 Yêu Cầu

- Python 3.8+
- GitHub Account + Personal Access Token
- Telegram Bot Token
- Tailscale Account (optional)
- 8GB RAM (cho GitHub Actions runners)

## 🚀 Cài Đặt

### 1. Clone Repository

```bash
git clone https://github.com/Sun-Forge/Sun-ai.git
cd Sun-ai
```

### 2. Cài Đặt Dependencies

```bash
pip install -r requirements.txt
```

### 3. Cấu Hình Environment

Sao chép `.env.example` thành `.env` và điền thông tin:

```bash
cp .env.example .env
```

Chỉnh sửa `.env`:

```
TELEGRAM_BOT_TOKEN=your_bot_token
GITHUB_TOKEN=your_github_token
GITHUB_REPO=your_username/Sun-ai
WORKFLOW_FILE=ai.yml
GATEWAY_URL=https://your-vps-domain.ts.net
```

### 4. Tạo GitHub Secrets

Trong repository settings, thêm 2 secrets:

- `TAILSCALE_AUTH_KEY` - Tailscale authentication key
- `GATEWAY_URL` - URL của VPS Gateway

### 5. Chạy Gateway

```bash
python main.py
```

### 6. Chạy Telegram Bot

```bash
python bot.py
```

## 📁 Cấu Trúc Thư Mục

```
Sun-ai/
├── main.py                 # Flask API Gateway
├── bot.py                  # Telegram Bot
├── database.py             # SQLite Database Manager
├── github_manager.py       # GitHub Actions Manager
├── models.json             # Supported models
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables example
├── .github/
│   └── workflows/
│       └── ai.yml         # GitHub Actions Workflow
└── README.md
```

## 🔑 Models Được Hỗ Trợ

- Qwen2.5-Coder 1.5B
- Qwen2.5-Coder 3B
- Qwen2.5-Coder 7B
- Gemma 3 1B
- Gemma 3 4B
- Llama 3.2 3B
- Qwen3 8B
- Llama 3.1 8B

## 📱 Telegram Bot Commands

**Main Menu:**
- 🤖 Tạo AI - Tạo AI instance mới
- 🧠 Chọn Model - Xem danh sách models
- 📊 AI Hiện Tại - Xem AI đang chạy
- 🔑 API Của Tôi - Xem API Key
- 📜 Danh Sách AI - Xem tất cả AI instances
- 📈 Thống Kê - Usage statistics
- ⚡ Trạng Thái VPS - VPS status
- 🔄 Làm Mới - Refresh data
- ❌ Xóa AI - Xóa AI instance
- ⚙️ Cài Đặt - Settings

## 🔌 API Endpoints

### Health Check
```
GET /health
```

### Node Heartbeat
```
POST /node/update
Content-Type: application/json

{
  "chat_id": "123456",
  "run_id": "99999",
  "model": "qwen3:8b",
  "status": "online",
  "requests": 123,
  "tokens": 50000
}
```

### Chat Completions (OpenAI Compatible)
```
POST /v1/chat/completions
Authorization: Bearer SUN-XXXXXXXXXXXX
Content-Type: application/json

{
  "model": "qwen3:8b",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7,
  "max_tokens": 100
}
```

### Get All Nodes
```
GET /api/nodes
```

### Get Node Info
```
GET /api/nodes/<chat_id>
```

### Get Usage Stats
```
GET /api/stats/<chat_id>?hours=24
```

## 💾 Database Schema

### users
```sql
CREATE TABLE users (
  chat_id TEXT PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  created_at TIMESTAMP,
  last_active TIMESTAMP,
  active BOOLEAN
);
```

### api_keys
```sql
CREATE TABLE api_keys (
  api_key TEXT PRIMARY KEY,
  chat_id TEXT UNIQUE,
  model_id TEXT,
  run_id TEXT,
  created_at TIMESTAMP,
  active BOOLEAN
);
```

### nodes
```sql
CREATE TABLE nodes (
  id INTEGER PRIMARY KEY,
  chat_id TEXT UNIQUE,
  api_key TEXT,
  model TEXT,
  run_id TEXT,
  status TEXT,
  requests INTEGER,
  tokens INTEGER,
  last_seen TIMESTAMP,
  created_at TIMESTAMP
);
```

### usage_logs
```sql
CREATE TABLE usage_logs (
  id INTEGER PRIMARY KEY,
  chat_id TEXT,
  api_key TEXT,
  endpoint TEXT,
  method TEXT,
  status_code INTEGER,
  response_time_ms FLOAT,
  tokens_used INTEGER,
  created_at TIMESTAMP
);
```

## ⚙️ Configuration

### Rate Limiting
Default: 100 requests/minute per API Key

Chỉnh sửa trong `main.py`:
```python
RATE_LIMIT_REQUESTS = 100  # requests per minute
```

### Heartbeat Timeout
Default: 30 seconds

Nếu node không gửi heartbeat trong 30 giây, sẽ được đánh dấu offline.

Chỉnh sửa trong `main.py`:
```python
HEARTBEAT_TIMEOUT = 30  # seconds
```

## 🔒 Security

- API Keys được lưu trong SQLite (plain text)
- Khuyến cáo: Thêm encryption layer cho production
- Sử dụng HTTPS cho production
- Tailscale VPN cho private network

## 🧪 Testing

### Test Health Check
```bash
curl http://localhost:5000/health
```

### Test Node Update
```bash
curl -X POST http://localhost:5000/node/update \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "123456",
    "run_id": "99999",
    "model": "qwen3:8b",
    "status": "online",
    "requests": 100,
    "tokens": 50000
  }'
```

### Test Chat Completions
```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Authorization: Bearer SUN-XXXXXXXXXXXX" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:8b",
    "messages": [{"role": "user", "content": "Hello"}],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

## 📊 Monitoring

View all active nodes:
```bash
curl http://localhost:5000/api/nodes
```

View node statistics:
```bash
curl http://localhost:5000/api/stats/123456
```

## 🐛 Troubleshooting

### Bot không nhận message
- Kiểm tra `TELEGRAM_BOT_TOKEN` trong `.env`
- Kiểm tra bot đã được start thành công

### GitHub Actions workflow không trigger
- Kiểm tra `GITHUB_TOKEN` có đủ permissions
- Kiểm tra `WORKFLOW_FILE` tên đúng
- Kiểm tra workflow file đã được commit

### Node không kết nối
- Kiểm tra `TAILSCALE_AUTH_KEY`
- Kiểm tra `GATEWAY_URL` đúng
- Kiểm tra VPS firewall rules

### Database errors
- Xóa `sun_ai.db` để reset
- Kiểm tra file permissions

## 🔄 Deployment

### VPS Deployment (Ubuntu)

```bash
# Install Python
sudo apt update && sudo apt install python3 python3-pip -y

# Clone repo
git clone https://github.com/Sun-Forge/Sun-ai.git
cd Sun-ai

# Install dependencies
pip3 install -r requirements.txt

# Create .env
cp .env.example .env
# Edit .env with your credentials

# Run with systemd
sudo nano /etc/systemd/system/sun-ai-gateway.service
```

```ini
[Unit]
Description=SUN AI Gateway
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/Sun-ai
ExecStart=/usr/bin/python3 /home/ubuntu/Sun-ai/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Run bot
python3 bot.py &
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

## 📝 License

MIT License

## 👤 Author

Sun-Forge

## 🤝 Contributing

Pull requests accepted!

## 📞 Support

- Telegram: @sun_forge
- GitHub Issues: Sun-Forge/Sun-ai

---

**Last Updated:** 2024
**Version:** 1.0.0
