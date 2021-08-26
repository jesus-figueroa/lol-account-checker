# League Of Legends Account Checker
Retrieve information about a league of legends account. Region independent, it will return the following values:

Accounts will be in a file named "accounts-1234567.12345.txt", created where the script is ran.

NEW: Added concurrency for faster account checking.

* Region
* Name
* Login
* Last Game
* Level
* Rank & LP
* IP & RP
* Refundable IP & RP
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
ACCOUNTS = "user:pass,user1:pass1"
```

Afterwards, run the **lolchecker.py** like any normal python script.
