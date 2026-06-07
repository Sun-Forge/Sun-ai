"""
SUN AI - Flask API Gateway
Máy chủ gateway nhận request từ Telegram Bot và chuyển tiếp đến GitHub Actions Job
"""

import os
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from database import Database
from github_manager import GitHubManager

# Load environment variables
load_dotenv()

# Khởi tạo Flask app
app = Flask(__name__)
CORS(app)

# Khởi tạo database
db = Database()

# Khởi tạo GitHub Manager
try:
    github_manager = GitHubManager()
except Exception as e:
    print(f"Warning: GitHub Manager initialization failed: {e}")
    github_manager = None

# Constants
RATE_LIMIT_REQUESTS = 100  # requests per minute
HEARTBEAT_TIMEOUT = 30  # seconds
OFFLINE_CHECK_INTERVAL = 10  # seconds

# ============ Helper Functions ============

def require_api_key(f):
    """Decorator để kiểm tra API Key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header:
            return jsonify({"error": "Missing Authorization header"}), 401
        
        # Format: "Bearer SUN-XXXXXXXXXXXX"
        try:
            auth_type, api_key = auth_header.split(" ")
            if auth_type.lower() != "bearer":
                return jsonify({"error": "Invalid Authorization type"}), 401
        except ValueError:
            return jsonify({"error": "Invalid Authorization format"}), 401
        
        # Kiểm tra API Key
        api_key_info = db.get_api_key_by_key(api_key)
        if not api_key_info:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Kiểm tra rate limit (100 requests/phút)
        request_count = db.get_requests_count(api_key, minutes=1)
        if request_count >= RATE_LIMIT_REQUESTS:
            return jsonify({
                "error": "Rate limit exceeded",
                "limit": RATE_LIMIT_REQUESTS,
                "window": "1 minute"
            }), 429
        
        # Thêm API key info vào request context
        request.api_key = api_key
        request.api_key_info = api_key_info
        request.chat_id = api_key_info["chat_id"]
        
        return f(*args, **kwargs)
    return decorated_function

def check_offline_nodes():
    """Background thread: Kiểm tra và đánh dấu nodes offline nếu heartbeat timeout"""
    while True:
        try:
            offline_nodes = db.get_offline_nodes(timeout_seconds=HEARTBEAT_TIMEOUT)
            for node in offline_nodes:
                db.update_node_status(node["chat_id"], "offline")
                print(f"Node {node['chat_id']} marked as offline")
        except Exception as e:
            print(f"Error checking offline nodes: {e}")
        
        time.sleep(OFFLINE_CHECK_INTERVAL)

# ============ Health Check ============

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "SUN AI Gateway"
    }), 200

# ============ Node Heartbeat Endpoint ============

@app.route("/node/update", methods=["POST"])
def node_update():
    """
    Node heartbeat endpoint
    Nhận heartbeat từ GitHub Actions Job
    
    Expected JSON:
    {
        "chat_id": "123456",
        "run_id": "99999",
        "model": "qwen3:8b",
        "status": "online",
        "requests": 123,
        "tokens": 50000
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        required_fields = ["chat_id", "run_id", "model", "status", "requests", "tokens"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400
        
        chat_id = data["chat_id"]
        run_id = data["run_id"]
        model = data["model"]
        status = data["status"]
        requests_count = data["requests"]
        tokens_count = data["tokens"]
        
        # Lấy API key của chat_id
        api_key_info = db.get_api_key_by_chat_id(chat_id)
        if not api_key_info:
            return jsonify({"error": "Chat ID not found"}), 404
        
        api_key = api_key_info["api_key"]
        
        # Cập nhật node
        db.upsert_node(
            chat_id=chat_id,
            api_key=api_key,
            model=model,
            run_id=run_id,
            status=status,
            requests=requests_count,
            tokens=tokens_count
        )
        
        # Cập nhật run_id nếu cần
        if api_key_info.get("run_id") != run_id:
            db.update_api_key_run_id(api_key, run_id)
        
        print(f"Node update: chat_id={chat_id}, status={status}, requests={requests_count}, tokens={tokens_count}")
        
        return jsonify({
            "status": "ok",
            "message": "Node update received"
        }), 200
    
    except Exception as e:
        print(f"Error in node_update: {e}")
        return jsonify({"error": str(e)}), 500

# ============ API Gateway - OpenAI Compatible ============

@app.route("/v1/chat/completions", methods=["POST"])
@require_api_key
def chat_completions():
    """
    OpenAI Compatible Chat Completions endpoint
    Nhận request từ client và chuyển tiếp đến GitHub Actions Job (Ollama)
    
    Expected format (OpenAI compatible):
    {
        "model": "qwen3:8b",
        "messages": [
            {"role": "user", "content": "Hello"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    }
    """
    try:
        api_key = request.api_key
        chat_id = request.chat_id
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Kiểm tra node có online không
        node = db.get_node(chat_id)
        if not node:
            return jsonify({
                "error": "No AI instance running for this chat_id",
                "chat_id": chat_id
            }), 404
        
        if node["status"] != "online":
            return jsonify({
                "error": f"AI instance is {node['status']}",
                "chat_id": chat_id,
                "status": node["status"],
                "last_seen": node["last_seen"]
            }), 503
        
        # Get node endpoint (từ Tailscale hoặc IP)
        # Trong thực tế, bạn cần lưu endpoint của mỗi node
        # Ở đây tạm thời chỉ ví dụ
        node_endpoint = os.getenv("NODE_ENDPOINT_PREFIX", "http://localhost:11434")
        
        # Chuyển tiếp request đến Ollama (trên GitHub Actions Job)
        start_time = time.time()
        try:
            response = request_ollama(node_endpoint, data)
            response_time_ms = (time.time() - start_time) * 1000
            
            # Log usage
            db.log_usage(
                chat_id=chat_id,
                api_key=api_key,
                endpoint="/v1/chat/completions",
                method="POST",
                status_code=200,
                response_time_ms=response_time_ms,
                tokens_used=response.get("usage", {}).get("completion_tokens", 0)
            )
            
            return jsonify(response), 200
        
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            db.log_usage(
                chat_id=chat_id,
                api_key=api_key,
                endpoint="/v1/chat/completions",
                method="POST",
                status_code=500,
                response_time_ms=response_time_ms
            )
            
            return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        print(f"Error in chat_completions: {e}")
        return jsonify({"error": str(e)}), 500

def request_ollama(endpoint: str, data: Dict) -> Dict:
    """
    Chuyển tiếp request đến Ollama API
    Chưa implement full, cần kết nối tới GitHub Actions Job
    """
    # TODO: Implement khi GitHub Actions Job được thiết lập
    # Tạm thời trả về dummy response
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": data.get("model", "unknown"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a test response from SUN AI Gateway"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 15,
            "total_tokens": 25
        }
    }

