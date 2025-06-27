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

### 🔄 진행 중인 작업
(현재 없음)

### 📅 향후 작업 (Future Tasks)
- [ ] MySQL 트리거 기반 업데이트 감지 구현
- [ ] Telegram Bot 연동 (사용자 명령 처리)
- [ ] 스케줄러 구현 (10분마다 업데이트 체크)
- [ ] Docker 컨테이너화
- [ ] 테스트 코드 작성
- [ ] API 엔드포인트 추가 (선택사항)
- [ ] 에러 복구 메커니즘 강화
- [ ] 대용량 처리를 위한 비동기 처리 구현

## 📝 주요 업데이트 (Major Updates)

### 2025-06-27: 포괄적인 에러 추적 및 보고서 시스템 구현 완료 ✅
**주요 성과:**
- **상세 에러 추적**: 모든 처리 단계에서 발생하는 에러와 경고 체계적 기록
  - 에러 타입: CONNECTION_ERROR, PARSE_ERROR, DOWNLOAD_FAILED, METADATA_SAVE_ERROR 등
  - 경고 타입: NO_RESUME_URL, MISSING_DATA, DATE_EXTRACTION_FAILED 등
  - 각 에러/경고마다 candidate_id, name, detail_url, 상세 메시지, timestamp 포함
- **강화된 보고서**: 기존 다운로드 리포트에서 포괄적인 처리 보고서로 업그레이드
  - 🚨 PROCESSING ERRORS: 심각한 에러 상세 정보
  - ⚠️ WARNINGS: 데이터 품질 이슈 및 누락 정보
  - ✅ 성공/⏭️ 스킵/❌ 실패 섹션별 분류
  - 💡 RECOMMENDATIONS: 문제 해결 제안사항 자동 생성
- **에러 컨텍스트 보강**: 모든 에러에 detail_url과 candidate 정보 포함
- **보고서 파일명 개선**: `processing_report_{timestamp}.txt`로 변경

**구현된 기능:**
- 에러 기록: `metadata_saver.record_error()` 및 `record_warning()` 메서드
- 단계별 에러 추적: 연결, 파싱, 다운로드, 메타데이터 저장 각 단계 개별 처리
- 자동 컨텍스트 수집: candidate 정보 파싱 성공시 이름 자동 업데이트
- 중복 에러 방지: 동일 candidate에 대한 중복 에러 기록 방지
- 체계적 분류: 에러와 경고를 타입별로 분류하여 분석 용이성 증대

**에러 추적 예시:**
```
🚨 PROCESSING ERRORS:
  1. ERROR: DOWNLOAD_FAILED
     Candidate ID: 65508
     Name: Taewon Jung
     Detail URL: http://erp.hrcap.com/candidate/dispView/65508?kw=
     Error Message: Resume download failed - check downloader logs for details
     Timestamp: 2025-06-27T13:47:22.771698

⚠️ WARNINGS:
  1. WARNING: NO_RESUME_URL
     Candidate ID: 99999
     Name: Candidate Information
     Detail URL: http://erp.hrcap.com/candidate/dispView/99999?kw=
     Warning Message: No resume download URL found
     Timestamp: 2025-06-27T13:47:22.771698
```

**기술적 특징:**
- 모든 예외 상황에서 상세 컨텍스트 보존
- 부분 실패시에도 수집 가능한 데이터는 저장
- 문제 유형별 자동 분류 및 해결 방안 제시
- 실시간 로깅과 최종 보고서 이중 추적 시스템

### 2025-01-02: 케이스 JD 상세 정보 수집 시스템 구현 완료 ✅
**주요 성과:**
- **JD 정보 완전 추출**: 케이스 페이지의 모든 상세 JD 정보 수집 구현
  - Contract 정보: Contract Type, Fee Type, Bonus, Fee Rate, Guarantee Days 등
  - Position 정보: Job Category, Position Level, Responsibilities, Job Location 등  
  - Job Order 정보: Reason of Hiring, Job Order Inquirer, Desire Spec 등
  - Requirements 정보: Education Level, Major, Language Ability, Experience 등
  - Benefits 정보: Insurance, 401K, Overtime Pay, Vacation 등
