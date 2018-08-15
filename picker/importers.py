from datetime import timedelta

from dateutil.parser import parse as parse_dt
from .exceptions import PickerConfigurationError


def valid_schema(data, expected_schema):
    schema = data.get('schema')
    if not schema:
        raise PickerConfigurationError('Missing schema type for {}'.format(expected_schema))

    if schema == 'complete':
        data = data[expected_schema]

    if data.get('schema') != expected_schema:
        raise PickerConfigurationError('Missing schema type for {}'.forma(expected_schema))

    return data



def import_season(cls, data):
    data = valid_schema(data, 'season')
    gs = None
    league = cls.objects.get(abbr=data['league'])
    season = data['season']
    teams = league.team_dict()
    gamesets = []
    for sequence, item in enumerate(data['gamesets'], 1):
        opens = item.get('opens')
        if opens:
            opens = parse_dt(opens)
        else:
            dt = parse_dt(item['games'][0]['start'])
            opens = dt - timedelta(days=dt.weekday() - 1)
            opens = opens.replace(hour=12, minute=0)

        closes = item.get('closes')
        if closes:
            closes = parse_dt(closes)
        else:
            closes = opens + timedelta(
                **league.config('GAMESET_DURATION', {'days': 7, 'seconds': -1})
            )

        gs, is_new = league.gamesets.get_or_create(
            season=season,
            sequence=sequence,
            defaults={'opens': opens, 'closes': closes}
        )
        gamesets.append([gs, is_new])
        if not is_new:
            if gs.opens != opens or gs.closes != closes:
                gs.opens = opens
                gs.closes = closes
                gs.save()

        games = gs.import_games(item, teams)
        gamesets[-1].append(games)

    return gamesets


def import_league(cls, data):
    data = valid_schema(data, 'league')
    name = data['name']
    default_abbr = ''.join(c[0] for c in name.upper().split())
    abbr = data.get('abbr', default_abbr).upper()
    league, created = cls.objects.get_or_create(
        name=name,
        abbr=abbr,
        slug=abbr.lower(),
        defaults={
            'is_pickable': data.get('is_pickable', False),
            'current_season': data.get('current_season')
        },
    )
    confs = {}
    divs = {}
    teams = {}
    for tm in data['teams']:
        if 'sub' in tm:
            conf, div = tm['sub']
            if conf not in confs:
                confs[conf] = league.conferences.get_or_create(
                    name=conf,
                    league=league,
                    abbr=conf.lower()
                )[0]

            if (div, conf) not in divs:
                divs[(div, conf)] = confs[conf].divisions.get_or_create(name=name)[0]
        else:
            conf = div = None

        teams[tm['abbr']] = league.teams.get_or_create(
            name=tm['name'],
            abbr=tm['abbr'],
            nickname=tm['nickname'],
            conference=confs.get(conf),
            division=divs.get((div, conf)),
            logo=tm.get('logo', '')
        )[0]

    for name, key in data.get('aliases', {}).items():
        teams[key].aliases.get_or_create(name=name)

    return league, teams

