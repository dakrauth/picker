from .. import utils
from .base import PickerViewBase


class PlayoffContext:

    @staticmethod
    def week(playoff):
        count = 1 + playoff.league.game_set.count()
        weeks = [{'season': playoff.season, 'week': w} for w in range(1, count)]
        return {'season_weeks': weeks, 'week': 'playoffs'}

    @staticmethod
    def conference(playoff, user, **kws):
        teams = {}
        confs = {
            abbr: []
            for abbr in playoff.league.conference_set.values_list('abbr', flat=True)
        }
        for seed, team in playoff.seeds:
            conf = confs[team.conference.abbr]
            conf.append(team.abbr)
            teams[team.abbr] = {
                'url': team.logo.url if team.logo else '',
                'seed': seed,
                'name': team.name,
                'abbr': team.abbr,
                'record': team.record_as_string,
                'conf': team.conference.abbr
            }

        try:
            picks = playoff.playoffpicks_set.get(user=user)
        except ObjectDoesNotExist:
            picks = None

        return dict(
            {key: json.dumps(confs[key]) for key in confs},
            teams=json.dumps(teams),
            picks=json.dumps(picks.picks if picks else []),
            week=PlayoffContext.week(playoff),
            **kws
        )


class PlayoffPicksMixin:

    def playoff_picks(self, request, playoff):
        season = self.season
        if utils.datetime_now() > playoff.kickoff:
            return self.redirect('picker-playoffs-results', self.league.slug, season)

        if request.method == 'POST':
            picks = playoff.user_picks(request.user)
            picks.picks = {k: v for k, v in request.POST.items()}
            picks.save()
            return self.redirect('picker-playoffs-results', self.league.slug, season)

        self.template_name = '@picks/playoffs.html'
        return self.render_to_response(PlayoffContext.conference(playoff, request.user))


class ResultsForPlayoffs(PlayoffPicksMixin, PickerViewBase):

    def get(self, request, *args, **kwargs):
        return self.playoff_picks(
            request,
            get_object_or_404(self.league.playoff_set, season=self.season)
        )
