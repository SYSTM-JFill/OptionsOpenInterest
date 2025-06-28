import yfinance as yf
import pandas as pd
from datetime import datetime

def get_stock_price(symbol):
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.history(period="1d")['Close'].iloc[0]  # changed here
        return price
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

def get_latest_friday():
    today = datetime.today()
    offset = (today.weekday() - 4) % 7  # 4 = Friday
    last_friday = today - pd.Timedelta(days=offset)
    return last_friday.strftime('%Y-%m-%d')

def fetch_options_latest_friday(symbol):
    try:
        ticker = yf.Ticker(symbol)
        expirations = ticker.options
        if not expirations:
            print("No options data available.")
            return None, None

        latest_friday = datetime.strptime(get_latest_friday(), '%Y-%m-%d')
        expiration_dates = [datetime.strptime(date, '%Y-%m-%d') for date in expirations]

        # Find expiration on or after latest Friday
        selected_exp = min((d for d in expiration_dates if d >= latest_friday), default=expiration_dates[-1])
        selected_exp_str = selected_exp.strftime('%Y-%m-%d')

        option_chain = ticker.option_chain(selected_exp_str)
        calls = option_chain.calls
        puts = option_chain.puts

        calls['type'] = 'call'
        puts['type'] = 'put'
        options_df = pd.concat([calls, puts])

        return options_df, selected_exp_str
    except Exception as e:
        print(f"Error fetching options data: {e}")
        return None, None

def find_max_pain(options_df, current_price=None, window_pct=0.1):
    strikes = options_df['strike'].unique()
    pain = {}
    for strike in strikes:
        calls_oi = options_df[(options_df['type'] == 'call') & (options_df['strike'] == strike)]['openInterest'].sum()
        puts_oi = options_df[(options_df['type'] == 'put') & (options_df['strike'] == strike)]['openInterest'].sum()
        pain[strike] = calls_oi + puts_oi

    global_max_pain = max(pain, key=pain.get)

    local_max_pain = None
    if current_price:
        lower_bound = current_price * (1 - window_pct)
        upper_bound = current_price * (1 + window_pct)
        nearby = {strike: value for strike, value in pain.items() if lower_bound <= strike <= upper_bound}
        if nearby:
            local_max_pain = max(nearby, key=nearby.get)

    return global_max_pain, local_max_pain

def calculate_atr(symbol, period_days=14):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo", interval="1d")

        if hist.empty or len(hist) < period_days:
            return None

        hist['H-L'] = hist['High'] - hist['Low']
        hist['H-PC'] = abs(hist['High'] - hist['Close'].shift(1))
        hist['L-PC'] = abs(hist['Low'] - hist['Close'].shift(1))
        hist['TR'] = hist[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        hist['ATR'] = hist['TR'].rolling(window=period_days).mean()

        return hist['ATR'].iloc[-1]
    except Exception as e:
        print(f"ATR Calculation Error: {e}")
        return None
