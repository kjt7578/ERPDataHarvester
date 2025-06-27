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
    generate_resume_filename,
    generate_case_filename,
    generate_metadata_filename,
    extract_date_parts,
    create_directory_structure,
    convert_candidate_id,
    convert_case_id, 
    parse_id_range,
    predict_real_candidate_id,
    predict_url_candidate_id,
    predict_real_case_id,
    predict_url_case_id,
    parse_case_id_range
)
from metadata_saver import MetadataSaver
from scraper import CandidateInfo


def test_file_utils():
    """Test file utility functions"""
    print("Testing File Utils...")
    print("-" * 50)
    
    # Test filename sanitization with bracket format
    test_names = [
        "[Resume-1001] John Doe.pdf",
        "[Case-12345] Samsung Electronics - Software Engineer.json",
        "[Resume-1002] 김동현.pdf",
        "[Case-12346] Test/Company<>Name - Very Long Position Title " + "X" * 200
    ]
    
    for name in test_names:
        safe_name = sanitize_filename(name)
        print(f"Original: {name[:70]}...")
        print(f"Sanitized: {safe_name}")
        print()
        
    # Test new filename generation functions
    print("Testing new filename generation:")
    
    # Test resume filename generation
    resume_filename = generate_resume_filename("John Doe", "1001", "pdf")
    print(f"Resume filename: {resume_filename}")
    
    resume_filename2 = generate_resume_filename("김동현", "1002", "docx")
    print(f"Resume filename (Korean): {resume_filename2}")
    
    # Test case filename generation
    case_filename = generate_case_filename("Samsung Electronics", "Software Engineer", "12345", "json")
    print(f"Case filename: {case_filename}")
    
    case_filename2 = generate_case_filename("Very Long Company Name Inc.", "Senior Software Development Engineer Manager", "12346", "json")
    print(f"Case filename (long): {case_filename2}")
    
    # Test metadata filename generation
    meta_filename = generate_metadata_filename(resume_filename, "meta")
    print(f"Metadata filename: {meta_filename}")
    
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


def test_id_pattern_analysis():
    """Test URL ID to Real Candidate ID pattern analysis"""
    print("Testing ID Pattern Analysis...")
    print("-" * 50)
    
    # Known mappings from existing data
    known_mappings = [
        {"url_id": 65586, "real_id": 1044760, "name": "Meghan Lee"},
        {"url_id": 64853, "real_id": 1044027, "name": "Candidate A"},
        {"url_id": 64879, "real_id": 1044053, "name": "Candidate B"},
    ]
    
    print("Known URL ID → Real ID mappings:")
    differences = []
    
    for mapping in known_mappings:
        url_id = mapping["url_id"]
        real_id = mapping["real_id"]
        name = mapping["name"]
        difference = real_id - url_id
        differences.append(difference)
        
        print(f"  {name}:")
        print(f"    URL ID: {url_id}")
        print(f"    Real ID: {real_id}")
        print(f"    Difference: {difference}")
        print()
    
    # Analyze pattern
    print("Pattern Analysis:")
    print(f"  Differences: {differences}")
    
    if len(set(differences)) == 1:
        offset = differences[0]
        print(f"  🎯 PATTERN FOUND: Real ID = URL ID + {offset}")
        
        # Test the pattern with new predictions
        test_cases = [65580, 65581, 65582, 65583, 65584, 65585]
        print(f"\n  Predicted mappings using offset {offset}:")
        
        for url_id in test_cases:
            predicted_real_id = url_id + offset
            print(f"    URL {url_id} → Real ID {predicted_real_id}")
            
    else:
        print("  ❌ NO CONSISTENT PATTERN FOUND")
        print(f"  Differences vary: {set(differences)}")
        
    print("\n" + "="*50 + "\n")


def test_reverse_id_calculation():
    """Test reverse calculation: Real ID to URL ID"""
    print("Testing Reverse ID Calculation...")
    print("-" * 50)
    
    offset = 979174  # From pattern analysis
    
    # If we know real IDs, what would be the URL IDs?
    real_ids = [1044760, 1044761, 1044762, 1044763, 1044764, 1044765]
    
    print(f"Using offset {offset} (Real ID - URL ID = {offset})")
    print("Real ID → Predicted URL ID:")
    
    for real_id in real_ids:
        predicted_url_id = real_id - offset
        print(f"  Real ID {real_id} → URL ID {predicted_url_id}")
        
    print("\n" + "="*50 + "\n")


