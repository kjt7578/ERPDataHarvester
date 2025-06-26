"""
Example test script for ERP Resume Harvester
This script demonstrates basic functionality without actual ERP connection
"""
import json
from pathlib import Path
from datetime import datetime

from config import config
from file_utils import (
    sanitize_filename, 
    generate_filename_from_template,
    extract_date_parts,
    create_directory_structure
)
from metadata_saver import MetadataSaver
from scraper import CandidateInfo


def test_file_utils():
    """Test file utility functions"""
    print("Testing File Utils...")
    print("-" * 50)
    
    # Test filename sanitization
    test_names = [
        "John Doe",
        "김동현",
        "Test/User<>Name",
        "Very Long Name " + "X" * 200
    ]
    
    for name in test_names:
        safe_name = sanitize_filename(name)
        print(f"Original: {name[:50]}...")
        print(f"Sanitized: {safe_name}")
        print()
        
    # Test filename generation
    filename = generate_filename_from_template(
        template="{name}_{id}_resume",
        name="John Doe",
        candidate_id="12345"
    )
    print(f"Generated filename: {filename}")
    
    # Test date extraction
    dates = ["2025-01-15", "2024-12-01", "invalid-date"]
    for date in dates:
        year, month = extract_date_parts(date)
        print(f"Date: {date} -> Year: {year}, Month: {month}")
        
    print("\n" + "="*50 + "\n")


def test_metadata_saver():
    """Test metadata saving functionality"""
    print("Testing Metadata Saver...")
    print("-" * 50)
    
    # Create test directories
    test_metadata_dir = Path("test_metadata")
    test_results_dir = Path("test_results")
    
    # Initialize metadata saver
    saver = MetadataSaver(test_metadata_dir, test_results_dir)
    
    # Create test candidate data
    test_candidates = [
        {
            'candidate_id': '1001',
            'name': 'John Doe',
            'email': 'john.doe@example.com',
            'phone': '+1-234-567-8900',
            'position': 'Software Engineer',
            'status': 'Active',
            'created_date': '2025-01-01',
            'updated_date': '2025-01-15',
            'resume_url': 'https://example.com/resume1.pdf',
            'detail_url': 'https://example.com/candidate/1001'
        },
        {
            'candidate_id': '1002',
            'name': '김동현',
            'email': 'kim.donghyun@example.com',
            'phone': '010-1234-5678',
            'position': 'Data Scientist',
            'status': 'Interview',
            'created_date': '2024-12-15',
            'updated_date': '2025-01-10',
            'resume_url': 'https://example.com/resume2.pdf',
            'detail_url': 'https://example.com/candidate/1002'
        }
    ]
    
    # Save individual metadata
    for candidate in test_candidates:
        success = saver.save_candidate_metadata(candidate)
        print(f"Saved metadata for {candidate['name']}: {success}")
        
    # Save consolidated results
    saver.save_consolidated_results(test_candidates)
    print(f"\nConsolidated results saved to:")
    print(f"- JSON: {saver.candidates_json_path}")
    print(f"- CSV: {saver.candidates_csv_path}")
    
    # Clean up test directories
    import shutil
    shutil.rmtree(test_metadata_dir)
    shutil.rmtree(test_results_dir)
    
    print("\n" + "="*50 + "\n")


def test_candidate_info():
    """Test CandidateInfo dataclass"""
    print("Testing CandidateInfo...")
    print("-" * 50)
    
    # Create test candidate
    candidate = CandidateInfo(
        candidate_id="1042714",
        name="Test User",
        created_date="2025-01-01",
        updated_date="2025-01-15",
        resume_url="https://example.com/resume.pdf",
        email="test@example.com",
        phone="123-456-7890",
        status="Active",
        position="Developer"
    )
    
    # Convert to dict
    candidate_dict = candidate.to_dict()
    print("CandidateInfo as dict:")
    print(json.dumps(candidate_dict, indent=2))
    
    print("\n" + "="*50 + "\n")


def test_directory_structure():
    """Test directory structure creation"""
    print("Testing Directory Structure...")
    print("-" * 50)
    
    # Create test base directory
    test_base = Path("test_resumes")
    
    # Test creating directories for different dates
    test_dates = [
        ("2025", "01"),
        ("2025", "06"),
        ("2024", "12")
    ]
    
    for year, month in test_dates:
        dir_path = create_directory_structure(test_base, year, month)
        print(f"Created: {dir_path}")
        
    # List created structure
    print("\nDirectory structure:")
    for path in sorted(test_base.rglob("*")):
        level = len(path.relative_to(test_base).parts)
        indent = "  " * level
        print(f"{indent}{path.name}/")
        
    # Clean up
    import shutil
    shutil.rmtree(test_base)
    
    print("\n" + "="*50 + "\n")


def main():
    """Run all tests"""
    print("ERP Resume Harvester - Test Suite")
    print("=" * 50)
    print(f"Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n")
    
    # Run tests
    test_file_utils()
    test_metadata_saver()
    test_candidate_info()
    test_directory_structure()
    
    print("All tests completed!")
    print("\nNote: This is a functionality test without actual ERP connection.")
    print("To test with real ERP system, configure .env file and run main.py")


if __name__ == '__main__':
    main() 