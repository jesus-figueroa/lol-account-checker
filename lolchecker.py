import datetime
import requests
import json
import re

'''
Paste you accounts below separated by commas
'''
ACCOUNTS = "user:pass"

class AccountChecker:
    AUTH_URL = "https://auth.riotgames.com/api/v1/authorization"
    INFO_URL = "https://auth.riotgames.com/userinfo"
    CHAMPION_DATA_URL = "http://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champions/"
    INVENTORY_TYPES = [
        'TOURNAMENT_TROPHY', 'TOURNAMENT_FLAG', 'TOURNAMENT_FRAME', 
        'TOURNAMENT_LOGO', 'GEAR', 'SKIN_UPGRADE_RECALL', 
        'SPELL_BOOK_PAGE', 'BOOST', 'BUNDLES', 'CHAMPION', 
        'CHAMPION_SKIN', 'EMOTE', 'GIFT', 'HEXTECH_CRAFTING', 
        'MYSTERY', 'RUNE', 'STATSTONE', 'SUMMONER_CUSTOMIZATION', 
        'SUMMONER_ICON', 'TEAM_SKIN_PURCHASE', 'TRANSFER', 
        'COMPANION', 'TFT_MAP_SKIN', 'WARD_SKIN', 'AUGMENT_SLOT'
        ]

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session  = requests.Session()
        
        auth_data = {
            "client_id": "riot-client",
            "nonce": "1",
            "redirect_uri": "http://localhost/redirect",
            "response_type": "token id_token",
            "scope":"openid link ban lol_region",
        }

        auth_response = self.session.post(
                url=self.AUTH_URL,
                json=auth_data
            )
        self._get_tokens()
        self._get_user_info()

    def _get_tokens(self):
        json_data = {
            "type": "auth",
            "username": self.username,
            "password": self.password,
        }
        response = self.session.put(
                url=self.AUTH_URL,
                json=json_data
            )
        response = response.json()
        # print (response, '-=-=-')
        # uri format 
        # "http://local/redirect#access_token=...
        # &scope=...&id_token=...&token_type=
        # &expires_in=...
        uri = response['response']['parameters']['uri']
        infos = uri.split('=')
        infos = [x.split('&')[0] for x in infos]
        self.access_token = infos[1]
        self.id_token = infos[3]
    
    def _get_user_info(self):
        auth = {"Authorization": f"Bearer {self.access_token}"}
        self.session.headers.update(auth)
        
        response = self.session.post(url=self.INFO_URL)
        self.user_info = response.json()

        return response.json()['ban']['code'] == ''
    
    def get_inventory(self, types=INVENTORY_TYPES):
        invt_url = f"https://{self.user_info['region']['id']}.cap.riotgames.com/lolinventoryservice/v2/inventories/simple?"
        detail_invt_url = f"https://{self.user_info['region']['id']}.cap.riotgames.com/lolinventoryservice/v2/inventoriesWithLoyalty?"

        query = {
            "puuid": self.user_info['sub'],
            "location": f"lolriot.pdx2.{self.user_info['region']['id']}",
            "accountId": self.user_info['lol']['cuid'],
        }
        query_string = [f"{k}={v}" for k, v in query.items()]
        for t in types:
            query_string.append(f"inventoryTypes={t}")
        query_string = '&'.join(query_string)
        URL = invt_url + query_string

        auth = {"Authorization": f"Bearer {self.access_token}"}
        self.session.headers.update(auth)

        response = self.session.get(url=URL)
        result = response.json()['data']['items']

        champion_names = []
        champion_skins = []

        for champion_id in result['CHAMPION']:
            champion_data = requests.get(self.CHAMPION_DATA_URL + str(champion_id) + '.json').json()
            champion_skins.extend([skin['name'] for skin in champion_data['skins'] if skin['id'] in result['CHAMPION_SKIN']])
            champion_names.append(champion_data['name'])
        
        result['CHAMPION'] = champion_names
        result['CHAMPION_SKIN'] = champion_skins

        return result
    
    def get_balance(self):
        store_url = f"https://{self.user_info['region']['tag']}.store.leagueoflegends.com/storefront/v3/view/misc?language=en_US"

        auth = {"Authorization": f"Bearer {self.access_token}"}
        self.session.headers.update(auth)

        response = self.session.get(store_url)
        result = response.json()['player']
        return result

    def get_purchase_history(self):
        hist_url = f"https://{self.user_info['region']['tag']}.store.leagueoflegends.com/storefront/v3/history/purchase"

        auth = {"Authorization": f"Bearer {self.access_token}"}
        self.session.headers.update(auth)

        response = self.session.get(url=hist_url)
        result = response.json()
        return result

    def refundable_RP(self):
        history = self.get_purchase_history()
        refund_num = history['refundCreditsRemaining']
        refundables = [x['amountSpent'] 
                            for x in history['transactions'] 
                            if x['refundable'] and
                            x['currencyType']=='RP']
        result = sum(sorted(refundables, reverse=True)[:refund_num])
        return result

    def refundable_IP(self):
        history = self.get_purchase_history()
        refund_num = history['refundCreditsRemaining']
        refundables = [x['amountSpent'] 
                            for x in history['transactions'] 
                            if x['refundable'] and
                            x['currencyType']=='IP']
        result = sum(sorted(refundables, reverse=True)[:refund_num])
        return result

    def last_play(self):
        matches_url = "https://acs.leagueoflegends.com/v1/stats/player_history/auth?begIndex=0&endIndex=1"
        
        auth = {"Authorization": f"Bearer {self.access_token}"}
        self.session.headers.update(auth)

        response = self.session.get(url=matches_url)
        return (self._date_readable(response.json()))
    
    def get_rank(self):
        rank_url = f"https://lolprofile.net/index.php?page=summoner&ajaxr=1&region={self.user_info['region']['tag']}&name={self.user_info['lol_account']['summoner_name']}"
        page = requests.get(rank_url).text
        pattern = '(?<=-block">)(.*?)(?=</div>)'
        rank = re.search(pattern, page)
        return rank.group() if rank is not None else "Unranked"
    
    def print_info(self):
        inventory_data = self.get_inventory()
        ip_value = self.refundable_IP()
        rp_value = self.refundable_RP()
        region = self.user_info['region']['tag'].upper()
        name  = self.user_info['lol_account']['summoner_name']
        level = self.user_info['lol_account']['summoner_level']
        balance = self.get_balance()
        last_game = self.last_play()
        champions = ', '.join(inventory_data['CHAMPION'])
        champion_skins = ', '.join(inventory_data['CHAMPION_SKIN'])
        rp_curr = balance['rp']
        ip_curr = balance['ip']
        rank = self.get_rank()
        ret_str = [f" | Region: {region}", f"Name: {name}", f"Login: {self.username}:{self.password}", f"Last Game: {last_game}", f"Level: {level}", f"Rank: {rank}", f"IP: {ip_curr} - Refundable {ip_value}", f"RP: {rp_curr} - Refundable {rp_value}", "\n", "\n", f"Champions ({len(inventory_data['CHAMPION'])}): {champions}", "\n", "\n", f"Skins ({len(inventory_data['CHAMPION_SKIN'])}): {champion_skins}"]
        return ' | '.join(ret_str)

    def _date_readable(self, variable):    
        timeCreation = variable['games']['games'][0]['gameCreation']
        
        dateTime = datetime.datetime.fromtimestamp(
            int(timeCreation /1000)
        ).strftime('%Y-%m-%d %H:%M:%S')
        
        return dateTime

account_list = [i for i in ACCOUNTS.replace(" ", "").split(",")]
for account in account_list:
    user, pw = account.split(":")
    account_checker = AccountChecker(user, pw)
    print(account_checker.print_info())
