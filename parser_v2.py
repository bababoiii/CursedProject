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

# Информация о матчах

hero_names = dict()
hero_names_indexes = []
matrix = []


# Информация о матчах - update version
matches_data = []


def analyser(info): # ДОПИСАТЬ
    global hero_names, hero_names_indexes, matrix, matches_data
    rad_heroes = info['radiant_heroes']
    dir_heroes = info['dire_heroes']
    heroes = rad_heroes + dir_heroes

    # Добавляем новых героев
    for hero in heroes:
        if hero not in hero_names:
            hero_names[hero] = len(hero_names)
            hero_names_indexes.append(hero)
            for row in matrix:
                row.append(0)
            matrix.append([0] * (len(matrix) + 1))

    # Проставляем победы одной команде над другой в матрице
    '''
    1) Если нужно, свапаем команды победителей и проигравших
    2) Попарно герою из команды победителей и герою из команды проигравших ставим добавляем +1 к победам первого
    '''
    if info['winner'] == dir_heroes:
        (rad_heroes, dir_heroes) = (dir_heroes, rad_heroes)
    for w in rad_heroes:
        for l in dir_heroes:
            matrix[hero_names[w]][hero_names[l]] += 1

    # Формируем словарь с информацией о матче
    match_data = {
        "match_id": info.get("match_id", "Unknown"),
        "radiant_heroes": info['radiant_heroes'],
        "radiant_players_info": [[] for _ in range(5)],
        "dire_heroes": info['dire_heroes'],
        "dire_players_info": [[] for _ in range(5)],
        "winner": True if info['winner'] == info['dire_heroes'] else False
    }
    matches_data.append(match_data)


def match_link_parser(link_soup, debug):
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
    if radiant_result_div and ("Победа" in radiant_result_div.get_text() or "winner" in radiant_result_div.get_text().lower()):
        winner_team = radiant_heroes
    elif dire_result_div and ("Победа" in dire_result_div.get_text() or "winner" in dire_result_div.get_text().lower()):
        winner_team = dire_heroes
    else:
        print("Ошибка: Не удалось определить победителя матча!")
        return {}

    if debug:
        print("Radiant heroes:", radiant_heroes)
        print("Dire heroes:", dire_heroes)
        print("Radiant team name:", radiant_team_name)
        print("Dire team name:", dire_team_name)
        if winner_team == radiant_heroes:
            print("Победитель: Radiant")
        elif winner_team == dire_heroes:
            print("Победитель: Dire")
        else:
            print("Победитель: Неизвестно")

    return {
        "radiant_heroes": radiant_heroes,
        "dire_heroes": dire_heroes,
        "radiant_team_name": radiant_team_name,
        "dire_team_name": dire_team_name,
        "winner": winner_team,
    }


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
        match_info = match_link_parser(link_soup, debug)
        match_info['match_id'] = match_id
        # Если ошибка, то не добавляем информацию про матч и идё дальше
        if not match_info:
            return

        # Строим матрицу, сохраняем героев в analyser
        analyser(match_info)
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


def matrix_normalizer():
    global matrix, hero_names, hero_names_rev
    n = len(matrix)
    for i in range(n):
        if matrix[i][i]:
            print(f"Ошибка! На диагонали матрицы персонажа {hero_names_rev[i]} не 0")
        for j in range(i + 1, n):
            div = matrix[j][i] + matrix[i][j]
            if div:
                matrix[i][j] /= div
                matrix[j][i] /= div


def write_matrix():
    with open('matrix.txt', 'w') as f:
        f.write(repr(matrix))
        f.write("\n")
        f.write(repr(hero_names))
        f.write("\n")
        f.write(repr(hero_names_indexes))
    print("Матрица сохранена в файл matrix.txt") 

iterations = 10
# ЗАПУСКАЕМ ПАРСЕР
parser(iterations)

matrix_normalizer()

# Сохраняем матрицу в файл
write_matrix()
