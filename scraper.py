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
        
    def parse_candidate_detail(self, html: str, candidate_id: str) -> CandidateInfo:
        """
        Parse HRcap ERP candidate detail page to extract complete information
        
        Args:
            html: HTML content of detail page
            candidate_id: Candidate ID
            
        Returns:
            CandidateInfo object with extracted data
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Initialize with defaults
        info = {
            'candidate_id': candidate_id,
            'name': 'Unknown',
            'created_date': datetime.now().strftime('%Y-%m-%d'),
            'updated_date': datetime.now().strftime('%Y-%m-%d'),
        }
        
        # Extract candidate ID from hidden input (more reliable)
        cdd_input = soup.find('input', {'id': 'cdd'})
        if cdd_input and cdd_input.get('value'):
            info['candidate_id'] = cdd_input['value']
            
        # Extract name from h2 tag
        h2_title = soup.find('h2')
        if h2_title:
            h2_text = h2_title.get_text(strip=True)
            # Extract name from "Candidate Information - Sang Youn HAN"
            if ' - ' in h2_text:
                name = h2_text.split(' - ', 1)[1].strip()
                info['name'] = name
        
        # Extract dates from Profile Status section
        created_date = self._extract_hrcap_date(soup, 'Created')
        if created_date:
            info['created_date'] = created_date
            
        updated_date = self._extract_hrcap_date(soup, 'Last Updated')
        if updated_date:
            info['updated_date'] = updated_date
            
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
            # Find td containing the label
            td_elements = soup.find_all('td')
            for td in td_elements:
                text = td.get_text(strip=True)
                if f'{label} :' in text:
                    # Extract date from format "Created : 06/12/2025"
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                    if date_match:
                        date_str = date_match.group(1)
                        # Convert MM/DD/YYYY to YYYY-MM-DD
                        month, day, year = date_str.split('/')
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
            # Method 1: Find downloadFile button with file key
            download_buttons = soup.find_all('button', string=re.compile('Download.*RESUME', re.I))
            for button in download_buttons:
                onclick = button.get('onclick')
                if onclick and 'downloadFile' in onclick:
                    # Extract file key from downloadFile('8100a96c-91ac-90b2-9211-6c923cb7a156')
                    key_match = re.search(r"downloadFile\('([^']+)'\)", onclick)
                    if key_match:
                        file_key = key_match.group(1)
                        return f"/file/procDownload/{file_key}"
                        
            # Method 2: Find direct file links in Resume section
            resume_section = soup.find('h3', string=re.compile('Candidate Resume', re.I))
            if resume_section:
                # Find table after this header
                table = resume_section.find_next('table')
                if table:
                    # Look for file links
                    file_links = table.find_all('a', href=True)
                    for link in file_links:
                        href = link['href']
                        # Check if it's a resume file link
                        if '/html/files/' in href and any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx']):
                            return href
                            
            # Method 3: Look for any downloadFile buttons
            all_download_buttons = soup.find_all('button', string=re.compile('Download', re.I))
            for button in all_download_buttons:
                onclick = button.get('onclick')
                if onclick and 'downloadFile' in onclick:
                    key_match = re.search(r"downloadFile\('([^']+)'\)", onclick)
                    if key_match:
                        file_key = key_match.group(1)
                        return f"/file/procDownload/{file_key}"
                        
        except Exception as e:
            logger.error(f"Error finding resume URL: {e}")
            
        return None
        
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