from datetime import datetime
import requests, os, concurrent.futures, json, time, traceback

#
# Please rename checker.env.example to checker.env and place information their instead
#
ACCOUNTS = "user:pass, user1:pass1,user2:pass2"
TIMEOUT = 5

if os.path.exists(rf"checker.env"):
    with open(rf"checker.env", "r") as f:
        ENV_DICT = dict(
            tuple(line.replace("\n", "").split("="))
            for line in f.readlines()
            if not line.startswith("#") or not line.strip()
        )

        ACCOUNTS = ENV_DICT["ACCOUNTS"]
        TIMEOUT = int(ENV_DICT["TIMEOUT"])


class Constants:
    AUTH_URL = "https://auth.riotgames.com/api/v1/authorization"
    INFO_URL = "https://auth.riotgames.com/userinfo"
    INVENTORY_URL = "https://{region_id}.cap.riotgames.com/lolinventoryservice/v2/inventories/simple?"
    DETAILED_INVENTORY_URL = "https://{region_id}.cap.riotgames.com/lolinventoryservice/v2/inventoriesWithLoyalty?"
    STORE_URL = "https://{store_front_id}.store.leagueoflegends.com/storefront/v3/view/misc?language=en_US"
    HISTORY_URL = "https://{store_front_id}.store.leagueoflegends.com/storefront/v3/history/purchase"
    MATCHES_URL = "https://acs.leagueoflegends.com/v1/stats/player_history/auth?begIndex=0&endIndex=1"

    # bl1tzgg rank checking endpoint
    RANK_URL = "https://riot.iesdev.com/graphql?query=query%20LeagueProfile%28%24summoner_name%3AString%2C%24summoner_id%3AString%2C%24account_id%3AString%2C%24region%3ARegion%21%2C%24puuid%3AString%29%7BleagueProfile%28summoner_name%3A%24summoner_name%2Csummoner_id%3A%24summoner_id%2Caccount_id%3A%24account_id%2Cregion%3A%24region%2Cpuuid%3A%24puuid%29%7BaccountId%20latestRanks%7Bqueue%20tier%20rank%20leaguePoints%7D%7D%7D&variables=%7B%22summoner_name%22%3A%22{summoner_name}%22%2C%22region%22%3A%22{region_id}%22%7D"

    # bl1tzgg matches checking endpoint
    NEW_MATCHES_URL = "https://league-player.iesdev.com/graphql?query=query%20matches%28%0A%20%20%24region%3A%20Region%21%0A%20%20%24accountId%3A%20String%21%0A%20%20%24first%3A%20Int%0A%20%20%24role%3A%20Role%0A%20%20%24queue%3A%20Queue%0A%20%20%24championId%3A%20Int%0A%20%20%24riotSeasonId%3A%20Int%0A%20%20%24maxMatchAge%3A%20Int%0A%29%20%7B%0A%20%20matches%28%0A%20%20%20%20region%3A%20%24region%0A%20%20%20%20accountId%3A%20%24accountId%0A%20%20%20%20first%3A%20%24first%0A%20%20%20%20role%3A%20%24role%0A%20%20%20%20queue%3A%20%24queue%0A%20%20%20%20championId%3A%20%24championId%0A%20%20%20%20riotSeasonId%3A%20%24riotSeasonId%0A%20%20%20%20maxMatchAge%3A%20%24maxMatchAge%0A%20%20%29%20%7B%0A%20%20%20%20id%0A%20%20%20%20gameCreation%0A%20%20%7D%0A%7D&variables=%7B%22maxMatchAge%22%3A300%2C%22first%22%3A1%2C%22region%22%3A%22{region_id}%22%2C%22accountId%22%3A%22{account_id}%22%7D"

    CHAMPION_DATA_URL = "https://cdn.communitydragon.org/latest/champion/"
    CHAMPION_IDS_URL = (
        "http://ddragon.leagueoflegends.com/cdn/{game_version}/data/en_US/champion.json"
    )

    VERSION_URL = "https://ddragon.leagueoflegends.com/api/versions.json"

    INVENTORY_TYPES = [
        "TOURNAMENT_TROPHY",
        "TOURNAMENT_FLAG",
        "TOURNAMENT_FRAME",
        "TOURNAMENT_LOGO",
        "GEAR",
        "SKIN_UPGRADE_RECALL",
        "SPELL_BOOK_PAGE",
        "BOOST",
        "BUNDLES",
        "CHAMPION",
        "CHAMPION_SKIN",
        "EMOTE",
        "GIFT",
        "HEXTECH_CRAFTING",
        "MYSTERY",
        "RUNE",
        "STATSTONE",
        "SUMMONER_CUSTOMIZATION",
        "SUMMONER_ICON",
        "TEAM_SKIN_PURCHASE",
        "TRANSFER",
        "COMPANION",
        "TFT_MAP_SKIN",
        "WARD_SKIN",
        "AUGMENT_SLOT",
    ]

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
        "TR1": "lolriot.euc1.tr1",
    }

    STORE_FRONTS = {
        "BR1": "br",
        "EUN1": "eun",
        "EUW1": "euw",
        "JP1": "jp",
        "LA1": "la1",
        "LA2": "la2",
        "NA1": "na",
        "OC1": "oc",
        "RU": "ru",
        "TR1": "tr",
    }


