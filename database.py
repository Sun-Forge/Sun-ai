"""
Database Manager for SUN AI
Quản lý SQLite database với các bảng: users, nodes, api_keys, usage_logs
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

class Database:
    def __init__(self, db_path: str = "sun_ai.db"):
        """
        Khởi tạo database
        
        Args:
            db_path: Đường dẫn tới file SQLite
        """
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Lấy kết nối tới database"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Khởi tạo các bảng nếu chưa tồn tại"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Bảng users - Lưu thông tin người dùng Telegram
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                chat_id TEXT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1
            )
        """)
        
        # Bảng api_keys - Lưu API Keys của mỗi chat_id
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                api_key TEXT PRIMARY KEY,
                chat_id TEXT NOT NULL UNIQUE,
                model_id TEXT,
                run_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id)
            )
        """)
        
        # Bảng nodes - Lưu thông tin GitHub Actions nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL UNIQUE,
                api_key TEXT NOT NULL,
                model TEXT,
                run_id TEXT,
                status TEXT DEFAULT 'offline',
                requests INTEGER DEFAULT 0,
                tokens INTEGER DEFAULT 0,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id),
                FOREIGN KEY (api_key) REFERENCES api_keys(api_key)
            )
        """)
        
        # Bảng usage_logs - Lưu log sử dụng API
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT,
                api_key TEXT,
                endpoint TEXT,
                method TEXT,
                status_code INTEGER,
                response_time_ms FLOAT,
                tokens_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_id) REFERENCES users(chat_id),
                FOREIGN KEY (api_key) REFERENCES api_keys(api_key)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ============ USERS ============
    
    def add_user(self, chat_id: str, username: str, first_name: str) -> bool:
        """Thêm người dùng mới"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO users (chat_id, username, first_name)
                VALUES (?, ?, ?)
            """, (str(chat_id), username, first_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def get_user(self, chat_id: str) -> Optional[Dict]:
        """Lấy thông tin người dùng"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT chat_id, username, first_name, created_at, last_active, active
                FROM users WHERE chat_id = ?
            """, (str(chat_id),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "chat_id": row[0],
                    "username": row[1],
                    "first_name": row[2],
                    "created_at": row[3],
                    "last_active": row[4],
                    "active": row[5]
                }
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_user_activity(self, chat_id: str):
        """Cập nhật thời gian hoạt động cuối cùng"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_active = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            """, (str(chat_id),))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating user activity: {e}")
    
    # ============ API KEYS ============
    
    def add_api_key(self, api_key: str, chat_id: str, model_id: str) -> bool:
        """Thêm API key mới"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO api_keys (api_key, chat_id, model_id)
                VALUES (?, ?, ?)
            """, (api_key, str(chat_id), model_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding API key: {e}")
            return False
    
    def get_api_key_by_key(self, api_key: str) -> Optional[Dict]:
        """Lấy thông tin API key"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT api_key, chat_id, model_id, run_id, created_at, active
                FROM api_keys WHERE api_key = ? AND active = 1
            """, (api_key,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "api_key": row[0],
                    "chat_id": row[1],
                    "model_id": row[2],
                    "run_id": row[3],
                    "created_at": row[4],
                    "active": row[5]
                }
            return None
        except Exception as e:
            print(f"Error getting API key: {e}")
            return None
    
    def get_api_key_by_chat_id(self, chat_id: str) -> Optional[Dict]:
        """Lấy API key của chat_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT api_key, chat_id, model_id, run_id, created_at, active
                FROM api_keys WHERE chat_id = ? AND active = 1
            """, (str(chat_id),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "api_key": row[0],
                    "chat_id": row[1],
                    "model_id": row[2],
                    "run_id": row[3],
                    "created_at": row[4],
                    "active": row[5]
                }
            return None
        except Exception as e:
            print(f"Error getting API key by chat_id: {e}")
            return None
    
    def update_api_key_run_id(self, api_key: str, run_id: str) -> bool:
        """Cập nhật run_id cho API key"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE api_keys SET run_id = ? WHERE api_key = ?
            """, (run_id, api_key))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating API key run_id: {e}")
            return False
    
    def deactivate_api_key(self, chat_id: str) -> bool:
        """Vô hiệu hóa API key của chat_id"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE api_keys SET active = 0 WHERE chat_id = ?
            """, (str(chat_id),))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deactivating API key: {e}")
            return False
    
    # ============ NODES ============
    
    def upsert_node(self, chat_id: str, api_key: str, model: str, run_id: str,
                   status: str, requests: int, tokens: int) -> bool:
        """Thêm hoặc cập nhật node"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Kiểm tra node đã tồn tại
            cursor.execute("SELECT id FROM nodes WHERE chat_id = ?", (str(chat_id),))
            exists = cursor.fetchone()
            
            if exists:
                cursor.execute("""
                    UPDATE nodes SET
                    api_key = ?, model = ?, run_id = ?, status = ?,
                    requests = ?, tokens = ?, last_seen = CURRENT_TIMESTAMP
                    WHERE chat_id = ?
                """, (api_key, model, run_id, status, requests, tokens, str(chat_id)))
            else:
                cursor.execute("""
                    INSERT INTO nodes (chat_id, api_key, model, run_id, status, requests, tokens)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(chat_id), api_key, model, run_id, status, requests, tokens))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error upserting node: {e}")
            return False
    
    def get_node(self, chat_id: str) -> Optional[Dict]:
        """Lấy thông tin node"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, chat_id, api_key, model, run_id, status, requests, tokens, last_seen, created_at
                FROM nodes WHERE chat_id = ?
            """, (str(chat_id),))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "chat_id": row[1],
                    "api_key": row[2],
                    "model": row[3],
                    "run_id": row[4],
                    "status": row[5],
                    "requests": row[6],
                    "tokens": row[7],
                    "last_seen": row[8],
                    "created_at": row[9]
                }
            return None
        except Exception as e:
            print(f"Error getting node: {e}")
            return None
    
    def get_all_nodes(self) -> List[Dict]:
        """Lấy tất cả nodes"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, chat_id, api_key, model, run_id, status, requests, tokens, last_seen, created_at
                FROM nodes ORDER BY last_seen DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            
            nodes = []
            for row in rows:
                nodes.append({
                    "id": row[0],
                    "chat_id": row[1],
                    "api_key": row[2],
                    "model": row[3],
                    "run_id": row[4],
                    "status": row[5],
                    "requests": row[6],
                    "tokens": row[7],
                    "last_seen": row[8],
                    "created_at": row[9]
                })
            return nodes
        except Exception as e:
            print(f"Error getting all nodes: {e}")
            return []
    
    def delete_node(self, chat_id: str) -> bool:
        """Xóa node"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM nodes WHERE chat_id = ?", (str(chat_id),))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error deleting node: {e}")
            return False
    
    def update_node_status(self, chat_id: str, status: str) -> bool:
        """Cập nhật trạng thái node"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE nodes SET status = ?, last_seen = CURRENT_TIMESTAMP
                WHERE chat_id = ?
            """, (status, str(chat_id)))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating node status: {e}")
            return False
    
    def get_offline_nodes(self, timeout_seconds: int = 30) -> List[Dict]:
        """Lấy nodes offline (timeout > 30 giây)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, chat_id, api_key, model, run_id, status, requests, tokens, last_seen, created_at
                FROM nodes
                WHERE status = 'online' AND 
                (strftime('%s', 'now') - strftime('%s', last_seen)) > ?
            """, (timeout_seconds,))
            rows = cursor.fetchall()
            conn.close()
            
            nodes = []
            for row in rows:
                nodes.append({
                    "id": row[0],
                    "chat_id": row[1],
                    "api_key": row[2],
                    "model": row[3],
                    "run_id": row[4],
                    "status": row[5],
                    "requests": row[6],
                    "tokens": row[7],
                    "last_seen": row[8],
                    "created_at": row[9]
                })
            return nodes
        except Exception as e:
            print(f"Error getting offline nodes: {e}")
            return []
    
    # ============ USAGE LOGS ============
    
    def log_usage(self, chat_id: str, api_key: str, endpoint: str, method: str,
                  status_code: int, response_time_ms: float, tokens_used: int = 0) -> bool:
        """Ghi log sử dụng API"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_logs
                (chat_id, api_key, endpoint, method, status_code, response_time_ms, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(chat_id), api_key, endpoint, method, status_code, response_time_ms, tokens_used))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging usage: {e}")
            return False
    
    def get_usage_stats(self, chat_id: str, hours: int = 24) -> Dict:
        """Lấy thống kê sử dụng trong N giờ qua"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Tổng requests
            cursor.execute("""
                SELECT COUNT(*) FROM usage_logs
                WHERE chat_id = ? AND created_at > datetime('now', '-' || ? || ' hours')
            """, (str(chat_id), hours))
            total_requests = cursor.fetchone()[0]
            
            # Tổng tokens
            cursor.execute("""
                SELECT COALESCE(SUM(tokens_used), 0) FROM usage_logs
                WHERE chat_id = ? AND created_at > datetime('now', '-' || ? || ' hours')
            """, (str(chat_id), hours))
            total_tokens = cursor.fetchone()[0]
            
            # Average response time
            cursor.execute("""
                SELECT COALESCE(AVG(response_time_ms), 0) FROM usage_logs
                WHERE chat_id = ? AND created_at > datetime('now', '-' || ? || ' hours')
            """, (str(chat_id), hours))
            avg_response_time = cursor.fetchone()[0]
            
            # Error rate
            cursor.execute("""
                SELECT COUNT(*) FROM usage_logs
                WHERE chat_id = ? AND status_code >= 400 AND
                created_at > datetime('now', '-' || ? || ' hours')
            """, (str(chat_id), hours))
            error_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "avg_response_time_ms": round(avg_response_time, 2),
                "error_count": error_count,
                "hours": hours
            }
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return {}
    
    def get_requests_count(self, api_key: str, minutes: int = 1) -> int:
        """Lấy số request trong N phút qua (cho rate limiting)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM usage_logs
                WHERE api_key = ? AND created_at > datetime('now', '-' || ? || ' minutes')
            """, (api_key, minutes))
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"Error getting requests count: {e}")
            return 0
