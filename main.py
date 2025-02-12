import imaplib
import email
from email.header import decode_header
import time
import os
import ssl
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL
from binance.helpers import round_step_size

# **1️⃣ API kulcsok beolvasása környezeti változókból**
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
EMAIL = os.getenv("GMAIL_EMAIL")
PASSWORD = os.getenv("GMAIL_PASSWORD")
IMAP_SERVER = "imap.gmail.com"

# **2️⃣ Binance kliens inicializálás**
client = Client(API_KEY, API_SECRET)

# **3️⃣ IMAP kapcsolat létrehozása biztonságosabb SSL contexttel**
def connect_imap():
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, ssl_context=context)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        return mail
    except Exception as e:
        print(f"⚠️ IMAP kapcsolat hiba: {e}")
        return None

def read_email():
    mail = connect_imap()
    if mail is None:
        return

    try:
        while True:
            try:
                result, data = mail.search(None, '(UNSEEN SUBJECT "TradingView Alert")')
                if result != "OK":
                    raise Exception("Nem sikerült az e-mailek keresése!")

                email_ids = data[0].split()

                for email_id in email_ids:
                    try:
                        result, msg_data = mail.fetch(email_id, "(RFC822)")
                        if result != "OK":
                            raise Exception(f"Hiba az e-mail letöltésénél: {email_id}")

                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                subject, encoding = decode_header(msg["Subject"])[0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode(encoding if encoding else "utf-8")

                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            body = part.get_payload(decode=True).decode()
                                else:
                                    body = msg.get_payload(decode=True).decode()

                                body = body.strip()
                                print(f"📩 Új TradingView riasztás: {body}")

                                # **Kereskedési logika**
                                if "TRADE: BUY SOLUSDT" in body:
                                    place_order("SOLUSDT", SIDE_BUY)  
                                elif "TRADE: SELL SOLUSDT" in body:
                                    place_order("SOLUSDT", SIDE_SELL)  
                                elif "TRADE: CLOSE BUY SOLUSDT" in body:
                                    close_position("SOLUSDT", SIDE_SELL)  
                                elif "TRADE: CLOSE SELL SOLUSDT" in body:
                                    close_position("SOLUSDT", SIDE_BUY)  

                        mail.store(email_id, "+FLAGS", "\\Seen")

                    except Exception as e:
                        print(f"⚠️ Hiba egy e-mail feldolgozása közben: {e}")

            except imaplib.IMAP4.error as e:
                print(f"⚠️ IMAP hiba: {e}")
                mail = connect_imap()

            except ssl.SSLError as e:
                print(f"⚠️ SSL kapcsolat hiba: {e}")
                mail = connect_imap()

            except Exception as e:
                print(f"⚠️ Általános hiba az e-mail ellenőrzés során: {e}")

            time.sleep(3)  # 3 másodpercenként újraellenőrizzük

    except Exception as e:
        print("⚠️ Kritikus hiba az e-mail figyelés közben:", e)

def place_order(symbol, side):
    try:
        usdt_balance = float(client.get_asset_balance(asset="USDT")["free"])
        trade_amount = usdt_balance * 0.50  # Mindig az aktuális egyenleg 50%-ával tradelünk

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
    print("🔍 E-mail figyelés elindult...")
    read_email()