class ChampionData:
    def __init__(self):
        game_version = requests.get(Constants.VERSION_URL).json()
        self.game_version = game_version[0]

    def build_champion_data(self):
        champion_ids = requests.get(
            Constants.CHAMPION_IDS_URL.format(game_version=self.game_version)
        ).json()
        champion_data_builder = {
            "champions": {
                int(value["key"]): champion_name
                for (champion_name, value) in champion_ids["data"].items()
            }
        }
        champion_data_builder["version"] = self.game_version
        champion_data_builder["skins"] = {}

        champion_urls = [
            Constants.CHAMPION_DATA_URL + str(champion_id) + "/data"
            for champion_id in champion_data_builder["champions"].keys()
        ]

        def load_url(url):
            champion_data = requests.get(url)
            return champion_data

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_url = (executor.submit(load_url, url) for url in champion_urls)
            for future in concurrent.futures.as_completed(future_to_url):
                data = future.result().json()
                for skin in data["skins"]:
                    champion_data_builder["skins"][skin["id"]] = skin["name"]
                    if "chromas" in skin:
                        for chroma in skin["chromas"]:
                            champion_data_builder["skins"][chroma["id"]] = (
                                chroma["name"] + " (Chroma)"
                            )

        return champion_data_builder

    def get_champion_data(self):
        CHAMPION_FILE_PATH = rf"data{os.path.sep}champion_data.json"
        FOLDER_PATH = rf"data{os.path.sep}"

        if not os.path.exists(FOLDER_PATH):
            os.makedirs(os.path.dirname(CHAMPION_FILE_PATH))

        if not os.path.exists(CHAMPION_FILE_PATH):
            file = open(CHAMPION_FILE_PATH, "x", encoding="utf-8")
            json.dump({"version": "0"}, file, ensure_ascii=False, indent=2)
            file.close()

        updated_champion_data = {}
        champion_data = {}

        with open(CHAMPION_FILE_PATH, "r", encoding="utf-8") as reader:
            champion_data = json.load(reader)

        with open(CHAMPION_FILE_PATH, "w", encoding="utf-8") as writer:
            if champion_data["version"] != self.game_version:
                champion_data = self.build_champion_data()
                updated_champion_data = champion_data
                json.dump(champion_data, writer, ensure_ascii=False, indent=2)
            else:
                updated_champion_data = champion_data
                json.dump(champion_data, writer, ensure_ascii=False, indent=2)

        return updated_champion_data


