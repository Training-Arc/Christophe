from AlgorithmImports import *


class BollingerBands(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2013, 10, 7)
        self.SetEndDate(2013, 10, 11)
        self.SetCash(100000)

        self.symbol = self.AddEquity("SPY", Resolution.Daily).Symbol

        self.bb = self.BB(self.symbol, 20, 2)

        self.SetBenchmark(self.symbol)
        self.SetWarmUp(20)

        self.trade_count = 0

    def OnData(self, data: Slice):
        if self.IsWarmingUp:
            return

        if not self.bb.IsReady:
            return

        holdings = self.Portfolio[self.symbol].Quantity

        if not holdings and data[self.symbol].Close < self.bb.LowerBand.Current.Value:
            self.SetHoldings(self.symbol, 1)
            self.Log(f"Buying SPY at {data[self.symbol].Close}")
            self.trade_count += 1
        elif holdings > 0 and data[self.symbol].Close > self.bb.UpperBand.Current.Value:
            self.Liquidate(self.symbol)
            self.Log(f"Selling SPY at {data[self.symbol].Close}")
            self.trade_count += 1

        self.Plot("BB", "Middle", self.bb.MiddleBand.Current.Value)
        self.Plot("BB", "Upper", self.bb.UpperBand.Current.Value)
        self.Plot("BB", "Lower", self.bb.LowerBand.Current.Value)
        self.Plot("BB", "Price", data[self.symbol].Close)

    def OnEndOfAlgorithm(self):
        self.Log(f"Final Portfolio Value: ${self.Portfolio.TotalPortfolioValue}")
        self.Log(f"Total Profit: ${self.Portfolio.TotalProfit}")
        self.Log(f"Total Trades: {self.trade_count}")
        self.Log(f"Sharpe Ratio: {self.Portfolio.SharpeRatio}")
        self.Log(f"Drawdown: {self.Portfolio.TotalDrawdown}")
        self.Log(f"Annual Return: {self.Portfolio.TotalPortfolioValue / self.Portfolio.StartingCash - 1}")
        self.Log(f"Win Rate: {self.Portfolio.WinRate}")
        self.Log(f"Loss Rate: {self.Portfolio.LossRate}")
        self.Log(f"Avg Win: {self.Portfolio.AverageWinRate}")
        self.Log(f"Avg Loss: {self.Portfolio.AverageLossRate}")