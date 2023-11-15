# -*- coding: utf-8 -*-
"""004.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1KKvFcYsZwrDtY05yLUCRvg87Yc6tlYlW
"""

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, accuracy_score, make_scorer
from sklearn.svm import SVC
from scipy.optimize import minimize
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

from sklearn.model_selection import train_test_split

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense,Conv1D, MaxPooling1D, Flatten,LSTM


# Import datasets
train_data = pd.read_csv("aapl_5m_train.csv")
validation_data = pd.read_csv("aapl_5m_validation.csv")

# Data preparation
df = train_data.loc[:,['Datetime','Close']].set_index("Datetime")

df1 = df.shift(periods=-1)
df2 = df1.shift(periods=-1)
df3 = df2.shift(periods=-1)
df4 = df3.shift(periods=-1)

a = pd.DataFrame({})

a['X1'] = df
a['X2'] = df1
a['X3'] = df2
a['X4'] = df3
a['X5'] = df4

a["Y"] = a["X5"].shift(-5) > a["X5"]

a = a.dropna()

# Variables
x = a.drop('Y', axis = 1)
y = a['Y']

y_int = y.astype(int)

# Create binary numbers(convert 1s to 1s & 2s to 0s)
array_binario = np.where(y_int == 1, 1, 0)

# Split the data into a training set (70%) and a test set (30%)
X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.3, random_state=42)

# Standardize (mejor sin el)
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


def generate_signals(predictions, buy_hold_period=5):
    signals = []

    # Variable para rastrear el tiempo desde la última señal de compra
    time_since_last_buy = 0

    for pred in predictions:
        if pred <= 0.49:  # Condición para generar señal de compra
            signals.append("Buy")
            time_since_last_buy = 0
        elif time_since_last_buy < buy_hold_period:
            signals.append("Hold")
            time_since_last_buy += 1
        else:
            signals.append("Sell")
            time_since_last_buy = 0

    return signals

def generate_signals(predictions, buy_hold_period=5):
    signals = []

    # Variable para rastrear el tiempo desde la última señal de compra
    time_since_last_buy = 0

    # Obtener la media de las predicciones
    mean_prediction = np.mean(predictions)

    for pred in predictions:
        if pred <= mean_prediction:  # Condición para generar señal de compra
            signals.append("Buy")
            time_since_last_buy = 0
        elif time_since_last_buy < buy_hold_period:
            signals.append("Hold")
            time_since_last_buy += 1
        else:
            signals.append("Sell")
            time_since_last_buy = 0

    return signals

# MLP Model Training
model_mlp = Sequential()
model_mlp.add(Dense(64, input_dim=x.shape[1], activation='relu'))
model_mlp.add(Dense(32, activation='relu'))
model_mlp.add(Dense(1, activation='sigmoid'))

model_mlp.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model_mlp.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.2)

# Generate MLP predictions
mlp_pred = model_mlp.predict(X_test).flatten()

# Generate trading signals for MLP
mlp_signals = generate_signals(mlp_pred)

pd.Series(mlp_signals).value_counts()

honda=[mlp_pred.mean(),
mlp_pred.min(),
mlp_pred.max()]
honda

# RNN Model Training
model_rnn = Sequential()
model_rnn.add(LSTM(128, input_shape=(X_train.shape[1], 1), return_sequences=True))
model_rnn.add(LSTM(64))
model_rnn.add(Dense(1, activation='sigmoid'))

model_rnn.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model_rnn.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.2)

# Generate RNN predictions
rnn_pred = model_rnn.predict(X_test).flatten()

# Generate trading signals for RNN
rnn_signals = generate_signals(rnn_pred)

# CNN Model Training
model_cnn = Sequential()
model_cnn.add(Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=(X_train.shape[1], 1)))
model_cnn.add(MaxPooling1D(pool_size=2))
model_cnn.add(Flatten())
model_cnn.add(Dense(1, activation='sigmoid'))

model_cnn.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
model_cnn.fit(X_train, y_train, epochs=10, batch_size=32, validation_split=0.2)

# Generate CNN predictions
cnn_pred = model_cnn.predict(X_test).flatten()

# Generate trading signals for CNN
cnn_signals = generate_signals(cnn_pred)

"""Backtesting MLP RNN y CNN"""

# Backtesting
commission = 0.0025
stop_loss = 0.025
take_profit = 0.025
initial_cash = 10_000

