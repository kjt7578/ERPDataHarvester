# HR ERP 자동 이력서 수집 시스템

ERP 웹 시스템에서 후보자 정보와 이력서 PDF를 자동으로 수집하고 체계적으로 저장하는 Python 애플리케이션입니다.

## 🎯 주요 기능

### 후보자 데이터 수집
- ERP 시스템 자동 로그인 및 세션 유지
- 후보자 리스트 페이지 순회 및 파싱
- 후보자 상세 정보 추출 (실제 ID, 이름, 이메일, 전화번호, 날짜 등)
- 이력서 PDF 자동 다운로드 (재시도 로직 포함)
- 체계적인 디렉토리 구조로 파일 저장

### 케이스 데이터 수집
- 케이스 리스트 페이지 순회 및 파싱  
- 케이스 상세 정보 추출 (실제 Case No, 회사명, 직무명, 상태)
- 연결된 후보자 실제 ID 자동 추출
- 클라이언트 실제 ID 자동 추출
- URL ID → 실제 ID 자동 변환

### 공통 기능
- 메타데이터 JSON/CSV 형식 저장
- 다운로드 진행 상황 표시 및 통계 제공
- 유연한 명령어 옵션 (단일/범위/전체 수집)

## 📁 프로젝트 구조

```
ERPDataHarvester/
├── main.py              # 메인 실행 파일
├── config.py            # 설정 관리
├── login_session.py     # ERP 로그인 및 세션 관리
├── scraper.py          # HTML 파싱 및 데이터 추출
├── downloader.py       # PDF 다운로드 관리
├── file_utils.py       # 파일 및 디렉토리 유틸리티
├── metadata_saver.py   # 메타데이터 저장
├── requirements.txt    # Python 의존성
├── env.example        # 환경변수 예시
├── tasks.md           # 작업 관리 문서
├── resumes/           # 다운로드된 이력서 저장
│   └── {year}/
│       └── {month}/
│           └── {name}_{id}_resume.pdf
├── metadata/          # 개별 메타데이터 JSON 파일
├── results/           # 통합 결과 파일
└── logs/             # 로그 파일
```

## 🚀 사용 방법 (Usage)

### 🎯 두 가지 ID 방식 지원

이 시스템은 **URL ID**와 **실제 ID** 두 가지 방식으로 작동합니다:

| ID 타입 | Candidate 예시 | Case 예시 | 설명 |
|---------|---------------|-----------|------|
| **URL ID** | 65586 | 3897 | ERP URL에 사용되는 ID (기존 방식) |
| **실제 ID** | 1044760 | 13897 | 실제 데이터베이스 ID (새로운 방식) |

### 📋 기본 명령어 구조

```bash
python main.py --type [candidate|case] [ID_옵션] [기타_옵션]
```

## 🔗 방법 1: URL ID 방식 (기존 방식)

### Candidate (후보자) 처리

```bash
# 단일 후보자 처리 (URL ID)
python main.py --type candidate --id 65586

# URL ID 범위 처리 
python main.py --type candidate --range "65585-65580"
python main.py --type candidate --range "65580,65581,65582"

# 전체 페이지 크롤링
python main.py --type candidate --page 1
```

### Case (케이스) 처리

```bash
# 단일 케이스 처리 (URL ID)
python main.py --type case --id 3897

# URL ID 범위 처리
python main.py --type case --range "3897-3890"
python main.py --type case --range "3890,3891,3892"

# 전체 페이지 크롤링
python main.py --type case --page 1
```

## 🎯 방법 2: 실제 ID 방식 (최신 방식)

### Candidate (후보자) 처리

```bash
# 단일 후보자 처리 (실제 ID)
python main.py --type candidate --real-id 1044760

# 실제 ID 범위 처리
python main.py --type candidate --real-range "1044759-1044754"
python main.py --type candidate --real-range "1044754,1044755,1044756"
```

### Case (케이스) 처리

```bash
# 단일 케이스 처리 (실제 ID)
python main.py --type case --real-id 13897

# 실제 ID 범위 처리
python main.py --type case --real-range "13897-13890"
python main.py --type case --real-range "13890,13891,13892"
```

## 🔧 고급 옵션

