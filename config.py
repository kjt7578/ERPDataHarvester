"""
Configuration management module for ERP Resume Harvester
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for managing all settings"""
    
    def __init__(self):
        # Load environment variables from .env if present
        self._load_env_file()
        
        # ERP System Configuration
        self.erp_base_url = os.getenv('ERP_BASE_URL', 'http://erp.hrcap.com')
        self.erp_username = os.getenv('ERP_USERNAME', '')
        self.erp_password = os.getenv('ERP_PASSWORD', '')
        
        # URL Patterns
        self.candidate_list_url = '/searchcandidate/dispSearchList/{page}'
        self.candidate_detail_url = '/candidate/dispView/{id}'
        self.case_list_url = '/case/dispList/{page}'
        self.case_detail_url = '/case/dispEdit/{id}'
        self.client_detail_url = '/client/dispEdit/{id}'
        self.login_url = '/mem/dispLogin'
        
        # Paths Configuration
        self.base_dir = Path(os.getenv('BASE_DIR', './Content'))
        self.resumes_dir = self.base_dir / 'Resume'
        self.metadata_dir = self.base_dir / 'metadata'
        self.results_dir = self.base_dir / 'results'
        self.logs_dir = self.base_dir / 'logs'
        
        # New folder structure
        self.jd_dir = self.base_dir / 'JD'
        self.case_dir = self.base_dir / 'case'
        self.client_dir = self.base_dir / 'client'
        
        # Metadata subdirectories
        self.metadata_case_dir = self.metadata_dir / 'case'
        self.metadata_resume_dir = self.metadata_dir / 'resume'
        
        # Scraping Configuration
        self.page_load_timeout = self._get_int_env('PAGE_LOAD_TIMEOUT', 30)
        self.download_timeout = self._get_int_env('DOWNLOAD_TIMEOUT', 60)
        self.max_retries = self._get_int_env('MAX_RETRIES', 3)
        self.retry_delay = self._get_float_env('RETRY_DELAY', 5.0)
        
        # Speed control for server protection
        self.request_delay = self._get_float_env('REQUEST_DELAY', 2.0)
        self.page_delay = self._get_float_env('PAGE_DELAY', 3.0)
        
        # Pagination
        self.items_per_page = self._get_int_env('ITEMS_PER_PAGE', 20)
        self.max_pages = self._get_int_env('MAX_PAGES', 2)
        
        # File naming - Updated to bracket format
        self.file_name_pattern = os.getenv('FILE_NAME_PATTERN', '[Resume-{id}] {name}')
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.log_format = os.getenv(
            'LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Telegram Bot (Optional)
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # MySQL Database (Optional)
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = self._get_int_env('DB_PORT', 3306)
        self.db_name = os.getenv('DB_NAME', 'erp_resumes')
        self.db_user = os.getenv('DB_USER', '')
        self.db_password = os.getenv('DB_PASSWORD', '')
        
        # Scheduler (Optional)
        self.schedule_enabled = os.getenv('SCHEDULE_ENABLED', 'false').lower() == 'true'
        self.schedule_interval_minutes = self._get_int_env('SCHEDULE_INTERVAL_MINUTES', 10)
        
        # Create directories if they don't exist
        self._create_directories()
        
    def _get_clean_env(self, key: str, default: str = '') -> str:
        """Get environment variable and remove any comments"""
        value = os.getenv(key, default)
        if value and '#' in value:
            # Remove everything after # (comment)
            value = value.split('#')[0].strip()
        return value
    
    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer environment variable with error handling"""
        try:
            value = self._get_clean_env(key, str(default))
            return int(value)
        except (ValueError, TypeError):
            logging.warning(f"Invalid integer value for {key}, using default: {default}")
            return default
    
    def _get_float_env(self, key: str, default: float) -> float:
        """Get float environment variable with error handling"""
        try:
            value = self._get_clean_env(key, str(default))
            return float(value)
        except (ValueError, TypeError):
            logging.warning(f"Invalid float value for {key}, using default: {default}")
            return default
    
    def _load_env_file(self):
        """Load environment variables from .env file if it exists"""
        env_file = Path('.env')
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            # Remove comments from value
                            if '#' in value:
                                value = value.split('#')[0].strip()
                            # Remove quotes if present
                            if value.startswith('"') and value.endswith('"'):
                                value = value[1:-1]
                            elif value.startswith("'") and value.endswith("'"):
                                value = value[1:-1]
                            os.environ[key] = value
            except Exception as e:
                logging.warning(f"Failed to load .env file: {e}")
    
    def _create_directories(self):
        """Create all necessary directories"""
        directories = [
            self.resumes_dir,
            self.metadata_dir,
            self.results_dir,
            self.logs_dir,
            # New directories
            self.jd_dir,
            self.case_dir,
            self.client_dir,
            self.metadata_case_dir,
            self.metadata_resume_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to create directory {directory}: {e}")
            
    def validate(self) -> bool:
        """Validate configuration settings"""
        errors = []
        
        if not self.erp_base_url:
            errors.append("ERP_BASE_URL is required")
            
        if not self.erp_username:
            errors.append("ERP_USERNAME is required")
            
        if not self.erp_password:
            errors.append("ERP_PASSWORD is required")
            
        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False
            
        return True
        
    def get_resume_path(self, created_date: str, filename: str) -> Path:
        """Get the full path for a resume file based on created date"""
        # Extract year and month from created_date (assuming format: YYYY-MM-DD)
        try:
            year = created_date[:4]
            month = created_date[5:7]
            return self.resumes_dir / year / month / filename
        except:
            # Fallback to current date structure
            from datetime import datetime
            now = datetime.now()
            return self.resumes_dir / str(now.year) / f"{now.month:02d}" / filename
            
    def get_metadata_path(self, filename: str, file_type: str = 'meta') -> Path:
        """Get the full path for a metadata file"""
        from file_utils import generate_metadata_filename
        
        # Generate metadata filename from base filename
        meta_filename = generate_metadata_filename(filename, file_type)
        return self.metadata_dir / meta_filename
        
    def __repr__(self):
        return f"<Config: {self.erp_base_url}>"


# Global config instance
config = Config() 