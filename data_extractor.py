# This script was used by us to downlaod and establish the 'appl.csv' as a basis for our dataset. 
# It was downloaded at the 24th of July 2023 

## Imports 
import datetime
import os
import requests
import pandas as pd
import yfinance as yf

## Definition of needed functions 
def get_stock_names():
    '''
    Get the needed Stocks: Apple Ticker == 'AAPL'
    '''
    stock_names = ['AAPL']
    return stock_names


def calculate_technical_indicators(data):
    '''
    Given a dataframe of stock data, calculate the following technical indicators:
    Simple Moving Average (SMA)
    Exponential Moving Average (EMA)
    Moving Average Convergence Divergence (MACD)
    Relative Strength Index (RSI)
    Commodity Channel Index (CCI)
    Average Directional Index (ADX)
    '''
    # Calculate SMA with a period of 10
    sma = data["Close"].rolling(window=10).mean()

    # Calculate EMA with a period of 10
    ema = data["Close"].ewm(span=10, adjust=False).mean()

    # Calculate MACD with fast period of 12, slow period of 26, and signal period of 9
    ema_12 = data["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = data["Close"].ewm(span=26, adjust=False).mean()
    macd = ema_12 - ema_26
    signal = macd.ewm(span=9, adjust=False).mean()
    macdhist = macd - signal

    # Calculate RSI with a period of 14
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Calculate the CCI with a period of 20
    typical_price = (data["High"] + data["Low"] + data["Close"]) / 3
    cci = typical_price - typical_price.rolling(window=20).mean()
    cci /= 0.015 * typical_price.rolling(window=20).std()

    # Calculate the ADX
    tr = data["High"] - data["Low"]
    tr1 = data["High"] - data["Close"].shift(1)
    tr2 = data["Low"] - data["Close"].shift(1)
    tr = tr.combine(tr1, max)
    tr = tr.combine(tr2, max)
    tr = tr.fillna(0)
    tr_sum = tr.rolling(window=14).sum()
    tr_sum = tr_sum.fillna(0)
    dm_plus = data["High"] - data["High"].shift(1)
    dm_minus = data["Low"].shift(1) - data["Low"]
    dm_plus = dm_plus.where((dm_plus > 0) & (dm_plus > dm_minus), 0)
    dm_minus = dm_minus.where((dm_minus > 0) & (dm_minus > dm_plus), 0)
    dm_plus = dm_plus.fillna(0)
    dm_minus = dm_minus.fillna(0)
    dm_plus_ewm = dm_plus.ewm(span=14, adjust=False).mean()
    dm_minus_ewm = dm_minus.ewm(span=14, adjust=False).mean()
    di_plus = 100 * dm_plus_ewm / tr_sum
    di_minus = 100 * dm_minus_ewm / tr_sum
    dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
    adx = dx.ewm(span=14, adjust=False).mean()

    # Append the SMA, EMA, MACD, and RSI to the data
    data["SMA"] = sma
    data["EMA"] = ema
    data["MACD"] = macd
    data["Signal"] = signal
    data["MACD_Hist"] = macdhist
    data["RSI"] = rsi
    data["CCI"] = cci
    data["ADX"] = adx

    return data


def dataset_downloader(stock_name):
    '''
    Downloads stock data.
    '''
    # Replace all . with - in stock name (e.g. BRK.B -> BRK-B)
    stock_name = stock_name.replace('.', '-')
    data = yf.download(stock_name, progress=False) # progress=false to avoid printing progress bar

    # Calculate technical indicators
    data = calculate_technical_indicators(data)

    return data


def create_dataset(stock_names, data_folder):
    '''
    Given an array of stock tickers, create a csv for the last 5 years of data
    for each stock and save it the data folder.
    '''
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)

    stock_count = 0
    for stock_name in stock_names:
        stock_count += 1
        try:
            print("Downloading data for " + stock_name + " [" + str(stock_count) + "/" + str(len(stock_names)) + "]")
            data = dataset_downloader(stock_name)
            data.to_csv(data_folder + stock_name + '.csv')
        except Exception as e:
            print(e)


def dataloader(stock_name, data_folder, start_date, end_date):
    '''
    Given a stock ticker, data folder, start date and end date, load the data
    from the csv file and return it as a pandas dataframe.
    It loads data from start_date to end_date inclusive, unless end_date is past the latest date.
    '''
    with open(data_folder + stock_name + '.csv', mode='r') as f:
        data = pd.read_csv(f)
        data = data[(data['Date'] >= start_date) & (data['Date'] <= end_date)]
        return data


def label_buy_sell_hold(data, threshold=0.02):
    '''
    Given a column of values, calculate for each value the average of the next 5 values (1 week).
    If the value is [threshold] greater than the current price, append 1 for buy to the labels array.
    If the value is [threshold] less than the current price, append 2 for sell to the labels array.
    Otherwise, append 0 for hold.
    You can change the threshold to fit your trading risk tolerance.
    '''
    # We only want the first column of values (Close price), but only if it's a 2D array
    if len(data.shape) == 2:
        data = data[:, 0]

    # Convert data from (length, 1) to (length,)
    data = data.reshape(-1)
    labels = []
    for i in range(len(data)):
        if i + 5 < len(data):
            avg = data[i+1:i+6].mean()
            if avg > data[i] * 1 + threshold:
                labels.append(1)
            elif avg < data[i] * 1 - threshold:
                labels.append(2)
            else:
                labels.append(0)
        else: # If the last 5 values are not available, append whatever the last value is
            labels.append(labels[-1])
    
    return labels # Labels is a list of 0, 1 or 2


if __name__ == "__main__":
    stock_names = get_stock_names()
    # print(len(stock_names))
    print(stock_names)

    # This will download the entire history for each stock and save it to the data folder
    create_dataset(stock_names, 'data/')

    # This is how you load the data
    data = dataloader('AAPL', 'data/', '2023-03-07', '2023-03-10')
    print(data)