import logging
from binance.um_futures import UMFutures
from binance.lib.utils import config_logging
from keys import TESTAPIKEY, TESTSECRETKEY
import time

# Configure logging
config_logging(logging, logging.DEBUG, 'binance.log')
# Initialize the client
client = UMFutures(
    key=TESTAPIKEY,
    secret=TESTSECRETKEY,
    base_url="https://testnet.binancefuture.com"
)

"""
My Strategy:
Investe 10% of my usdt balance: Investe 10% of my usdt balance only if it's worths $100 or more placing a buy market order with a 3x leverage in ISOLATED type. 
Secure my position: Then i place a take profit order when my unrealized profit is greater than or equal to 10% of my position size;
a buy market order just above my liquidation price with amout that is twice my curent position size;
finally i place a buy market order just above my take profit price with 10% of my current balance;

1. Check  if any position is open
2. If there is no position open, check if the balance is greater than $100
3. If the balance is greater than $100, place a buy market order with 3x leverage in ISOLATED type
4. Place a take profit order when the unrealized profit is greater than or equal to 10% of the position size
5. Place a buy market order just above the liquidation price with an amount that is twice the current position size
6. Place a buy market order just above the take profit price with 10% of the current balance
"""
# Define the symbol
symbol = "1000SHIBUSDT"
# Define the leverage
leverage = 3
# Define the margin type
margin_type = "ISOLATED"
# Define the take profit percentage
take_profit_percentage = 0.035


# Get my current balance
def get_balance_usdt():
    try:
        balance = client.balance(recvWindow=6000)
        for asset in balance:
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['balance'])
                logging.info(f"Current USDT balance: {usdt_balance}")
                return usdt_balance
        logging.info("USDT balance not found.")
        return 0.0
    except Exception as e:
        logging.error(f"Error getting balance: {e}")
        return 0.0


# Change margin type
def set_margin_type(symbol, margin_type):
    try:
        response = client.change_margin_type(symbol=symbol, marginType=margin_type)
        logging.info(f"Margin type set to {margin_type} for {symbol}: {response}")
    except Exception as e:
        logging.error(f"Error setting margin type: {e}")


# Set leverage
def set_leverage(symbol, leverage):
    try:
        response = client.change_leverage(symbol=symbol, leverage=leverage)
        logging.info(f"Leverage set to {leverage} for {symbol}: {response}")
    except Exception as e:
        logging.error(f"Error setting leverage: {e}")


# Get the current position
def get_opened_position(symbol):
    try:
        positions = client.get_position_risk(symbol=symbol)
        for position in positions:
            if position['symbol'] == symbol:
                if float(position['positionAmt']) > 0.0:
                    return position
        return 0.0
    except Exception as e:
        logging.error(f"Error getting position: {e}")
        return 0.0


# Get price precision
def get_price_precision(symbol):
    resp = client.exchange_info()['symbols']
    for elem in resp:
        if elem['symbol'] == symbol:
            return elem['pricePrecision']


# Get quantity precision
def get_qty_precision(symbol):
    resp = client.exchange_info()['symbols']
    for elem in resp:
        if elem['symbol'] == symbol:
            return elem['quantityPrecision']


# Place a market order
def place_market_order(symbol, side, quantity):
    try:
        response = client.new_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity,
            recvWindow=6000
        )
        logging.info(f"Market order placed: {response}")
        return response
    except Exception as e:
        logging.error(f"Error placing market order: {e}")
        return None


# Place a stop market order
def place_stop_market_order(symbol, side, quantity, stopPrice):
    try:
        response = client.new_order(
            symbol=symbol,
            side=side,
            type='STOP_MARKET',
            quantity=quantity,
            stopPrice=stopPrice,
            recvWindow=6000
        )
        logging.info(f"Stop market order placed: {response}")
        return response
    except Exception as e:
        logging.error(f"Error placing stop market order: {e}")
        return None


# Place a take profit order
def place_take_profit_order(symbol, side, price):
    try:
        response = client.new_order(
            symbol=symbol,
            side=side,
            type='TAKE_PROFIT_MARKET',
            closePosition=True,
            stopPrice=price,
            recvWindow=6000
        )
        logging.info(f"Take profit order placed: {response}")
        return response
    except Exception as e:
        logging.error(f"Error placing take profit order: {e}")


# Cancel all open orders
def cancel_all_open_orders(symbol):
    try:
        response = client.cancel_open_orders(symbol=symbol)
        logging.info(f"All open orders canceled: {response}")
        return response
    except Exception as e:
        logging.error(f"Error canceling open orders: {e}")


# Get open orders
def get_open_orders(symbol):
    try:
        open_orders = client.get_orders(symbol=symbol)
        if open_orders:
            logging.info(f"Open orders for {symbol}: {open_orders}")
        else:
            logging.info(f"No open orders for {symbol}.")
        return open_orders
    except Exception as e:
        logging.error(f"Error getting open orders: {e}")
        return []


