"""
Web scraping module for extracting candidate information from ERP pages
"""
import re
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from dataclasses import dataclass, asdict
import time

logger = logging.getLogger(__name__)


@dataclass
class CandidateInfo:
    """Data class for storing candidate information"""
    candidate_id: str
    name: str
    created_date: str
    updated_date: str
    resume_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    position: Optional[str] = None
    detail_url: Optional[str] = None
    url_id: Optional[str] = None  # URL ID for reference (e.g., 65586)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class JobCaseInfo:
    """Data class for storing job case information"""
    jobcase_id: str
    job_title: str
    created_date: str
    updated_date: str
    company_name: Optional[str] = None  # CJ Foodville
    job_description: Optional[str] = None
    requirements: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    employment_type: Optional[str] = None  # Full-time, Part-time, Contract
    experience_level: Optional[str] = None
    job_status: Optional[str] = None  # Manage Hiree, Active, Closed, Draft
    posting_date: Optional[str] = None
    closing_date: Optional[str] = None
    document_url: Optional[str] = None  # Job description PDF
    detail_url: Optional[str] = None
    url_id: Optional[str] = None
    assigned_team: Optional[str] = None  # PST HQ
    drafter: Optional[str] = None  # Sean Kim
    client_id: Optional[str] = None  # 245
    candidate_ids: Optional[List[str]] = None  # Connected candidate IDs
    
    # Contract Information
    contract_type: Optional[str] = None  # Contingency
    fee_type: Optional[str] = None  # Gross
    bonus_types: Optional[str] = None  # Sign on Bonus, Performance Bonus, etc.
    fee_rate: Optional[str] = None  # Flat Rate 20%
    guarantee_days: Optional[str] = None  # Base 90 days
    candidate_ownership_period: Optional[str] = None  # 1 Year
    payment_due_days: Optional[str] = None  # 15
    contract_expiration_date: Optional[str] = None  # No
    signer_name: Optional[str] = None  # Jihyun Kwon
    signer_position_level: Optional[str] = None  # Manager / Sr. Manager
    signed_date: Optional[str] = None  # 01/12/2016
    
    # Position Details  
    job_category: Optional[str] = None  # Accounting > Accounting
    position_level: Optional[str] = None  # Manager / Sr. Manager
    responsibilities: Optional[str] = None  # supervising overall accounting matters
    responsibilities_input_tag: Optional[str] = None  # accounting manager
    responsibilities_file_attach: Optional[str] = None
    job_location: Optional[str] = None  # East rutherford, New Jersey, USA
    business_trip_frequency: Optional[str] = None  # 0 ~ 10%
    targeted_due_date: Optional[str] = None  # 06/30/2025
    
    # Job Order Information
    reason_of_hiring: Optional[str] = None  # New Position
    job_order_inquirer: Optional[str] = None  # Jia Kwon, COO
    job_order_background: Optional[str] = None  # need someone to supervise
    desire_spec: Optional[str] = None  # enough experience in every aspects
    strategy_approach: Optional[str] = None  # contact southpole accounting candidates
    important_notes: Optional[str] = None  # find someone very hungry
    additional_client_info: Optional[str] = None
    other_info: Optional[str] = None
    
    # Requirements
    education_level: Optional[str] = None  # Bachelors
    major: Optional[str] = None  # Accounting/Auditing
    language_ability: Optional[str] = None  # Bilingual
    select_languages: Optional[Dict[str, str]] = None  # English: Min 4 / Max 5
    experience_range: Optional[str] = None  # Min 10 year / Max 25 year
    relocation_supported: Optional[str] = None
    
    # Benefits
    insurance_info: Optional[str] = None
    k401_info: Optional[str] = None  # Company Support, Start Date, %
    overtime_pay: Optional[str] = None  # No
    personal_sick_days: Optional[str] = None  # 0 days
    vacation_info: Optional[Dict[str, str]] = None  # First Year, Annual Increment, Max
    other_benefits: Optional[str] = None
    benefits_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class ERPScraper:
    """Scraper for extracting data from ERP pages"""
    
    def __init__(self, base_url: str):
        """
        Initialize scraper
        
        Args:
            base_url: Base URL of ERP system
        """
        self.base_url = base_url.rstrip('/')
        
    def parse_candidate_list(self, html: str) -> List[Dict[str, str]]:
        """
        Parse candidate list page to extract basic info and detail URLs
        
        Args:
            html: HTML content of candidate list page
            
        Returns:
            List of dictionaries with candidate info
        """
        soup = BeautifulSoup(html, 'html.parser')
        candidates = []
        
        logger.info(f"HTML length: {len(html)} characters")
        logger.debug(f"HTML preview: {html[:1000]}...")
        
        # HRcap ERP specific patterns first
        hrcap_selectors = [
            'tr[onclick*="dispView"]',  # HRcap specific onclick pattern
            'tr[onclick*="candidate"]',
            'table tr:has(td)',  # Table rows with cells
            'tbody tr',
            '.candidate-row',
            'tr.candidate',
        ]
        
        candidate_rows = None
        for selector in hrcap_selectors:
            try:
                candidate_rows = soup.select(selector)
                if candidate_rows:
                    logger.info(f"Found {len(candidate_rows)} candidates using HRcap selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                
        # Fallback to general patterns
        if not candidate_rows:
            general_selectors = [
                'tr.candidate-row',
                'div.candidate-item', 
                'li.candidate',
                'tr[data-candidate-id]',
                'div[data-candidate-id]',
            ]
            
            for selector in general_selectors:
                try:
                    candidate_rows = soup.select(selector)
                    if candidate_rows:
                        logger.info(f"Found {len(candidate_rows)} candidates using general selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    
        # Last resort - find any table with data
        if not candidate_rows:
            logger.warning("No candidates found with specific selectors, trying table analysis...")
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on page")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has header + data rows
                    # Skip header row
                    data_rows = rows[1:]
                    if data_rows:
                        logger.info(f"Table {i+1} has {len(data_rows)} data rows")
                        # Check if rows contain candidate-like data
                        sample_row = data_rows[0]
                        cells = sample_row.find_all(['td', 'th'])
                        logger.info(f"Sample row has {len(cells)} cells")
                        
                        # Look for patterns that suggest candidate data
                        has_links = sample_row.find('a') is not None
                        has_onclick = sample_row.get('onclick') is not None
                        cell_texts = [cell.get_text(strip=True)[:50] for cell in cells[:5]]
                        logger.info(f"Sample row - has_links: {has_links}, has_onclick: {has_onclick}")
                        logger.info(f"Cell texts: {cell_texts}")
                        
                        if has_links or has_onclick or len(cells) >= 3:
                            candidate_rows = data_rows
                            logger.info(f"Using table {i+1} with {len(data_rows)} rows")
                            break
                            
        if not candidate_rows:
            logger.error("No candidate rows found in HTML")
            # Log more details for debugging
            all_links = soup.find_all('a', href=True)
            logger.info(f"Found {len(all_links)} links on page")
            for link in all_links[:5]:  # Show first 5 links
                logger.info(f"Link: {link.get('href')} - Text: {link.get_text(strip=True)[:50]}")
            return candidates
            
        logger.info(f"Processing {len(candidate_rows)} candidate rows")
        for i, row in enumerate(candidate_rows):
            try:
                candidate = self.extract_candidate_from_row(row)
                if candidate:
                    candidates.append(candidate)
                    logger.debug(f"Extracted candidate {i+1}: {candidate.get('candidate_id', 'unknown')} - {candidate.get('name', 'unknown')}")
                else:
                    logger.debug(f"Failed to extract candidate from row {i+1}")
            except Exception as e:
                logger.error(f"Error parsing candidate row {i+1}: {e}")
                
        logger.info(f"Successfully extracted {len(candidates)} candidates")
        return candidates
        
    def extract_candidate_from_row(self, row) -> Optional[Dict[str, str]]:
        """
        Extract candidate information from a single row/element
        
        Args:
            row: BeautifulSoup element containing candidate data
            
        Returns:
            Dictionary with candidate info or None
        """
        candidate = {}
        
        # Try to extract ID
        candidate_id = None
        
        # Method 1: From data attribute
        if row.get('data-candidate-id'):
            candidate_id = row.get('data-candidate-id')
        
        # Method 2: From link
        if not candidate_id:
            link = row.find('a', href=True)
            if link:
                href = link['href']
                # Extract ID from URL patterns like /candidate/12345 or ?id=12345
                id_match = re.search(r'/dispView/(\d+)', href)
                if id_match:
                    candidate_id = id_match.group(1)
                    
        # Method 3: From text content
        if not candidate_id:
            id_cell = row.find(text=re.compile(r'^\d{5,}$'))
            if id_cell:
                candidate_id = id_cell.strip()
                
        if not candidate_id:
            return None
            
        candidate['candidate_id'] = candidate_id
        
        # Extract name
        name = None
        name_patterns = [
            row.find('td', class_='name'),
            row.find('span', class_='candidate-name'),
            row.find('a', class_='name-link'),
        ]
        
        for element in name_patterns:
            if element:
                name = element.get_text(strip=True)
                break
                
        if not name:
            # Try to find name in link text
            links = row.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                if text and not text.isdigit() and len(text) > 2:
                    name = text
                    break
                    
        candidate['name'] = name or 'Unknown'
        
        # Extract detail URL
        detail_link = row.find('a', href=True)
        if detail_link:
            candidate['detail_url'] = urljoin(self.base_url, detail_link['href'])
            
        # Try to extract dates if available in list view
        date_cells = row.find_all('td')
        for cell in date_cells:
            text = cell.get_text(strip=True)
            if re.match(r'\d{4}-\d{2}-\d{2}', text):
                if 'created_date' not in candidate:
                    candidate['created_date'] = text
                else:
                    candidate['updated_date'] = text
                    
        return candidate
        
    def parse_candidate_detail(self, html: str, candidate_id: str, raw_html: Optional[str] = None, detail_url: Optional[str] = None) -> CandidateInfo:
        """
        Parse HRcap ERP candidate detail page to extract complete information
        
        Args:
            html: HTML content of detail page
            candidate_id: Candidate ID
            
        Returns:
            CandidateInfo object with extracted data
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize with defaults (use URL ID as fallback)
        url_id = candidate_id  # Keep URL ID as backup
        info = {
            'candidate_id': candidate_id,
            'name': 'Unknown',
            'created_date': datetime.now().strftime('%Y-%m-%d'),
            'updated_date': datetime.now().strftime('%Y-%m-%d'),
            'detail_url': detail_url,  # Add detail URL to info
        }
        
        # Extract REAL candidate ID from HTML (multiple methods)
        real_candidate_id = None
        
        # Method 1: From table with "Candidate ID" header
        try:
            # Find th containing "Candidate ID"
            th_elements = soup.find_all('th')
            for th in th_elements:
                if 'Candidate ID' in th.get_text(strip=True):
                    # Find the corresponding td
                    td = th.find_next_sibling('td')
                    if td:
                        real_candidate_id = td.get_text(strip=True)
                        logger.info(f"Found real Candidate ID: {real_candidate_id} (URL ID: {url_id})")
                        break
        except Exception as e:
            logger.debug(f"Method 1 failed: {e}")
        
        # Method 2: From hidden input with id='cdd'
        if not real_candidate_id:
            try:
                cdd_input = soup.find('input', {'id': 'cdd'})
                if cdd_input and cdd_input.get('value'):
                    real_candidate_id = cdd_input['value']
                    logger.info(f"Found Candidate ID from input: {real_candidate_id}")
            except Exception as e:
                logger.debug(f"Method 2 failed: {e}")
        
        # Method 3: Search for pattern in all table cells
        if not real_candidate_id:
            try:
                td_elements = soup.find_all('td')
                for td in td_elements:
                    text = td.get_text(strip=True)
                    # Look for numeric ID that's different from URL ID
                    if text.isdigit() and len(text) >= 6 and text != url_id:
                        # Check if previous th contains "ID" or similar
                        prev_th = td.find_previous_sibling('th')
                        if prev_th and 'id' in prev_th.get_text(strip=True).lower():
                            real_candidate_id = text
                            logger.info(f"Found Candidate ID from pattern: {real_candidate_id}")
                            break
            except Exception as e:
                logger.debug(f"Method 3 failed: {e}")
        
        # Use real candidate ID if found
        if real_candidate_id:
            info['candidate_id'] = real_candidate_id
            # Store URL ID as additional field for reference
            info['url_id'] = url_id
        else:
            logger.warning(f"Could not find real Candidate ID, using URL ID: {url_id}")
            info['candidate_id'] = url_id
        
        # Extract name from h2 tag
        h2_title = soup.find('h2')
        if h2_title:
            h2_text = h2_title.get_text(strip=True)
            # Extract name from "Candidate Information - Meghan Lee"
            if ' - ' in h2_text:
                name = h2_text.split(' - ', 1)[1].strip()
                info['name'] = name
            else:
                # Fallback: just use the text after "Candidate Information"
                name_part = h2_text.replace('Candidate Information', '').strip()
                if name_part:
                    info['name'] = name_part.lstrip(' -').strip()
                    
        # Also try to extract name from document title (backup method)
        if info['name'] == 'Unknown':
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                # Extract from "Meghan Lee : HRCap"
                if ' : ' in title_text:
                    name = title_text.split(' : ')[0].strip()
                    if name and name != 'HRCap':
                        info['name'] = name
                        
        # Method 3: Try to find name in Contact Information table
        if info['name'] == 'Unknown':
            try:
                # Look for Contact Information section
                contact_section = soup.find('h3', string=re.compile('Contact Information', re.I))
                if contact_section:
                    table = contact_section.find_next('table')
                    if table:
                        rows = table.find_all('tr')
                        for row in rows:
                            th = row.find('th')
                            td = row.find('td')
                            if th and td:
                                header = th.get_text(strip=True)
                                value = td.get_text(strip=True)
                                if 'name' in header.lower() and value:
                                    info['name'] = value
                                    logger.info(f"Found name from Contact table: {value}")
                                    break
            except Exception as e:
                logger.debug(f"Contact name extraction failed: {e}")
                
        # Method 4: Try to find name from any table cell that looks like a name
        if info['name'] == 'Unknown':
            try:
                # Look for patterns like "Name: John Doe" in any td
                td_elements = soup.find_all('td')
                for td in td_elements:
                    text = td.get_text(strip=True)
                    # Pattern: "Name: John Doe" or "Name : John Doe"
                    name_match = re.search(r'Name\s*[:]\s*(.+)', text, re.I)
                    if name_match:
                        name = name_match.group(1).strip()
                        if name and len(name) > 1:
                            info['name'] = name
                            logger.info(f"Found name from table pattern: {name}")
                            break
            except Exception as e:
                logger.debug(f"Pattern name extraction failed: {e}")
                
        # Method 5: Try to extract from page content (last resort)
        if info['name'] == 'Unknown':
            try:
                # Look for common Korean/English name patterns in the page
                page_text = soup.get_text()
                # Pattern for Korean names (3-4 characters)
                korean_name_match = re.search(r'[가-힣]{2,4}\s*(?:님|씨|후보자|지원자)?', page_text)
                if korean_name_match:
                    name = korean_name_match.group(0).replace('님', '').replace('씨', '').replace('후보자', '').replace('지원자', '').strip()
                    if len(name) >= 2:
                        info['name'] = name
                        logger.info(f"Found Korean name pattern: {name}")
                else:
                    # Pattern for English names (First Last)
                    english_name_match = re.search(r'\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b', page_text)
                    if english_name_match:
                        name = f"{english_name_match.group(1)} {english_name_match.group(2)}"
                        info['name'] = name
                        logger.info(f"Found English name pattern: {name}")
            except Exception as e:
                logger.debug(f"Content name extraction failed: {e}")
                
        # Log if still unknown
        if info['name'] == 'Unknown':
            logger.warning(f"Could not extract name for candidate {info['candidate_id']}, page might be empty or have different structure")
        
        # Extract dates from Profile Status section using raw HTML if available
        raw_soup = BeautifulSoup(raw_html, 'html.parser') if raw_html else soup
        
        # Debug: log raw HTML content for date extraction
        if raw_html:
            logger.debug(f"Raw HTML available: {len(raw_html)} characters")
            # Find and log date-related content in raw HTML
            raw_date_elements = raw_soup.find_all('td')
            for td in raw_date_elements:
                text = td.get_text(strip=True)
                if 'Created' in text or 'Last Updated' in text:
                    logger.debug(f"Raw HTML date element: {text}")
        else:
            logger.debug("No raw HTML available, using rendered HTML")
        
        created_date = self._extract_hrcap_date(raw_soup, 'Created')
        if created_date:
            info['created_date'] = created_date
            logger.info(f"✅ Extracted created date from raw HTML: {created_date}")
        else:
            # Fallback to rendered HTML
            created_date = self._extract_hrcap_date(soup, 'Created')
            if created_date:
                info['created_date'] = created_date
                logger.warning(f"⚠️ Used rendered HTML for created date: {created_date}")
            else:
                logger.error(f"❌ Failed to extract created date from both raw and rendered HTML")
            
        updated_date = self._extract_hrcap_date(raw_soup, 'Last Updated')
        if updated_date:
            info['updated_date'] = updated_date
            logger.info(f"✅ Extracted updated date from raw HTML: {updated_date}")
        else:
            # Fallback to rendered HTML
            updated_date = self._extract_hrcap_date(soup, 'Last Updated')
            if updated_date:
                info['updated_date'] = updated_date
                logger.warning(f"⚠️ Used rendered HTML for updated date: {updated_date}")
            else:
                logger.error(f"❌ Failed to extract updated date from both raw and rendered HTML")
            
        # Extract contact information from Contact Information table
        contact_info = self._extract_hrcap_contact_info(soup)
        info.update(contact_info)
        
        # Extract resume URL
        resume_url = self._find_hrcap_resume_url(soup)
        if resume_url:
            info['resume_url'] = urljoin(self.base_url, resume_url)
            
        # Extract additional fields from Qualification section
        qualification_info = self._extract_hrcap_qualification(soup)
        info.update(qualification_info)
        
        return CandidateInfo(**info)
        
    def _extract_hrcap_date(self, soup: BeautifulSoup, label: str) -> Optional[str]:
        """
        Extract date from HRcap ERP format: 'Created : 06/12/2025'
        
        Args:
            soup: BeautifulSoup object
            label: Date label ('Created' or 'Last Updated')
            
        Returns:
            Date string in YYYY-MM-DD format or None
        """
        try:
            # Find td containing the label (both with and without space)
            td_elements = soup.find_all('td')
            for td in td_elements:
                text = td.get_text(strip=True)
                # Check for both formats: "Created : 06/12/2025" and "Created: 06/12/2025"
                if f'{label}:' in text or f'{label} :' in text:
                    # Extract date from format "Created : 06/12/2025" or "Created: 06/12/2025"
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                    if date_match:
                        date_str = date_match.group(1)
                        # Convert MM/DD/YYYY to YYYY-MM-DD
                        month, day, year = date_str.split('/')
                        logger.debug(f"Date conversion: {date_str} -> {year}-{month}-{day}")
                        return f"{year}-{month}-{day}"
        except Exception as e:
            logger.error(f"Error extracting {label} date: {e}")
            
        return None
        
    def _extract_hrcap_contact_info(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """
        Extract contact information from HRcap Contact Information table
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary with contact information
        """
        contact_info = {
            'email': None,
            'phone': None,
            'position': None,
            'status': None
        }
        
        try:
            # Find Contact Information section
            contact_section = soup.find('h3', string=re.compile('Candidate Contact Information', re.I))
            if contact_section:
                # Find the table after this header
                table = contact_section.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            header = th.get_text(strip=True)
                            value = td.get_text(strip=True)
                            
                            if 'E-Mail' in header:
                                contact_info['email'] = value
                            elif 'Phone' in header:
                                contact_info['phone'] = value
                                
            # Extract position from Qualification section
            qual_section = soup.find('h3', string=re.compile('Candidate Qualification', re.I))
            if qual_section:
                table = qual_section.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            header = th.get_text(strip=True)
                            value = td.get_text(strip=True)
                            
                            if 'Current Position Title' in header:
                                contact_info['position'] = value
                                
        except Exception as e:
            logger.error(f"Error extracting contact info: {e}")
            
        return contact_info
        
    def _extract_hrcap_qualification(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """
        Extract qualification information from HRcap
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary with qualification information
        """
        qual_info = {}
        
        try:
            qual_section = soup.find('h3', string=re.compile('Candidate Qualification', re.I))
            if qual_section:
                table = qual_section.find_next('table')
                if table:
                    rows = table.find_all('tr')
                    for row in rows:
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            header = th.get_text(strip=True)
                            value = td.get_text(strip=True)
                            
                            if 'Experience Year' in header:
                                qual_info['experience'] = value
                            elif 'Work Eligibility' in header:
                                qual_info['work_eligibility'] = value
                                
        except Exception as e:
            logger.error(f"Error extracting qualification info: {e}")
            
        return qual_info
        
    def _find_hrcap_resume_url(self, soup: BeautifulSoup) -> Optional[str]:
        """
        Find resume download URL from HRcap ERP page
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Resume URL or None
        """
        try:
            # Method 1: Find downloadFile button with file key from onclick
            # <button type="button" onclick="downloadFile('f26632f3-5419-b4d4-654c-13b51e32f228');">Download</button>
            download_buttons = soup.find_all('button')
            for button in download_buttons:
                onclick = button.get('onclick')
                if onclick and 'downloadFile' in onclick:
                    # Extract file key from downloadFile('f26632f3-5419-b4d4-654c-13b51e32f228')
                    key_match = re.search(r"downloadFile\('([^']+)'\)", onclick)
                    if key_match:
                        file_key = key_match.group(1)
                        logger.info(f"Found resume file key: {file_key}")
                        return f"/file/procDownload/{file_key}"
                        
            # Method 2: Find direct PDF links in Resume section
            # <a href="http://erp.hrcap.com/html/files/f/2/f26632f3-5419-b4d4-654c-13b51e32f228.pdf" target="_blank">Meghan-Lee.pdf</a>
            pdf_links = soup.find_all('a', href=True)
            for link in pdf_links:
                href = link['href']
                if '.pdf' in href.lower() and 'files' in href:
                    # Extract file key from direct PDF URL
                    # http://erp.hrcap.com/html/files/f/2/f26632f3-5419-b4d4-654c-13b51e32f228.pdf
                    key_match = re.search(r'/files/[^/]+/[^/]+/([^/]+)\.pdf', href)
                    if key_match:
                        file_key = key_match.group(1)
                        logger.info(f"Found resume file key from PDF link: {file_key}")
                        return f"/file/procDownload/{file_key}"
                    else:
                        # Use direct PDF URL if no key found
                        logger.info(f"Found direct PDF URL: {href}")
                        return href
                        
            # Method 3: Search for any resume-related onclick with RESUME keyword
            # <button type="button" onclick="downloadFile('f26632f3-5419-b4d4-654c-13b51e32f228');">Download RESUME</button>
            all_elements = soup.find_all(attrs={'onclick': True})
            for element in all_elements:
                onclick = element.get('onclick')
                button_text = element.get_text(strip=True).upper()
                if onclick and 'downloadFile' in onclick and 'RESUME' in button_text:
                    key_match = re.search(r"downloadFile\('([^']+)'\)", onclick)
                    if key_match:
                        file_key = key_match.group(1)
                        logger.info(f"Found resume file key from RESUME button: {file_key}")
                        return f"/file/procDownload/{file_key}"
                        
            logger.warning("No resume URL found in any method")
            return None
            
        except Exception as e:
            logger.error(f"Error finding resume URL: {e}")
            return None
        
    def parse_jobcase_list(self, html: str) -> List[Dict[str, str]]:
        """
        Parse jobcase list page to extract basic info and detail URLs
        
        Args:
            html: HTML content of jobcase list page
            
        Returns:
            List of dictionaries with jobcase info
        """
        soup = BeautifulSoup(html, 'html.parser')
        jobcases = []
        
        logger.info(f"HTML length: {len(html)} characters")
        logger.debug(f"HTML preview: {html[:1000]}...")
        
        # HRcap ERP jobcase specific patterns
        jobcase_selectors = [
            'tr[onclick*="dispEdit"]',  # HRcap case edit pattern
            'tr[onclick*="case"]',
            'table tr:has(td)',  # Table rows with cells
            'tbody tr',
            '.case-row',
            'tr.case',
        ]
        
        jobcase_rows = None
        for selector in jobcase_selectors:
            try:
                jobcase_rows = soup.select(selector)
                if jobcase_rows:
                    logger.info(f"Found {len(jobcase_rows)} jobcases using selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                
        # Fallback to general patterns
        if not jobcase_rows:
            general_selectors = [
                'tr.case-row',
                'div.case-item', 
                'li.case',
                'tr[data-case-id]',
                'div[data-case-id]',
            ]
            
            for selector in general_selectors:
                try:
                    jobcase_rows = soup.select(selector)
                    if jobcase_rows:
                        logger.info(f"Found {len(jobcase_rows)} jobcases using general selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    
        # Last resort - find any table with data
        if not jobcase_rows:
            logger.warning("No jobcases found with specific selectors, trying table analysis...")
            tables = soup.find_all('table')
            logger.info(f"Found {len(tables)} tables on page")
            
            for i, table in enumerate(tables):
                rows = table.find_all('tr')
                if len(rows) > 1:  # Has header + data rows
                    data_rows = rows[1:]
                    if data_rows:
                        logger.info(f"Table {i+1} has {len(data_rows)} data rows")
                        sample_row = data_rows[0]
                        cells = sample_row.find_all(['td', 'th'])
                        logger.info(f"Sample row has {len(cells)} cells")
                        
                        has_links = sample_row.find('a') is not None
                        has_onclick = sample_row.get('onclick') is not None
                        cell_texts = [cell.get_text(strip=True)[:50] for cell in cells[:5]]
                        logger.info(f"Sample row - has_links: {has_links}, has_onclick: {has_onclick}")
                        logger.info(f"Cell texts: {cell_texts}")
                        
                        if has_links or has_onclick or len(cells) >= 3:
                            jobcase_rows = data_rows
                            logger.info(f"Using table {i+1} with {len(data_rows)} rows")
                            break
                            
        if not jobcase_rows:
            logger.error("No jobcase rows found in HTML")
            all_links = soup.find_all('a', href=True)
            logger.info(f"Found {len(all_links)} links on page")
            for link in all_links[:5]:
                logger.info(f"Link: {link.get('href')} - Text: {link.get_text(strip=True)[:50]}")
            return jobcases
            
        logger.info(f"Processing {len(jobcase_rows)} jobcase rows")
        for i, row in enumerate(jobcase_rows):
            try:
                jobcase = self.extract_jobcase_from_row(row)
                if jobcase:
                    jobcases.append(jobcase)
                    logger.debug(f"Extracted jobcase {i+1}: {jobcase.get('jobcase_id', 'unknown')} - {jobcase.get('job_title', 'unknown')}")
                else:
                    logger.debug(f"Failed to extract jobcase from row {i+1}")
            except Exception as e:
                logger.error(f"Error parsing jobcase row {i+1}: {e}")
                
        logger.info(f"Successfully extracted {len(jobcases)} jobcases")
        return jobcases
        
    def extract_jobcase_from_row(self, row) -> Optional[Dict[str, str]]:
        """
        Extract jobcase information from a single row/element
        
        Args:
            row: BeautifulSoup element containing jobcase data
            
        Returns:
            Dictionary with jobcase info or None
        """
        jobcase = {}
        
        # Try to extract ID
        jobcase_id = None
        
        # Method 1: From data attribute
        if row.get('data-case-id'):
            jobcase_id = row.get('data-case-id')
        
        # Method 2: From link
        if not jobcase_id:
            link = row.find('a', href=True)
            if link:
                href = link['href']
                # Extract ID from URL patterns like /case/dispEdit/3897
                id_match = re.search(r'/dispEdit/(\d+)', href)
                if id_match:
                    jobcase_id = id_match.group(1)
                    
        # Method 3: From text content
        if not jobcase_id:
            id_cell = row.find(text=re.compile(r'^\d{3,}$'))
            if id_cell:
                jobcase_id = id_cell.strip()
                
        if not jobcase_id:
            return None
            
        jobcase['jobcase_id'] = jobcase_id
        
        # Extract job title
        job_title = None
        title_patterns = [
            row.find('td', class_='title'),
            row.find('span', class_='case-title'),
            row.find('a', class_='title-link'),
        ]
        
        for element in title_patterns:
            if element:
                job_title = element.get_text(strip=True)
                break
                
        if not job_title:
            # Try to find title in link text
            links = row.find_all('a')
            for link in links:
                text = link.get_text(strip=True)
                if text and not text.isdigit() and len(text) > 2:
                    job_title = text
                    break
                    
        jobcase['job_title'] = job_title or 'Unknown'
        
        # Extract detail URL
        detail_link = row.find('a', href=True)
        if detail_link:
            jobcase['detail_url'] = urljoin(self.base_url, detail_link['href'])
            
        # Try to extract dates if available in list view
        date_cells = row.find_all('td')
        for cell in date_cells:
            text = cell.get_text(strip=True)
            if re.match(r'\d{4}-\d{2}-\d{2}', text):
                if 'created_date' not in jobcase:
                    jobcase['created_date'] = text
                else:
                    jobcase['updated_date'] = text
                    
        return jobcase
        
    def parse_jobcase_detail(self, html: str, jobcase_id: str) -> JobCaseInfo:
        """
        Parse HRcap ERP jobcase detail page to extract complete information
        
        Args:
            html: HTML content of detail page
            jobcase_id: JobCase URL ID (will be replaced with actual Case No)
            
        Returns:
            JobCaseInfo object with extracted data
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize with defaults
        url_id = jobcase_id  # Keep URL ID as backup
        info = {
            'jobcase_id': jobcase_id,  # Will be updated with actual Case No
            'job_title': 'Unknown',
            'created_date': datetime.now().strftime('%Y-%m-%d'),
            'updated_date': datetime.now().strftime('%Y-%m-%d'),
        }
        
        # Extract actual Case No (not URL ID)
        try:
            # Try multiple patterns for Case No
            case_patterns = ['Case No', 'Case Number', 'CaseNo', 'Case ID']
            actual_case_id = None
            
            for pattern in case_patterns:
                case_no_th = soup.find('th', string=pattern)
                if not case_no_th:
                    # Try partial match
                    case_no_th = soup.find('th', string=re.compile(pattern, re.IGNORECASE))
                    
                if case_no_th:
                    case_no_td = case_no_th.find_next_sibling('td')
                    if case_no_td:
                        actual_case_id = case_no_td.get_text(strip=True)
                        info['jobcase_id'] = actual_case_id
                        logger.info(f"Found actual Case No: {actual_case_id} (URL ID: {jobcase_id}) using pattern: {pattern}")
                        break
                        
            # If still not found, try looking for text containing case number
            if not actual_case_id:
                # Look for title that might contain case number like "Case 13897 : HRCap"
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    case_match = re.search(r'Case\s+(\d+)', title_text, re.IGNORECASE)
                    if case_match:
                        actual_case_id = case_match.group(1)
                        info['jobcase_id'] = actual_case_id
                        logger.info(f"Found actual Case No from title: {actual_case_id} (URL ID: {jobcase_id})")
                        
            if not actual_case_id:
                logger.warning(f"Case No not found in any pattern, keeping URL ID: {jobcase_id}")
                
        except Exception as e:
            logger.debug(f"Failed to extract Case No: {e}")
            logger.warning(f"Case No extraction failed, keeping URL ID: {jobcase_id}")
            
        # Extract company name from Client table row
        try:
            client_th = soup.find('th', string='Client')
            if client_th:
                client_td = client_th.find_next_sibling('td')
                if client_td:
                    info['company_name'] = client_td.get_text(strip=True)
                    logger.info(f"Found company name: {info['company_name']}")
        except Exception as e:
            logger.debug(f"Failed to extract company name: {e}")
            
        # Extract position title
        try:
            position_th = soup.find('th', string='Position Title')
            if position_th:
                position_td = position_th.find_next_sibling('td')
                if position_td:
                    info['job_title'] = position_td.get_text(strip=True)
                    logger.info(f"Found position title: {info['job_title']}")
        except Exception as e:
            logger.debug(f"Failed to extract position title: {e}")
            
        # Extract case status
        try:
            status_th = soup.find('th', string='Case Status')
            if status_th:
                status_td = status_th.find_next_sibling('td')
                if status_td:
                    info['job_status'] = status_td.get_text(strip=True)
                    logger.info(f"Found case status: {info['job_status']}")
        except Exception as e:
            logger.debug(f"Failed to extract case status: {e}")
            
        # Extract register date
        try:
            register_th = soup.find('th', string='Register Date')
            if register_th:
                register_td = register_th.find_next_sibling('td')
                if register_td:
                    date_text = register_td.get_text(strip=True)
                    # Convert MM/DD/YYYY to YYYY-MM-DD
                    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', date_text)
                    if date_match:
                        month, day, year = date_match.groups()
                        info['created_date'] = f"{year}-{month}-{day}"
                        logger.info(f"Found register date: {info['created_date']}")
        except Exception as e:
            logger.debug(f"Failed to extract register date: {e}")
            
        # Extract assigned team
        try:
            team_th = soup.find('th', string='Assigned Team')
            if team_th:
                team_td = team_th.find_next_sibling('td')
                if team_td:
                    info['assigned_team'] = team_td.get_text(strip=True)
                    logger.info(f"Found assigned team: {info['assigned_team']}")
        except Exception as e:
            logger.debug(f"Failed to extract assigned team: {e}")
            
        # Extract drafter
        try:
            drafter_th = soup.find('th', string='Drafter')
            if drafter_th:
                drafter_td = drafter_th.find_next_sibling('td')
                if drafter_td:
                    info['drafter'] = drafter_td.get_text(strip=True)
                    logger.info(f"Found drafter: {info['drafter']}")
        except Exception as e:
            logger.debug(f"Failed to extract drafter: {e}")
            
        # Extract connected candidate IDs by visiting each candidate page
        candidate_ids = []
        try:
            # Find all elements with openCandidate onclick to get URL IDs
            onclick_elements = soup.find_all(attrs={'onclick': re.compile(r'openCandidate\(\d+\)')})
            candidate_url_ids = []
            for element in onclick_elements:
                onclick = element.get('onclick')
                if onclick:
                    id_match = re.search(r'openCandidate\((\d+)\)', onclick)
                    if id_match:
                        url_candidate_id = id_match.group(1)
                        candidate_url_ids.append(url_candidate_id)
                        logger.info(f"Found candidate URL ID: {url_candidate_id}")
            
            # Visit each candidate page to get actual Candidate ID
            if hasattr(self, 'session') and self.session:
                for candidate_url_id in candidate_url_ids:
                    try:
                        candidate_url = f"{self.base_url}/candidate/dispView/{candidate_url_id}"
                        logger.info(f"Fetching candidate details from: {candidate_url}")
                        
                        response = self.session.get(candidate_url)
                        candidate_html = response.text if hasattr(response, 'text') else str(response)
                        candidate_soup = BeautifulSoup(candidate_html, 'html.parser')
                        
                        # Extract actual Candidate ID
                        candidate_id_th = candidate_soup.find('th', string='Candidate ID')
                        if candidate_id_th:
                            candidate_id_td = candidate_id_th.find_next_sibling('td')
                            if candidate_id_td:
                                actual_candidate_id = candidate_id_td.get_text(strip=True)
                                candidate_ids.append(actual_candidate_id)
                                logger.info(f"Found actual Candidate ID: {actual_candidate_id} (from URL ID: {candidate_url_id})")
                            else:
                                # Fallback to URL ID if actual ID not found
                                candidate_ids.append(candidate_url_id)
                                logger.warning(f"Candidate ID td not found, using URL ID: {candidate_url_id}")
                        else:
                            # Fallback to URL ID if actual ID not found  
                            candidate_ids.append(candidate_url_id)
                            logger.warning(f"Candidate ID th not found, using URL ID: {candidate_url_id}")
                            
                        time.sleep(1)  # Brief delay between requests
                        
                    except Exception as e:
                        logger.error(f"Failed to fetch candidate {candidate_url_id}: {e}")
                        # Fallback to URL ID if page fetch fails
                        candidate_ids.append(candidate_url_id)
            else:
                # Fallback to URL IDs if session not available
                candidate_ids = candidate_url_ids
                logger.warning("Session not available, using URL IDs for candidates")
                        
            info['candidate_ids'] = candidate_ids
            logger.info(f"Total connected candidates: {len(candidate_ids)}")
        except Exception as e:
            logger.debug(f"Failed to extract candidate IDs: {e}")
            info['candidate_ids'] = []
            
        # Extract client ID by visiting client page
        try:
            client_info_link = soup.find('a', href=re.compile(r'/client/dispEdit/\d+'))
            if client_info_link and hasattr(self, 'session') and self.session:
                client_url = urljoin(self.base_url, client_info_link['href'])
                logger.info(f"Fetching client details from: {client_url}")
                
                response = self.session.get(client_url)
                client_html = response.text if hasattr(response, 'text') else str(response)
                client_soup = BeautifulSoup(client_html, 'html.parser')
                
                # Try multiple patterns to find Client ID
                actual_client_id = None
                
                # Pattern 1: Find th with "Client Id" text
                client_id_th = client_soup.find('th', string=re.compile(r'Client\s*Id', re.I))
                if client_id_th:
                    client_id_td = client_id_th.find_next_sibling('td')
                    if client_id_td:
                        client_id_text = client_id_td.get_text(strip=True)
                        # Remove # if present
                        actual_client_id = client_id_text.replace('#', '').strip()
                        logger.info(f"Found actual Client ID (pattern 1): {actual_client_id}")
                
                # Pattern 2: Find any th containing "Client" and "Id"
                if not actual_client_id:
                    for th in client_soup.find_all('th'):
                        th_text = th.get_text(strip=True)
                        if 'client' in th_text.lower() and 'id' in th_text.lower():
                            client_id_td = th.find_next_sibling('td')
                            if client_id_td:
                                client_id_text = client_id_td.get_text(strip=True)
                                actual_client_id = client_id_text.replace('#', '').strip()
                                logger.info(f"Found actual Client ID (pattern 2): {actual_client_id} from header: {th_text}")
                                break
                
                # Pattern 3: Find in page title or main header
                if not actual_client_id:
                    # Check page title for Client ID
                    title = client_soup.find('title')
                    if title:
                        title_text = title.get_text(strip=True)
                        client_id_match = re.search(r'Client\s*Id\s*[:#]?\s*(\d+)', title_text, re.I)
                        if client_id_match:
                            actual_client_id = client_id_match.group(1)
                            logger.info(f"Found actual Client ID (pattern 3 - title): {actual_client_id}")
                    
                    # Check main headers
                    if not actual_client_id:
                        for header in client_soup.find_all(['h1', 'h2', 'h3', 'h4']):
                            header_text = header.get_text(strip=True)
                            client_id_match = re.search(r'Client\s*Id\s*[:#]?\s*(\d+)', header_text, re.I)
                            if client_id_match:
                                actual_client_id = client_id_match.group(1)
                                logger.info(f"Found actual Client ID (pattern 3 - header): {actual_client_id}")
                                break
                
                # Pattern 4: Search all text for Client ID pattern
                if not actual_client_id:
                    page_text = client_soup.get_text()
                    client_id_matches = re.findall(r'Client\s*Id\s*[:#]?\s*(\d+)', page_text, re.I)
                    if client_id_matches:
                        actual_client_id = client_id_matches[0]  # Take first match
                        logger.info(f"Found actual Client ID (pattern 4 - text search): {actual_client_id}")
                
                if actual_client_id:
                    info['client_id'] = actual_client_id
                else:
                    # Fallback to URL ID if no actual ID found
                    href = client_info_link['href']
                    client_id_match = re.search(r'/client/dispEdit/(\d+)', href)
                    if client_id_match:
                        info['client_id'] = client_id_match.group(1)
                        logger.warning(f"No actual Client ID found, using URL ID: {info['client_id']}")
                        
                time.sleep(1)  # Brief delay
                
            elif client_info_link:
                # Fallback to URL ID if session not available
                href = client_info_link['href']
                client_id_match = re.search(r'/client/dispEdit/(\d+)', href)
                if client_id_match:
                    info['client_id'] = client_id_match.group(1)
                    logger.warning(f"Session not available, using Client URL ID: {info['client_id']}")
        except Exception as e:
            logger.debug(f"Failed to extract client ID: {e}")
            
        # Extract detailed JD information
        try:
            # Contract Information
            contract_fields = {
                'contract_type': 'Contract Type',
                'fee_type': 'Fee Type', 
                'bonus_types': 'Bonus',
                'fee_rate': 'Fee Rate',
                'guarantee_days': 'Guarantee Days',
                'candidate_ownership_period': 'Candidate Ownership Period',
                'payment_due_days': 'Payment Due Days',
                'contract_expiration_date': 'Contract Expiration Date',
                'signer_name': 'Signer Name',
                'signer_position_level': 'Signer Position Level',
                'signed_date': 'Signed Date'
            }
            
            for field_key, field_label in contract_fields.items():
                try:
                    th = soup.find('th', string=field_label)
                    if th:
                        td = th.find_next_sibling('td')
                        if td:
                            value = td.get_text(strip=True)
                            if value and value.lower() not in ['', '-', 'n/a', 'none']:
                                info[field_key] = value
                                logger.debug(f"Found {field_label}: {value}")
                except Exception as e:
                    logger.debug(f"Failed to extract {field_label}: {e}")
                    
            # Position Details
            position_fields = {
                'job_category': 'Job Category',
                'position_level': 'Position Level',
                'responsibilities': 'Responsibilities', 
                'responsibilities_input_tag': 'Responsibilities Input Tag',
                'responsibilities_file_attach': 'Responsibilities File Attach',
                'job_location': 'Job Location',
                'business_trip_frequency': 'Business Trip Frequency',
                'targeted_due_date': 'Targeted Due Date'
            }
            
            for field_key, field_label in position_fields.items():
                try:
                    th = soup.find('th', string=field_label)
                    if th:
                        td = th.find_next_sibling('td')
                        if td:
                            value = td.get_text(strip=True)
                            if value and value.lower() not in ['', '-', 'n/a', 'none']:
                                info[field_key] = value
                                logger.debug(f"Found {field_label}: {value}")
                except Exception as e:
                    logger.debug(f"Failed to extract {field_label}: {e}")
                    
            # Job Order Information
            job_order_fields = {
                'reason_of_hiring': 'Reason of Hiring',
                'job_order_inquirer': 'Job Order Inquirer',
                'job_order_background': 'Job Order Background',
                'desire_spec': 'Desire Spec',
                'strategy_approach': 'Strategy Approach',
                'important_notes': 'Important Notes',
                'additional_client_info': 'Additional Client Info',
                'other_info': 'Other'
            }
            
            for field_key, field_label in job_order_fields.items():
                try:
                    th = soup.find('th', string=field_label)
                    if th:
                        td = th.find_next_sibling('td')
                        if td:
                            value = td.get_text(strip=True)
                            if value and value.lower() not in ['', '-', 'n/a', 'none']:
                                info[field_key] = value
                                logger.debug(f"Found {field_label}: {value}")
                except Exception as e:
                    logger.debug(f"Failed to extract {field_label}: {e}")
                    
            # Requirements Information
            requirements_fields = {
                'education_level': 'Education Level',
                'major': 'Major',
                'language_ability': 'Language Ability',
                'experience_range': 'Experience',
                'relocation_supported': 'Relocation Supported'
            }
            
            for field_key, field_label in requirements_fields.items():
                try:
                    th = soup.find('th', string=field_label)
                    if th:
                        td = th.find_next_sibling('td')
                        if td:
                            value = td.get_text(strip=True)
                            if value and value.lower() not in ['', '-', 'n/a', 'none']:
                                info[field_key] = value
                                logger.debug(f"Found {field_label}: {value}")
                except Exception as e:
                    logger.debug(f"Failed to extract {field_label}: {e}")
                    
            # Language Details (complex structure)
            try:
                select_languages = {}
                # Look for language entries like "English Language Level : Min 4 / Max 5"
                lang_elements = soup.find_all(text=re.compile(r'Language Level\s*:', re.I))
                for lang_text in lang_elements:
                    if isinstance(lang_text, str):
                        # Extract language name and levels
                        lang_match = re.search(r'(\w+)\s+Language Level\s*:\s*Min\s*(\d+)\s*/\s*Max\s*(\d+)', lang_text, re.I)
                        if lang_match:
                            lang_name, min_level, max_level = lang_match.groups()
                            select_languages[lang_name] = f"Min {min_level} / Max {max_level}"
                            logger.debug(f"Found language: {lang_name} = Min {min_level} / Max {max_level}")
                            
                if select_languages:
                    info['select_languages'] = select_languages
            except Exception as e:
                logger.debug(f"Failed to extract language details: {e}")
                
            # Benefits Information
            benefits_fields = {
                'insurance_info': 'Insurance',
                'k401_info': '401K',
                'overtime_pay': 'Overtime Pay',
                'personal_sick_days': 'Personal/ Sick Day',
                'other_benefits': 'Other Benefits',
                'benefits_file': 'Benefits File'
            }
            
            for field_key, field_label in benefits_fields.items():
                try:
                    th = soup.find('th', string=field_label)
                    if th:
                        td = th.find_next_sibling('td')
                        if td:
                            value = td.get_text(strip=True)
                            if value and value.lower() not in ['', '-', 'n/a', 'none']:
                                info[field_key] = value
                                logger.debug(f"Found {field_label}: {value}")
                except Exception as e:
                    logger.debug(f"Failed to extract {field_label}: {e}")
                    
            # Vacation Information (complex structure)
            try:
                vacation_info = {}
                vacation_fields = {
                    'first_year': 'First Year Vacation Days',
                    'annual_increment': 'Anuual Increment', 
                    'max_days': 'Max'
                }
                
                for key, label in vacation_fields.items():
                    th = soup.find('th', string=label)
                    if th:
                        td = th.find_next_sibling('td')
                        if td:
                            value = td.get_text(strip=True)
                            if value and value.lower() not in ['', '-', 'n/a', 'none']:
                                vacation_info[key] = value
                                
                if vacation_info:
                    info['vacation_info'] = vacation_info
                    logger.debug(f"Found vacation info: {vacation_info}")
            except Exception as e:
                logger.debug(f"Failed to extract vacation info: {e}")
                
        except Exception as e:
            logger.warning(f"Error extracting detailed JD information: {e}")
        
        # Set URL ID for reference
        info['url_id'] = jobcase_id  # Store original URL ID for reference
        
        # For JobCaseInfo compatibility, set required fields
        if 'company_name' not in info:
            info['company_name'] = 'Unknown'
        if 'assigned_team' not in info:
            info['assigned_team'] = None
        if 'drafter' not in info:
            info['drafter'] = None
        if 'client_id' not in info:
            info['client_id'] = None
            
        return JobCaseInfo(**info)

    def extract_pagination_info(self, html: str) -> Dict[str, Any]:
        """
        Extract pagination information from list page
        
        Args:
            html: HTML content
            
        Returns:
            Dictionary with pagination info
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        info = {
            'current_page': 1,
            'total_pages': 1,
            'has_next': False,
            'next_url': None
        }
        
        # Look for pagination elements
        pagination = soup.find('div', class_=re.compile('pagination|paging'))
        if not pagination:
            pagination = soup.find('ul', class_=re.compile('pagination|paging'))
            
        if pagination:
            # Current page
            current = pagination.find('li', class_='active')
            if current:
                try:
                    info['current_page'] = int(current.get_text(strip=True))
                except:
                    pass
                    
            # Next page link
            next_link = pagination.find('a', string=re.compile('next|>', re.I))
            if next_link and next_link.get('href'):
                info['has_next'] = True
                info['next_url'] = urljoin(self.base_url, next_link['href'])
                
            # Total pages
            page_links = pagination.find_all('a', string=re.compile(r'^\d+$'))
            if page_links:
                try:
                    page_numbers = [int(link.get_text(strip=True)) for link in page_links]
                    info['total_pages'] = max(page_numbers)
                except:
                    pass
                    
        return info 