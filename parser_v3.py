'''
parser v3
Оформили готовый код, который считывают всю нужную инфу с сайта и записывает в json.
Теперь будем переходить на париснг апи.
'''


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

# Информация о матчах - update version
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


def match_link_parser(link_soup, debug, match_id):
    global matches_data
    """
    Собираем полезную информацию со страницы матча
    1) Герои Radiant и Dire.
    2) Названия команд (если есть) или "Силы Света"/"Силы Тьмы".
    3) Победитель матча.
    """
    # 1) ПОИСК ГЕРОЕВ
    radiant_selector = (
        "section.radiant > article > table > tbody tr.col-hints.faction-radiant "
        "td.cell-fill-image div[data-component-name='HeroIconEntry'] div.x-tw-base a[href^='/heroes/']"
    )
    radiant_anchors = link_soup.select(radiant_selector)
    radiant_heroes = [a.get("href", "").split("/")[-1] for a in radiant_anchors]

    dire_selector = (
        "section.dire > article > table > tbody tr.col-hints.faction-dire "
        "td.cell-fill-image div[data-component-name='HeroIconEntry'] div.x-tw-base a[href^='/heroes/']"
    )
    dire_anchors = link_soup.select(dire_selector)
    dire_heroes = [a.get("href", "").split("/")[-1] for a in dire_anchors]

    # 2) ПОИСК НАЗВАНИЯ КОМАНДА
    radiant_team_name_elem = link_soup.select_one(
        ".match-result.team.radiant a span.team-text.team-text-full"
    )
    dire_team_name_elem = link_soup.select_one(
        ".match-result.team.dire a span.team-text.team-text-full"
    )

    if radiant_team_name_elem and dire_team_name_elem:
        radiant_team_name = radiant_team_name_elem.get_text(strip=True)
        dire_team_name = dire_team_name_elem.get_text(strip=True)
    else:
        rad_header = link_soup.select_one("section.radiant > header")
        dire_header = link_soup.select_one("section.dire > header")
        radiant_team_name = rad_header.get_text(strip=True) if rad_header else "Силы Света"
        dire_team_name = dire_header.get_text(strip=True) if dire_header else "Силы Тьмы"

    # 3) ПОИСК РЕЗУЛЬТАТА МАТЧА
    radiant_result_div = link_soup.select_one(".match-result.team.radiant")
    dire_result_div = link_soup.select_one(".match-result.team.dire")
    winner_team = None
    '''if radiant_result_div and ("Победа" in radiant_result_div.get_text() or "winner" in radiant_result_div.get_text().lower()):
        winner_team = False
    elif dire_result_div and ("Победа" in dire_result_div.get_text() or "winner" in dire_result_div.get_text().lower()):
        winner_team = True
    else:
        print("Ошибка: Не удалось определить победителя матча!")
        return {}'
    '''
    if radiant_result_div:
        radiant_text = radiant_result_div.get_text(strip=True)
        if "Победа" in radiant_text or "winner" in radiant_text.lower():
            winner_team = False  # Победа Radiant
    if dire_result_div and winner_team is None:
        dire_text = dire_result_div.get_text(strip=True)
        if "Победа" in dire_text or "winner" in dire_text.lower():
            winner_team = True   # Победа Dire
    if winner_team is None:
        print("Ошибка: Не удалось о пределить победителя матча!")
        return {}
    

    if debug:
        print("Radiant heroes:", radiant_heroes)
        print("Dire heroes:", dire_heroes)
        print("Radiant team name:", radiant_team_name)
        print("Dire team name:", dire_team_name)
        if winner_team is False:
            print("Победитель: Radiant")
        elif winner_team is True:
            print("Победитель: Dire")


    # Сохраняем информацию в parsed_matches.json
    match_data = {
        "match_id": match_id, # ДОПИСАТЬ
        "radiant_team_name": radiant_team_name,
        "dire_team_name": dire_team_name,
        "radiant_heroes": radiant_heroes,
        "dire_heroes": dire_heroes,
        "radiant_players_info": [
            {
                "hero_id": hero,
                "kda": "",
                "kills": "",
                "deaths": "",
                "assists": "",
                "gold_per_min": "",
                "xp_per_min": "",
                "last_hits": "",
                "hero_damage": "",
                "tower_damage": ""
            }
            for hero in radiant_heroes
        ],
        "dire_players_info": [
            {
                "hero_id": hero,
                "kda": "",
                "kills": "",
                "deaths": "",
                "assists": "",
                "gold_per_min": "",
                "xp_per_min": "",
                "last_hits": "",
                "hero_damage": "",
                "tower_damage": ""
            }
            for hero in dire_heroes
        ],
        # Если победила первая команда (Radiant), то winner = False
        # Если победила вторая команда (Dire), то winner = True
        "winner": winner_team,
        "radiant_score": 0,
        "dire_score": 0
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
            print("Ошибка 404: пропускаем следующий запрос")
            return
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
        link_soup = BeautifulSoup(match_response.text, 'html.parser')
        page_title = link_soup.find('title').text if link_soup.find('title') else 'No Title'
        if debug:
            print("Заголовок страницы:", page_title)
        # Извлекаем match_id из URL (последняя часть ссылки)
        match_id = link.split('/')[-1]
        status = match_link_parser(link_soup, debug, match_id)
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
        full_link = ""
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            match_link = cols[2].find('a')
            # Нашли первую страницу - запомнили id последнего матча и вышли из цикла
            if match_link:
                first_id = int(match_link.get('href')[9:])
                full_link = "https://ru.dotabuff.com" + match_link['href'][:9]
                break
        # Генерируем ссылки на матчи
        match_links = [full_link + str(first_id - it) for it in range(num)]
        cnt = 0
        # Идём парсить список ссылок циклом
        for link in match_links:
            cnt += 1
            match_link_reader(link, debug)
            # Следим за процессом работы
            print(f'{cnt} / {num}')
    else:
        print(f"Ошибка: {response.status_code}")


def write_matrix():
    print("Матрица сохранена в файл matrix.txt") 


iterations = 10
# ЗАПУСКАЕМ ПАРСЕР
parser(iterations)
