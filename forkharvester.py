import logging
import os
import argparse
from web3 import Web3
from web3 import middleware
from web3.gas_strategies.time_based import fast_gas_price_strategy
from dotenv import load_dotenv
from uniswap import Uniswap, constants as uni_constants
from datetime import date, datetime

load_dotenv()
uni_constants._netid_to_name[250] = "fantom"

uni_logger = logging.getLogger("uniswap")
uni_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
logging.basicConfig(filename="harvester.log", level=logging.INFO)
logging.Formatter(fmt='%(message)s')

PROFIT_COIN = "USDC"
WALLET_ADDRESS = os.environ.get('ADDRESS')
PROFIT_WALLET = os.environ.get('PROFIT_WALLET')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')
PROFIT_CHAIN = 137

parser = argparse.ArgumentParser(description='Harvest your tomb fork yields!')
parser.add_argument('--take-profits', default=False, dest='take_profits', action="store_true",
                   help='Passing this flag will not stake the yield in the masonry, but instead sell to USDC.')
parser.add_argument('--pool-minimum', type=int, default=100, dest='pool_minimum',
                   help='The minimum amount of USDC value in the pool in order to harvest.')
parser.add_argument('--profit-wallet', type=str, default=PROFIT_WALLET, dest='profit_wallet',
                   help='Use the provided profit wallet address instead of using the $PROFIT_WALLET env var')
parser.add_argument('--profit-chain', type=int, default=PROFIT_CHAIN, dest='profit_chain',
                   help='Bridge to the provided chain id. Default is 137 (Polygon).')
args = parser.parse_args()

w3 = Web3(Web3.HTTPProvider(os.environ.get('PROVIDER')))
w3.eth.set_gas_price_strategy(fast_gas_price_strategy)

w3.middleware_onion.add(middleware.time_based_cache_middleware)
w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
w3.middleware_onion.add(middleware.simple_cache_middleware)

w3.eth.default_account = WALLET_ADDRESS

with open("abis/REWARDS_POOL.abi") as f:
    abi_two_rewards = f.readlines()[0]

with open("abis/SHARES_TOKEN.abi") as f:
    abi_two = f.readlines()[0]

with open("abis/MASONRY.abi") as f:
    abi_two_masonry = f.readlines()[0]

with open("abis/ANYSWAP_ROUTER.abi") as f:
    abi_anyswap = f.readlines()[0]
    anyswap = w3.eth.contract(address=Web3.toChecksumAddress("0x1ccca1ce62c62f7be95d4a67722a8fdbed6eecb4"), abi=abi_anyswap)

class Fork:
    def __init__(self, token_addr, masonry_addr, shares_reward_addr, pid) -> None:
        self.token_addr = Web3.toChecksumAddress(token_addr)
        self.masonry_addr = Web3.toChecksumAddress(masonry_addr)
        self.shares_reward_addr = Web3.toChecksumAddress(shares_reward_addr)
        self.pid = pid

        self.rewards_contract = w3.eth.contract(address=self.shares_reward_addr, abi=abi_two_rewards)
        self.token_contract = w3.eth.contract(address=self.token_addr, abi=abi_two)
        self.masonry_contract = w3.eth.contract(address=self.masonry_addr, abi=abi_two_masonry)

class BasedFork(Fork):
    def __init__(self, pid) -> None:
        super().__init__("0x49C290Ff692149A4E16611c694fdED42C954ab7a", 
                         "0xe5009dd5912a68b0d7c6f874cd0b4492c9f0e5cd", 
                         "0xAc0fa95058616D7539b6Eecb6418A68e7c18A746", pid)

