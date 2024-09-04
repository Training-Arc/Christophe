from AlgorithmImports import *


class SimpleBollingerBands(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2024, 1, 1)
        self.SetCash(100000)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol

        self.bb = self.BB(self.symbol, 20, 2)

        self.SetBenchmark(self.symbol)
        self.SetWarmUp(timedelta(days=20))

        self.trade_count = 0
        self.initial_portfolio_value = 5000

    def OnData(self, data: Slice):
        if self.IsWarmingUp or not self.bb.IsReady:
            return

        if self.initial_portfolio_value is None:
            self.initial_portfolio_value = self.Portfolio.TotalPortfolioValue

        holdings = self.Portfolio[self.symbol].Quantity
        price = data[self.symbol].Close

        if not holdings and price < self.bb.LowerBand.Current.Value:
            self.SetHoldings(self.symbol, 1)
            self.trade_count += 1
        elif holdings > 0 and price > self.bb.UpperBand.Current.Value:
            self.Liquidate(self.symbol)
            self.trade_count += 1

    def OnEndOfAlgorithm(self):
        final_value = self.Portfolio.TotalPortfolioValue
        total_return = (final_value / self.initial_portfolio_value) - 1 if self.initial_portfolio_value else 0

        self.Log(f"Initial Portfolio Value: ${self.initial_portfolio_value}")
        self.Log(f"Final Portfolio Value: ${final_value}")
        self.Log(f"Total Return: {total_return:.2%}")
        self.Log(f"Total Trades: {self.trade_count}")