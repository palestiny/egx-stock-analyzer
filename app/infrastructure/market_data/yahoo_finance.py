from datetime import date, datetime, timezone
from decimal import Decimal

from app.domain.fundamental_analysis.financial_period import FinancialPeriod
from app.domain.market_data.raw_observation import RawPriceBarObservation
from app.domain.market_data.timeframe import Timeframe
from app.domain.stocks.stock import Stock


class YahooFinanceHistoryClient:
    def __init__(self, yfinance_module) -> None:
        self._yfinance = yfinance_module

    def history(self, ticker: str, start: date, end: date) -> list[dict]:
        return (
            self._yfinance.Ticker(ticker)
            .history(
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,
            )
            .reset_index()
            .to_dict("records")
        )


class YahooFinanceFundamentalDataSource:
    """Reads annual income and balance-sheet data from Yahoo Finance."""

    def __init__(self, yfinance_module) -> None:
        self._yfinance = yfinance_module

    def get_periods(
        self,
        stock: Stock,
        as_of: date,
    ) -> tuple[FinancialPeriod, FinancialPeriod]:
        ticker = self._yfinance.Ticker(f"{stock.symbol}.CA")
        income_statement = ticker.income_stmt
        balance_sheet = ticker.balance_sheet

        income_rows = self._dataframe_to_rows(income_statement)
        balance_rows = self._dataframe_to_rows(balance_sheet)

        periods = self._merge_periods(income_rows, balance_rows, as_of)
        if len(periods) < 2:
            raise ValueError(
                "Yahoo Finance did not return two usable annual financial periods"
            )
        return periods[0], periods[1]

    @classmethod
    def _dataframe_to_rows(cls, dataframe) -> list[dict]:
        if dataframe is None or dataframe.empty:
            return []

        rows: list[dict] = []
        for column in dataframe.columns:
            row = {"period": cls._period_date(column)}
            for index, value in dataframe[column].items():
                row[str(index)] = value
            rows.append(row)
        return rows

    @classmethod
    def _merge_periods(
        cls,
        income_rows: list[dict],
        balance_rows: list[dict],
        as_of: date,
    ) -> list[FinancialPeriod]:
        balance_by_period = {
            row["period"]: row
            for row in balance_rows
            if row.get("period") is not None
        }

        merged: list[FinancialPeriod] = []
        for income_row in income_rows:
            period_end = income_row.get("period")
            if period_end is None or period_end > as_of:
                continue

            revenue = cls._decimal(
                cls._first_present(income_row, "Total Revenue", "Operating Revenue")
            )
            net_income = cls._decimal(
                cls._first_present(
                    income_row,
                    "Net Income",
                    "Net Income Common Stockholders",
                    "Net Income Including Noncontrolling Interests",
                )
            )
            if revenue is None or net_income is None:
                continue

            balance_row = balance_by_period.get(period_end, {})
            merged.append(
                FinancialPeriod(
                    period_end=period_end,
                    revenue=revenue,
                    net_income=net_income,
                    current_assets=cls._decimal(
                        cls._first_present(
                            balance_row,
                            "Current Assets",
                            "Total Current Assets",
                        )
                    ),
                    current_liabilities=cls._decimal(
                        cls._first_present(
                            balance_row,
                            "Current Liabilities",
                            "Total Current Liabilities",
                        )
                    ),
                )
            )

        return sorted(
            merged,
            key=lambda period: period.period_end,
            reverse=True,
        )

    @staticmethod
    def _first_present(row: dict, *keys: str):
        for key in keys:
            value = row.get(key)
            if value is not None:
                return value
        return None

    @staticmethod
    def _period_date(value) -> date | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    @staticmethod
    def _decimal(value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def close(self) -> None:
        return None


class YahooFinanceAdapter:
    def __init__(self, history_client) -> None:
        self._history_client = history_client

    @staticmethod
    def _provider_symbol(stock: Stock) -> str:
        return f"{stock.symbol}.CA"

    @staticmethod
    def _timestamp(value) -> datetime:
        if isinstance(value, datetime):
            timestamp = value
        else:
            timestamp = datetime.combine(value, datetime.min.time())

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            return timestamp.replace(tzinfo=timezone.utc)

        return timestamp

    @staticmethod
    def _decimal(value) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def get_daily_observations(
        self,
        stock: Stock,
        from_date: date,
        to_date: date,
    ) -> list[RawPriceBarObservation]:
        rows = self._history_client.history(
            self._provider_symbol(stock),
            from_date,
            to_date,
        )

        return [
            RawPriceBarObservation(
                stock_id=stock.id,
                timeframe=Timeframe.DAILY,
                timestamp=self._timestamp(row["Date"]),
                open=self._decimal(row["Open"]),
                high=self._decimal(row["High"]),
                low=self._decimal(row["Low"]),
                close=self._decimal(row["Close"]),
                volume=None if row["Volume"] is None else int(row["Volume"]),
            )
            for row in rows
        ]
