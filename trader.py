import requests
import json
import time
import datetime
import sys

trade_ogre_api_key = 'db9a6605a97cc550855146b3d05dde32'
trade_ogre_secret_key = 'ca195986c18fb9c19dd81d14389630f2'
COINS = ['RVN', 'LTC', 'XMR', 'ETH', 'DOGE', 'BEAM']

debug = '--debug' in sys.argv
base_url = 'https://tradeogre.com/api/v1'

def timestamp_print(msg):
	date = datetime.datetime.now()
	print(f'\u001b[36m[ {date.year}{date.month}{date.day} {date.hour}:{date.minute} ]\u001b[37m {msg}')

class TradeOgre:
	def __init__(self, trade_ogre_api, trade_ogre_secret):
		self.trade_ogre_secret = trade_ogre_secret
		self.trade_ogre_api = trade_ogre_api

	def get_market_info(self, coin):
		'''
		RVN data at [30]['BTC-RVN']
		'''

		api_response = requests.get(base_url + '/markets', headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {self.trade_ogre_secret}'})
		j = json.loads(api_response.content.decode('utf-8'))		

		if api_response.status_code == 200:
			for i in j:
				if [k for k in i.keys()][0] == 'BTC-' + coin:
					return i['BTC-' + coin]
		else:
			return None

	def buy_coin(self, coin, amount, price):
		'''
		Buys RVN

		MIN AMOUNT IN BTC IS 0.0001
		'''
		sats = str(price * 100000000)
		sats = sats.split('.')[0] if '.' in sats else sats

		total = format(amount*price, '.8f')

		api_response = requests.post(base_url + '/order/buy', {'market': 'BTC-' + coin, 'quantity': str(round(amount, 2)), 'price': format(price, '.8f')}, auth = (self.trade_ogre_api, self.trade_ogre_secret))
		
		if json.loads(api_response.text)['success']:
			timestamp_print(f'[!] Buy placed for {amount} {coin} at {sats} satoshis, total of {total} BTC')
		
		if debug:
			timestamp_print(json.loads(api_response.content.decode('utf-8')))
		return json.loads(api_response.content.decode('utf-8'))


	def sell_coin(self, coin, amount, price):
		'''
		Sells RVN

		MIN AMOUNT IN BTC IS 0.0001
		'''
		sats = str(price * 100000000)
		sats = sats.split('.')[0] if '.' in sats else sats

		total = format(amount*price, '.8f')

		api_response = requests.post(base_url + '/order/sell', {'market':'BTC-' + coin, 'quantity':amount, 'price': format(price, '.8f')}, auth = (self.trade_ogre_api, self.trade_ogre_secret))
		
		if json.loads(api_response.text)['success']:
			timestamp_print(f'[!] Sell placed for {amount} {coin} at {sats} satoshis, total of {total} BTC')
		
		if debug:
			timestamp_print(json.loads(api_response.content.decode('utf-8')))
		return json.loads(api_response.content.decode('utf-8'))


	def cancel_order(self, uuid):
		api_response = requests.post(base_url + '/order/cancel', data = {'uuid':uuid}, auth = (self.trade_ogre_api, self.trade_ogre_secret))
		timestamp_print(f'[!] Order cancelled for {uuid}')
		return json.loads(api_response.content.decode('utf-8'))


	def get_bal(self, currency_ticker):
		api_response = requests.get(base_url + '/account/balances', auth = (self.trade_ogre_api, self.trade_ogre_secret))
		return float(json.loads(api_response.content.decode('utf-8'))['balances'][currency_ticker])

	def get_order(self):
		api_response = requests.post(base_url + '/account/orders', auth = (self.trade_ogre_api, self.trade_ogre_secret))
		data = json.loads(api_response.content.decode('utf-8'))
		prev_orders = [0, 0]
		ctr = 0

		for i in data:
			if prev_orders[0] != 0 and prev_orders[1] != 0:
				break
			elif i['type'] == 'sell':
				prev_orders[1] = i['price']
			elif i['type'] == 'buy':
				prev_orders[0] = i['price']

		return prev_orders


class Binance:

	def get_market_info(self, coin):
		'''
		RVN data at [398]
		'''
		api_response = requests.get('https://api.binance.com/api/v1/ticker/24hr')

		for c in json.loads(api_response.content.decode('utf-8')):
			if c['symbol'] == coin + 'BTC':
				if debug:
					timestamp_print(c)
				return c
		if debug:
			timestamp_print(f'Binance.get_market_info("{coin}") returned None!')

	def get_order_book(self, ticker):
		api_response = requests.get('https://api.binance.com/api/v1/depth', params = {'symbol': ticker, 'limit':100})
		return json.loads(api_response.content.decode('utf-8'))


'''

Create classes with API keys.

'''

binance = Binance()
trade_ogre = TradeOgre(trade_ogre_api_key, trade_ogre_secret_key)

def get_day_low(coin):
	binance_day_low = float(binance.get_market_info(coin)['lowPrice'])
	trade_ogre_day_low = float(trade_ogre.get_market_info(coin)['low'])

	return (binance_day_low + trade_ogre_day_low) / 2

def get_day_high(coin):
	binance_day_hi = float(binance.get_market_info(coin)['highPrice'])
	trade_ogre_day_hi = float(trade_ogre.get_market_info(coin)['high'])

	return (binance_day_hi + trade_ogre_day_hi) / 2


def buy_low(coin):
	price = get_day_low(coin) + 0.00000001
	return trade_ogre.buy_coin(coin, (trade_ogre.get_bal('BTC') / len(COINS)) / price, price)['success']

def sell_high(coin):
	return trade_ogre.sell_coin(coin, trade_ogre.get_bal(coin) / 2, get_day_high(coin) - 0.00000001)['success']

def algo_one():
	print('\u001b[37m', end='')

	while True:
		trade_ogre.cancel_order('all')

		for c in COINS:
			buy_low(c)
			sell_high(c)

		timestamp_print(f"\u001b[33m[^] Your BTC balance is {trade_ogre.get_bal('BTC')}")

		for c in COINS:
			timestamp_print(f"\u001b[33m[^] Your {c} balance is {trade_ogre.get_bal(c)}")
		
		print('\u001b[37m' + '-' * 30)

		time.sleep(600)

if __name__ == '__main__':	
	algo_one()


# jesus christ this was the 1st real project i made and i just came back to it 2 years later... VERY glad i dont code like this anymore
# also those aren't my real keys, just jokin bro :)
