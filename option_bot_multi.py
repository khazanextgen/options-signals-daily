from ib_insync import *
import json
import os
import time

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=4)

# ✅ GitHub signal folder
SIGNAL_FOLDER = '/Users/khazashareef/Documents/2025/bot/options-signals-daily/signals'
active_trades = {}

def load_signals():
    files = [f for f in os.listdir(SIGNAL_FOLDER) if f.endswith('.json')]
    signals = {}
    for file in files:
        with open(os.path.join(SIGNAL_FOLDER, file)) as f:
            try:
                signal = json.load(f)
                symbol = signal['symbol']
                signals[file] = signal
            except Exception as e:
                print(f"⚠️ Failed to load {file}: {e}")
    return signals

def setup_market_data(signal):
    stock = Stock(signal['symbol'], 'SMART', 'USD')
    option = Option(
        signal['symbol'],
        signal['expiry'],
        float(signal['strike']),
        signal['type'][0],  # C or P
        'SMART'
    )
    ib.qualifyContracts(stock)
    ib.qualifyContracts(option)
    stock_data = ib.reqMktData(stock, '', False, False)
    option_data = ib.reqMktData(option, '', False, False)
    return stock_data, option_data, stock, option

signals = load_signals()
for fname, signal in signals.items():
    stock_data, option_data, stock, option = setup_market_data(signal)
    active_trades[fname] = {
        "signal": signal,
        "stock": stock,
        "option": option,
        "stock_data": stock_data,
        "option_data": option_data,
        "position_open": False,
        "sold_tp1": False
    }

print(f"✅ Monitoring {len(active_trades)} signals...")

while True:
    ib.sleep(1)
    for fname, trade in list(active_trades.items()):
        s = trade['signal']
        stock_price = float(trade['stock_data'].last)
        option_price = float(trade['option_data'].last)

        print(f"[{s['symbol']}] Stock: {stock_price:.2f}, Option: {option_price:.2f}")

        if not trade["position_open"] and stock_price >= s['entry_trigger'] and option_price <= s['limit_price"]:
            order = LimitOrder('BUY', s['contracts'], option_price)
            ib.placeOrder(trade['option'], order)
            trade["position_open"] = True
            print(f"🎯 Bought {s['contracts']} {s['symbol']} {s['strike']}C @ {option_price:.2f}")

        elif trade["position_open"]:
            if not trade["sold_tp1"] and option_price >= s['take_profit_1']:
                ib.placeOrder(trade['option'], LimitOrder('SELL', s['contracts']//2, option_price))
                trade["sold_tp1"] = True
                print(f"💰 TP1 hit on {s['symbol']} @ {option_price:.2f}")

            elif trade["sold_tp1"] and option_price >= s['take_profit_2']:
                ib.placeOrder(trade['option'], LimitOrder('SELL', s['contracts'] - (s['contracts']//2), option_price))
                print(f"🚀 TP2 hit on {s['symbol']} @ {option_price:.2f}")
                del active_trades[fname]

            elif option_price <= s['stop_loss']:
                ib.placeOrder(trade['option'], LimitOrder('SELL', s['contracts'], option_price))
                print(f"🛑 SL hit on {s['symbol']} @ {option_price:.2f}")
                del active_trades[fname]

    if not active_trades:
        print("✅ All trades complete.")
        break

ib.disconnect()
print("📘 Bot stopped.")