### 로깅 레벨 설정
```bash
# 상세한 로그 출력
python main.py --type candidate --real-id 1044760 --log-level DEBUG

# 간단한 로그 출력
python main.py --type case --id 3897 --log-level WARNING
```

### Case ID 패턴 분석 (고급 사용자용)
```bash
# Case ID 패턴 분석 모드
python main.py --type case --range "3897-3890" --analyze-case-pattern
```

### ✨ Case + Candidate 통합 수집 (NEW!)
```bash
# Case 정보와 연결된 모든 candidate 정보도 함께 수집
python main.py --type case --id 3897 --with-candidates
python main.py --type case --range "3897-3890" --with-candidates
python main.py --type case --real-id 13897 --with-candidates
python main.py --type case --real-range "13897-13890" --with-candidates

# 주의: --with-candidates는 Case 타입에서만 사용 가능
```

## 📊 ID 변환 패턴

### 자동 변환 규칙
시스템이 자동으로 ID를 변환합니다:

**Candidate ID 변환:**
```
실제 ID = URL ID + 979,174
예시: URL 65586 → Real 1044760
```

**Case ID 변환:**
```
실제 ID = URL ID + 10,000
예시: URL 3897 → Real 13897
```

### 사용 팁
- **URL ID 방식**: 기존 ERP URL에서 보이는 숫자를 그대로 사용
- **실제 ID 방식**: 데이터베이스에 저장된 실제 ID를 사용
- **범위 지정**: 큰 숫자에서 작은 숫자 순으로 처리됨
- **쉼표 구분**: 특정 ID들만 선택적으로 처리 가능

## 💡 명령어 예시 모음

### URL ID 방식 (기존)
```bash
# Candidate
python main.py --type candidate --id 65586
python main.py --type candidate --range "65590-65585"

# Case  
python main.py --type case --id 3897
python main.py --type case --range "3900-3895"
```

### 실제 ID 방식 (최신)
```bash
# Candidate
python main.py --type candidate --real-id 1044760
python main.py --type candidate --real-range "1044765-1044760"

# Case
python main.py --type case --real-id 13897  
python main.py --type case --real-range "13900-13895"
```

### 혼합 사용 불가
```bash
# ❌ 잘못된 예시 (동시 사용 불가)
python main.py --type candidate --id 65586 --real-id 1044760

# ✅ 올바른 예시 (하나씩 사용)
python main.py --type candidate --id 65586
python main.py --type candidate --real-id 1044760
```

## 📝 향후 개발 계획

- [ ] MySQL 트리거 기반 실시간 업데이트
- [ ] Telegram Bot 연동 (명령어 기반 수집)
- [ ] 스케줄러 구현 (주기적 자동 실행)
- [ ] Docker 컨테이너화
- [ ] RESTful API 제공
- [ ] 중복 검사 강화
- [ ] 다국어 지원

## ⚠️ 중요 주의사항

### 외부 호스팅 ERP 시스템 사용시
**이 도구를 외부 업체가 호스팅하는 ERP 시스템에 사용하기 전에 반드시:**

1. **사전 승인 필수**
   - IT 관리자/담당자 승인
   - ERP 호스팅 업체 정책 확인
   - 서비스 약관 검토

2. **법적 검토**
   - 자동화 접근 허용 여부 확인
   - 데이터 수집 권한 검토
   - 개인정보보호 정책 준수

3. **기술적 고려사항**
   - 운영 환경이 아닌 테스트 환경 사용 권장
   - 공식 API 연동 방식 우선 검토
   - 트래픽 제한 및 속도 조절 필수

### 권장 대안
- **공식 API 사용**: HRcap에서 제공하는 정식 API 활용
- **내부 시스템**: 자체 호스팅 ERP 시스템에서만 사용
- **테스트 환경**: 운영 데이터가 아닌 샘플 데이터로 테스트

**⚠️ 무단 사용으로 인한 모든 법적 책임은 사용자에게 있습니다.**

## 🤝 기여하기

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.

## 🔍 ID 패턴 분석

### Candidate ID 패턴 (✅ 발견됨)
- **패턴**: `실제 Candidate ID = URL ID + 979,174`
- **검증됨**: 3개 샘플 100% 일치
- **사용 가능**: 양방향 변환 지원

