import math
import pandas as pd


def rsi(series, length):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(length).mean()
    loss = (-delta.clip(upper=0)).rolling(length).mean()
    rs = gain / loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def atr(df, length):
    high_low = df["High"] - df["Low"]
    high_close = (df["High"] - df["Close"].shift()).abs()
    low_close = (df["Low"] - df["Close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(length).mean()


def build_technical_snapshot(df, cfg):
    close = df["Close"]
    volume = df["Volume"]
    sma_fast = close.rolling(cfg["sma_fast"]).mean()
    sma_slow = close.rolling(cfg["sma_slow"]).mean()
    rsi_series = rsi(close, cfg["rsi_length"])
    atr_series = atr(df, cfg["atr_length"])
    high_n = close.rolling(cfg["breakout_lookback"]).max()
    low_n = df["Low"].rolling(cfg["breakout_lookback"]).min()
    vol_avg = volume.rolling(cfg["volume_lookback"]).mean()

    last_close = float(close.iloc[-1])
    last_sma_fast = float(sma_fast.iloc[-1])
    last_sma_slow = float(sma_slow.iloc[-1])
    last_rsi = float(rsi_series.iloc[-1])
    last_atr = float(atr_series.iloc[-1])
    last_atr_pct = float((last_atr / close.iloc[-1]) * 100)
    breakout = last_close >= float(high_n.iloc[-2]) if len(high_n) > 1 else False
    recent_high = float(high_n.iloc[-2]) if len(high_n) > 1 else last_close
    recent_low = float(low_n.iloc[-1]) if len(low_n) > 0 else last_close
    volume_confirm = float(volume.iloc[-1]) >= float(vol_avg.iloc[-1]) * cfg["volume_multiple_min"]

    checks = [
        last_close > last_sma_fast > last_sma_slow,
        cfg["rsi_min"] <= last_rsi <= cfg["rsi_max"],
        breakout,
        volume_confirm,
        last_atr_pct <= cfg["atr_pct_max"],
    ]
    passed = sum(1 for x in checks if x)
    score = round((passed / len(checks)) * 100, 2)

    return {
        "score": score,
        "close": round(last_close, 4),
        "sma_fast": round(last_sma_fast, 4),
        "sma_slow": round(last_sma_slow, 4),
        "rsi": round(last_rsi, 2) if not math.isnan(last_rsi) else None,
        "atr_pct": round(last_atr_pct, 2) if not math.isnan(last_atr_pct) else None,
        "atr_abs": round(last_atr, 4) if not math.isnan(last_atr) else None,
        "breakout": breakout,
        "volume_confirm": volume_confirm,
        "recent_high": round(recent_high, 4),
        "recent_low": round(recent_low, 4),
    }