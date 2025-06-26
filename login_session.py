"""
Login session management module for ERP system
"""
import time
import logging
from typing import Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class ERPSession:
    """Manages ERP login session and authentication"""
    
    def __init__(self, base_url: str, username: str, password: str, 
                 use_selenium: bool = False, headless: bool = True):
        """
        Initialize ERP session
        
        Args:
            base_url: Base URL of ERP system
            username: Login username
            password: Login password
            use_selenium: Use Selenium instead of requests
            headless: Run Selenium in headless mode
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.use_selenium = use_selenium
        self.headless = headless
        
        self.session: Optional[requests.Session] = None
        self.driver: Optional[webdriver.Chrome] = None
        self.logged_in = False
        self.last_activity = 0
        self.session_timeout = 1800  # 30 minutes
        
    def __enter__(self):
        """Context manager entry"""
        self.login()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def create_requests_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        return session
        
    def create_selenium_driver(self) -> webdriver.Chrome:
        """Create Selenium Chrome driver"""
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        if self.headless:
            options.add_argument('--headless')
            
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Use webdriver-manager to automatically download driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        return driver
        
    def login_with_requests(self) -> bool:
        """Login using requests library"""
        try:
            self.session = self.create_requests_session()
            
            # First, get the login page to obtain any CSRF tokens
            login_page_url = f"{self.base_url}/login"
            response = self.session.get(login_page_url)
            
            # Extract CSRF token if needed (adjust based on actual ERP system)
            # csrf_token = self.extract_csrf_token(response.text)
            
            # Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password,
                # 'csrf_token': csrf_token,  # Add if needed
            }
            
            # Submit login form
            login_url = f"{self.base_url}/login"  # Adjust based on actual endpoint
            response = self.session.post(
                login_url,
                data=login_data,
                allow_redirects=True
            )
            
            # Check if login was successful
            if response.status_code == 200:
                # Look for indicators of successful login
                # This needs to be customized based on the actual ERP system
                if 'dashboard' in response.url or 'welcome' in response.text.lower():
                    logger.info("Successfully logged in with requests")
                    self.logged_in = True
                    self.last_activity = time.time()
                    return True
                    
            logger.error(f"Login failed. Status code: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error during requests login: {e}")
            return False
            
    def login_with_selenium(self) -> bool:
        """Login using Selenium WebDriver"""
        try:
            self.driver = self.create_selenium_driver()
            
            # Navigate to login page
            login_url = f"{self.base_url}/login"
            self.driver.get(login_url)
            
            # Wait for login form to load
            wait = WebDriverWait(self.driver, 10)
            
            # Find and fill username field
            username_field = wait.until(
                EC.presence_of_element_located((By.NAME, "username"))
            )
            username_field.clear()
            username_field.send_keys(self.username)
            
            # Find and fill password field
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Submit form
            submit_button = self.driver.find_element(
                By.CSS_SELECTOR, 
                "button[type='submit'], input[type='submit']"
            )
            submit_button.click()
            
            # Wait for redirect after login
            time.sleep(3)
            
            # Check if login was successful
            if 'dashboard' in self.driver.current_url or 'welcome' in self.driver.title.lower():
                logger.info("Successfully logged in with Selenium")
                self.logged_in = True
                self.last_activity = time.time()
                return True
                
            logger.error("Login failed - no redirect to dashboard")
            return False
            
        except TimeoutException:
            logger.error("Timeout waiting for login form")
            return False
        except Exception as e:
            logger.error(f"Error during Selenium login: {e}")
            return False
            
    def login(self) -> bool:
        """Perform login based on configured method"""
        if self.use_selenium:
            return self.login_with_selenium()
        else:
            return self.login_with_requests()
            
    def is_session_valid(self) -> bool:
        """Check if current session is still valid"""
        if not self.logged_in:
            return False
            
        # Check session timeout
        if time.time() - self.last_activity > self.session_timeout:
            logger.warning("Session timeout detected")
            return False
            
        return True
        
    def refresh_session(self) -> bool:
        """Refresh session if needed"""
        if not self.is_session_valid():
            logger.info("Refreshing session...")
            self.close()
            return self.login()
            
        self.last_activity = time.time()
        return True
        
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request with session"""
        if not self.refresh_session():
            raise Exception("Failed to refresh session")
            
        if self.use_selenium:
            # For Selenium, navigate to URL and return page source
            self.driver.get(url)
            # Create a mock response object
            class MockResponse:
                def __init__(self, text, url):
                    self.text = text
                    self.content = text.encode('utf-8')
                    self.url = url
                    self.status_code = 200
                    
            return MockResponse(self.driver.page_source, self.driver.current_url)
        else:
            return self.session.get(url, **kwargs)
            
    def post(self, url: str, **kwargs) -> requests.Response:
        """Make POST request with session"""
        if not self.refresh_session():
            raise Exception("Failed to refresh session")
            
        if self.use_selenium:
            raise NotImplementedError("POST requests not implemented for Selenium")
        else:
            return self.session.post(url, **kwargs)
            
    def download_file(self, url: str, save_path: str, **kwargs) -> bool:
        """Download file using session"""
        try:
            if not self.refresh_session():
                return False
                
            if self.use_selenium:
                # For Selenium, use requests with cookies from driver
                cookies = self.driver.get_cookies()
                session = self.create_requests_session()
                
                # Transfer cookies
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                    
                response = session.get(url, stream=True, **kwargs)
            else:
                response = self.session.get(url, stream=True, **kwargs)
                
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
                
            logger.error(f"Failed to download file. Status: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False
            
    def close(self):
        """Close session and cleanup resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
            
        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None
            
        self.logged_in = False 