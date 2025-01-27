import time
import random as rnd
import requests
from bs4 import BeautifulSoup

# Адрес страницы со списком матчей
url = 'https://ru.dotabuff.com/esports/matches'

# Заголовки, чтобы имитировать браузерный запрос
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


save_id = "" # сохранить id последнего матча, чтобы генерировать ссылки начиная с него

response = requests.get(url, headers=headers)

hero_names = dict()
hero_names_rev = []
matrix = []
def analyze(info):
    global hero_names, hero_names_rev, matrix
    rad_heroes = info['radiant_heroes']
    dir_heroes = info['dire_heroes']
    heroes = info['radiant_heroes'] + info['dire_heroes']
    for hero in heroes:
        hero_names[hero] = hero_names.get(hero, len(hero_names))
        if len(hero_names) > len(matrix):
            hero_names_rev += [hero]
            for i in range(len(matrix)):
                matrix[i] += [0]
            matrix += [[0] * (1 + len(matrix))]

    #проставить всем выигравшим победу у всех проигравших
    if info['winner'] == dir_heroes:
        (rad_heroes, dir_heroes) = (dir_heroes, rad_heroes)
    for w in rad_heroes:
        for l in dir_heroes:
            matrix[hero_names[w]][hero_names[l]] += 1

def link_info(link_soup, wr=1):
    """
        1) Находит и выводит героев Radiant (A) и Dire (B).
        2) Определяет названия команд (если есть) или выводит "Силы Света"/"Силы Тьмы".
        3) Определяет, кто победил.
    """

    radiant_selector = (
        "section.radiant > article > table > tbody tr.col-hints.faction-radiant "
        "td.cell-fill-image > div > div > div > a > img"
    )
    radiant_imgs = link_soup.select(radiant_selector)

    radiant_heroes = []
    for img in radiant_imgs:
        hero_name = img.get("alt")
        radiant_heroes.append(hero_name)

    dire_selector = (
        "section.dire > article > table > tbody tr.col-hints.faction-dire "
        "td.cell-fill-image > div > div > div > a > img"
    )
    dire_imgs = link_soup.select(dire_selector)

    dire_heroes = []
    for img in dire_imgs:
        hero_name = img.get("alt")
        dire_heroes.append(hero_name)

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

    radiant_result_div = link_soup.select_one(".match-result.team.radiant")
    dire_result_div = link_soup.select_one(".match-result.team.dire")

    winner_team = None

    if radiant_result_div and (
            "Победа" in radiant_result_div.get_text() or "winner" in radiant_result_div.get_text().lower()):
        winner_team = radiant_team_name
    elif dire_result_div and ("Победа" in dire_result_div.get_text() or "winner" in dire_result_div.get_text().lower()):
        winner_team = dire_team_name
    else:
        winner_team = "Неизвестно"

    if wr:
        print("Radiant heroes:", radiant_heroes)
        print("Dire heroes:", dire_heroes)
        print("Radiant team name:", radiant_team_name)
        print("Dire team name:", dire_team_name)
        print("Победитель:", winner_team)

    return {
        "radiant_heroes": radiant_heroes,
        "dire_heroes": dire_heroes,
        "radiant_team_name": radiant_team_name,
        "dire_team_name": dire_team_name,
        "winner": winner_team,
    }

def parse_link(link, wr=1):
    print(f"Переходим по ссылке: {link}")
    try:
        # Запрос с тайм-аутом
        time.sleep(rnd.uniform(1, 2))  # Пауза между запросами
        match_response = requests.get(link, headers=headers, timeout=10)
        match_response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if match_response.status_code == 429:
            print(f"Ошибка 429: слишком много запросов. Ожидание 60 секунд...")
            time.sleep(30)  # Ждём 30 секунд перед повторным запросом
            return parse_link(link, wr)  # Пробуем снова после ожидания
        elif match_response.status_code == 404:
            print(f"Ошибка 404: пропускаем следующий запрос")
            return
        else:
            print(f"Ошибка при выполнении запроса {link}: {e}")
            return  # Пропускаем обработку этой ссылки
    except requests.exceptions.Timeout:
        print(f"Ошибка таймаута при запросе {link}")
        return  # Пропускаем обработку этой ссылки
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при выполнении запроса {link}: {e}")
        return  # Пропускаем обработку этой ссылки

    if match_response.status_code == 200:
        link_soup = BeautifulSoup(match_response.text, 'html.parser')
        page_title = link_soup.find('title').text
        if wr:
            print("Заголовок страницы:", page_title)
        match_info = link_info(link_soup, 0)
        analyze(match_info)
    else:
        print(f"Ошибка при загрузке {link}: статус {match_response.status_code}")

def test_parse_site():
    global save_id, response
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')

        table = soup.find('table', class_='recent-esports-matches')
        rows = table.tbody.find_all('tr')

        match_links = []

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue

            match_link = cols[2].find('a')
            if match_link:
                if save_id == "":
                    save_id = match_link.get('href')[9:]
                full_link = "https://ru.dotabuff.com" + match_link['href']
                match_links.append(full_link)
        for link in match_links:
            parse_link(link)
    else:
        print(f"Ошибка: {response.status_code}")

def parse_site(wr=1, n=10):
    global save_id, response
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
            if match_link:
                save_id = int(match_link.get('href')[9:])
                full_link = "https://ru.dotabuff.com" + match_link['href'][:9]
                break
        match_links = [full_link + str(save_id - i) for i in range(n)]
        cnt = 0
        for link in match_links:
            cnt += 1
            parse_link(link, 0)
            if wr:
                print(f'{cnt} / {len(match_links)}')

    else:
        print(f"Ошибка: {response.status_code}")

parse_site(n=100)

def build_matrix():
    global matrix, hero_names, hero_names_rev
    n = len(matrix)
    for i in range(n):
        if matrix[i][i]:
            print("WHAT THE FUC", hero_names_rev[i])
        for j in range(i + 1, n):
            div = matrix[j][i] + matrix[i][j]
            if div:
                matrix[i][j] /= div
                matrix[j][i] /= div

build_matrix()

# Сохраняем матрицу в файл
with open('matrix.txt', 'w') as f:
    f.write(repr(matrix))
    f.write("\n")
    f.write(repr(hero_names))
    f.write("\n")
    f.write(repr(hero_names_rev))

print("Матрица сохранена в файл matrix.txt.")