class AccountChecker:
    def __init__(self, username, password, proxy={}):
        self.username = username
        self.password = password
        self.session = requests.Session()

        self.session.proxies.update(proxy)

        tokens = self._authorize()
        self.access_token = tokens[1]
        self.id_token = tokens[3]

        auth = {
            "Accept-Encoding": "deflate, gzip",
            "user-agent": "RiotClient/44.0.1.4223069.4190634 lol-inventory (Windows;10;;Professional, x64)",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }

        self.session.headers.update(auth)

        self.user_info = self._get_user_info()

        self.region_id = self.user_info["region"]["id"]
        self.region_tag = self.user_info["region"]["tag"]
        self.summoner_name = self.user_info["lol_account"]["summoner_name"]

        self.purchase_history = self.get_purchase_history()

    def _authorize(self):
        headers = {
            "user-agent": "RiotClient/44.0.1.4223069.4190634 rso-auth (Windows;10;;Professional, x64)",
            "Accept": "application/json",
        }

        auth_data = {
            "client_id": "riot-client",
            "nonce": "1",
            "redirect_uri": "http://localhost/redirect",
            "response_type": "token id_token",
            "scope": "openid offline_access lol ban profile email phone",
        }

        login_data = {
            "language": "en_US",
            "password": self.password,
            "remember": "true",
            "type": "auth",
            "username": self.username,
        }

        self.session.post(url=Constants.AUTH_URL, headers=headers, json=auth_data)

        response = self.session.put(
            url=Constants.AUTH_URL, headers=headers, json=login_data
        ).json()

        # print (response, '-=-=-')
        # uri format
        # "http://local/redirect#access_token=...
        # &scope=...&id_token=...&token_type=
        # &expires_in=...
        try:
            uri = response["response"]["parameters"]["uri"]
        except:
            print(f"Error authenticating {self.username}!")
            print(f"Response: {response}")
            raise

        tokens = [x.split("&")[0] for x in uri.split("=")]
        return tokens

    def _get_user_info(self):
        return self.session.post(url=Constants.INFO_URL).json()

    def get_inventory(self, types=Constants.INVENTORY_TYPES):
        champion_data_builder = ChampionData()
        champion_data = champion_data_builder.get_champion_data()

        query = {
            "puuid": self.user_info["sub"],
            "location": Constants.LOCATION_PARAMETERS[self.region_id],
            "accountId": self.user_info["pvpnet_account_id"],
        }
        query_string = "&".join(
            [f"{k}={v}" for k, v in query.items()]
            + [f"inventoryTypes={t}" for t in types]
        )

        response = self.session.get(
            url=Constants.INVENTORY_URL.format(region_id=self.region_id) + query_string
        )

        try:
            result = response.json()["data"]["items"]
        except:
            print(f"Failed to get inventory data on {self.username}")
            print(f"Response: {response.json()}")
            return {"CHAMPION": [], "CHAMPION_SKINS": []}

        result["CHAMPION"] = [
            champion_data["champions"][str(id)] for id in result["CHAMPION"]
        ]
        result["CHAMPION_SKIN"] = [
            champion_data["skins"][str(id)] for id in result["CHAMPION_SKIN"]
        ]

        return result

    def get_balance(self):
        response = self.session.get(
            Constants.STORE_URL.format(
                store_front_id=Constants.STORE_FRONTS[self.region_id]
            )
        ).json()
        return response["player"]

    def get_purchase_history(self):
        response = self.session.get(
            Constants.HISTORY_URL.format(
                store_front_id=Constants.STORE_FRONTS[self.region_id]
            )
        ).json()
        return response

    def refundable_RP(self):
        history = self.purchase_history
        refund_num = history["refundCreditsRemaining"]
        refundables = [
            x["amountSpent"]
            for x in history["transactions"]
            if x["refundable"] and x["currencyType"] == "RP"
        ]
        result = sum(sorted(refundables, reverse=True)[:refund_num])
        return result

    def refundable_IP(self):
        history = self.purchase_history
        refund_num = history["refundCreditsRemaining"]
        refundables = [
            x["amountSpent"]
            for x in history["transactions"]
            if x["refundable"] and x["currencyType"] == "IP"
        ]
        result = sum(sorted(refundables, reverse=True)[:refund_num])
        return result

    def last_play(self):
        response = self.session.get(
            Constants.NEW_MATCHES_URL.format(
                region_id=self.region_id, account_id=self.account_id
            )
        ).json()

        try:
            recent_match_date = list(response["data"]["matches"])
        except:
            print(f"Failed getting recent match of {self.username}")
            print(f"Response: {response}")
            return "Unknown"

        if len(recent_match_date) > 0:
            return datetime.strptime(
                recent_match_date[0]["gameCreation"], "%Y-%m-%dT%H:%M:%S.%fZ"
            )
        return "Unavailable"

    def get_rank(self):
        response = requests.get(
            Constants.RANK_URL.format(
                region_id=self.region_id, summoner_name=self.summoner_name
            )
        ).json()

        try:
            rank = response["data"]["leagueProfile"]["latestRanks"]
            self.account_id = response["data"]["leagueProfile"]["accountId"]
        except:
            print(f"Failed getting rank of {self.username}")
            print(f"Response: {response}")
            return "Unranked"

        if rank:
            for queue in rank:
                if queue["queue"] == "RANKED_SOLO_5X5":
                    return f'{queue["tier"]} {queue["rank"]} {queue["leaguePoints"]} LP'
        return "Unranked"

    def get_ban(self):
        try:
            if int(time.time() * 1000) < int(self.user_info["ban"]["exp"]):
                return f"True ({self.user_info['ban']['code']})"
            return "False"
        except:
            return "False"

    def print_info(self):
        inventory_data = self.get_inventory()
        rank = self.get_rank()
        ip_value = self.refundable_IP()
        rp_value = self.refundable_RP()
        refunds = self.purchase_history["refundCreditsRemaining"]
        region = self.region_tag.upper()
        ban_status = self.get_ban()
        name = self.summoner_name
        level = self.user_info["lol_account"]["summoner_level"]
        balance = self.get_balance()
        last_game = self.last_play()
        champions = ", ".join(inventory_data["CHAMPION"])
        champion_skins = ", ".join(inventory_data["CHAMPION_SKIN"])
        rp_curr = balance["rp"]
        ip_curr = balance["ip"]
        ret_str = [
            f" | Region: {region}",
            f"Name: {name}",
            f"Login: {self.username}:{self.password}",
            f"Last Game: {last_game}",
            f"Level: {level}",
            f"Rank: {rank}",
            f"IP: {ip_curr} - Refundable {ip_value}",
            f"RP: {rp_curr} - Refundable {rp_value}",
            f"Refunds: {refunds}",
            f"Banned: {ban_status}",
            "\n",
            "\n",
            f"Champions ({len(inventory_data['CHAMPION'])}): {champions}",
            "\n",
            "\n",
            f"Skins ({len(inventory_data['CHAMPION_SKIN'])}): {champion_skins}",
            "\n",
            "\n",
            "\n",
        ]
        return " | ".join(ret_str)


