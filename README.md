# Riemann Trading 데이터 수집 환경

Python 3.12에서 Binance USD-M 선물 1시간 OHLCV를 수집하고 CSV와 Excel로 저장합니다. 첨부 스크립트의 실제 대상인 **SOLUSDT**가 기본값입니다. 파일명 `fetch_eth_1h.py`는 유지했으며 ETH는 옵션으로 선택합니다. 공개 시세만 조회하므로 API 키, 계좌 접근, 주문 기능이 필요하지 않습니다.

## 설치 및 테스트

```bash
bash scripts/setup.sh
.venv/bin/python -m unittest discover -s tests -v
```

`requirements.txt`는 검증한 직접·간접 의존성 버전을 고정합니다. Python 3.12를 사용하세요.

## 실행

먼저 하루 분량으로 연결과 출력을 검증하세요.

```bash
.venv/bin/python fetch_eth_1h.py --symbol SOLUSDT --start 2024-01-01 --end 2024-01-02
```

전체 기간 또는 ETH 수집:

```bash
.venv/bin/python fetch_eth_1h.py
.venv/bin/python fetch_eth_1h.py --symbol ETHUSDT --start 2020-01-01
```

- 시작 시각 포함, 종료 시각 제외입니다. 날짜만 입력하면 UTC 자정입니다.
- 기본 시작일은 2020-01-01이며, 상장 이전 구간에는 데이터가 없습니다.
- 완료된 1시간 캔들만 저장하며 현재 진행 중인 캔들은 제외합니다.
- `data/`에 심볼과 조회 범위가 포함된 CSV·XLSX를 저장합니다. 동일 파일은 덮어쓰지 않습니다. 재실행 시 `--output-dir data/another-run`으로 다른 폴더를 지정하세요.
- `datetime, open, high, low, close, volume` 열을 제공합니다. CSV·Excel 시간은 UTC이며 Excel 호환을 위해 타임존 표기는 생략합니다.
- 중복 타임스탬프는 제거하고 시간순으로 정렬합니다. `gaps`는 연속 캔들 사이의 1시간 간격 불일치 수입니다. 누락값을 임의로 보간하지 않습니다.
- 네트워크 오류는 최대 3회 재시도 후 실패합니다. 모든 수집이 성공한 뒤 파일을 저장하며 중단 지점 재개는 지원하지 않습니다.

## 네트워크 및 보안

HTTPS `fapi.binance.com:443` 접근이 필요합니다. 설치에는 `pypi.org`, `files.pythonhosted.org` 접근이 필요합니다. 프록시 CONNECT 403은 환경의 도메인 허용 설정을 확인하세요. Binance 자체 지역 제한 응답은 지원되는 실행 지역이 필요하며 API 키로 해결되지 않습니다.

`BinanceAPI.txt`, `.env*`, 가상환경, 생성 데이터는 Git에서 제외됩니다. 첨부된 키 파일은 복사하거나 읽지 않습니다. 이 수집기는 인증 정보를 받거나 전송하지 않습니다.

## 검증 상태

로컬 테스트 7개에서 페이지네이션·중복·미완성 캔들 제외·재시도 제한·CSV/XLSX 출력을 검증했습니다. 현재 클라우드의 Binance 요청은 프록시 CONNECT 403으로 차단되어 실제 데이터 수집 검증은 미완료입니다. 도메인 허용 설정 적용 후 위의 하루 수집 명령을 실행하고 24행인지 확인하세요. 로컬 테스트는 실제 서비스 접근을 대체하지 않습니다.
