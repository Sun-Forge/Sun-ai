"""
GitHub Actions Manager for SUN AI
Quản lý việc trigger GitHub Actions workflow
"""

import os
import json
import string
import random
import requests
from typing import Optional, Dict
from github import Github

class GitHubManager:
    def __init__(self, token: str = None):
        """
        Khởi tạo GitHub Manager
        
        Args:
            token: GitHub Personal Access Token
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GITHUB_TOKEN không được cấu hình")
        
        self.gh = Github(self.token)
        self.repo_name = os.getenv("GITHUB_REPO", "Sun-Forge/Sun-ai")
        self.workflow_file = os.getenv("WORKFLOW_FILE", "ai.yml")
    
    @staticmethod
    def generate_api_key(chat_id: str) -> str:
        """
        Tạo API Key dạng SUN-XXXXXXXXXXXX
        
        Args:
            chat_id: Chat ID từ Telegram
            
        Returns:
            API Key mới
        """
        # Tạo 12 ký tự ngẫu nhiên
        characters = string.ascii_uppercase + string.digits
        random_part = ''.join(random.choices(characters, k=12))
        return f"SUN-{random_part}"
    
    def trigger_workflow(self, chat_id: str, model: str) -> Optional[Dict]:
        """
        Trigger GitHub Actions workflow
        
        Args:
            chat_id: Chat ID từ Telegram
            model: Model ID để chạy
            
        Returns:
            Dict chứa run_id hoặc None nếu thất bại
        """
        try:
            repo = self.gh.get_repo(self.repo_name)
            
            # Chuẩn bị inputs
            inputs = {
                "chat_id": str(chat_id),
                "model": model
            }
            
            # Trigger workflow
            workflow = repo.get_workflow(self.workflow_file)
            run = workflow.create_dispatch(ref="main", inputs=inputs)
            
            return {
                "run_id": run.id,
                "status": "requested",
                "html_url": run.html_url
            }
        except Exception as e:
            print(f"Error triggering workflow: {e}")
            return None
    
    def get_workflow_run(self, run_id: int) -> Optional[Dict]:
        """
        Lấy thông tin workflow run
        
        Args:
            run_id: ID của workflow run
            
        Returns:
            Dict chứa thông tin run hoặc None
        """
        try:
            repo = self.gh.get_repo(self.repo_name)
            run = repo.get_workflow_run(run_id)
            
            return {
                "id": run.id,
                "status": run.status,
                "conclusion": run.conclusion,
                "name": run.name,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "html_url": run.html_url
            }
        except Exception as e:
            print(f"Error getting workflow run: {e}")
            return None
    
    def cancel_workflow_run(self, run_id: int) -> bool:
        """
        Hủy workflow run
        
        Args:
            run_id: ID của workflow run
            
        Returns:
            True nếu thành công
        """
        try:
            repo = self.gh.get_repo(self.repo_name)
            run = repo.get_workflow_run(run_id)
            run.cancel()
            return True
        except Exception as e:
            print(f"Error canceling workflow run: {e}")
            return False
    
    def get_run_logs(self, run_id: int) -> Optional[str]:
        """
        Lấy logs của workflow run
        
        Args:
            run_id: ID của workflow run
            
        Returns:
            Log content hoặc None
        """
        try:
            repo = self.gh.get_repo(self.repo_name)
            run = repo.get_workflow_run(run_id)
            
            # Lấy logs zip
            logs = run.logs_url
            
            response = requests.get(logs, headers={
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3.raw"
            })
            
            if response.status_code == 200:
                return response.text
            return None
        except Exception as e:
            print(f"Error getting run logs: {e}")
            return None
    
    def check_workflow_exists(self) -> bool:
        """Kiểm tra workflow file tồn tại"""
        try:
            repo = self.gh.get_repo(self.repo_name)
            workflows = repo.get_workflows()
            
            for workflow in workflows:
                if workflow.path.endswith(self.workflow_file):
                    return True
            return False
        except Exception as e:
            print(f"Error checking workflow: {e}")
            return False
    
    def get_available_workflows(self) -> list:
        """Lấy danh sách workflows có sẵn"""
        try:
            repo = self.gh.get_repo(self.repo_name)
            workflows = repo.get_workflows()
            
            result = []
            for workflow in workflows:
                result.append({
                    "id": workflow.id,
                    "name": workflow.name,
                    "path": workflow.path,
                    "state": workflow.state
                })
            return result
        except Exception as e:
            print(f"Error getting workflows: {e}")
            return []
