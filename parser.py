import time
import random as rnd
import requests
from bs4 import BeautifulSoup
import json
import os


# Делаем запрос на сайт, сохраняем id последнего матча
url = 'https://ru.dotabuff.com/esports/matches'
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
response = requests.get(url, headers=headers)
first_id = ""
# API KEY для доступа к API
API_KEY = "44d9bbe4-ea83-4790-a35f-f8b07f1e60fe"

# Информация о матчах
matches_data = []

#Сохранённая информация о матчах
json_file = "parsed_matches.json"


def json_write(json_file):
    global matches_data
    # Читаем файл, если не удаётся, вываливаемся с ошибкой
    if os.path.exists(json_file):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                # Проверяем, не пустой ли файл
                content = f.read().strip()
                if content:
                    file_data = json.loads(content)
                else:
                    file_data = []
        except Exception as e:
            print(f"Ошибка чтения файла {json_file}: {e}")
            return
    else:
        # Если файла нет, создаем пустой
        print(f"Файл {json_file} не найден, создаем новый.")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=4)
        file_data = []
    
    # Сортируем данные по match_id
    file_data_sorted = sorted(file_data, key=lambda m: int(m["match_id"]))
    matches_data_sorted = sorted(matches_data, key=lambda m: int(m["match_id"]))
    # Слияние двух отсортированных списков в один (с учётом уникальности матчей)
    merged = []
    i, j = 0, 0
    while i < len(file_data_sorted) and j < len(matches_data_sorted):
        id_file = int(file_data_sorted[i]["match_id"])
        id_new = int(matches_data_sorted[j]["match_id"])
        if id_file == id_new:
            merged.append(file_data_sorted[i])
            i += 1
            j += 1
        elif id_file < id_new:
            merged.append(file_data_sorted[i])
            i += 1
        else:
            merged.append(matches_data_sorted[j])
            j += 1
    while i < len(file_data_sorted):
        merged.append(file_data_sorted[i])
        i += 1
    while j < len(matches_data_sorted):
        merged.append(matches_data_sorted[j])
        j += 1
    # Перезаписываем файл
    try:
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка записи в файл {json_file}: {e}")
        return
    print("Информация успешно записана!")
    print("Количество уникальных матчей:", len(merged))
    matches_data = []


def match_link_parser(api_response, debug, match_id):
    global matches_data
    
    # Извлекаем информацию из JSON, полученного через API
    radiant_win = api_response.get("radiant_win", None)
    if radiant_win is None:
        print("Ошибка: Нет информации о победе Radiant!")
        return {}
    # Если Radiant выиграли, то winner = False
    # Если Dire, то True
    winner_team = False if radiant_win else True
    # Разделяем игроков на Radiant и Dire
    radiant_players = []
    dire_players = []
    for player in api_response.get("players", []):
        if player.get("isRadiant", False):
            radiant_players.append(player)
        else:
            dire_players.append(player)
    # Формируем списки героев для обеих команд
    radiant_heroes = [str(player.get("hero_id", "")) for player in radiant_players]
    dire_heroes = [str(player.get("hero_id", "")) for player in dire_players]
    # Сохраняем всю нужную информацию
    def extract_player_info(player):
        return {
            "hero_id": player.get("hero_id", ""),
            "kills": player.get("kills", ""),
            "deaths": player.get("deaths", ""),
            "assists": player.get("assists", ""),
            "gold_per_min": player.get("gold_per_min", ""),
            "xp_per_min": player.get("xp_per_min", ""),
            "last_hits": player.get("last_hits", ""),
            "hero_damage": player.get("hero_damage", ""),
            "tower_damage": player.get("tower_damage", ""),
            "kda": ""
        }
    radiant_players_info = [extract_player_info(p) for p in radiant_players]
    dire_players_info = [extract_player_info(p) for p in dire_players]
    radiant_team_name = "Силы Света"
    dire_team_name = "Силы Тьмы"
    radiant_score = api_response.get("radiant_score", 0)
    dire_score = api_response.get("dire_score", 0)

    if debug:
        print("Radiant heroes:", radiant_heroes)
        print("Dire heroes:", dire_heroes)
        print("Победитель:", "Radiant" if not winner_team else "Dire")
    match_data = {
        "match_id": match_id,
        "radiant_team_name": radiant_team_name,
        "dire_team_name": dire_team_name,
        "radiant_heroes": radiant_heroes,
        "dire_heroes": dire_heroes,
        "radiant_players_info": radiant_players_info,
        "dire_players_info": dire_players_info,
        "winner": winner_team,
        "radiant_score": radiant_score,
        "dire_score": dire_score
    }
    matches_data.append(match_data)
    return 0


def match_link_reader(link, debug):
    print(f"Переходим по ссылке: {link}")
    try: # Ждём немного времени и делаем запрос
        time.sleep(rnd.uniform(1, 2))
        match_response = requests.get(link, headers=headers, timeout=10)
        match_response.raise_for_status()
    except requests.exceptions.HTTPError as e: # Ловим ошибки запроса
        if match_response.status_code == 429:
            time_wait = 30
            print(f"Ошибка 429: слишком много запросов. Ожидание {time_wait} секунд...")
            time.sleep(time_wait)
            return match_link_reader(link, debug)
        elif match_response.status_code == 404:
            print("Ошибка 404: пропускаем следующие 5 запросов")
            return 404
        else:
            print(f"Ошибка при выполнении запроса {link}: {e}")
            return
    except requests.exceptions.Timeout:
        print(f"Ошибка таймаута при запросе {link}")
        return
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса {link}: {e}")
        return
    except Exception as e:
        print(f"Ошибка при выполнении запроса {link}: {e}")
        return

    # Аналогично - если получили информацию с сайта, начинаем его парсить
    if match_response.status_code == 200:
        try:
            api_response = match_response.json()
        except json.JSONDecodeError as e:
            print(f"Ошибка декодирования JSON {link}: {e}")
            return
        # Извлекаем match_id из ссылки
        match_id = link.split('/')[-1].split('?')[0]
        status = match_link_parser(api_response, debug, match_id)
        # Если status = 0, то записываем данные в датасет
        if not(status):
            json_write(json_file)
        else:
            print(f"Пропускаем матч из-за ошибки при парсинге. Status = {status}")
            return
    else:
        print(f"Ошибка при загрузке {link}: статус {match_response.status_code}")


def parser(num=10, debug=True):
    global first_id, response
    # Делаем запрос на стартовую страницу - если response, то идём в if читать страницу
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='recent-esports-matches')
        rows = table.tbody.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            match_link = cols[2].find('a')
            # Нашли первую страницу - запомнили id последнего матча и вышли из цикла
            if match_link:
                first_id = int(match_link.get('href')[9:]) - rnd.randint(0, 252)
                break
        # Генерируем ссылки на матчи
        match_links = [f"{"https://api.opendota.com/api/matches/"}{first_id - it}?api_key={API_KEY}" for it in range(num)]
        cnt = 0
        skip_count = 0
        # Идём парсить список ссылок циклом
        for link in match_links:
            cnt += 1
            if skip_count > 0:
                skip_count -= 1
                continue
            if match_link_reader(link, debug) == 404:  # Если получаем 404, то пропускаем следующие 5 ссылок
                skip_count = 5
                continue
            # Следим за процессом работы
            print(f'{cnt} / {num}')
    else:
        print(f"Ошибка: {response.status_code}")


iterations = 6000

# ЗАПУСКАЕМ ПАРСЕР
parser(iterations)
