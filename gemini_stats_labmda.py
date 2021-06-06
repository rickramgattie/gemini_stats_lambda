import base64
import datetime
import hashlib
import hmac
import json
import logging
import os
import smtplib
import time
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3
import requests

# Script Config
logging.basicConfig(level=logging.FATAL)
logger = logging.getLogger()
t = datetime.datetime.now()


def get_secret(secret_name, region_name):
    try:
        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region_name)

        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        return json.loads(get_secret_value_response["SecretString"])
    except Exception as e:
        logger.fatal(f"There was an error ({e}): {traceback.format_exc()}")
        raise e


# API Callers
def private_api_call(
    domain, gemini_api_key, gemini_api_secret, path, additional_params={}
):
    url = domain + path
    nonce = str(int(time.mktime(t.timetuple()) * 1000))
    payload = {
        "nonce": f"{nonce}",
        "request": path,
    }
    payload.update(additional_params)
    encoded_payload = json.dumps(payload).encode()
    b64 = base64.b64encode(encoded_payload)
    signature = hmac.new(gemini_api_secret, b64, hashlib.sha384).hexdigest()
    request_headers = {
        "Content-Type": "text/plain",
        "Content-Length": "0",
        "X-GEMINI-APIKEY": gemini_api_key,
        "X-GEMINI-PAYLOAD": b64,
        "X-GEMINI-SIGNATURE": signature,
        "Cache-Control": "no-cache",
    }
    response = requests.post(url, headers=request_headers)
    return response.json()


def public_api_call(domain, path):
    url = domain + path
    response = requests.get(url)
    return response.json()


# API Endpoints
def get_all_trades(domain, gemini_api_key, gemini_api_secret):
    path = "/v1/mytrades"
    return private_api_call(
        domain,
        gemini_api_key,
        gemini_api_secret,
        path,
        additional_params={"limit_trades": 500},
    )


def get_current_asset_prices(domain):
    path = "/v1/pricefeed"
    return public_api_call(domain, path)


# Data Parsers
def convert_price_list_to_dict(price_list):
    price_dict = {}
    for symbol_group in price_list:
        symbol = symbol_group.get("pair")
        price_dict[symbol] = float(symbol_group.get("price"))
    return price_dict


def get_crypto_holding_summary(domain, gemini_api_key, gemini_api_secret):
    price_dict = convert_price_list_to_dict(get_current_asset_prices(domain))
    buy_order_tokens = {}
    for order in get_all_trades(domain, gemini_api_key, gemini_api_secret):
        if order.get("type") == "Buy":
            symbol = order.get("symbol")
            amount = float(order.get("amount"))
            spent = round(float(order.get("price")) * amount, 2)
            buy_order_tokens[symbol] = buy_order_tokens.get(
                symbol, {"amount": 0, "spent": 0, "value": 0}
            )
            buy_order_tokens[symbol]["amount"] += amount
            buy_order_tokens[symbol]["spent"] += spent
            buy_order_tokens[symbol]["value"] = buy_order_tokens[symbol][
                "amount"
            ] * price_dict.get(symbol)
    return buy_order_tokens


# Generate HTML
def generate_toke_color(spent, value):
    if spent < value:
        color = "green"
    else:
        color = "red"
    return f"<b style='color:{color}'>{round(value-spent, 2)}</b>"


def generate_token_rows(crypto_summary_dict):
    tokens_html = ""
    total_spent = 0
    total_value = 0
    for k, v in crypto_summary_dict.items():
        spent = v.get("spent")
        amount = v.get("amount")
        value = v.get("value")
        total_spent += spent
        total_value += value
        tokens_html += f'<tr> <td>{k.replace("USD", "")}</td> <td>{generate_toke_color(spent, value)}</td> <td>{round(spent, 2)}</td> <td>{round(value, 2)}</td> </tr>'
    tokens_html += f"<tr> <td><b>TOTAL</b></td> <td>{generate_toke_color(total_spent, total_value)}</td> <td>{round(total_spent, 2)}</td> <td>{round(total_value, 2)}</td> </tr>"
    return tokens_html


def generate_html(crypto_summary_dict):
    style = "<style> td { text-align: center; vertical-align: middle; }</style>"
    table_header = (
        "<tr> <th>Symbol</th> <th>Delta</th> <th>Spent</th> <th>Value</th> </tr>"
    )
    token_rows = generate_token_rows(crypto_summary_dict)
    final_html = f'{style}<table style="width:100%; border: 1px solid black;">{table_header}{token_rows}</table>'
    return final_html


# Send email
def send_email(sender, app_password, recipient, subject, email_body):
    try:
        mail_server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        mail_server.ehlo()
        mail_server.login(sender, app_password)

        message = MIMEMultipart("alternative")
        message["From"] = f"Gemini Trading API <{sender}>"
        message["To"] = recipient
        message["Subject"] = subject
        message.set_charset("utf-8")
        message.attach(MIMEText(email_body, "html"))
        mail_server.sendmail(sender, recipient, message.as_string())
        mail_server.close()
    except Exception as e:
        logger.fatal(f"There was an error ({e}): {traceback.format_exc()}")
        raise e


def lambda_handler(event, context):
    # AWS Config
    secret_name = os.environ["SECRET_NAME"]
    region_name = os.environ["REGION_NAME"]
    app_password = get_secret(secret_name, region_name)["gmail_app_password"]

    # Gemini API Account Config
    gemini_api_key = get_secret(secret_name, region_name)["gemini_api_key"]
    gemini_api_secret = get_secret(secret_name, region_name)["gemini_api_secret"]
    domain = "https://api.gemini.com"

    # Email Config
    sender = os.environ["SENDER_GMAIL_ADDRESS"]
    recipient = os.environ["RECIPIENT_GMAIL_ADDRESS"]

    subject = (
        f"Gemini Trading Account Stats - {datetime.datetime.now().strftime('%Y-%m-%d')}"
    )
    email_body = generate_html(
        get_crypto_holding_summary(domain, gemini_api_key, gemini_api_secret)
    )
    send_email(sender, app_password, recipient, subject, email_body)