# Check if there is a valid Take profit order
def check_take_profit_order(symbol, position):
    try:
        price_precision = get_price_precision(symbol)
        open_orders = client.get_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] == 'TAKE_PROFIT_MARKET' and order['side'] == 'SELL' and float(order['stopPrice']) == round(
                    float(position['breakEvenPrice']) * (1 + take_profit_percentage), price_precision):
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking take profit order: {e}")
        return False


def is_bottom_secured(symbol, position):
    try:
        price_precision = get_price_precision(symbol)
        open_orders = client.get_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] == 'TAKE_PROFIT_MARKET' and order['side'] == 'BUY' and float(order['stopPrice']) == round(
                    float(position['liquidationPrice']) * 1.05, price_precision):
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking take profit order: {e}")
        return False


def is_top_secured(symbol, position):
    try:
        price_precision = get_price_precision(symbol)
        open_orders = client.get_orders(symbol=symbol)
        for order in open_orders:
            if order['type'] == 'STOP_MARKET' and order['side'] == 'BUY' and float(order['stopPrice']) == round(
                    float(position['breakEvenPrice']) * (1 + take_profit_percentage + 0.005), price_precision):
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking take profit order: {e}")
        return False


# Check if position is secured
def is_position_secured(symbol, position):
    try:
        if check_take_profit_order(symbol, position) and is_bottom_secured(symbol, position) and is_top_secured(symbol,
                                                                                                                position):
            return True
        else:
            return False
    except Exception as e:
        logging.error(f"Error checking position security: {e}")
        return False


# Secure position
def secure_position(symbol, position):
    try:
        price_precision = get_price_precision(symbol)
        qty_precision = get_qty_precision(symbol)
        # Take profit price
        take_profit_price = round(float(position['breakEvenPrice']) * (1 + take_profit_percentage), price_precision)
        # Place take profit order
        response = place_take_profit_order(symbol=symbol, side='SELL', price=take_profit_price)
        print(f"Take profit order placed: {response}")
        # Place buy market order just above liquidation price
        bottom_protection_price = round(float(position['liquidationPrice']) * 1.05, price_precision)
        # Calculate the quantity to buy
        quantity = round((float(position['positionAmt']) * float(position['entryPrice']) * 2) / bottom_protection_price,
                         qty_precision)
        # Place buy market order
        response = client.new_order(symbol=symbol, side='BUY', type='TAKE_PROFIT_MARKET', quantity=quantity,
                                    stopPrice=bottom_protection_price)
        print(f"Bottom protection order placed: {response}")

        # Place buy market order just above take profit price
        # Calculate the quantity to buy
        follow_up_price = round(float(position['breakEvenPrice']) * (1 + take_profit_percentage + 0.005),
                                price_precision)
        quantity = round(float(get_balance_usdt()) * 0.1 / follow_up_price, qty_precision)
        # Place buy market order
        response = place_stop_market_order(symbol=symbol, side='BUY', quantity=quantity, stopPrice=follow_up_price)
        print(f"Follow up order placed: {response}")
        return True
    except Exception as e:
        logging.error(f"Error securing position: {e}")
        return False


# Play my strategy
def play_my_strategy(symbol, leverage, margin_type):
    while True:
        try:
            # Set the margin type
            set_margin_type(symbol, margin_type)
            # Set the leverage
            set_leverage(symbol, leverage)
            # Get the current USDT balance
            usdt_balance = get_balance_usdt()
            print(f"Current USDT balance: {usdt_balance}")
            # Check if there is any opened position
            position = get_opened_position(symbol=symbol)
            # Check if there is no opened position
            if position == 0.0:
                # Check if the balance is greater than $100
                if usdt_balance >= 100.0:
                    print("Balance is greater than $100.")
                    # Calculate the quantity to buy (10% of the balance)
                    qty_precision = get_qty_precision(symbol)
                    market_price = client.ticker_price(symbol=symbol)['price']
                    quantity = round((usdt_balance * 0.1) / float(market_price), qty_precision)
                    # Place a market order
                    print(f"Placing market order for {quantity} {symbol} at market price {market_price}")
                    response = place_market_order(symbol=symbol, side='BUY', quantity=quantity)
                    print(f"Market order placed: {response}")
                else:
                    print("Balance is less than $100.")
                time.sleep(3)
            else:
                # Check if the position is secured
                if is_position_secured(symbol, position):
                    print("Position is secured.")
                else:
                    print("Position is not secured.")
                    print("Canceling all open orders.")
                    cancel_all_open_orders(symbol)
                    print("Securing position.")
                    secure_position(symbol, position)
                    print("Position secured.")
                time.sleep(15)
        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error playing strategy: {e}")


if __name__ == "__main__":
    print("Starting bot...")
    # Play my strategy
    play_my_strategy(symbol, leverage, margin_type)
    print("Bot stopped.")
