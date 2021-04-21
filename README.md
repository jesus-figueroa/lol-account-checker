# League Of Legends Account Checker
Retrieve information about a league of legends account. Region independent, it will return the following values:

* Region
* Name
* Login
* Last Game
* Level
* Rank & LP
* IP & RP
* Refundable IP & RP
* Champions
* Skins

## Usage

Install requests

```
pip install requests
```

Open the **lolchecker.py** and place your account(s) in the **ACCOUNTS** variable like below (seperate with commas for multiple accounts):

```
ACCOUNTS = "user:pass,user1:pass1"
```

Afterwards, run the **lolchecker.py** like any normal python.

Original code by [guitar-toucher](https://github.com/guitar-toucher).