# ============ Management Endpoints ============

@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    """Lấy danh sách tất cả nodes"""
    try:
        nodes = db.get_all_nodes()
        return jsonify({
            "nodes": nodes,
            "count": len(nodes)
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/nodes/<chat_id>", methods=["GET"])
def get_node(chat_id):
    """Lấy thông tin node cụ thể"""
    try:
        node = db.get_node(chat_id)
        if not node:
            return jsonify({"error": "Node not found"}), 404
        
        return jsonify(node), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats/<chat_id>", methods=["GET"])
def get_stats(chat_id):
    """Lấy thống kê của chat_id"""
    try:
        hours = request.args.get("hours", 24, type=int)
        stats = db.get_usage_stats(chat_id, hours=hours)
        
        if not stats:
            return jsonify({"error": "No stats found"}), 404
        
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ Error Handlers ============

@app.errorhandler(404)
def not_found(e):
    """404 handler"""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    """500 handler"""
    return jsonify({"error": "Internal server error"}), 500

# ============ Startup ============

if __name__ == "__main__":
    # Khởi động background thread để kiểm tra offline nodes
    offline_check_thread = threading.Thread(target=check_offline_nodes, daemon=True)
    offline_check_thread.start()
    
    print("=" * 50)
    print("SUN AI - Flask API Gateway")
    print("=" * 50)
    print(f"Database: {db.db_path}")
    print(f"GitHub Workflow: {github_manager.repo_name if github_manager else 'N/A'}")
    print(f"Rate Limit: {RATE_LIMIT_REQUESTS} requests/minute")
    print(f"Heartbeat Timeout: {HEARTBEAT_TIMEOUT} seconds")
    print("=" * 50)
    
    # Chạy Flask server
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    
    app.run(host=host, port=port, debug=debug)
