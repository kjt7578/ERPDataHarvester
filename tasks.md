# HR ERP 자동 이력서 수집 시스템 - 작업 관리

## 🎯 프로젝트 개요
ERP 웹 시스템에서 후보자 정보와 케이스 정보를 자동으로 수집하고 체계적으로 저장하는 시스템

## 📌 주요 작업 (Major Tasks)

### ✅ 완료된 작업
- [x] 프로젝트 구조 설계 및 아키텍처 다이어그램 생성
- [x] 모듈별 역할 정의 및 구현 계획 수립
- [x] 기본 프로젝트 구조 생성 (디렉토리, requirements.txt, .gitignore)
- [x] config.py - 설정 관리 모듈 구현
- [x] login_session.py - 로그인 세션 관리 구현
- [x] scraper.py - HTML 파싱 및 데이터 추출 구현 (후보자 + 케이스)
- [x] downloader.py - PDF 다운로드 모듈 구현
- [x] file_utils.py - 파일 및 디렉토리 관리 구현
- [x] metadata_saver.py - 메타데이터 저장 구현 (후보자 + 케이스)
- [x] main.py - 메인 실행 로직 구현 (듀얼 모드)
- [x] README.md - 프로젝트 문서화 (케이스 기능 포함)
- [x] JobCase 기능 완전 구현 (실제 ID 추출 포함)
- [x] 브래킷 기반 파일명 시스템 구현 (가독성 향상)
- [x] **URL ID ↔ 실제 ID 양방향 지원 시스템 구현**
- [x] **Case ID 패턴 분석 및 양방향 변환 구현**
- [x] **향상된 폴더 구조 시스템 구현 (100~1000000단위 지원)**

## 🔄 진행 중인 작업

### ✨ 향상된 폴더 구조 시스템 (NEW!) 
- **상태**: ✅ 완료! (2025-01-27)
- **기능**: 100단위부터 1000000단위까지 지원하는 스마트 폴더 구조 시스템
- **주요 특징**:
  - **다중 단위 지원**: 100, 1000, 10000, 100000, 1000000 단위
  - **자동 단위 선택**: ID 크기에 따른 최적 단위 자동 선택
  - **설정 가능**: 환경변수로 단위 및 자동 선택 제어
  - **하위 호환성**: 기존 코드와 완전 호환
- **자동 단위 선택 로직**:
  - ID < 1000: 100단위
  - ID < 10000: 1000단위  
  - ID < 100000: 10000단위
  - ID < 1000000: 100000단위
  - ID >= 1000000: 1000000단위
- **환경변수 설정**:
  ```bash
  # 수동 단위 설정 (100, 1000, 10000, 100000, 1000000)
  FOLDER_UNIT=1000000
  
  # 자동 단위 선택 (기본값: true)
  AUTO_FOLDER_UNIT=true
  ```
- **사용 예시**:
  - ID 1044790 → 1000000단위 → `1000000-1999999/` 폴더
  - ID 50000 → 10000단위 → `50000-59999/` 폴더
  - ID 1000 → 1000단위 → `1000-1999/` 폴더
- **구현 파일**:
  - `file_utils.py`: 새로운 폴더 구조 함수들
  - `config.py`: 설정 옵션 추가
  - `main.py`, `scraper.py`: 자동 단위 선택 적용

### ✨ Case + Candidate 통합 수집 기능 (NEW!) 
- **상태**: ✅ 완료! (2025-01-27)
- **기능**: Case 정보 추출과 동시에 연결된 candidate의 metadata와 resume도 함께 다운로드
- **테스트 결과**: 
  - ✅ Case 정보 추출 정상 작동
  - ✅ 연결된 candidate 없는 경우 적절히 처리
  - ✅ 명확한 로그 메시지 출력
  - ✅ 오류 없이 Case 파일 생성
