import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import ccxt
import pandas as pd
from fetch_eth_1h import HOUR_MS as H, collect, save, timestamp


def candle(t):
    return [t, '10', '12', '9', '11', '100']


class CollectorTests(unittest.TestCase):
    def test_pagination_overlap_and_open_candle(self):
        exchange = Mock()
        exchange.fapiPublicGetKlines.side_effect = [
            [candle(0), candle(H)], [candle(H), candle(2 * H), candle(3 * H)]
        ]
        rows = collect(exchange, 'SOLUSDT', 0, 3 * H)
        self.assertEqual([r[0] for r in rows], [0, H, 2 * H])
        self.assertEqual(exchange.fapiPublicGetKlines.call_args.args[0]['startTime'], 2 * H)

    @patch('fetch_eth_1h.time.sleep')
    def test_retry_is_bounded(self, sleep):
        exchange = Mock()
        exchange.fapiPublicGetKlines.side_effect = ccxt.NetworkError('offline')
        with self.assertRaises(ccxt.NetworkError):
            collect(exchange, 'SOLUSDT', 0, H, retries=2)
        self.assertEqual(exchange.fapiPublicGetKlines.call_count, 3)

    def test_non_transient_failure_is_not_retried(self):
        exchange = Mock()
        exchange.fapiPublicGetKlines.side_effect = ccxt.ExchangeError('denied')
        with self.assertRaises(ccxt.ExchangeError):
            collect(exchange, 'SOLUSDT', 0, H)
        self.assertEqual(exchange.fapiPublicGetKlines.call_count, 1)

    def test_stale_page_fails(self):
        exchange = Mock()
        exchange.fapiPublicGetKlines.return_value = [candle(0)]
        with self.assertRaises(RuntimeError):
            collect(exchange, 'SOLUSDT', H, 3 * H)

    def test_exports_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [[0, 10., 12., 9., 11., 100.]]
            csv, xlsx = save(rows, Path(tmp), 'SOLUSDT', 0, H)
            for frame in [pd.read_csv(csv), pd.read_excel(xlsx)]:
                self.assertEqual(len(frame), 1)
                self.assertEqual(frame.iloc[0]['close'], 11)
            with self.assertRaises(FileExistsError):
                save(rows, Path(tmp), 'SOLUSDT', 0, H)

    def test_empty_response_does_not_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                save([], Path(tmp), 'SOLUSDT', 0, H)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_dates_are_utc(self):
        self.assertEqual(timestamp('1970-01-01'), 0)
        self.assertEqual(timestamp('1970-01-01T09:00:00+09:00'), 0)


if __name__ == '__main__':
    unittest.main()
