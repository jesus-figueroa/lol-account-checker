# League Of Legends Account Checker

Retrieve information about a league of legends account. Region independent, it will return the following values:

Accounts will be in a file named "output/accounts 1234-56-78_90-12.txt", created where the script is ran.

- Region
- Name
- Login
- Last Game
- Level
- Rank & LP
- IP & RP
- Refundable IP & RP
- Refunds
- Ban Status
- Champions - BROKEN
- Skins - BROKEN

## Usage

Install python 3.6 or higher

Install requests

```
pip install requests
```

Rename **checker.env.example** to **checker.env** and place your account(s) in the **ACCOUNTS** variable like below (seperate with commas for multiple accounts):

```
#
# Paste you accounts below separated by commas
#
ACCOUNTS=user:pass, user1:pass1,user2:pass2

#
# Timeout between each account check (in seconds)
# Set to 0 for no timeout (May cause temporary rate limiting)
#
TIMEOUT=5
```

Afterwards, run the **lolchecker.py** like any normal python script.
