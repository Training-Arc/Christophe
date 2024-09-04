import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt


def get_bollinger_bands(data, window=20, num_std=2):
    rolling_mean = data['Close'].rolling(window=window).mean()
    rolling_std = data['Close'].rolling(window=window).std()

    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)

    return rolling_mean, upper_band, lower_band


def implement_bollinger_band_strategy(data):
    data['Middle Band'], data['Upper Band'], data['Lower Band'] = get_bollinger_bands(data)

    data['Buy Signal'] = np.where(data['Close'] <= data['Lower Band'], 1, 0)
    data['Sell Signal'] = np.where(data['Close'] >= data['Upper Band'], -1, 0)

    data['Position'] = data['Buy Signal'] + data['Sell Signal']
    data['Strategy Returns'] = data['Position'].shift(1) * data['Close'].pct_change()

    return data


# Download sample data
symbol = 'AAPL'
start_date = '2022-01-01'
end_date = '2023-01-01'
data = yf.download(symbol, start=start_date, end=end_date)

# Implement strategy
strategy_data = implement_bollinger_band_strategy(data)

# Calculate cumulative returns
strategy_data['Cumulative Returns'] = (1 + strategy_data['Strategy Returns']).cumprod()
buy_and_hold_returns = (1 + data['Close'].pct_change()).cumprod()

# Plot results
plt.figure(figsize=(12, 8))
plt.plot(strategy_data.index, strategy_data['Close'], label='Close Price')
plt.plot(strategy_data.index, strategy_data['Upper Band'], label='Upper Band', linestyle='--')
plt.plot(strategy_data.index, strategy_data['Middle Band'], label='Middle Band', linestyle='--')
plt.plot(strategy_data.index, strategy_data['Lower Band'], label='Lower Band', linestyle='--')
plt.scatter(strategy_data[strategy_data['Buy Signal'] == 1].index,
            strategy_data[strategy_data['Buy Signal'] == 1]['Close'],
            marker='^', color='g', label='Buy Signal')
plt.scatter(strategy_data[strategy_data['Sell Signal'] == -1].index,
            strategy_data[strategy_data['Sell Signal'] == -1]['Close'],
            marker='v', color='r', label='Sell Signal')
plt.title(f'Bollinger Bands Strategy for {symbol}')
plt.legend()
plt.show()

# Plot cumulative returns
plt.figure(figsize=(12, 6))
plt.plot(strategy_data.index, strategy_data['Cumulative Returns'], label='Strategy Returns')
plt.plot(strategy_data.index, buy_and_hold_returns, label='Buy and Hold Returns')
plt.title(f'Cumulative Returns: Strategy vs Buy and Hold for {symbol}')
plt.legend()
plt.show()

print(f"Total Strategy Return: {strategy_data['Cumulative Returns'].iloc[-1]:.2f}")
print(f"Total Buy and Hold Return: {buy_and_hold_returns.iloc[-1]:.2f}")