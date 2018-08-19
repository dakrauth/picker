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
def nfl_data():
    return read_json('nfl2018.json')


@pytest.fixture
def league(nfl_data):
    league_info, teams_info = picker.League.import_league(nfl_data)
    return league_info[0]


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
def gamesets(league, nfl_data):
    picker.League.import_season(nfl_data)
    return league.season_gamesets()


@pytest.fixture
def quidditch():
    data = read_json('quidditch.json')
    league_info, teams_info = picker.League.import_league(data)
    league = league_info[0]
    picker.League.import_season(data)
    grouping = create_grouping(league, 'Quidditch grouping')
    users = load_users(grouping)
    return league, grouping, users



