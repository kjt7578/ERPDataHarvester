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
from selenium.webdriver.common.keys import Keys

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
            
            # HRcap ERP specific login URL
            login_page_url = f"{self.base_url}/mem/dispLogin"
            
            logger.info(f"Accessing HRcap ERP login page: {login_page_url}")
            
            # Get the login page
            response = self.session.get(login_page_url)
            
            if response.status_code != 200:
                logger.error(f"Failed to access login page. Status code: {response.status_code}")
                return False
                
            logger.info(f"Successfully accessed login page")
            
            # Extract CSRF token if needed (adjust based on actual ERP system)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for any hidden form fields (CSRF tokens, etc.)
            hidden_fields = {}
            for hidden_input in soup.find_all('input', type='hidden'):
                name = hidden_input.get('name')
                value = hidden_input.get('value', '')
                if name:
                    hidden_fields[name] = value
                    logger.debug(f"Found hidden field: {name} = {value}")
                    
            # Also check for any other form inputs that might be required
            all_inputs = soup.find_all('input')
            logger.debug(f"All form inputs found: {[inp.get('name', 'unnamed') + '(' + inp.get('type', 'text') + ')' for inp in all_inputs]}")
                    
            # Prepare login data for HRcap ERP (ID/PW fields)
            login_data = {
                'ID': self.username,  # HRcap uses 'ID' field
                'PW': self.password,  # HRcap uses 'PW' field
                **hidden_fields  # Include any hidden fields
            }
            
            # Find the actual login form action
            login_form = soup.find('form')
            if login_form:
                action = login_form.get('action')
                if action:
                    if action.startswith('/'):
                        login_url = f"{self.base_url}{action}"
                    elif action.startswith('http'):
                        login_url = action
                    else:
                        login_url = f"{self.base_url}/mem/{action}"
                else:
                    # Default to login processing URL for HRcap
                    login_url = f"{self.base_url}/mem/procLogin"
            else:
                login_url = f"{self.base_url}/mem/procLogin"
                
            logger.info(f"Attempting login to: {login_url}")
            logger.debug(f"Login data fields: {list(login_data.keys())}")
            
            # Submit login form
            response = self.session.post(
                login_url,
                data=login_data,
                allow_redirects=True
            )
            
            # Check if login was successful
            if response.status_code == 200:
                # Look for indicators of successful login in HRcap ERP
                response_text = response.text.lower()
                response_url = response.url.lower()
                
                success_indicators = [
                    'candidate', 'search', 'dashboard', 'welcome', 'logout',
                    'dispSearchList', 'searchcandidate',  # HRcap specific
                    'main', 'menu', 'home'  # General success indicators
                ]
                
                # Check for login failure indicators
                failure_indicators = [
                    'login', 'error', '로그인', '실패', 'fail', 'invalid'
                ]
                
                has_success = any(indicator in response_text or indicator in response_url 
                                for indicator in success_indicators)
                has_failure = any(indicator in response_text for indicator in failure_indicators)
                
                # If we're redirected away from login page and have success indicators
                if has_success and not has_failure and '/mem/dispLogin' not in response_url:
                    logger.info("Successfully logged in with requests")
                    logger.info(f"Redirected to: {response.url}")
                    self.logged_in = True
                    self.last_activity = time.time()
                    return True
                    
            logger.error(f"Login failed. Status code: {response.status_code}")
            logger.error(f"Response URL: {response.url}")
            
            # Enhanced debugging for login failure
            response_text_lower = response.text.lower()
            
            # Check for specific error messages
            error_messages = [
                '잘못된', 'invalid', 'incorrect', 'error', '실패', 'fail',
                '아이디', 'username', 'password', '비밀번호', '로그인'
            ]
            
            found_errors = [msg for msg in error_messages if msg in response_text_lower]
            if found_errors:
                logger.error(f"Detected error keywords: {found_errors}")
            
            # Log response content for debugging (more detailed)
            if len(response.text) > 0:
                logger.debug(f"Response content preview: {response.text[:1000]}...")
                
                # Look for form fields in response (might indicate login page returned)
                if 'input' in response_text_lower and ('id' in response_text_lower or 'pw' in response_text_lower):
                    logger.warning("Response still contains login form - login likely failed")
                    
            # Check if we're still on login-related page
            if '/mem/' in response.url and ('login' in response.url.lower() or 'dispLogin' in response.url):
                logger.error("Still on login page - credentials might be incorrect")
            
            return False
            
        except Exception as e:
            logger.error(f"Error during requests login: {e}")
            return False
            
    def login_with_selenium(self) -> bool:
        """Login using Selenium WebDriver"""
        try:
            self.driver = self.create_selenium_driver()
            
            # Navigate to HRcap ERP login page
            login_url = f"{self.base_url}/mem/dispLogin"
            logger.info(f"Navigating to HRcap login page: {login_url}")
            self.driver.get(login_url)
            
            # Wait for login form to load
            wait = WebDriverWait(self.driver, 10)
            
            # Find and fill ID field (HRcap uses 'ID' field)
            try:
                username_field = wait.until(
                    EC.presence_of_element_located((By.NAME, "ID"))
                )
                logger.info("Found ID field")
            except TimeoutException:
                # Fallback to other possible field names
                try:
                    username_field = self.driver.find_element(By.NAME, "username")
                    logger.info("Found username field")
                except NoSuchElementException:
                    username_field = self.driver.find_element(By.NAME, "loginid")
                    logger.info("Found loginid field")
            
            username_field.clear()
            username_field.send_keys(self.username)
            logger.info(f"Entered username: {self.username}")
            
            # Find and fill PW field (HRcap uses 'PW' field)
            try:
                password_field = self.driver.find_element(By.NAME, "PW")
                logger.info("Found PW field")
            except NoSuchElementException:
                password_field = self.driver.find_element(By.NAME, "password")
                logger.info("Found password field")
            
            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Entered password")
            
            # Wait a moment for any JavaScript to load
            time.sleep(1)
            
            # Submit form - look for LOGIN button or submit
            try:
                submit_button = self.driver.find_element(By.XPATH, "//input[@value='LOGIN']")
                logger.info("Found LOGIN input button")
            except NoSuchElementException:
                try:
                    submit_button = self.driver.find_element(
                        By.CSS_SELECTOR, 
                        "button[type='submit'], input[type='submit']"
                    )
                    logger.info("Found submit button")
                except NoSuchElementException:
                    try:
                        # Look for any button with LOGIN text
                        submit_button = self.driver.find_element(By.XPATH, "//*[contains(text(), 'LOGIN') or contains(text(), '로그인')]")
                        logger.info("Found button with LOGIN text")
                    except NoSuchElementException:
                        # Last resort - try clicking Enter on password field
                        logger.warning("No submit button found, trying Enter key")
                        password_field.send_keys(Keys.RETURN)
                        submit_button = None
            
            if submit_button:
                submit_button.click()
                logger.info("Clicked login button")
            
            # Wait for AJAX response or redirect
            logger.info("Waiting for login response...")
            time.sleep(3)
            
            # Check current URL and page content
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            logger.info(f"Current URL after login: {current_url}")
            
            # Check for error messages in page
            if '{"message":"require id or password !!!","error":2}' in page_source:
                logger.error("HRcap ERP returned: require id or password error")
                return False
            
            # Look for other JSON error responses
            import re
            json_errors = re.findall(r'\{"message":"([^"]+)","error":\d+\}', page_source)
            if json_errors:
                logger.error(f"HRcap ERP JSON errors: {json_errors}")
                return False
            
            # Check if login was successful for HRcap ERP
            current_url_lower = current_url.lower()
            page_source_lower = page_source.lower()
            
            success_indicators = [
                'candidate', 'search', 'main', 'menu', 'logout',
                'dispSearchList', 'searchcandidate',  # HRcap specific
                'dashboard', 'home'
            ]
            
            # If we're redirected away from login page and have success indicators
            if '/mem/dispLogin' not in current_url_lower:
                if any(indicator in page_source_lower or indicator in current_url_lower for indicator in success_indicators):
                    logger.info("Successfully logged in with Selenium")
                    logger.info(f"Redirected to: {current_url}")
                    self.logged_in = True
                    self.last_activity = time.time()
                    return True
                else:
                    logger.warning("Redirected from login page but no success indicators found")
                    logger.debug(f"Page content preview: {page_source[:500]}...")
            
            logger.error(f"Login failed - still on login page: {current_url}")
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