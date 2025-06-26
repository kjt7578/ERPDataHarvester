# HR ERP 자동 이력서 수집 시스템

ERP 웹 시스템에서 후보자 정보와 이력서 PDF를 자동으로 수집하고 체계적으로 저장하는 Python 애플리케이션입니다.

## 🎯 주요 기능

- ERP 시스템 자동 로그인 및 세션 유지
- 후보자 리스트 페이지 순회 및 파싱
- 후보자 상세 정보 추출 (ID, 이름, 이메일, 전화번호, 날짜 등)
- 이력서 PDF 자동 다운로드 (재시도 로직 포함)
- 체계적인 디렉토리 구조로 파일 저장
- 메타데이터 JSON/CSV 형식 저장
- 다운로드 진행 상황 표시 및 통계 제공

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

### 3. 실행

```bash
# 전체 후보자 수집
python main.py

# Selenium 모드로 실행 (JavaScript 렌더링이 필요한 경우)
python main.py --selenium

# 특정 페이지부터 시작
python main.py --page 5

# 특정 후보자만 처리
# URL 번호로 접근하지만, 실제 candidate_id로 저장
python main.py --id 65586

# 디버그 모드
python main.py --log-level DEBUG
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

### 1. 이력서 PDF
- 위치: `resumes/{year}/{month}/{name}_{id}_resume.pdf`
- 생성일 기준으로 연도/월 폴더에 자동 분류

### 2. 개별 메타데이터
- 위치: `metadata/{name}_{id}_resume.meta.json`
- 후보자별 상세 정보 포함

### 3. 통합 결과
- `results/candidates.json`: 모든 후보자 정보 (JSON)
- `results/candidates.csv`: 모든 후보자 정보 (CSV)
- `results/download_report_*.txt`: 다운로드 통계 보고서

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
