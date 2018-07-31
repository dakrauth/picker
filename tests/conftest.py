import os
import pytest
from picker import models as picker
from demo.management.commands.loaddemo import load_users


def filepath_here(name):
    return os.path.join(os.path.dirname(__file__), name)


@pytest.fixture
def nfl_season_json_path():
    return filepath_here('nfl2018.json')


@pytest.fixture
def nfl_json_path():
    return filepath_here('nfl.json')


@pytest.fixture
def league(nfl_json_path):
    return picker.League.import_league(nfl_json_path)[0]


@pytest.fixture
def users(league):
    return load_users(league)[0]


@pytest.fixture
def gamesets(league, nfl_season_json_path):
    league.import_season(nfl_season_json_path)
    return league.season_weeks()