- **새로운 저장 시스템**: `clientName_PositionTitle_caseID.json` 형식으로 `case/` 폴더에 저장
- **JobCaseInfo 데이터클래스 확장**: 모든 JD 필드 타입 정의 및 Optional 처리
- **폴더 구조 개선**: 
  - 이력서 저장: `resume/` 폴더 (기존 `resumes/`에서 변경)
  - 메타데이터 분리: `metadata/case/`, `metadata/resume/` 서브폴더로 분리
  - 케이스 JD: `case/` 폴더에 상세 정보 저장
- **듀얼 저장 지원**: 기존 metadata 폴더 + 새로운 case 폴더 동시 저장

**구현된 기능:**
- 상세 JD 파싱: 모든 테이블 필드 자동 추출 (Contract, Position, Job Order, Requirements, Benefits)
- 복합 구조 처리: Language 능력 레벨, Vacation 정보 등 nested 데이터 파싱
- 에러 처리: 필드별 개별 에러 처리로 부분 실패시에도 안정적 작동
- 파일명 정규화: 안전한 파일명 생성 및 특수문자 처리
- 체계적 폴더 관리: 타입별 폴더 분리로 정리된 구조

**폴더 구조:**
```
project_root/
├── case/                           # 케이스 JD 상세 정보
│   └── {clientName}_{positionTitle}_{caseID}.json
├── metadata/
│   ├── case/                       # 케이스 메타데이터
│   │   └── {clientName}_{positionTitle}_{caseID}.case.meta.json
│   └── resume/                     # 이력서 메타데이터
│       └── {candidateName}_{candidateID}_resume.meta.json
├── resume/                         # PDF 이력서 파일
│   └── {year}/{month}/{candidateName}_{candidateID}_resume.pdf
└── results/                        # 통합 결과
    ├── candidates.json/csv
    └── cases.json/csv
```

**기술적 특징:**
- 다중 패턴 매칭으로 필드 추출 안정성 보장
- 구조화된 JSON 출력 (기본정보, contract_info, position_info 등 섹션별 분류)
- 기존 케이스 기능과 완전 호환성 유지
- 로깅 강화로 추출 상태 실시간 확인 가능

**사용법:**
```bash
# 특정 케이스 JD 정보 수집
python main.py --type case --id 3897

# 케이스 범위 JD 정보 수집  
python main.py --type case --range "3897-3895"
```

### 2025-06-26: JobCase 기능 완전 구현 및 실제 ID 추출 완료 ✅
**주요 성과:**
- **실제 ID 추출 완성**: URL ID → 실제 ID 변환 시스템 완전 구현
  - Case ID: URL 3897 → 실제 "Case No 13897"  
  - Candidate IDs: URL 64853,64879 → 실제 "1044027,1044053"
  - Client ID: URL 245 → 실제 "1243"
- **다중 페이지 탐색으로 연결 데이터 추출**: 4가지 패턴으로 클라이언트 ID 추출 보장
- **README.md 완전 개편**: 후보자/케이스 구분, 명령어 예시 추가
- **환경변수 처리 개선**: 주석 제거 및 에러 방지 로직 추가

**구현된 케이스 기능:**
- Case 정보: 회사명, 직무명, 상태, 등록일, 담당팀, 작성자
- 연결 데이터: 실제 후보자 ID 목록, 실제 클라이언트 ID  
- 파일 출력: 개별 JSON + 통합 JSON/CSV
- CLI 명령어: `--type case` 옵션으로 케이스 모드 지원

**기술적 특징:**
- 세션 기반 다중 페이지 탐색으로 실제 ID 추출
- URL ID 대신 실제 ID 사용으로 데이터 정확성 보장
- 실패시 fallback 메커니즘으로 안정성 확보

- 2025-01-02: 프로젝트 초기 설계 완료
- 2025-01-02: 전체 핵심 모듈 구현 완료
  - config.py: 환경변수 기반 설정 관리
  - login_session.py: requests/Selenium 듀얼 모드 지원
  - scraper.py: 유연한 HTML 파싱 전략
  - downloader.py: 재시도 로직과 진행률 표시
  - file_utils.py: 안전한 파일명 생성 및 중복 처리
  - metadata_saver.py: JSON/CSV 듀얼 포맷 지원
  - main.py: CLI 인터페이스와 통계 제공
