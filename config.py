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
        # ERP System Configuration
        self.erp_base_url = os.getenv('ERP_BASE_URL', 'http://erp.hrcap.com')
        self.erp_username = os.getenv('ERP_USERNAME', '')
        self.erp_password = os.getenv('ERP_PASSWORD', '')
        
        # Paths Configuration
        self.resumes_dir = Path(os.getenv('RESUMES_DIR', './resumes'))
        self.metadata_dir = Path(os.getenv('METADATA_DIR', './metadata'))
        self.results_dir = Path(os.getenv('RESULTS_DIR', './results'))
        self.logs_dir = Path(os.getenv('LOGS_DIR', './logs'))
        
        # Scraping Configuration
        self.page_load_timeout = int(os.getenv('PAGE_LOAD_TIMEOUT', '30'))
        self.download_timeout = int(os.getenv('DOWNLOAD_TIMEOUT', '60'))
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('RETRY_DELAY', '5'))
        
        # Speed control for server protection
        self.request_delay = float(os.getenv('REQUEST_DELAY', '2.0'))  # 2 second delay
        self.page_delay = float(os.getenv('PAGE_DELAY', '3.0'))       # 3 second delay between pages
        
        # Pagination
        self.items_per_page = int(os.getenv('ITEMS_PER_PAGE', '20'))
        self.max_pages = int(os.getenv('MAX_PAGES', '2'))  # Limited to 2 pages for testing
        
        # File naming
        self.file_name_pattern = os.getenv('FILE_NAME_PATTERN', '{name}_{id}_resume')
        
        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'DEBUG')
        self.log_format = os.getenv(
            'LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Telegram Bot (Optional)
        self.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        
        # MySQL Database (Optional)
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', '3306'))
        self.db_name = os.getenv('DB_NAME', 'erp_resumes')
        self.db_user = os.getenv('DB_USER', '')
        self.db_password = os.getenv('DB_PASSWORD', '')
        
        # Scheduler (Optional)
        self.schedule_enabled = os.getenv('SCHEDULE_ENABLED', 'false').lower() == 'true'
        self.schedule_interval_minutes = int(os.getenv('SCHEDULE_INTERVAL_MINUTES', '10'))
        
    def create_directories(self):
        """Create all necessary directories"""
        directories = [
            self.resumes_dir,
            self.metadata_dir,
            self.results_dir,
            self.logs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
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
            
    def get_metadata_path(self, filename: str) -> Path:
        """Get the full path for a metadata file"""
        # Change extension from .pdf to .meta.json
        meta_filename = filename.replace('.pdf', '.meta.json')
        return self.metadata_dir / meta_filename
        
    def __repr__(self):
        return f"<Config: {self.erp_base_url}>"


# Global config instance
config = Config() 