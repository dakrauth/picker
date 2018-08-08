import os
import json
import pytest
from datetime import datetime, timedelta
from picker import models as picker
from demo.management.commands.loaddemo import load_users, create_grouping

json_data = {}

def read_json(name):
    global json_data
    if name not in json_data:
        filepath = os.path.join(os.path.dirname(__file__), name)
        with open(filepath) as fin:
            json_data[name] = json.load(fin)

    return json_data[name]


@pytest.fixture
def nfl_season_data():
    return read_json('nfl2018.json')


@pytest.fixture
def nfl_data():
    return read_json('nfl.json')


@pytest.fixture
def league(nfl_data):
    return picker.League.import_league(nfl_data)[0]


@pytest.fixture
def grouping(league):
    return create_grouping(league, 'Test group')


@pytest.fixture
def users(grouping):
    return load_users(grouping)


@pytest.fixture
def user(users):
    return users[1]


@pytest.fixture
def superuser(users):
    return users[0]


@pytest.fixture
def gamesets(league, nfl_season_data):
    picker.League.import_season(nfl_season_data)
    return league.season_gamesets()


@pytest.fixture
def quidditch():
    year = 2018
    league = picker.League.import_league({
        "name": "Quidditch",
        "slug": "quidditch",
        "abbr": "QDCH",
        "is_pickable": True,
        "current_season": year,
        "teams": [
            {"abbr": "GRF", "name": "Gryffindor", "nickname": "Lions"},
            {"abbr": "HUF", "name": "Hufflepuff", "nickname": "Badgers"},
            {"abbr": "RVN", "name": "Ravenclaw", "nickname": "Eagles"},
            {"abbr": "SLY", "name": "Slytherin", "nickname": "Serpents"}
        ]
    })[0]

    picker.League.import_season({"league": "QDCH", "season": year, "gamesets": [
        {"games": [
            {"away": "GRF", "home": "HUF", "start": "2018-09-07T04:00Z", "location": "Hogwarts"},
            {"away": "RVN", "home": "SLY", "start": "2018-09-07T08:00Z", "location": "Hogwarts"}
        ]},
        {"games": [
            {"away": "GRF", "home": "RVN", "start": "2018-09-14T04:00Z", "location": "Hogwarts"},
            {"away": "HUF", "home": "SLY", "start": "2018-09-14T08:00Z", "location": "Hogwarts"}
        ]}
    ]})

    grouping = create_grouping(league, 'Quidditch grouping')
    users = load_users(grouping)
    return league, grouping, users



