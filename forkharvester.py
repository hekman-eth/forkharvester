import logging
import os
import argparse
import time
from web3 import Web3
from web3 import middleware
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from dotenv import load_dotenv
from uniswap import constants
from uniswap import Uniswap
from datetime import datetime

load_dotenv()


uni_logger = logging.getLogger("uniswap")
uni_logger.setLevel(logging.DEBUG)



PROFIT_COIN = "USDC"
WALLET_ADDRESS = os.environ.get('ADDRESS')
PROFIT_WALLET = os.environ.get('PROFIT_WALLET')
PRIVATE_KEY = os.environ.get('PRIVATE_KEY')
PROFIT_CHAIN = 137

parser = argparse.ArgumentParser(description='Harvest your tomb fork yields!')
parser.add_argument('--pool-minimum', type=int, default=100, dest='pool_minimum',
                   help='The minimum amount of USDC value in the pool in order to harvest.')
parser.add_argument('--profit-wallet', type=str, default=PROFIT_WALLET, dest='profit_wallet',
                   help='Use the provided profit wallet address instead of using the $PROFIT_WALLET env var')
parser.add_argument('--profit-chain', type=int, default=PROFIT_CHAIN, dest='profit_chain',
                   help='Bridge to the provided chain id. Default is 137 (Polygon).')
parser.add_argument('--profit-coin', type=str, default=PROFIT_COIN, dest='profit_coin',
                   help='The coin to take profits into.')
parser.add_argument('--profit-pct', type=int, default=10, dest='profit_pct',
                   help='Percent of the profit to sell (in int format, e.g. 10 for 10%).')
parser.add_argument('--log-file', type=str, default="harvester.log")
                   
args = parser.parse_args()

logger = logging.getLogger(__name__)
logging.basicConfig(filename=args.log_file, level=logging.ERROR)
logging.Formatter(fmt='%(message)s')

w3 = Web3(Web3.HTTPProvider(os.environ.get('PROVIDER')))
w3.eth.set_gas_price_strategy(rpc_gas_price_strategy)

w3.middleware_onion.add(middleware.time_based_cache_middleware)
w3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
w3.middleware_onion.add(middleware.simple_cache_middleware)

w3.eth.default_account = WALLET_ADDRESS

with open("abis/REWARDS_POOL.abi") as f:
    abi_two_rewards = f.readlines()[0]

with open("abis/TOKEN.abi") as f:
    abi_two = f.readlines()[0]

with open("abis/MASONRY.abi") as f:
    abi_two_masonry = f.readlines()[0]

with open("abis/ANYSWAP_ROUTER.abi") as f:
    abi_anyswap = f.readlines()[0]
    anyswap = w3.eth.contract(address=Web3.toChecksumAddress("0x1ccca1ce62c62f7be95d4a67722a8fdbed6eecb4"), abi=abi_anyswap)

with open("abis/SPOOKY_ROUTER.abi") as f:
    abi_spooky = f.readlines()[0]
    spooky = w3.eth.contract(address=Web3.toChecksumAddress("0xF491e7B69E4244ad4002BC14e878a34207E38c29"), abi=abi_spooky)

class Fork:
    def __init__(self, shares_token_addr, masonry_addr, shares_reward_addr, token_addr, pid, lp_partner=None) -> None:
        self.shares_token_addr = Web3.toChecksumAddress(shares_token_addr)
        self.masonry_addr = Web3.toChecksumAddress(masonry_addr)
        self.shares_reward_addr = Web3.toChecksumAddress(shares_reward_addr)
        self.token_addr = Web3.toChecksumAddress(token_addr)
        self.pid = pid
        self.lp_partner = Web3.toChecksumAddress(lp_partner) if lp_partner else None

        self.rewards_contract = w3.eth.contract(address=self.shares_reward_addr, abi=abi_two_rewards)
        self.shares_token_contract = w3.eth.contract(address=self.shares_token_addr, abi=abi_two)
        self.token_contract = w3.eth.contract(address=self.token_addr, abi=abi_two)
        self.masonry_contract = w3.eth.contract(address=self.masonry_addr, abi=abi_two_masonry)