- **사용법**: 
  ```bash
  # Case 정보만 (기존 방식)
  python main.py --type case --id 3999
  
  # Case + 연결된 Candidate 정보까지 (새로운 방식)
  python main.py --type case --id 3999 --with-candidates
  python main.py --type case --range "3999-3990" --with-candidates
  python main.py --type case --real-id 13999 --with-candidates
  python main.py --type case --real-range "13999-13990" --with-candidates
  ```
- **구현 내용**:
  - CLI에 `--with-candidates` 플래그 추가
  - Case 타입에서만 사용 가능하도록 검증
  - Case 정보 추출 시 연결된 candidate 페이지도 자동 방문
  - Candidate 상세 정보 파싱 및 metadata 저장
  - Resume 파일 자동 다운로드 (PDFDownloader 통합)
  - 한 번의 명령어로 완전한 데이터 수집 가능
  - 연결된 candidate가 없는 경우 안전하게 처리
- **성능**: 이미 candidate 페이지를 방문하므로 추가 네트워크 비용 최소화

## 📅 향후 작업 (Future Tasks)
- [ ] MySQL 트리거 기반 업데이트 감지 구현
- [ ] Telegram Bot 연동 (사용자 명령 처리)
- [ ] 스케줄러 구현 (10분마다 업데이트 체크)
- [ ] Docker 컨테이너화
- [ ] 테스트 코드 작성
- [ ] API 엔드포인트 추가 (선택사항)
- [ ] 에러 복구 메커니즘 강화

## 📋 기술 스택
- Python 3.12
- requests / selenium  
- BeautifulSoup4
- pandas (CSV 처리)
- tqdm (진행률 표시)
- colorlog (컬러 로깅)
- python-telegram-bot (예정)
- MySQL connector (예정)

## 🔍 구현 특징
1. **이중 모드 지원**: 후보자 수집(`--type candidate`) + 케이스 수집(`--type case`)
2. **실제 ID 추출**: URL ID가 아닌 실제 시스템 ID 사용
3. **모듈화된 구조**: 각 기능별로 독립된 모듈로 분리
4. **유연한 스크래핑**: 다양한 HTML 구조에 대응 가능
5. **안정적인 다운로드**: 재시도 로직과 검증 기능
6. **체계적인 저장**: 연도/월 기반 디렉토리 구조
7. **상세한 로깅**: 디버깅과 모니터링 용이
8. **CLI 지원**: 다양한 실행 옵션 제공

## 완료된 작업 (Completed Tasks)

✅ **JobCase 실제 ID 추출 시스템 완성** - 2025-06-26
- URL ID → 실제 ID 변환: Case 3897 → Case No 13897
- 다중 페이지 탐색으로 연결 데이터 추출
- 4가지 패턴으로 클라이언트 ID 추출 보장
- 환경변수 주석 처리 로직 추가

✅ **ID 범위 다운로드 기능 추가** - 2025-06-26
- 페이지 스크래핑 대신 ID 범위로 안정적 다운로드
- 지원 형식: `65585-65580` (범위) 또는 `65580,65581,65582` (개별)
- 자동 딜레이 및 진행률 표시
- 통합 결과 저장 및 리포트 생성

✅ **Core Module Implementation** 
- config.py: 환경변수 기반 설정 관리
- login_session.py: requests/Selenium 듀얼 모드 로그인
- file_utils.py: 파일명 정리 및 중복 처리  
- downloader.py: 재시도 로직 및 진행률 표시
- metadata_saver.py: JSON/CSV 듀얼 포맷 지원
- main.py: CLI 인터페이스 및 전체 조율

✅ **HRcap ERP Integration**
- URL 구조 분석: `/candidate/dispView/{id}?kw=`
- 리스트 페이지: `/searchcandidate/dispSearchList/{page}`  
- HTML 파싱 로직 구현
- PDF 다운로드 패턴 분석

✅ **Safety & Performance**
- 서버 보호: REQUEST_DELAY=2.0초, PAGE_DELAY=3.0초
- 테스트 제한: MAX_PAGES=2
- 로깅 시스템 구축
- 에러 처리 강화

## 사용법 (Usage)

