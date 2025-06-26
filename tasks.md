# HR ERP 자동 이력서 수집 시스템 - 작업 관리

## 🎯 프로젝트 개요
ERP 웹 시스템에서 후보자 정보와 이력서를 자동으로 수집하고 체계적으로 저장하는 시스템

## 📌 주요 작업 (Major Tasks)

### ✅ 완료된 작업
- [x] 프로젝트 구조 설계 및 아키텍처 다이어그램 생성
- [x] 모듈별 역할 정의 및 구현 계획 수립
- [x] 기본 프로젝트 구조 생성 (디렉토리, requirements.txt, .gitignore)
- [x] config.py - 설정 관리 모듈 구현
- [x] login_session.py - 로그인 세션 관리 구현
- [x] scraper.py - HTML 파싱 및 데이터 추출 구현
- [x] downloader.py - PDF 다운로드 모듈 구현
- [x] file_utils.py - 파일 및 디렉토리 관리 구현
- [x] metadata_saver.py - 메타데이터 저장 구현
- [x] main.py - 메인 실행 로직 구현
- [x] README.md - 프로젝트 문서화

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

## ⚠️ 에러 및 해결 (Errors & Solutions)

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
1. **모듈화된 구조**: 각 기능별로 독립된 모듈로 분리
2. **유연한 스크래핑**: 다양한 HTML 구조에 대응 가능
3. **안정적인 다운로드**: 재시도 로직과 검증 기능
4. **체계적인 저장**: 연도/월 기반 디렉토리 구조
5. **상세한 로깅**: 디버깅과 모니터링 용이
6. **CLI 지원**: 다양한 실행 옵션 제공 

## 완료된 작업 (Completed Tasks)

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

## 다음 실행 단계

1. **환경변수 설정**:
   ```
   $env:ERP_USERNAME="your_username"
   $env:ERP_PASSWORD="your_password"
   ```

2. **테스트 실행**:
   ```
   python main.py --id 65586
   ```

3. **대량 수집** (주의):
   ```
   python main.py --page 1
   ``` 