uniswap = Uniswap(address=WALLET_ADDRESS, 
                  private_key=PRIVATE_KEY, 
                  version=2, 
                  factory_contract_addr="0x152eE697f2E276fA89E96742e9bB9aB1F2E61bE3",
                  router_contract_addr="0xf491e7b69e4244ad4002bc14e878a34207e38c29",
                  web3=w3,
                  default_slippage=0.5,
                  use_estimate_gas=False)

class BasedFork(Fork):
    # A Fork that is tailored to compound back into the SHARES LP
    def __init__(self, shares_token_addr="0x49C290Ff692149A4E16611c694fdED42C954ab7a", 
                 masonry_addr="0xe5009dd5912a68b0d7c6f874cd0b4492c9f0e5cd", 
                 shares_reward_addr="0xAc0fa95058616D7539b6Eecb6418A68e7c18A746", 
                 token_addr="0x8D7d3409881b51466B483B11Ea1B8A03cdEd89ae", 
                 pid=0, 
                 lp_partner=uniswap.get_weth_address()) -> None:
        super().__init__(shares_token_addr, 
                         masonry_addr,
                         shares_reward_addr,
                         token_addr,
                         pid,
                         lp_partner)

# Add the forks you want to harvest here. All of these addresses currently work.    
FORKS = {
    # '2SHARES': Fork("0xc54A1684fD1bef1f077a336E6be4Bd9a3096a6Ca", "0x627a83b6f8743c89d58f17f994d3f7f69c32f461", "0x8d426eb8c7e19b8f13817b07c0ab55d30d209a96", 1),
    # '3OMB':    Fork("0x6437adac543583c4b31bf0323a0870430f5cc2e7", "0x32c7bb562e7ecc15bed153ea731bc371dc7ff379", "0x1040085d268253e8d4f932399a8019f527e58d04", 0),
    # '3SHARES': Fork("0x6437adac543583c4b31bf0323a0870430f5cc2e7", "0x32c7bb562e7ecc15bed153ea731bc371dc7ff379", "0x1040085d268253e8d4f932399a8019f527e58d04", 2),
    # 'TOMB':    Fork("0x4cdF39285D7Ca8eB3f090fDA0C069ba5F4145B37", "0x8764DE60236C5843D9faEB1B638fbCE962773B67", "0xcc0a87F7e7c693042a9Cc703661F5060c80ACb43", 1),

    'BASED-TOMB':  BasedFork(pid=0),
    'BSHARE-FTM':  BasedFork(pid=1),
    'BASED-GEIST': BasedFork(pid=3),
    'BASED-TRI':   BasedFork(pid=4),
}

profit_coins = {
    'USDC': Web3.toChecksumAddress("0x04068da6c83afcfa0e13ba15a6696662335d5b75"),
    'WFTM': uniswap.get_weth_address()
}

ANYUSDC = Web3.toChecksumAddress("0x95bf7E307BC1ab0BA38ae10fc27084bC36FcD605")
usdc_contract = w3.eth.contract(address=profit_coins[args.profit_coin], abi=abi_two)

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
    return w3.eth.wait_for_transaction_receipt(txnHash)

def stake(contract, balance):
    txn = signTransaction(contract.functions.stake(balance))
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(txnHash)  

def claim(contract):
    txn = signTransaction(contract.functions.claimReward())
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(txnHash)  
    
def check_balance(contract):
    if contract.address.lower() == constants.ETH_ADDRESS.lower():
        return uniswap.get_eth_balance()
    else:
        return contract.functions.balanceOf(WALLET_ADDRESS).call()

def check_pending(contract, pool_id):
    return contract.functions.pendingShare(pool_id, WALLET_ADDRESS).call()

def bridge(amount):
    txn = signTransaction(anyswap.functions.anySwapOutUnderlying(ANYUSDC, PROFIT_WALLET, amount, PROFIT_CHAIN))
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(txnHash)  

def approve(token, amount):
    txn = signTransaction(token.functions.approve(spooky.address, amount))
    txnHash = w3.eth.send_raw_transaction(txn.rawTransaction)
    return w3.eth.wait_for_transaction_receipt(txnHash)

