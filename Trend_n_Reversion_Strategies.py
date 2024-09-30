from datetime import timedelta
from AlgorithmImports import *

class MomentumMeanReversionAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)  # Set Start Date
        self.SetCash(20000)  # Set Strategy Cash
        # Setting resolution to daily for the universe selection
        self.UniverseSettings.Resolution = Resolution.Daily
        self.AddEquity("SPY")
        self.AddUniverse(self.CoarseSelectionFunction)
        self.Schedule.On(self.DateRules.EveryDay("SPY"), self.TimeRules.AfterMarketOpen("SPY", 5), self.Rebalance)
        self.momentum_period = 90
        self.mean_reversion_period = 20
        self.number_of_stocks = 30
        self.stop_loss_percent = 0.95  # Stop loss at 5% below purchase price
        self.symbols = []
        self.next_rebalance_time = self.Time
        self.stop_loss_orders = {}
        self.std_dev_indicators = {}
        #self.SetWarmUp(30, Resolution.Daily)

    def CoarseSelectionFunction(self, coarse):
        if self.Time < self.next_rebalance_time:
            return Universe.Unchanged

        filtered = filter(lambda x: x.HasFundamentalData and x.Price > 5, coarse)
        sorted_by_dollar_volume = sorted(filtered, key=lambda x: x.DollarVolume, reverse=True)
        selected_symbols = [x.Symbol for x in sorted_by_dollar_volume[:200]]

        self.symbols = selected_symbols[:self.number_of_stocks]
        return self.symbols

    def Rebalance(self):
        if self.Time < self.next_rebalance_time:
            return
        
        # Calculate momentum and mean reversion scores
        momentum_scores = self.CalculateMomentumScores(self.symbols)
        mean_reversion_scores = self.CalculateMeanReversionScores(self.symbols)

        # Select symbols based on scores
        selected_symbols = self.SelectSymbols(momentum_scores, mean_reversion_scores)

        # Liquidate and invest
        self.LiquidateUnselectedSymbols(selected_symbols)
        for symbol in selected_symbols:
            if not self.Portfolio[symbol].Invested:
                self.SetHoldings(symbol, 1 / len(selected_symbols))

        self.next_rebalance_time = self.Time + timedelta(30)

    def CalculateMomentumScores(self, symbols):
        scores = {}
        for symbol in symbols:
            history = self.History(symbol, self.momentum_period, Resolution.Daily)
            if not history.empty:
                momentum = (history["close"][-1] - history["close"][0]) / history["close"][0]
                scores[symbol] = momentum
        return scores

    def CalculateMeanReversionScores(self, symbols):
        scores = {}
        for symbol in symbols:
            history = self.History(symbol, self.mean_reversion_period, Resolution.Daily)
            if not history.empty and len(history["close"]) > 1:
                rolling_mean = history["close"].mean()
                rolling_std = history["close"].std()
                current_price = history["close"][-1]
                z_score = (current_price - rolling_mean) / rolling_std
                scores[symbol] = -z_score  # Negative Z-score for mean reversion
        return scores

    def SelectSymbols(self, momentum_scores, mean_reversion_scores):
        sorted_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        sorted_mean_reversion = sorted(mean_reversion_scores.items(), key=lambda x: x[1])
        
        # Example selection: top N/2 from each strategy
        top_momentum = {x[0] for x in sorted_momentum[:self.number_of_stocks // 2]}
        top_mean_reversion = {x[0] for x in sorted_mean_reversion[:self.number_of_stocks // 2]}

        return top_momentum.union(top_mean_reversion)

    def LiquidateUnselectedSymbols(self, selected_symbols):
        for symbol in self.Portfolio.Keys:
            if symbol not in selected_symbols and self.Portfolio[symbol].Invested:
                self.Liquidate(symbol)

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled and orderEvent.OrderId in self.stop_loss_orders.values():
            symbol = orderEvent.Symbol
            self.Debug(f"Stop loss triggered for {symbol}")
            keys_to_remove = [key for key, value in self.stop_loss_orders.items() if value == orderEvent.OrderId]
            for key in keys_to_remove:
                del self.stop_loss_orders[key]


    def SelectSymbols(self, momentum_scores, mean_reversion_scores):
        sorted_momentum = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        sorted_mean_reversion = sorted(mean_reversion_scores.items(), key=lambda x: x[1])
        
        # Example selection: top N/2 from each strategy
        top_momentum = {x[0] for x in sorted_momentum[:self.number_of_stocks // 2]}
        top_mean_reversion = {x[0] for x in sorted_mean_reversion[:self.number_of_stocks // 2]}

        return top_momentum.union(top_mean_reversion)

    def LiquidateUnselectedSymbols(self, selected_symbols):
        for symbol in self.Portfolio.Keys:
            if symbol not in selected_symbols and self.Portfolio[symbol].Invested:
                self.Liquidate(symbol)

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled and orderEvent.OrderId in self.stop_loss_orders.values():
            symbol = orderEvent.Symbol
            self.Debug(f"Stop loss triggered for {symbol}")
            keys_to_remove = [key for key, value in self.stop_loss_orders.items() if value == orderEvent.OrderId]
            for key in keys_to_remove:
                del self.stop_loss_orders[key]