### 후보자 수집
```bash
# 전체 후보자 수집
python main.py --type candidate

# 특정 후보자 (URL ID로 접근, 실제 ID로 저장)
python main.py --type candidate --id 65586

# 범위로 다운로드  
python main.py --type candidate --range "65585-65580"
```

### 케이스 수집  
```bash
# 전체 케이스 수집
python main.py --type case

# 특정 케이스 (URL ID로 접근, 실제 Case No로 저장)
python main.py --type case --id 3897

# 케이스 범위로 다운로드
python main.py --type case --range "3897-3900"
```

## 다음 실행 단계

1. **환경변수 설정**:
   ```bash
   # .env 파일에서 설정
   ERP_USERNAME=your_username  
   ERP_PASSWORD=your_password
   REQUEST_DELAY=2.0
   ```

2. **단일 케이스 테스트** (추천!):
   ```bash
   python main.py --type case --id 3897
   ```

3. **단일 후보자 테스트**:
   ```bash
   python main.py --type candidate --id 65586
   ```

4. **범위 다운로드**:
   ```bash
   # 케이스 범위
   python main.py --type case --range "3897-3900"
   
   # 후보자 범위
   python main.py --type candidate --range "65585-65580"
   ``` 

### 📅 2025-06-27: ID 타입 양방향 지원 시스템 구현
**구현 내용:**
- **ID 변환 패턴 발견**: URL ID + 979,174 = 실제 Candidate ID
- **양방향 변환 기능**: URL ID ↔ 실제 ID 자동 변환
- **새로운 CLI 옵션**: `--id-type url|real|auto` 추가
- **범위 처리 개선**: 실제 ID 범위도 지원 (예: 1044759-1044754)
- **자동 감지**: ID 범위에 따른 타입 자동 감지

**주요 기능:**
1. **개별 ID 처리**: `--id 1044760 --id-type real`
2. **범위 처리**: `--range '1044759-1044754' --id-type real`
3. **자동 감지**: `--id-type auto` (범위별 자동 판단)
4. **변환 함수**: `convert_candidate_id()`, `parse_id_range()`
5. **검증 함수**: `verify_candidate_id_pattern()`

**사용 예시:**
```bash
# 실제 ID로 단일 후보자 처리
python main.py --type candidate --id 1044760 --id-type real

# 실제 ID 범위로 처리  
python main.py --type candidate --range '1044759-1044754' --id-type real

# 자동 감지
python main.py --type candidate --id 65586 --id-type auto
```

**기술적 세부사항:**
- **상수**: `CANDIDATE_ID_OFFSET = 979174`
- **검증됨**: Meghan Lee (URL:65586 → Real:1044760), 3개 샘플 100% 일치
- **Case ID**: 현재 동일 (패턴 발견 시 확장 예정)
- **하위 호환성**: 기존 URL ID 방식 완전 지원

## 🔍 현재 ID 패턴 상황

### ✅ Candidate ID (완료)
- **패턴**: `실제 ID = URL ID + 979,174`
- **검증**: 3개 샘플 100% 일치 (Meghan Lee 등)
- **구현**: 완전 양방향 지원

### ✅ Case ID (완료!)
- **패턴**: `실제 ID = URL ID + 10,000`
- **검증**: 7개 샘플 100% 일치 (URL 3897 → Real 13897 등)
- **구현**: 완전 양방향 지원
- **기능**: 개별 ID, 범위 처리, 자동 감지 모든 지원

### 📅 2025-06-27: Case ID 패턴 발견 및 양방향 변환 완성
**구현 내용:**
- **Case ID 패턴 발견**: `실제 Case ID = URL ID + 10,000`
- **패턴 검증**: 7개 Case 샘플 100% 일치 (3897→13897, 3896→13896 등)
- **양방향 변환 구현**: URL ID ↔ 실제 Case ID 완전 지원
- **범위 처리**: 실제 Case ID 범위도 지원 (예: 13897-13895)
- **자동 감지**: ID 범위에 따른 타입 자동 감지

