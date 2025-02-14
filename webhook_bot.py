import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL
from binance.helpers import round_step_size

# 🔄 Környezeti változók betöltése
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

# 🔄 Binance kliens
client = Client(API_KEY, API_SECRET)

app = Flask(__name__)

# 📌 Webhook végpont
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        message = data.get("message", "")

        print(f"📩 Webhook érkezett: {message}")

        if "TRADE: BUY SOLUSDT" in message:
            place_order("SOLUSDT", SIDE_BUY)  
        elif "TRADE: SELL SOLUSDT" in message:
            place_order("SOLUSDT", SIDE_SELL)  
        elif "TRADE: CLOSE BUY SOLUSDT" in message:
            close_position("SOLUSDT", SIDE_SELL)  
        elif "TRADE: CLOSE SELL SOLUSDT" in message:
            close_position("SOLUSDT", SIDE_BUY)  

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f"⚠️ Webhook hiba: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400

# 📌 Market order nyitása
def place_order(symbol, side):
    try:
        usdt_balance = float(client.get_asset_balance(asset="USDT")["free"])
        trade_amount = usdt_balance * 0.50  # 50%-os egyenleggel tradelünk

        current_price = float(client.get_symbol_ticker(symbol=symbol)["price"])
        quantity = trade_amount / current_price

        info = client.get_symbol_info(symbol)
        step_size = float(info["filters"][2]["stepSize"])
        quantity = round_step_size(quantity, step_size)

        order = client.order_market(
            symbol=symbol,
            side=side,
            quantity=quantity
        )

        print(f"✅ {side} order végrehajtva: {order}")

    except Exception as e:
        print(f"⚠️ Hiba a trade végrehajtásánál: {e}")

# 📌 Pozíció zárása
def close_position(symbol, side):
    try:
        balance = float(client.get_asset_balance(asset="SOL")["free"])

        if balance > 0:
            step_size = float(client.get_symbol_info(symbol)["filters"][2]["stepSize"])
            quantity = round_step_size(balance, step_size)

            order = client.order_market(
                symbol=symbol,
                side=side,
                quantity=quantity
            )
            print(f"🚪 {side} pozíció lezárva: {order}")
        else:
            print(f"❌ Nincs nyitott {symbol} pozíció.")

    except Exception as e:
        print(f"⚠️ Hiba a pozíció lezárásánál: {e}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
