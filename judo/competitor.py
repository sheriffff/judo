import pandas as pd
import time
import datetime
import traceback

from config import columns_map, treatment_battle, competition_to_family_map, category_map, min_date
from db import conn
from driver import driver


# TODO: update actions a la vez que update battles


class Competitor:
    def __init__(self, profile_id):
        self.id = profile_id
        comp = conn.as_pandas(f"select * from competitors where profile_id='{profile_id}'", parse_dates="last_extraction").iloc[0]
        self.name = comp["name"]
        self.last_extraction = comp["last_extraction"]

    def update_battles(self):
        """
        1. Extracts new battles since competitor's last extraction
        2. Appends new battles to battles table
        3. Updates last_extraction value for this competitor
        """
        # print(f"Looking for new battles from {self.name}")
        # extract new battles
        new_battles = self.scrape_battles(from_date=self.last_extraction)

        if new_battles is not None:
            # print("There are new battles!")
            # append new_battles to battles table
            conn.append_table('battles', new_battles)
            # update last_extraction in competitors table
            last_extraction_str = str(new_battles.date.max())
            conn.query(
                f'''
                UPDATE competitors 
                SET last_extraction="{last_extraction_str}" 
                WHERE profile_id="{self.id}";
                '''
            )

    def scrape_battles(self, from_date, time_sleep=0.1):
        """
        Extracts all contests information of a profile, including video url.
        Args:
            from_date (datetime.datetime): extract contests only after this date
            time_sleep (float): time to wait after clicking play to video url
        """
        # start crawling
        profile_web = 'https://judobase.ijf.org/#/competitor/profile/' + self.id
        numero_petes = 0
        driver.get(profile_web)
        time.sleep(1)

        # extract Contests info
        driver.find_element_by_xpath('//a[@data-view="contests"]').click()
        time.sleep(1)

        battles = list()

        # scrape several pages
        curr_page = 0
        n_videos_per_page = dict()
        while True:
            curr_page += 1
            b, done, n_videos = self.scrape_page_battles(from_date)
            battles.extend(b)
            n_videos_per_page[curr_page] = n_videos
            if done:
                break
            else:
                next_page_button = driver.find_element_by_class_name("dataTables_paginate.paging_bootstrap").find_elements_by_tag_name(
                    "a")[curr_page + 1]
                if next_page_button.text == "Next →":
                    break
                else:
                    next_page_button.click()

        if len(battles) == 0:
            print('Up to date!')
            return None

        battles = pd.DataFrame(battles)

        # extraer video urls
        # print('Extracting video URLs...')
        contests_url = driver.current_url
        play_buttons = driver.find_elements_by_xpath("//div[contains(@class, 'btn') and contains(@class, 'btn-sm') "
                                                     "and contains(@class, 'btn-default')]")
        urls = list()

        for page_number, n_videos in n_videos_per_page.items():
            print(f"page number: {page_number}")
            driver.get(contests_url)
            driver.find_element_by_class_name("dataTables_paginate.paging_bootstrap").find_elements_by_tag_name(
                "a")[page_number].click()

            for play_index in range(n_videos):
                while True:
                    try:
                        # hay que hacerlo asi porque el loop pierde el norte al clickear
                        driver.get(contests_url)
                        driver.find_element_by_class_name(
                            "dataTables_paginate.paging_bootstrap").find_elements_by_tag_name(
                            "a")[page_number].click()
                        time.sleep(time_sleep)
                        play = driver.find_elements_by_xpath("//div[contains(@class, 'btn') and contains(@class, 'btn-sm') "
                                                             "and contains(@class, 'btn-default')]")[play_index]
                        play.click()
                        time.sleep(time_sleep)
                        urls.append(driver.current_url)
                        # solo llega aquí si no peta. si peta, repite
                        break
                    except:
                        numero_petes += 1
                        pass

        battles.loc[battles.has_video, 'url_video'] = urls

        battles['local'] = self.name
        battles['competition_family'] = battles.event.apply(
            lambda event: next((competition_to_family_map[c] for c in competition_to_family_map.keys() if c in event),
                               'Other'))

        battles.category = battles.category.apply(category_map)

        column_order = ['wins', 'local', 'opponent', 'event', 'date', 'round',
                        'local_points', 'opponent_points', 'duration', 'category',
                        'has_video', 'competition_family', 'url_video']
        battles = battles[column_order]

        return battles

    @staticmethod
    def scrape_page_battles(from_date):
        n_videos = 0
        # do we get to last battle?
        done = False
        tabla = driver.find_element_by_tag_name('tbody')
        assert tabla.get_attribute('role') == 'alert', 'No encontró la tabla apropiada en Contests'

        battles = list()
        filas = tabla.find_elements_by_tag_name('tr')

        for rowindex, row in enumerate(filas):
            battle = {}
            for colindex, value in enumerate(row.find_elements_by_tag_name('td')):
                if colindex in columns_map.keys():
                    # print(colindex, value.text)
                    colname = columns_map[colindex]
                    battle[colname] = treatment_battle[colname](value.text)
                elif colindex == 13:
                    # tiene o no video
                    has_video = len(value.find_elements_by_tag_name('div')) > 0
                    battle['has_video'] = has_video

            if (battle['date'] <= from_date) or (battle["date"] < min_date):
                done = True
                break
            else:
                battles.append(battle)
                n_videos += has_video

        return battles, done, n_videos

    def get_battles(self):
        return conn.as_pandas(
            f'select * from battles where local=="{self.name}"',
            parse_dates=['date'],
            index_col='index'
        ).reset_index(drop=True).sort_values('date', ascending=False)

    def update_actions(self):
        self.update_battles()
        b = self.get_battles()

        all_actions = []

        for battle in b.itertuples():
            if battle.url_video is None:
                continue
            else:
                try:
                    actions_battle = self.get_info_video_judobase(battle.local, battle.url_video)
                    actions_battle = (a + (battle.event,) for a in actions_battle)
                    all_actions.extend(actions_battle)
                except:
                    pass

        df = pd.DataFrame(
            all_actions,
            columns=('opponent', 'you', 'action', 'action_detail', 'time', 'url_youtube', 'event')
        )

        df['local'] = self.name
        cols_order = [df.columns[-1]] + list(df.columns[:-1])
        df = df[cols_order]

        conn.add_table('actions', df, if_exists='append', index=False)

        #    print('error con ', nombre)

    def get_actions(self):
        return conn.as_pandas(f'select * from actions where local="{self.name}"')

    @staticmethod
    def get_info_video_judobase(competitor_name, url_video):
        """
        Extracts local, opponent, and YOUTUBE url of embedded video in judobase

        Args:
            competitor_name (str): name of competitor
            url_video (str): url to video in judobase.
                example: 'https://judobase.ijf.org/#/competition/contest/gs_jpn2017_m_p100_0004'
        """
        driver.get(url_video)

        try:
            time.sleep(1)
            # extract names
            local, opponent = map(lambda x: x.text, driver.find_elements_by_class_name('col-xs-6'))
            local, opponent = map(lambda x: x[:x.find('\n')], [local, opponent])

            is_local = (local == competitor_name)

            # extract battle info
            # tabla con puntuaciones etiquetadas en tiempo
            tablas = driver.find_elements_by_tag_name('tbody')
            tabla_timed_points = tablas[1]
            filas = tabla_timed_points.find_elements_by_tag_name('tr')

            if len(filas) == 0:
                return []

            ncols = len(filas[0].find_elements_by_tag_name('td'))
            actions = []

            if ncols == 3:
                    for row_number, row in enumerate(filas):
                        cols = row.find_elements_by_tag_name('td')
                        if cols[0].text:
                            you = 0 + is_local
                            what, what2 = cols[0].text.split('\n')[:2] + (
                                [' '] if len(cols[0].text.split('\n')) == 1 else [])
                        else:
                            you = 1 - is_local
                            what, what2 = cols[2].text.split('\n')[:2] + (
                                [' '] if len(cols[2].text.split('\n')) == 1 else [])

                        time_action = cols[1].text
                        minutes, seconds = time_action.split(':')
                        # url = url_youtube + '&t=' + str(60*int(minutes) + int(seconds))
                        # will be returned instead of url_video if better

                        if 'HSK' in what2:
                            what, what2 = what2, what

                        actions.append((opponent if is_local else local, you, what, what2, time_action, url_video))
                    '''    
                    else:
                        for row_number, row in enumerate(filas):
                            for col_number, value in enumerate(row.find_elements_by_tag_name('td')):
                                print(row_number, col_number, value.text)
                    '''

            return actions

        except Exception:
            return []

    def delete_info(self):
        conn.query(f"DELETE FROM battles WHERE local='{self.name}';")
        conn.query(f"DELETE FROM actions WHERE local='{self.name}';")
        conn.query(f"UPDATE competitors SET last_extraction = '2014-04-16 00:00:00' WHERE profile_id='{self.id}';")