def test_new_id_conversion_features():
    """Test the new ID conversion and range parsing features"""
    print("Testing New ID Conversion Features...")
    print("-" * 50)
    
    # Test individual ID conversion
    print("1. Individual ID Conversion:")
    
    # Test URL ID conversion
    url_id = "65586"
    result = convert_candidate_id(url_id, 'url')
    print(f"  URL ID {url_id} → URL: {result['url_id']}, Real: {result['real_id']}")
    
    # Test Real ID conversion  
    real_id = "1044760"
    result = convert_candidate_id(real_id, 'real')
    print(f"  Real ID {real_id} → URL: {result['url_id']}, Real: {result['real_id']}")
    
    # Test auto-detection
    test_ids = ["65586", "1044760", "67000"]
    for test_id in test_ids:
        result = convert_candidate_id(test_id, 'auto')
        print(f"  Auto-detect {test_id} → URL: {result['url_id']}, Real: {result['real_id']}")
    
    print()
    
    # Test range parsing
    print("2. Range Parsing:")
    
    # URL ID ranges
    url_ranges = ["65585-65580", "65580,65581,65582"]
    for range_str in url_ranges:
        try:
            ids = parse_id_range(range_str, 'url')
            print(f"  URL range '{range_str}' → {ids}")
        except ValueError as e:
            print(f"  Error parsing '{range_str}': {e}")
    
    # Real ID ranges  
    real_ranges = ["1044759-1044754", "1044754,1044755,1044756"]
    for range_str in real_ranges:
        try:
            ids = parse_id_range(range_str, 'real')
            print(f"  Real range '{range_str}' → converted to URL IDs: {ids}")
        except ValueError as e:
            print(f"  Error parsing '{range_str}': {e}")
    
    print()
    
    # Test case ID conversion (currently same ID)
    print("3. Case ID Conversion:")
    case_id = "12345"
    case_result = convert_case_id(case_id, 'auto')
    print(f"  Case ID {case_id} → URL: {case_result['url_id']}, Real: {case_result['real_id']}")
    
    print()
    
    # Test command line examples
    print("4. Command Line Usage Examples:")
    print("  # URL ID (traditional)")
    print("  python main.py --type candidate --id 65586")
    print("  python main.py --type candidate --range '65585-65580'")
    print()
    print("  # Real ID (new feature)")
    print("  python main.py --type candidate --id 1044760 --id-type real")
    print("  python main.py --type candidate --range '1044759-1044754' --id-type real")
    print()
    print("  # Auto-detection")
    print("  python main.py --type candidate --id 1044760 --id-type auto")
    print("  python main.py --type candidate --range '65585-65580' --id-type auto")
    
    print("\n" + "="*50 + "\n")


def test_case_id_pattern_analysis():
    """Test Case ID pattern analysis - Pattern DISCOVERED!"""
    print("Testing Case ID Pattern Analysis...")
    print("-" * 50)
    
    # Import the new functions
    from file_utils import (
        convert_case_id,
        predict_real_case_id,
        predict_url_case_id,
        parse_case_id_range
    )
    
    print("✅ Case ID Pattern DISCOVERED!")
    print("  패턴: Real Case ID = URL ID + 10,000")
    print("  검증: 7개 샘플 100% 일치")
    print()
    
    # Test individual Case ID conversion
    print("1. Individual Case ID Conversion:")
    
    # Test URL ID conversion
    url_id = "3897"
    result = convert_case_id(url_id, 'url')
    print(f"  URL ID {url_id} → URL: {result['url_id']}, Real: {result['real_id']}")
    
    # Test Real ID conversion  
    real_id = "13897"
    result = convert_case_id(real_id, 'real')
    print(f"  Real ID {real_id} → URL: {result['url_id']}, Real: {result['real_id']}")
    
    # Test auto-detection
    test_ids = ["3897", "13897", "4000"]
    for test_id in test_ids:
        result = convert_case_id(test_id, 'auto')
        print(f"  Auto-detect {test_id} → URL: {result['url_id']}, Real: {result['real_id']}")
    
    print()
    
    # Test range parsing
    print("2. Case Range Parsing:")
    
    # URL ID ranges
    url_ranges = ["3897-3890", "3890,3891,3892"]
    for range_str in url_ranges:
        try:
            ids = parse_case_id_range(range_str, 'url')
            print(f"  URL range '{range_str}' → {ids}")
        except ValueError as e:
            print(f"  Error parsing '{range_str}': {e}")
    
    # Real ID ranges  
    real_ranges = ["13897-13890", "13890,13891,13892"]
    for range_str in real_ranges:
        try:
            ids = parse_case_id_range(range_str, 'real')
            print(f"  Real range '{range_str}' → converted to URL IDs: {ids}")
        except ValueError as e:
            print(f"  Error parsing '{range_str}': {e}")
    
    print()
    
    # Test verified mappings
    print("3. Pattern Verification (실제 수집된 데이터):")
    verified_mappings = [
        (3897, 13897), (3896, 13896), (3895, 13895),
        (3894, 13894), (3893, 13893), (3891, 13891), (3890, 13890)
    ]
    
    for url_id, expected_real_id in verified_mappings:
        predicted_real_id = predict_real_case_id(url_id)
        match = "✅" if predicted_real_id == expected_real_id else "❌"
        print(f"  URL {url_id} → Real {expected_real_id} (예상: {predicted_real_id}) {match}")
    
    print()
    
    # Test command line examples
    print("4. Updated Command Line Usage Examples:")
    print("  # URL ID (traditional)")
    print("  python main.py --type case --id 3897")
    print("  python main.py --type case --range '3897-3890'")
    print()
    print("  # Real ID (NEW!)")
    print("  python main.py --type case --id 13897 --id-type real")
    print("  python main.py --type case --range '13897-13890' --id-type real")
    print()
    print("  # Auto-detection")
    print("  python main.py --type case --id 13897 --id-type auto")
    print("  python main.py --type case --range '3897-3890' --id-type auto")
    
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
    test_id_pattern_analysis()
    test_reverse_id_calculation()
    test_new_id_conversion_features()
    test_case_id_pattern_analysis()
    
    print("All tests completed!")
    print("\nNote: This is a functionality test without actual ERP connection.")
    print("To test with real ERP system, configure .env file and run main.py")


if __name__ == '__main__':
    main() 