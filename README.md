# forkharvester
---

This is a Tomb fork harvester. Nothing here is financial advice, of course.

It's very simple right now:

1. Check to see if we have pending masonry rewards and we can claim. If so, do it. TODO: Make LPs.
1. If the pending LP rewards are > 100 USDC, harvest each.
1. After harvesting, if we are taking profits, sell to USDC and then use anyswap router to send to the `PROFIT_WALLET` on Polygon (you can configure the chain if you want to go somewhere else). I have my `PROFIT_WALLET` set to my Crypto.com wallet address.
1. If we are not taking profits, stake to the masonry.

## Quickstart:

1. `pip install -r requirements.txt`
2. Set up your environment variables (you can use a .env file for this):
```
ADDRESS="WALLET_ADDRESS"
PROFIT_WALLET="ADDRESS OF THE WALLET YOU WANT TO TAKE PROFITS TO"
PRIVATE_KEY="YOUR WALLET'S PRIVATE KEY -- MAKE SURE TO KEEP THIS SAFE!!!"
PROVIDER='https://rpc.ankr.com/fantom'
``` 
3. Run the script! `python forkharvester.py -h` to learn about the command line options:
```
usage: forkharvester.py [-h] [--take-profits] [--pool-minimum POOL_MINIMUM] [--profit-wallet PROFIT_WALLET] [--profit-chain PROFIT_CHAIN]

Harvest your tomb fork yields!

optional arguments:
  -h, --help            show this help message and exit
  --take-profits        Passing this flag will not stake the yield in the masonry, but instead sell to USDC.
  --pool-minimum POOL_MINIMUM
                        The minimum amount of USDC value in the pool in order to harvest.
  --profit-wallet PROFIT_WALLET
                        Use the provided profit wallet address instead of using the $PROFIT_WALLET env var
  --profit-chain PROFIT_CHAIN
                        Bridge to the provided chain id. Default is 137 (Polygon).
```
4. You could set this up as a cron job to run as often as you'd like, or just run it once or twice a day.