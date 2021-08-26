from datetime import datetime
import requests, concurrent.futures, re, time

'''
Paste you accounts below separated by commas
'''
ACCOUNTS = "user:pass, user1:pass1,user2:pass2"


class AccountChecker:
    AUTH_URL = "https://auth.riotgames.com/api/v1/authorization"
    INFO_URL = "https://auth.riotgames.com/userinfo"
    CHAMPION_DATA_URL = "https://cdn.communitydragon.org/latest/champion/"
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

        self.session.post(
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
        try:
            uri = response['response']['parameters']['uri']
            infos = uri.split('=')
            infos = [x.split('&')[0] for x in infos]
            self.access_token = infos[1]
            self.id_token = infos[3]
        except:
            print(f"Authorization error on {self.username}")
            print(response)
    
    def _get_user_info(self):
        auth = {"Authorization": f"Bearer {self.access_token}"}
        self.session.headers.update(auth)
        
        response = self.session.post(url=self.INFO_URL)
        self.user_info = response.json()

        self.region_id = self.user_info['region']['id']
        self.region_tag = self.user_info['region']['tag']

        return response.json()['ban']['code'] == ''
    
    def get_inventory(self, types=INVENTORY_TYPES):
        invt_url = f"https://{self.region_id}.cap.riotgames.com/lolinventoryservice/v2/inventories/simple?"
        #detail_invt_url = f"https://{self.region_id}.cap.riotgames.com/lolinventoryservice/v2/inventoriesWithLoyalty?"

        LOCATION_PARAMETERS = {
            "BR1": "lolriot.mia1.br1",
            "EUN1": "lolriot.euc1.eun1",
            "EUW1": "lolriot.ams1.euw1",
            "JP1": "lolriot.nrt1.jp1",
            "LA1": "lolriot.mia1.la1",
            "LA2": "lolriot.mia1.la2",
            "NA1": "lolriot.pdx2.na1",
            "OC1": "lolriot.pdx1.oc1",
            "RU": "lolriot.euc1.ru",
            "TR1": "lolriot.euc1.tr1"
        }

        query = {
            "puuid": self.user_info['sub'],
            "location": LOCATION_PARAMETERS[self.region_id],
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

        try:
            result = response.json()['data']['items']
        except:
            print(f"Failed to get inventory data on {self.username}")
            print(response)
            return
        
        champion_names = []
        champion_skins = []
        champion_urls = [self.CHAMPION_DATA_URL + str(champion_id) + "/data" for champion_id in result['CHAMPION']]

        def load_url(url):
            champion_data = requests.get(url)
            return champion_data

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_url = (executor.submit(load_url, url) for url in champion_urls)
            
            for future in concurrent.futures.as_completed(future_to_url):
                try:
                    data = future.result().json()
                    champion_skins.extend([skin['name'] for skin in data['skins'] if skin['id'] in result['CHAMPION_SKIN']])
                    champion_names.append(data['name'])
                except:
                    print("Champion/skin conversion failed for 1 champion")
        
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
        rank_url = f"https://lolprofile.net/index.php?page=summoner&ajaxr=1&region={self.region_tag}&name={self.user_info['lol_account']['summoner_name']}"
        page = requests.get(rank_url).text
        pattern = '((?<="tier">)(.*?)(?=<)|(?<="lp">)(.*?)(?=<))'
        rank = re.findall(pattern, page)
        return ' '.join([rank[0][0], rank[1][0]]) if rank else "Unranked"
    
    def print_info(self):
        inventory_data = self.get_inventory()
        ip_value = self.refundable_IP()
        rp_value = self.refundable_RP()
        region = self.region_tag.upper()
        ban_status = f"True ({self.user_info['ban']['code']})" if self.user_info['ban']['code'] else "False"
        name  = self.user_info['lol_account']['summoner_name']
        level = self.user_info['lol_account']['summoner_level']
        balance = self.get_balance()
        last_game = self.last_play()
        champions = ', '.join(inventory_data['CHAMPION'])
        champion_skins = ', '.join(inventory_data['CHAMPION_SKIN'])
        rp_curr = balance['rp']
        ip_curr = balance['ip']
        rank = self.get_rank()
        ret_str = [f" | Region: {region}", f"Name: {name}", f"Login: {self.username}:{self.password}", f"Last Game: {last_game}", f"Level: {level}", f"Rank: {rank}", f"IP: {ip_curr} - Refundable {ip_value}", f"RP: {rp_curr} - Refundable {rp_value}", f"Banned: {ban_status}", "\n", "\n", f"Champions ({len(inventory_data['CHAMPION'])}): {champions}", "\n", "\n", f"Skins ({len(inventory_data['CHAMPION_SKIN'])}): {champion_skins}", "\n", "\n", "\n"]
        return ' | '.join(ret_str)

    def _date_readable(self, variable):
        try:
            timeCreation = variable['games']['games'][0]['gameCreation']
        
            dateTime = datetime.datetime.fromtimestamp(
                int(timeCreation /1000)
            ).strftime('%Y-%m-%d %H:%M:%S')
        
            return dateTime
        except:
            return "No previous games"

account_list = [i for i in ACCOUNTS.replace(" ", "").split(",")]

def load_account(account):
    user, pw = account.split(":")
    account_checker = AccountChecker(user, pw)
    return account_checker

time1 = time.time()
print(f"Checking accounts, please wait...")
with concurrent.futures.ThreadPoolExecutor() as executor:
    future_to_acc = (executor.submit(load_account, acc) for acc in account_list)
    for future in concurrent.futures.as_completed(future_to_acc):
        try:
            data = future.result()
            with open(f"accounts-{str(time1)}.txt", 'a') as account_writer:
                account_writer.write(data.print_info())
        except Exception as exc:
            print("Failed to retrieve account.")
time2 = time.time()
print(f"Complete! Account information located in accounts-{str(time1)}.txt")
print(f'Took {time2-time1:.2f} s')