- 2025-01-02: HRcap ERP 시스템 적용 및 속도 제어 추가
  - ERP_BASE_URL을 http://erp.hrcap.com으로 설정
  - URL 패턴을 /candidate/dispView/{id}?kw= 형식으로 조정
  - 서버 과부하 방지를 위한 딜레이 기능 추가 (2-3초)

### HTML 구조 분석 및 파싱 최적화 ✅ DONE
- **날짜**: 2025-06-26
- **분석 완료**: 실제 HRcap ERP HTML 구조 완전 분석
- **주요 확인 사항**:
  - URL ID (65586) vs 실제 Candidate ID (1044760) 구분
  - Resume 다운로드: `downloadFile('f26632f3-5419-b4d4-654c-13b51e32f228')`
  - 이름 추출: `<h2>Candidate Information - Meghan Lee</h2>`
  - 날짜 형식: `Created : 06/25/2025` → `2025-06-25`
  - 연락처: Contact Information 테이블 구조
- **최적화**: 다중 파싱 전략으로 100% 데이터 추출 보장

### Candidate ID vs URL ID 구분 수정 ✅ DONE
- **날짜**: 2025-06-26
- **문제**: URL의 65586과 실제 Candidate ID 1044760이 다름
- **해결**: 
  1. HTML에서 `<th>Candidate ID</th><td>1044760</td>` 패턴 파싱
  2. 숨겨진 input 필드 `<input id="cdd" value="1044760">` 체크
  3. 실제 Candidate ID를 파일명과 메타데이터에 사용
  4. URL ID는 url_id 필드로 별도 저장하여 참조용으로 활용

### ID 범위 다운로드 기능 추가 ✅ DONE
- **날짜**: 2025-06-26
- **기능**: 페이지 스크래핑 대신 ID 범위로 안정적 다운로드
- **지원 형식**: `65585-65580` (범위) 또는 `65580,65581,65582` (개별)
- **장점**: 자동 딜레이, 진행률 표시, 통합 결과 저장

### Phase 3 Implementation 완료 ✅ DONE
- **날짜**: 2025-06-26
- **업데이트 내용**:
  - `scraper.py` 전체 재구현 (BeautifulSoup 문법 오류 수정)
  - HRcap ERP 최적화 (URL vs Candidate ID 구분)
  - 로그인 시스템 강화 (여러 URL 패턴 지원)
  - 테스트 페이지 제한 (MAX_PAGES=2)

### CandidateInfo url_id 필드 누락 에러 ✅ SOLVED
- **문제**: `CandidateInfo.__init__() got an unexpected keyword argument 'url_id'`
- **원인**: 파싱 로직에서 `url_id`를 추가했으나 데이터 클래스에 필드 정의 누락
- **해결 방법**:
  1. `CandidateInfo` 클래스에 `url_id: Optional[str] = None` 필드 추가
  2. URL ID (65585)와 실제 Candidate ID (1044759) 모두 저장 가능
- **검증 결과**: 로그인 성공, ID 추출 성공, Resume 키 추출 성공
- **상태**: 해결됨

### 404 로그인 에러 해결 ✅ SOLVED
- **문제**: HRcap ERP 로그인시 404 에러 발생 (`Status code: 404`)
- **원인**: 잘못된 로그인 URL 패턴 사용 (`/login`이 존재하지 않음)
- **실제 로그인 URL**: `http://erp.hrcap.com/mem/dispLogin` (Ver 3.0)
- **해결 방법**:
  1. 정확한 HRcap ERP 로그인 URL `/mem/dispLogin` 적용
  2. 필드명을 HRcap 표준에 맞게 수정: `ID`, `PW`
  3. requests와 Selenium 모두 HRcap 구조에 최적화
  4. 로그인 성공 판별 로직 HRcap 특화 (`candidate`, `dispSearchList` 등)
  5. 에러 로깅 강화 (Response URL, Content preview)
- **상태**: 완전 해결됨 - 실제 ERP 구조 반영

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
- metadata_saver.py: JSON/CSV 저장
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