# League Of Legends Account Checker
Retrieve information about a league of legends account. Region independent, it will return the following values:

Accounts will be in a file named "accounts-1234567.12345.txt", created where the script is ran.

NEW: Added concurrency for faster account checking. Timeout to reduce rate limiting. Changed rank endpoint for faster checking. Caching for champion data.

* Region
* Name
* Login
* Last Game
* Level
* Rank & LP
* IP & RP
* Refundable IP & RP
* Refunds
* Ban Status
* Champions
* Skins

## Usage

Install python 3.2 or higher

Install requests

```
pip install requests
```

Open the **lolchecker.py** and place your account(s) in the **ACCOUNTS** variable like below (seperate with commas for multiple accounts):

```
#
# Paste you accounts below separated by commas
#
ACCOUNTS = "user:pass, user1:pass1,user2:pass2"

#
# Timeout between each account check
# Set to 0 for no timeout (May cause temporary rate limiting)
#
TIMEOUT = 5
```

Afterwards, run the **lolchecker.py** like any normal python script.