```bash
# 실제 ID로 처리
python main.py --type candidate --id 1044760 --id-type real
python main.py --type candidate --range '1044759-1044754' --id-type real
```

### Case ID 패턴 (❓ 분석 필요)
- **상태**: 패턴 미발견
- **분석 방법**: 실제 ERP 데이터 수집 후 패턴 도출

#### Case ID 패턴 분석 가이드

1. **데이터 수집 명령어**:
```bash
# Case ID 패턴 분석 모드로 실행
python main.py --type case --range '3897-3890' --analyze-case-pattern --log-level INFO

# 또는 개별 Case 분석
python main.py --type case --id 3897 --analyze-case-pattern --log-level INFO
```

2. **로그에서 패턴 찾기**:
```
CASE ID MAPPING: URL 3897 → Real 13897 (차이: 10000)
CASE ID MAPPING: URL 3896 → Real 13896 (차이: 10000)  
CASE ID MAPPING: URL 3895 → Real 13895 (차이: 10000)
```

3. **패턴 확인 요소**:
   - 충분한 샘플 수집 (최소 3-5개)
   - 일관된 차이값 확인
   - 예외 사례 검토

4. **패턴 발견 시 구현**:
   - `file_utils.py`의 `convert_case_id()` 함수 업데이트
   - Case ID 양방향 변환 기능 활성화

## 🚀 시작하기

### 1. 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-repo/ERPDataHarvester.git
cd ERPDataHarvester

# 가상환경 생성 및 활성화
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
# .env 파일을 편집하여 ERP 접속 정보 입력
```

## ⚙️ 환경변수 설정

`.env` 파일에서 다음 항목들을 설정하세요:

```env
# ERP 시스템 설정 (필수)
ERP_BASE_URL=https://your-erp-system.com
ERP_USERNAME=your_username
ERP_PASSWORD=your_password

# 경로 설정
RESUMES_DIR=./resumes
METADATA_DIR=./metadata
RESULTS_DIR=./results
LOGS_DIR=./logs

# 스크래핑 설정
PAGE_LOAD_TIMEOUT=30
DOWNLOAD_TIMEOUT=60
MAX_RETRIES=3
RETRY_DELAY=5

# 페이지네이션
ITEMS_PER_PAGE=20
MAX_PAGES=0  # 0은 제한 없음

# 파일명 패턴
FILE_NAME_PATTERN={name}_{id}_resume
```

## 📊 출력 파일

### 후보자 데이터

#### 1. 이력서 PDF
- 위치: `resumes/{year}/{month}/{name}_{id}_resume.pdf`
- 생성일 기준으로 연도/월 폴더에 자동 분류

#### 2. 개별 메타데이터
- 위치: `metadata/{name}_{id}_resume.meta.json`
- 후보자별 상세 정보 포함

#### 3. 통합 결과
- `results/candidates.json`: 모든 후보자 정보 (JSON)
- `results/candidates.csv`: 모든 후보자 정보 (CSV)
- `results/download_report_*.txt`: 다운로드 통계 보고서

### 케이스 데이터

#### 1. 개별 케이스 메타데이터
- 위치: `metadata/{company}_{jobcase_id}_{job_title}.case.meta.json`
- 케이스별 상세 정보 포함:
  - 실제 Case No (URL ID에서 변환)
  - 회사명, 직무명, 상태
  - 등록일, 담당팀, 작성자
  - 연결된 후보자 실제 ID 목록
  - 실제 클라이언트 ID

#### 2. 통합 케이스 결과
- `results/cases.json`: 모든 케이스 정보 (JSON)
- `results/cases.csv`: 모든 케이스 정보 (CSV)

## 🔧 고급 사용법

### 특정 페이지 범위 처리

```python
# main.py를 수정하여 페이지 범위 지정
harvester.harvest_candidates(start_page=10, end_page=20)
```

### 커스텀 필터 적용

```python
# scraper.py에서 특정 조건의 후보자만 필터링
if candidate_info.status == 'Active':
    process_candidate(candidate_info)
```

**특별한 경우:**
- Case에 연결된 candidate가 없는 경우: Case 정보만 정상적으로 수집됨
- 네트워크 오류나 권한 문제로 candidate 페이지 접근 실패 시: Case 정보는 수집되고 candidate 처리는 건너뜀
