# region imports
from AlgorithmImports import *
# endregion

class Bollingerbands(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2013, 10, 7)
        self.set_end_date(2013, 10, 11)
        self.set_cash(1000000)
        self.symbol = self.add_equity("SPY", Resolution.Daily)

        # Initialize plots
        self.plot("Equity", "Strategy Equity", self.portfolio.total_portfolio_value)

    def on_data(self, data: Slice):
        if not self.portfolio.invested:
            self.set_holdings("SPY", 1)
            self.debug("Purchased Stock")

        # Update plots
        self.plot("Equity", "Strategy Equity", self.portfolio.total_portfolio_value)
        if data.bars.get(self.symbol):
            self.plot("Price", "SPY", data[self.symbol].close)

    def on_end_of_algorithm(self):
        self.log(f"Final Portfolio Value: ${self.portfolio.total_portfolio_value}")
        self.log(f"Total Profit: ${self.portfolio.total_profit}")
        self.log(f"Total Trades: {self.portfolio.transactions.count()}")
