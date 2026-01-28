import pandas as pd
import numpy as np

from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from pandas.tseries.offsets import BDay, DateOffset


# =====================================================
# MAIN FUNCTION (SAFE FOR DJANGO PRODUCTION)
# =====================================================
def train_and_predict_stock(
    csv_path,
    time_steps=60,
    future_days=5,
    months_to_show=6,
    epochs=20,          # 🔥 reduced for web performance
    batch_size=32
):
    """
    Trains an LSTM model on a single stock CSV and predicts future prices.
    Returns JSON-serializable results for Django.
    """

    # =====================================================
    # LAZY IMPORT (CRITICAL FIX)
    # =====================================================
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input

    # =====================================================
    # LOAD & VALIDATE DATA
    # =====================================================
    df = pd.read_csv(csv_path)

    required_cols = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume'}
    if not required_cols.issubset(df.columns):
        raise ValueError("CSV file does not contain required OHLCV columns")

    # Remove bad rows
    df = df[pd.to_numeric(df['Open'], errors='coerce').notnull()]

    if len(df) < time_steps + 10:
        raise ValueError("Not enough data points for prediction")

    df[['Open', 'High', 'Low', 'Close', 'Volume']] = df[
        ['Open', 'High', 'Low', 'Close', 'Volume']
    ].astype(float)

    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
    df.set_index('Date', inplace=True)

    data = df[['Open', 'High', 'Low', 'Close', 'Volume']]

    # =====================================================
    # SCALE DATA
    # =====================================================
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data)

    # =====================================================
    # CREATE SEQUENCES
    # =====================================================
    def create_sequences(dataset, steps):
        X, y = [], []
        for i in range(steps, len(dataset)):
            X.append(dataset[i - steps:i])
            y.append(dataset[i, 3])  # Close price
        return np.array(X), np.array(y)

    X, y = create_sequences(scaled_data, time_steps)

    # =====================================================
    # TRAIN-TEST SPLIT
    # =====================================================
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    # =====================================================
    # BUILD MODEL
    # =====================================================
    model = Sequential([
        Input(shape=(X_train.shape[1], X_train.shape[2])),
        LSTM(64, return_sequences=True),
        Dropout(0.2),
        LSTM(64),
        Dropout(0.2),
        Dense(1)
    ])

    model.compile(optimizer='adam', loss='mean_squared_error')

    # =====================================================
    # TRAIN MODEL
    # =====================================================
    model.fit(
        X_train,
        y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_test, y_test),
        verbose=0
    )

    # =====================================================
    # EVALUATION METRICS
    # =====================================================
    y_pred = model.predict(X_test, verbose=0)

    dummy = np.zeros((len(y_test), 5))
    dummy[:, 3] = y_test
    y_test_actual = scaler.inverse_transform(dummy)[:, 3]

    dummy[:, 3] = y_pred.flatten()
    y_pred_actual = scaler.inverse_transform(dummy)[:, 3]

    mae = mean_absolute_error(y_test_actual, y_pred_actual)
    rmse = np.sqrt(mean_squared_error(y_test_actual, y_pred_actual))
    r2 = r2_score(y_test_actual, y_pred_actual)

    approx_accuracy = round(
        max(0, (1 - mae / np.mean(y_test_actual)) * 100), 2
    )

    # =====================================================
    # FUTURE PREDICTION
    # =====================================================
    last_window = scaled_data[-time_steps:]
    future_predictions = []

    for _ in range(future_days):
        X_input = np.array([last_window])
        pred_scaled = model.predict(X_input, verbose=0)

        next_day = last_window[-1].copy()
        next_day[3] = pred_scaled[0][0]

        # Approximate OHLC
        next_day[0] = next_day[3]
        next_day[1] = next_day[3] * 1.01
        next_day[2] = next_day[3] * 0.99

        last_window = np.vstack([last_window[1:], next_day])

        dummy = np.zeros((1, 5))
        dummy[0, 3] = pred_scaled[0][0]
        price = scaler.inverse_transform(dummy)[0, 3]

        future_predictions.append(round(price, 2))

    # =====================================================
    # TREND & ACTION
    # =====================================================
    last_close = data['Close'].iloc[-1]
    avg_future = np.mean(future_predictions)

    if avg_future > last_close * 1.01:
        trend, action = "UP", "BUY"
    elif avg_future < last_close * 0.99:
        trend, action = "DOWN", "SELL"
    else:
        trend, action = "NEUTRAL", "WAIT"

    confidence = round(
        min(abs(avg_future - last_close) / last_close * 100, 99), 2
    )

    # =====================================================
    # CHART DATA
    # =====================================================
    last_date = data.index[-1]

    future_dates = [
        (last_date + BDay(i)).strftime('%Y-%m-%d')
        for i in range(1, future_days + 1)
    ]

    start_date = last_date - DateOffset(months=months_to_show)
    recent_data = data.loc[start_date:last_date]

    chart_data = {
        "historical_dates": recent_data.index.strftime('%Y-%m-%d').tolist(),
        "historical_close": recent_data['Close'].round(2).tolist(),
        "future_dates": future_dates,
        "future_predictions": future_predictions
    }

    # =====================================================
    # FINAL RESPONSE
    # =====================================================
    return {
        "trend": trend,
        "confidence": confidence,
        "action": action,
        "metrics": {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(r2, 3),
            "accuracy": approx_accuracy
        },
        "chart_data": chart_data
    }