def take_profit(token_addr, profits):
    # Double-check we have the right balance in our token_addr
    _balance = uniswap.get_token_balance(token_addr)
    if _balance < profits:
        profits = _balance

    w3.eth.wait_for_transaction_receipt(
        uniswap.make_trade(
            token_addr, 
            profit_coins[args.profit_coin], 
            profits,
            args.profit_wallet
        )
    )

def check_spooky_approval(token, _amount):
    amount = (
        token.functions.allowance(WALLET_ADDRESS, spooky.address)
        .call()
    )
    if amount > _amount:
        return True
    else:
        return False

def compound(fork, amount):
    # Sell half
    w3.eth.wait_for_transaction_receipt(
        uniswap.make_trade(
            fork.shares_token_addr,
            fork.lp_partner,
            int(amount / 2)
        )
    )
    # Make LP
    a_balance = uniswap.get_token_balance(fork.shares_token_addr)
    a_desired = uniswap.get_price_input(fork.shares_token_addr, fork.lp_partner, a_balance)
    b_desired = uniswap.get_price_output(fork.shares_token_addr, fork.lp_partner, a_balance)

    if not check_spooky_approval(fork.shares_token_contract, a_balance):
        approve(fork.shares_token_contract, a_balance)

    addliq = spooky.functions.addLiquidityETH(
        fork.shares_token_addr, 
        a_desired, 
        0, 
        0,
        WALLET_ADDRESS, 
        int(time.time()) + 1000000
    )
    w3.eth.send_raw_transaction(signTransaction(addliq, value=b_desired).rawTransaction)
    # Deposit back to farm
    lp_balance = uniswap.get_token_balance("0x6F607443DC307DCBe570D0ecFf79d65838630B56")
    w3.eth.send_raw_transaction(
        signTransaction(fork.rewards_contract.functions.deposit(fork.pid, lp_balance)).rawTransaction
    )

for k, v in FORKS.items():  
    # # Withdraw from LP
    _pending = check_pending(v.rewards_contract, v.pid)
    pending = w3.fromWei(_pending, 'ether')
    # This only works for USDC right now...
    if _pending == 0:
        continue
    _value = uniswap.get_price_input(v.shares_token_addr, profit_coins["USDC"], _pending)
    value = w3.fromWei(_value, 'picoether')
    print("%s: %i" % (k, value))
    if value > args.pool_minimum:
        txnReceipt = withdraw(v.rewards_contract, pid=v.pid)

        # Get balance
        _balance = check_balance(v.shares_token_contract)
        balance = w3.fromWei(_balance, 'ether')
        if _balance > 0:
            if args.profit_pct > 0:
                profits = int((args.profit_pct / 100) * _balance)
                _balance = _balance - profits
                # approve(v.shares_token_contract, _balance)
                take_profit(v.shares_token_addr, profits)
                if _balance and v.lp_partner:
                    remainder_balance = uniswap.get_token_balance(v.shares_token_addr)
                    if remainder_balance > 0:
                        compound(v, remainder_balance)

            profits_value = uniswap.get_price_input(v.shares_token_addr, profit_coins[args.profit_coin], profits)
            
            logger.info("{date},{k},{pending},{value},{pcoin},{profits}".format(
                pending=pending, k=k, value=value, pcoin=args.profit_coin, date=datetime.now().isoformat(), 
                profits=profits_value))

# Transfer all USDC to Crypto.com.
# BE CAREFUL! If you do not want to transfer everything, you might want to use a different
# wallet for this.
# usdc_balance = check_balance(usdc_contract)
# if usdc_balance > 0 and args.profit_chain != 0:
#     # We bridge to Polygon, but we give the address of the Crypto.com wallet
#     # which basically does a direct withdrawl
#     #
#     # Sometimes there's a delay, so let's just loop until we have bridged
#     print("Bridging {b} to chain: {chain}".format(b=w3.fromWei(usdc_balance, 'picoether'), chain=args.profit_chain))
#     bridge(usdc_balance)