class Backtester:
    def __init__(self, signals, prices, initial_cash, commission=0.0025, stop_loss=0.025, take_profit=0.025):
        self.signals = signals
        self.prices = prices
        self.cash = initial_cash
        self.portfolio_value = [initial_cash]
        self.positions = 0
        self.commission = commission
        self.stop_loss = stop_loss
        self.take_profit = take_profit

    def backtest(self):
        for i in range(len(self.signals)):
            if self.signals[i] == "Buy":
                # Execute a buy order
                price = self.prices[i]
                max_buyable = self.cash // price
                self.positions += max_buyable
                self.cash -= max_buyable * price
                # Apply commission
                self.cash -= max_buyable * price * self.commission
                # Update stop-loss and take-profit levels
                stop_loss_price = price * (1 - self.stop_loss)
                take_profit_price = price * (1 + self.take_profit)

            elif self.signals[i] == "Sell":
                # Execute a sell order
                price = self.prices[i]
                self.cash += self.positions * price
                self.positions = 0
                # Apply commission
                self.cash -= self.positions * price * self.commission

            # Check for stop-loss or take-profit conditions
            if self.positions > 0:
                if price <= stop_loss_price or price >= take_profit_price:
                    # Execute a sell order if stop-loss or take-profit conditions are met
                    self.cash += self.positions * price
                    self.positions = 0
                    # Apply commission
                    self.cash -= self.positions * price * self.commission

            self.portfolio_value.append(self.cash + self.positions * self.prices[i])

# Create Backtester instances for each model
backtester_mlp = Backtester(mlp_signals, validation_data["Close"], initial_cash, commission, stop_loss, take_profit)
backtester_rnn = Backtester(rnn_signals, validation_data["Close"], initial_cash, commission, stop_loss, take_profit)
backtester_cnn = Backtester(cnn_signals, validation_data["Close"], initial_cash, commission, stop_loss, take_profit)

# Backtest the strategies
backtester_mlp.backtest()
backtester_rnn.backtest()
backtester_cnn.backtest()

# Get the portfolio values over time
portfolio_value_mlp = backtester_mlp.portfolio_value
portfolio_value_rnn = backtester_rnn.portfolio_value
portfolio_value_cnn = backtester_cnn.portfolio_value

# Backtest MLP strategy
backtester_mlp = Backtester(mlp_signals, validation_data["Close"], initial_cash, commission, stop_loss, take_profit)
backtester_mlp.backtest()
portfolio_value_mlp = backtester_mlp.portfolio_value
profit_mlp = calculate_profit(portfolio_value_mlp)

# Print MLP signals for debugging
print("MLP Signals:", mlp_signals)

# Backtest RNN strategy
backtester_rnn = Backtester(rnn_signals, validation_data["Close"], initial_cash, commission, stop_loss, take_profit)
backtester_rnn.backtest()
portfolio_value_rnn = backtester_rnn.portfolio_value
profit_rnn = calculate_profit(portfolio_value_rnn)

# Print RNN signals for debugging
print("RNN Signals:", rnn_signals)

# Backtest CNN strategy
backtester_cnn = Backtester(cnn_signals, validation_data["Close"], initial_cash, commission, stop_loss, take_profit)
backtester_cnn.backtest()
portfolio_value_cnn = backtester_cnn.portfolio_value
profit_cnn = calculate_profit(portfolio_value_cnn)

# Print CNN signals for debugging
print("CNN Signals:", cnn_signals)

# Print results
print(f"MLP Profit: {profit_mlp:.2f}")
print(f"RNN Profit: {profit_rnn:.2f}")
print(f"CNN Profit: {profit_cnn:.2f}")

"""Checar señales para ver restirccion que si no hay buy no pueda vender"""

import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Function to plot candlestick chart
def plot_candlestick(data, title='Candlestick Chart'):
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                                          open=data['Open'],
                                          high=data['High'],
                                          low=data['Low'],
                                          close=data['Close'])])
    fig.update_layout(title=title, xaxis_title='Date', yaxis_title='Price')
    fig.show()

# Plot candlestick chart for validation data
plot_candlestick(validation_data)

# Function to plot portfolio value over time
def plot_portfolio_value(portfolio_values, title='Portfolio Value Over Time'):
    plt.figure(figsize=(10, 6))
    plt.plot(portfolio_values)
    plt.title(title)
    plt.xlabel('Time')
    plt.ylabel('Portfolio Value')
    plt.show()

# Plot portfolio value over time for each model
plot_portfolio_value(portfolio_value_mlp, title='MLP Portfolio Value Over Time')
plot_portfolio_value(portfolio_value_rnn, title='RNN Portfolio Value Over Time')
plot_portfolio_value(portfolio_value_cnn, title='CNN Portfolio Value Over Time')

# Function to plot model performance metrics
def plot_model_metrics(y_true, y_pred, model_name='Model'):
    cm = confusion_matrix(y_true, y_pred)
    accuracy = accuracy_score(y_true, y_pred)

    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title(f'{model_name} Confusion Matrix')
    plt.colorbar()

    classes = ['Sell', 'Buy']
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes)
    plt.yticks(tick_marks, classes)

    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')
    plt.show()

    print(f'{model_name} Accuracy: {accuracy:.2f}')

# Plot model performance metrics for each model
plot_model_metrics(y_test, mlp_pred.round(), model_name='MLP')
plot_model_metrics(y_test, rnn_pred.round(), model_name='RNN')
plot_model_metrics(y_test, cnn_pred.round(), model_name='CNN')