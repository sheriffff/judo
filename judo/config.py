import datetime

min_date = datetime.datetime.strptime("2017/01/01", "%Y/%m/%d")

# how to treat the text of each column in the web
columns_map = {
    1: 'wins',
    3: 'opponent',
    5: 'local_points',
    7: 'opponent_points',
    8: 'duration',
    9: 'date',
    10: 'event',
    11: 'category',
    12: 'round',
}

treatment_battle = {
    'wins': lambda win_local: 1 if win_local == 'won' else 0,
    'opponent': lambda name: name.replace('\n', ' '),
    'local_points': lambda points: points.replace(' ', ''),
    'opponent_points': lambda points: points.replace(' ', ''),
    'duration': lambda x: x,
    'date': lambda date: datetime.datetime.strptime(date, '%d %b %Y'),
    'event': lambda comp: comp.replace('\n', ' '),
    'category': lambda x: x,
    'round': lambda x: x
}
competition_families = {
    'World Championships': ['World Championships'],
    'Masters': ['Masters'],
    'Grand Prix': ['Grand Prix'],
    'Grand Slam': ['Grand Slam'],
    'Olympic Games': ['Olympic Games'],
    'Continental Championships': [
        'European Championships',
        'Panamerican Championships',
        'Asian Championships',
        'African Championships',
        'Oceanian Championships'
    ],
    'Continental Open': [
        'World Cup',
        'Continental Cup',
        'European Open',
        'Panamerican Open',
        'Asian Open',
        'African Open',
        'Oceanian Open',
    ]
}
url_leaders_by_weight = {
    'men_60': 'https://judobase.ijf.org/#/wrl/1/simple',
    'men_66': 'https://judobase.ijf.org/#/wrl/2/simple',
    'men_73': 'https://judobase.ijf.org/#/wrl/3/simple',
    'men_81': 'https://judobase.ijf.org/#/wrl/4/simple',
    'men_90': 'https://judobase.ijf.org/#/wrl/5/simple',
    'men_100': 'https://judobase.ijf.org/#/wrl/6/simple',
    'men_100+': 'https://judobase.ijf.org/#/wrl/7/simple',
    'women_48': 'https://judobase.ijf.org/#/wrl/8/simple',
    'women_52': 'https://judobase.ijf.org/#/wrl/9/simple',
    'women_57': 'https://judobase.ijf.org/#/wrl/10/simple',
    'women_63': 'https://judobase.ijf.org/#/wrl/11/simple',
    'women_70': 'https://judobase.ijf.org/#/wrl/12/simple',
    'women_78': 'https://judobase.ijf.org/#/wrl/13/simple',
    'women_78+': 'https://judobase.ijf.org/#/wrl/14/simple'
}
competition_to_family_map = {element: family for family in competition_families.keys() for element in competition_families[family]}


def category_map(category):
    """
    Turns '-52 kg' into 'women_52'
    """
    men_weights = ['60', '66', '73', '81', '90', '100']

    temp = category.split()[0]
    menos = temp[0] == '-'
    peso = temp[1:]

    new_category = ('men_' if peso in men_weights else 'women_') + peso + ('+' if not menos else '')

    return new_category