# Add the forks you want to harvest here. All of these addresses currently work.    
FORKS = {
    # '2SHARES': Fork("0xc54A1684fD1bef1f077a336E6be4Bd9a3096a6Ca", "0x627a83b6f8743c89d58f17f994d3f7f69c32f461", "0x8d426eb8c7e19b8f13817b07c0ab55d30d209a96", 1),
    # '3OMB':    Fork("0x6437adac543583c4b31bf0323a0870430f5cc2e7", "0x32c7bb562e7ecc15bed153ea731bc371dc7ff379", "0x1040085d268253e8d4f932399a8019f527e58d04", 0),
    # '3SHARES': Fork("0x6437adac543583c4b31bf0323a0870430f5cc2e7", "0x32c7bb562e7ecc15bed153ea731bc371dc7ff379", "0x1040085d268253e8d4f932399a8019f527e58d04", 2),
    # 'TOMB':    Fork("0x4cdF39285D7Ca8eB3f090fDA0C069ba5F4145B37", "0x8764DE60236C5843D9faEB1B638fbCE962773B67", "0xcc0a87F7e7c693042a9Cc703661F5060c80ACb43", 1),
    # 'MAGIK':   Fork("0xc8ca9026ad0882133ef126824f6852567c571a4e", "0xac55a55676657d793d965ffa1ccc550b95535634", "0x38f006eb9c6778d02351fbd5966f829e7c4445d7", 0),
    'BASED-TOMB':  BasedFork(0),
    'BSHARE-FTM':  BasedFork(1),
    'BASED-GEIST': BasedFork(3),
    'BASED-TRI':   BasedFork(4)
}

uniswap = Uniswap(address=WALLET_ADDRESS, 
                  private_key=PRIVATE_KEY, 
                  version=2, 
                  factory_contract_addr="0x152eE697f2E276fA89E96742e9bB9aB1F2E61bE3",
                  router_contract_addr="0xf491e7b69e4244ad4002bc14e878a34207e38c29",
                  web3=w3)

profit_coins = {
    'USDC': Web3.toChecksumAddress("0x04068da6c83afcfa0e13ba15a6696662335d5b75")
}

ANYUSDC = Web3.toChecksumAddress("0x95bf7E307BC1ab0BA38ae10fc27084bC36FcD605")
usdc_contract = w3.eth.contract(address=profit_coins[PROFIT_COIN], abi=abi_two)

def signTransaction(contract, **kwargs):
    xDict = {
        "nonce": w3.eth.get_transaction_count(WALLET_ADDRESS),
        "from": w3.eth.default_account,
        "chainId": 250
    }
    if kwargs:
        xDict.update(**kwargs)

    txn = contract.buildTransaction(xDict)
    return w3.eth.account.sign_transaction(txn, PRIVATE_KEY)

def withdraw(contract, pid=1):
    txn = signTransaction(contract.functions.withdraw(pid, 0))
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.waitForTransactionReceipt(txnHash)

def stake(contract, balance):
    txn = signTransaction(contract.functions.stake(balance))
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.waitForTransactionReceipt(txnHash)  
    
def check_balance(contract):
    return contract.functions.balanceOf(WALLET_ADDRESS).call()

def check_pending(contract, pool_id):
    return contract.functions.pendingShare(pool_id, WALLET_ADDRESS).call()

def bridge(amount):
    txn = signTransaction(anyswap.functions.anySwapOutUnderlying(ANYUSDC, PROFIT_WALLET, amount, PROFIT_CHAIN))
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.waitForTransactionReceipt(txnHash)  

for k, v in FORKS.items():
    # # Withdraw from LP
    _pending = check_pending(v.rewards_contract, v.pid)
    pending = w3.fromWei(_pending, 'ether')
    # This only works for USDC right now...
    _value = uniswap.get_price_input(v.token_addr, profit_coins[PROFIT_COIN], _pending)
    value = w3.fromWei(_value, 'picoether')
    if value > args.pool_minimum:
        txnReceipt = withdraw(v.rewards_contract, pid=v.pid)

        # Get balance
        _balance = check_balance(v.token_contract)
        balance = w3.fromWei(_balance, 'ether')
        if _balance > 0:
            if not args.take_profits:
                # # Stake to masonry
                txnReceipt = stake(v.masonry_contract, _balance)
            else:
                uniswap.make_trade(v.token_addr, profit_coins[PROFIT_COIN], _balance)
            
            logger.info("{date},{k},{pending},{value},{pcoin},{profits}".format(
                pending=pending, k=k, value=value, pcoin=PROFIT_COIN, date=datetime.now().isoformat(), 
                profits=args.take_profits))

# Transfer all USDC to Crypto.com.
# BE CAREFUL! If you do not want to transfer everything, you might want to use a different
# wallet for this.
usdc_balance = check_balance(usdc_contract)
if usdc_balance > 0 and args.profit_chain != 0:
    # We bridge to Polygon, but we give the address of the Crypto.com wallet
    # which basically does a direct withdrawl
    print("Bridging {b} to chain: {chain}".format(b=w3.fromWei(usdc_balance, 'picoether'), chain=args.profit_chain))
    bridge(usdc_balance)