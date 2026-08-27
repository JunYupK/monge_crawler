# Naver Cafe Crawler - 운영 가이드

이 가이드는 운영자가 Naver Cafe 게시글 수집 도구를 설정하고 실행하는 절차를 설명합니다.

## 설치

### 1단계: 의존성 설치

```bash
pip install -r requirements.txt
```

### 2단계: 설정 파일 확인

프로젝트 루트에 `config.yaml` 파일이 있어야 합니다. 다음과 같은 형식입니다:

```yaml
board_url: https://cafe.naver.com/cafes/[cafe_id]/menus/[menu_id]
output_dir: output
log_dir: logs
page_size: 15
```

## 첫 점검 (설치 후 반드시 실행)

설치 후 운영자 PC에서 다음 명령으로 실제 API 접근을 확인합니다:

```bash
PYTHONPATH=src python -m monge_crawler.cli selftest
```

이 명령은 다음을 검증합니다:
- 게시글 목록 접근 가능 여부
- 게시글 본문 접근 가능 여부  
- 이미지 다운로드 가능 여부

**접근 오류 발생 시:**
실제 API 응답이 예상과 다를 수 있습니다. 이 경우:
1. 네트워크 및 프록시 설정 확인
2. `src/monge_crawler/parser.py`의 파싱 로직과 `tests/fixtures/` 디렉토리의 픽스처가 현재 API 응답과 일치하는지 검증
3. 필요시 파싱 로직과 픽스처 업데이트

## 게시글 수집

### 기본 명령

지정된 기간의 게시글을 수집하여 Excel 파일로 저장합니다:

```bash
PYTHONPATH=src python -m monge_crawler.cli run --from 2025-09-12 --to 2025-09-16
```

**파라미터:**
- `--from YYYY-MM-DD`: 수집 시작 날짜 (포함)
- `--to YYYY-MM-DD`: 수집 종료 날짜 (포함)

### 출력 위치

수집 후 다음 위치에 파일이 생성됩니다:

- **Excel 파일**: `output/monge_<from>_<to>.xlsx`
  - 예: `output/monge_2025-09-12_2025-09-16.xlsx`
  - 성공한 게시글과 오류 정보 포함

- **이미지 파일**: `output/images/<글ID>/`
  - 각 글의 이미지가 별도 폴더에 저장됨

- **로그 파일**: `logs/run_YYYYMMDD_HHMMSS.log`
  - 실행 기록 및 오류 로그

## 로그인 (현재 불필요 / 향후 대비)

현재는 로그인 없이 접근 가능합니다.

**향후 게시판이 회원 전용으로 변경된 경우:**
1. Naver 계정으로 로그인하여 세션 쿠키 획득
2. `src/monge_crawler/fetcher.py`의 `fetch_posts()` 함수에 쿠키 주입
3. 쿠키는 보안을 위해 별도 설정 파일에서 로드하거나 환경 변수 사용

## 자동 실행 (정기 수집)

### Windows - 작업 스케줄러

1. **작업 스케줄러 열기**: `tasksched.msc` 실행
2. **새 작업 만들기**
3. **일반** 탭:
   - 이름: "Naver Cafe Crawler"
   - 사용자 계정: 시스템 권한 필요 시 선택
4. **트리거** 탭: 일정 설정 (예: 매일 오전 9시)
   - 작업 시작: 일정
   - 일정 유형: 일별
   - 매일: 매일, 반복 간격: 1일
   - 시간: 09:00
5. **작업** 탭:
   - 작업: 프로그램 시작
   - 프로그램/스크립트: `C:\path\to\run.bat`
   - 시작 위치: `C:\path\to\monge_crawler`

### macOS / Linux - Cron

`crontab -e` 명령으로 크론탭 편집:

```bash
# 매일 오전 9시에 실행 (결과는 메일로 수신)
0 9 * * * cd /home/user/monge_crawler && PYTHONPATH=src python -m monge_crawler.cli run --from $(date -d yesterday +\%Y-\%m-\%d) --to $(date +\%Y-\%m-\%d) >> logs/cron.log 2>&1
```

**크론 설정 팁:**
- `--from`과 `--to`에 동일한 날짜를 설정하면 당일만 수집
- 매일 전날 데이터를 수집하려면 위 예시의 `date` 명령 사용
- 로그는 `logs/cron.log`에 누적 저장 (필요시 로테이션 설정)

## 트러블슈팅

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'monge_crawler'` | PYTHONPATH 미설정 | `PYTHONPATH=src` 설정 확인 |
| API 접근 실패 (ConnectionError) | 네트워크 불안정 | VPN/프록시 설정 확인, 재시도 |
| 파싱 오류 | API 응답 변경 | `parser.py` 검증, 픽스처 업데이트 |
| 디스크 부족 | 이미지 용량 과다 | 이전 이미지 정리, 저장소 확장 |

## 지원

문제 발생 시 로그 파일(`logs/`)을 확인하고 개발팀에 보고합니다.
