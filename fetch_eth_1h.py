"""Download closed Binance USD-M futures hourly candles without API keys."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import time

import ccxt
import pandas as pd

HOUR_MS = 3_600_000
COLUMNS = ['datetime', 'open', 'high', 'low', 'close', 'volume']


def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def collect(exchange, symbol, start, end, retries=3):
    """Return candles fully contained in [start, end); end must exclude open bars."""
    rows = {}
    cursor = start
    while cursor + HOUR_MS <= end:
        for attempt in range(retries + 1):
            try:
                page = exchange.fapiPublicGetKlines({
                    'symbol': symbol, 'interval': '1h', 'startTime': cursor,
                    'endTime': end - 1, 'limit': 1000,
                })
                break
            except (ccxt.NetworkError, ccxt.RateLimitExceeded):
                if attempt == retries:
                    raise
                time.sleep(min(2 ** attempt, 8))
        if not page:
            break
        latest = max(int(row[0]) for row in page)
        if latest < cursor:
            raise RuntimeError('Pagination made no progress')
        for row in page:
            ts = int(row[0])
            if start <= ts and ts + HOUR_MS <= end:
                rows[ts] = [ts, *map(float, row[1:6])]
        cursor = latest + HOUR_MS
    return [rows[ts] for ts in sorted(rows)]


def save(rows, output, symbol, start, end):
    if not rows:
        raise RuntimeError('No closed candles returned; no files written')
    output.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame['datetime'] = pd.to_datetime(frame['datetime'], unit='ms', utc=True)
    # Excel cannot represent timezone-aware timestamps. Both exports use UTC.
    frame['datetime'] = frame['datetime'].dt.tz_localize(None)
    stem = output / f'Binance_{symbol}_futures_1h_{start}_{end}'
    csv, xlsx = Path(str(stem) + '.csv'), Path(str(stem) + '.xlsx')
    if csv.exists() or xlsx.exists():
        raise FileExistsError('Output already exists; use a different --output-dir')
    frame.to_csv(csv, index=False)
    frame.to_excel(xlsx, index=False)
    gaps = int((frame['datetime'].diff().dropna() != pd.Timedelta(hours=1)).sum())
    print(f'{len(frame)} closed candles; UTC {frame.datetime.min()} ~ {frame.datetime.max()}; gaps={gaps}')
    print(f'Saved: {csv}\nSaved: {xlsx}')
    return csv, xlsx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol', default='SOLUSDT', help='USD-M symbol, e.g. SOLUSDT or ETHUSDT')
    parser.add_argument('--start', default='2020-01-01', help='ISO date/time; naive dates mean UTC')
    parser.add_argument('--end', help='Exclusive ISO end time; defaults to current UTC hour')
    parser.add_argument('--output-dir', type=Path, default=Path('data'))
    args = parser.parse_args()
    try:
        start = timestamp(args.start)
        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        end = min(timestamp(args.end) if args.end else now, now // HOUR_MS * HOUR_MS)
        if start + HOUR_MS > end:
            raise ValueError('The range must contain at least one closed hourly candle')
        symbol = args.symbol.upper()
        if not symbol.isalnum() or not symbol.endswith('USDT'):
            raise ValueError('Use a USDT futures symbol such as SOLUSDT or ETHUSDT')
        exchange = ccxt.binanceusdm({'enableRateLimit': True, 'timeout': 20000, 'requests_trust_env': True})
        rows = collect(exchange, symbol, start, end)
        save(rows, args.output_dir, symbol, start, end)
    except (ValueError, RuntimeError, OSError, ccxt.BaseError) as exc:
        parser.exit(1, f'Collection failed: {exc}\n')


if __name__ == '__main__':
    main()
