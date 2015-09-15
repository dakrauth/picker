import re
import json
import urllib
from time import time
from xml.etree import cElementTree
from pprint import pprint

try:
    from django.core.cache import cache
except ImportError:
    class Cache(object):
        def get(*args, **kws): return None
        def set(*args, **kws): pass
            
    cache = Cache()

TEAM_ABBRS = dict(
    ARZ = 'ARI', ATL = 'ATL', BLT = 'BAL', BUF = 'BUF', CAR = 'CAR', CHI = 'CHI',
    CIN = 'CIN', CLV = 'CLE', DAL = 'DAL', DEN = 'DEN', DET = 'DET', GB  = 'GB',
    HST = 'HOU', IND = 'IND', JAX = 'JAC', KC  = 'KC',  MIA = 'MIA', MIN = 'MIN',
    NE  = 'NE',  NO  = 'NO',  NYG = 'NYG', NYJ = 'NYJ', OAK = 'OAK', PHI = 'PHI',
    PIT = 'PIT', SD  = 'SD',  SF  = 'SF',  SEA = 'SEA', SL  = 'STL', TB  = 'TB',
    TEN = 'TEN', WAS = 'WAS'
)

TEAM_NICKNAMES = {
    'TB':  'buccaneers', 'BAL': 'ravens',  'DEN': 'broncos', 'NE':  'patriots',
    'SEA': 'seahawks',   'BUF': 'bills',   'CHI': 'bears',   'CLE': 'browns',
    'CAR': 'panthers',   'IND': 'colts',   'NYJ': 'jets',    'CIN': 'bengals',
    'ARI': 'cardinals',  'OAK': 'raiders', 'JAC': 'jaguars', 'NO':  'saints',
    'WAS': 'redskins',   'KC':  'chiefs',  'SF':  '49ers',   'TEN': 'titans',
    'MIA': 'dolphins',   'MIN': 'vikings', 'DET': 'lions',   'STL': 'rams',
    'PIT': 'steelers',   'ATL': 'falcons', 'NYG': 'giants',  'DAL': 'cowboys',
    'GB':  'packers',    'PHI': 'eagles',  'HOU': 'texans',  'SD':  'chargers',
}

#-------------------------------------------------------------------------------
def fetch(url):
    return urllib.urlopen(url).read()

try:
    from django.conf import settings
    fake = getattr(settings, 'FAKE_NFL_SCORES', None)
    if fake:
        def fetch(url): return open(fake).read()
except:
    pass


#===============================================================================
class ScoreStrip(object):
    # <?xml version="1.0" encoding="UTF-8"?>
    # <ss>
    #   <gms w="1" y="2013" t="R" gd="1" bph="119">
    #     <g eid="2013090500" gsis="55837" d="Thu" t="8:30" q="F" h="DEN" hnn="broncos" hs="49" v="BAL" vnn="ravens" vs="27" rz="0" ga="" gt="REG"/>
    #     <g eid="2013090800" gsis="55838" d="Sun" t="1:00" q="F" h="BUF" hnn="bills" hs="21" v="NE" vnn="patriots" vs="23" rz="0" ga="" gt="REG"/>
    #   </gms>

    POSTSEASON = 'http://www.nfl.com/liveupdate/scorestrip/postseason/ss.xml'
    URL        = 'http://www.nfl.com/liveupdate/scorestrip/ss.xml'
    TYPE_CODE  = {
        'R': 'Regular Season',
        'P': 'Preseason',
        'POST': 'Post Season',
        'PRO': 'Post Season'
    }
    URL_CODE = {
        'R': 'REG',
        'P': 'PRE',
        'POST': 'POST',
        'PRO': 'PRO'
    }

    STATUS_CODES = {
        'F'  : 'Final',
        'FO' : 'F/OT',
        'P'  : 'Pending',
        'H'  : 'Half', 
        '1'  : '1Q',
        '2'  : '2Q',
        '3'  : '3Q',
        '4'  : '4Q',
    }
    
    #---------------------------------------------------------------------------
    def __init__(self, url=None):
        self.url = url or self.URL
        
    #---------------------------------------------------------------------------
    def get_url(self):
        return '{}?random={}'.format(self.url, time())
        
    #---------------------------------------------------------------------------
    def read_data(self):
        tree = cElementTree.fromstring(fetch(self.get_url()))
        games = []
        attrs = tree.find('gms').attrib
        abbr  = self.URL_CODE[attrs['t']]
        week = dict(
            games=games,
            week=int(attrs['w']),
            season=int(attrs['y']),
            type=self.TYPE_CODE.get(attrs['t'])
        )
        
        for e in tree.findall('gms/g'):
            attrs = e.attrib
            if 'TBD' == attrs['h'] or 'TBD' == attrs['v']:
                continue
                
            q = attrs['q']
            home_score = int(attrs['hs'])
            away_score = int(attrs['vs'])
            winner = None
            if q.startswith('F'):
                winner = (
                    attrs['h'] if home_score > away_score 
                    else (None if home_score == away_score else attrs['v'])
                )
            
            # <g eid="2013090500" gsis="55837" d="Thu" t="8:30" q="F" h="DEN" hnn="broncos" hs="49" v="BAL" vnn="ravens" vs="27" rz="0" ga="" gt="REG"/>
            # http://www.nfl.com/gamecenter/2013090804/2013/REG1/vikings@lions
            game = dict(
                home=attrs['h'],
                away=attrs['v'],
                eid=attrs['eid'],
                home_score=home_score,
                away_score=away_score,
                status=self.STATUS_CODES.get(q, q),
                winner=winner,
                day=attrs['d'],
                time=attrs['t'],
                clock=attrs.get('k', None),
                pos=attrs.get('p', None),
                url='http://www.nfl.com/gamecenter/%s/%s/%s%s/%s@%s' % (
                    attrs['eid'],
                    week['season'],
                    abbr,
                    week['week'],
                    attrs['vnn'],
                    attrs['hnn']
                )
            )

            games.append(game)
            
        return week


#-------------------------------------------------------------------------------
def scores(playoffs=False, cache_ttl=120, no_cache=False, completed=False):
    if no_cache:
        data = None
    else:
        data = cache.get('nfl_score_strip')
        
    if not data:
        try:
            data = ScoreStrip(ScoreStrip.POSTSEASON if playoffs else None).read_data()
        except Exception, why:
            data = None

        if data:
            cache.set('nfl_score_strip', data, cache_ttl)

    if data and completed:
        data = [
            g for g in data['games']
            if g['status'].startswith(('Final', 'F/OT'))
        ]
        
    return data


################################################################################
if __name__ == '__main__':
    import sys
    pprint(scores(len(sys.argv) > 1, no_cache=True))




