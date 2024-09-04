from AlgorithmImports import *


class SimpleBollingerBands(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2024, 1, 1)
        self.SetCash(100000)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol

        self.bb = self.BB(self.symbol, 20, 2)

        self.SetBenchmark(self.symbol)
        self.SetWarmUp(20)

        self.trade_count = 0

    def OnData(self, data: Slice):
        if self.IsWarmingUp or not self.bb.IsReady:
            return

        holdings = self.Portfolio[self.symbol].Quantity
        price = data[self.symbol].Close

        if not holdings and price < self.bb.LowerBand.Current.Value:
            self.SetHoldings(self.symbol, 1)
            self.trade_count += 1
        elif holdings > 0 and price > self.bb.UpperBand.Current.Value:
            self.Liquidate(self.symbol)
            self.trade_count += 1

    def OnEndOfAlgorithm(self):
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue}")
        self.Log(f"Total Profit: ${self.Portfolio.TotalProfit}")
        self.Log(f"Total Trades: {self.trade_count}")
        self.Log(f"Sharpe Ratio: {self.Portfolio.SharpeRatio}")
        self.Log(f"Drawdown: {self.Portfolio.TotalDrawdown}")
        self.Log(f"Annual Return: {(self.Portfolio.TotalPortfolioValue / self.Portfolio.StartingCash - 1) * 100}%")
        self.Log(f"Win Rate: {self.Portfolio.WinRate * 100}%")
        self.Log(f"Loss Rate: {self.Portfolio.LossRate * 100}%")