account_list = [i for i in ACCOUNTS.replace(" ", "").split(",")]


def load_account(account):
    user, pw = account.split(":")
    # account_checker = AccountChecker(user, pw, {"https": "https://PROXY:PORT"})
    account_checker = AccountChecker(user, pw)
    return account_checker


time1 = time.time()
print(f"Checking/building champion data...")
cache_champion_data = ChampionData()
cache_champion_data.get_champion_data()
time2 = time.time()
print(f"Took {time2-time1:.2f} s")

time1 = time.time()
formated_time = datetime.fromtimestamp(time1).strftime("%Y-%m-%d_%H-%M-%S")
print(f"Checking accounts, please wait...")

ACCOUNTS_FOLDER_PATH = rf"output{os.path.sep}"

if not os.path.exists(ACCOUNTS_FOLDER_PATH):
    os.makedirs(os.path.dirname(ACCOUNTS_FOLDER_PATH))

for account in account_list:
    try:
        (username, password) = account.split(":")
        # To use a proxy, may not work
        # account_checker = AccountChecker(username, password, {"https": "https://PROXY:PORT"})
        account_checker = AccountChecker(username, password)
        with open(
            f"{ACCOUNTS_FOLDER_PATH}accounts {str(formated_time)}.txt",
            "a",
            encoding="utf-8",
        ) as account_writer:
            account_writer.write(account_checker.print_info())
    except:
        print(f"Error occured while checking {username}")
        print(traceback.format_exc())
    if TIMEOUT > 0:
        print(f"Waiting {TIMEOUT} seconds before checking account...")
        time.sleep(TIMEOUT)

time2 = time.time()
print(f"Complete! Account information located in accounts-{str(formated_time)}.txt")
print(f"Took {time2-time1:.2f} s")