**주요 기능:**
1. **개별 Case ID 처리**: `--id 13897 --id-type real`
2. **범위 처리**: `--range '13897-13895' --id-type real`
3. **자동 감지**: `--id-type auto` (Case ID 범위별 자동 판단)
4. **변환 함수**: `convert_case_id()`, `parse_case_id_range()`
5. **예측 함수**: `predict_real_case_id()`, `predict_url_case_id()`

**실제 테스트 성공:**
```bash
# 실제 Case ID로 단일 처리
python main.py --type case --id 13897 --id-type real ✅

# 실제 Case ID 범위로 처리  
python main.py --type case --range '13897-13895' --id-type real ✅

# 자동 감지
python main.py --type case --id 3897 --id-type auto ✅
```

**기술적 세부사항:**
- **상수**: `CASE_ID_OFFSET = 10000`
- **검증**: 7개 Case 샘플 100% 일치 (CJ Foodville, 삼성전자 MX, Semes 등)
- **하위 호환성**: 기존 URL ID 방식 완전 지원
- **로깅**: 실시간 ID 매핑 및 변환 과정 표시

## 🚨 주요 에러 (Major Errors)

### ✅ Case Candidate 추출 문제 해결 완료 ✅ SOLVED (2025-06-30)
- **문제**: "No candidates connected to this case" 로그가 출력되어 candidate 추출이 작동하지 않는 것으로 보임
- **원인 분석**: 
  1. 실제로는 정상 작동하고 있었으나 일부 case에는 연결된 candidate가 없었음
  2. 디버깅 정보 부족으로 정확한 상황 파악이 어려웠음
- **해결 방법**:
  1. **디버깅 코드 대폭 강화**: session 검증, HTML 저장, 단계별 상세 로깅 추가
  2. **대안 패턴 추가**: openCandidate 외에도 href="/candidate/", data-candidate-id, 텍스트 패턴 검색 지원
  3. **실시간 검증**: Case 3897 (Real ID: 13897)에서 2명 candidate 성공 추출 확인
- **테스트 결과**:
  ```
  ✅ Found candidate URL ID: 64853 from onclick: openCandidate(64853)
  ✅ Found candidate URL ID: 64879 from onclick: openCandidate(64879)
  ✅ Found actual Candidate ID: 1044027 (from URL ID: 64853)
  ✅ Found actual Candidate ID: 1044053 (from URL ID: 64879)
  Total connected candidates: 2
  ```

### ✅ --with-candidates 통합 수집 기능 완전 구현 ✅ SOLVED (2025-06-30)
- **문제**: Case 다운로드시 연결된 candidate resume까지 함께 수집하는 기능 완성도 확인 필요
- **해결된 이슈들**:
  1. **Downloader 초기화 순서 문제**: main.py에서 scraper 초기화시 downloader가 None이었음
     - **수정**: downloader를 먼저 초기화한 후 scraper에 전달하도록 순서 변경
  2. **Config Import 문제**: scraper.py에서 `import config` 대신 `from config import config` 사용
     - **에러**: "module 'config' has no attribute 'resumes_dir'"
     - **수정**: 올바른 import 방식으로 변경
- **최종 테스트 결과** (Case 3897):
  ```
  🎯 Case + Candidate Mode: Will also download connected candidate resumes and metadata
  ✅ Found actual Candidate ID: 1044027 (from URL ID: 64853)
  📄 Downloaded resume for candidate 1044027: [Resume-1044027] JESSICA SEO.pdf (1.30 MB)
  ✅ Found actual Candidate ID: 1044053 (from URL ID: 64879) 
  📄 Downloaded resume for candidate 1044053: [Resume-1044053] Yujin Oh.pdf (0.17 MB)
  🎯 Total connected candidates: 2 (processed 2 with full details)
  ```
- **기능 완성도**: ✅ 100% 작동
  - Case metadata 수집 ✅
  - 연결된 candidate 발견 ✅
  - Candidate 상세 정보 추출 ✅
  - Resume 파일 다운로드 ✅
  - 통합 저장 ✅