import functools
from dateutil.parser import parse as dt_parse

from django import http
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.template.base import add_to_builtins

from .models import League, Game, RosterStats, Preference
from .forms import UserPickForm, ManagementPickForm, PlayoffBuilderForm
from . import utils
from .decorators import management_user_required


datetime_now = utils.datetime_now
add_to_builtins('picker.templatetags.picker_tags')


#-------------------------------------------------------------------------------
def picker_adapter(view):
    @functools.wraps(view)
    def view_wrapper(request, *args, **kws):
        league = League.get(kws.pop('league'))
        result = view(request, league, *args, **kws)
        if isinstance(result, http.HttpResponse):
            return result
        
        tmpl, ctx = (result, {}) if isinstance(result, basestring) else result
        tmpls = utils.get_templates(league, tmpl)
        data = {'league': league, 'season': league.current_season}
        if ctx:
            data.update(**ctx)
            
        return render(request, tmpls, data)
        
    return view_wrapper


#-------------------------------------------------------------------------------
def _playoff_week(playoff):
    N = 1 + playoff.league.game_set.count()
    weeks = [{'season': playoff.season, 'week': w} for w in range(1, N)]
    return {'season_weeks': weeks, 'week': 'playoffs'}


#-------------------------------------------------------------------------------
def _conference_playoff_context(playoff, user):
    
    teams = {}
    confs = {
        abbr: []
        for abbr in playoff.league.conference_set.values_list('abbr', flat=True)
    }
    for seed, team in playoff.seeds:
        conf = confs[team.conference.abbr]
        conf.append(team.abbr)
        teams[team.abbr] = {
            'url': team.image_url,
            'seed': seed,
            'name': team.name,
            'abbr': team.abbr,
            'record': team.record_as_string,
            'conf': team.conference.abbr
        }

    try:
        picks = playoff.playoffpicks_set.get(user=user)
    except:
        picks = None
    
    data = {key: utils.json_dumps(confs[key]) for key in confs}
    return dict(data,
        teams=utils.json_dumps(teams),
        picks=utils.json_dumps(picks.picks if picks else []),
        week=_playoff_week(playoff)
    )


#===============================================================================
# Public views
#===============================================================================


#-------------------------------------------------------------------------------
@picker_adapter
def home(request, league):
    return '@home.html', {'week': league.current_gameset, 'feed': utils.parse_feed()}


#-------------------------------------------------------------------------------
def api_v1(request, action, league=None):
    league = League.get(league)
    if action == 'scores':
        return utils.JsonResponse(league.scores(not league.current_gameset))
        
    raise http.Http404


#-------------------------------------------------------------------------------
@picker_adapter
def teams(request, league, pk=None):
    if pk:
        team =  get_object_or_404(league.team_set, pk=pk)
        return '@team_info.html', {'team': team}
    
    return '@teams.html'


#-------------------------------------------------------------------------------
@picker_adapter
def schedule(request, league, season=None):
    weeks = get_list_or_404(league.game_set, season=league.current_season)
    return '@schedule/season.html', {'weeks': weeks}


#===============================================================================
# Views requiring login
#===============================================================================


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def roster_profile(request, league, username):
    pref = get_object_or_404(Preference, user__username=username)
    seasons = list(league.available_seasons) + [None]
    stats = [RosterStats(pref, league, s) for s in seasons]
    return '@roster_profile.html', {'profile': pref, 'stats': stats}


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def roster(request, league, season=None):
    season = int(season) if season else league.current_season
    roster = RosterStats.get_details(league, season)
    return '@roster.html', {'season':  season, 'roster':  roster}


#===============================================================================
#  Results
#===============================================================================


#-------------------------------------------------------------------------------
def _week_results(request, week, **extras):
    extras.update(week=week, weekly_results=week.weekly_results())
    return '@results/week.html', extras


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def results(request, league):
    week = league.current_gameset
    if not week:
        return utils.redirect_reverse('picker-playoffs-results', league.current_season)

    if week.has_started:
        week.update_results()
    
    return _week_results(request, week)


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def results_by_season(request, league, season):
    weeks = league.game_set.filter(season=season)
    return '@results/season.html', {'season': season, 'weeks': weeks}


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def results_by_week(request, league, season, week):
    week = get_object_or_404(league.game_set, season=season, week=week)
    return _week_results(request, week)


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def results_for_playoffs(request, league, season):
    playoff = get_object_or_404(league.playoff_set, season=season)
    return '@results/playoffs.html', {'week': _playoff_week(playoff), 'playoff': playoff}


#===============================================================================
#  Picks
#===============================================================================

#-------------------------------------------------------------------------------
def _weekly_picks(request, league, week):
    if week.is_open:
        return utils.basic_form_view(
            request,
            '@picks/make.html',
            UserPickForm,
            context={'user': request.user, 'week': week},
            redirect_path=week.get_absolute_url(),
            form_kws={'user': request.user, 'week': week},
            success_msg='Your picks have been saved'
        )
    
    picks = week.pick_for_user(request.user)
    return '@picks/show.html', {'week': week, 'picks': picks}


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def picks_history(request, league):
    return '@picks/history.html', {'seasons': league.available_seasons}


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def picks_by_season(request, league, season):
    weeks = [
        (week, week.pick_for_user(request.user))
        for week in get_list_or_404(league.game_set, season=season)
    ]
    return '@picks/season.html', {'weeks': weeks}


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def picks(request, league):
    week = league.current_gameset
    if week:
        return _weekly_picks(request, league, week)

    return utils.redirect_reverse('picker-playoffs-picks', league.current_season)


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def picks_by_week(request, league, season, week):
    week = get_object_or_404(league.game_set, season=season, week=week)
    return _weekly_picks(request, league, week)


#-------------------------------------------------------------------------------
@login_required
@picker_adapter
def picks_for_playoffs(request, league, season):
    playoff = get_object_or_404(league.playoff_set, season=season)
    if datetime_now() > playoff.kickoff:
        return utils.redirect_reverse('picker-playoffs-results', season)

    if request.method == 'POST':
        picks, created = playoff.playoffpicks_set.objects.get_or_create(
            user=request.user,
        )
        picks.picks = dict([(k, v) for k,v in request.POST.items()])
        picks.save()
        return utils.redirect_reverse('picker-playoffs-results', season)
    
    data = _conference_playoff_context(playoff, request.user)
    return '@picks/playoffs.html', data


#===============================================================================
# Views requiring management user
#===============================================================================

#-------------------------------------------------------------------------------
@management_user_required
@picker_adapter
def management_home(request, league):
    gs = league.current_gameset or _playoff_week(league.playoff)
    return '@manage/home.html', {'week': gs, 'management': True,}


#-------------------------------------------------------------------------------
@management_user_required
@picker_adapter
def manage_season(request, league, season):
    weeks = get_list_or_404(league.game_set, season=season)
    return '@manage/season.html', {'weeks': weeks, 'management': True}


#-------------------------------------------------------------------------------
@management_user_required
@picker_adapter
def manage_week(request, league, season, week):
    gs = get_object_or_404(league.game_set, season=season, week=week)
    if request.method == 'POST':
        go_to = reverse('picker-game-week', args=(league.lower, gs.season, gs.week))
        if 'kickoff' in request.POST:
            gs.picks_kickoff()
            gs.update_results()
            messages.success(request, 'Week kickoff successful')
            return http.HttpResponseRedirect(go_to)
            
        if 'reminder' in request.POST:
            league.send_reminder_email()
            messages.success(request, 'User email sent')
            return http.HttpResponseRedirect(go_to)
            
        if 'update' in request.POST:
            res = gs.update_results()
            if res is None:
                messages.warning(request, 'No completed games!')
            elif res is False:
                messages.error(request, 'Could not update (service unavailable)')
            else:
                messages.success(request, '%s game(s) update' % res)
            return http.HttpResponseRedirect(go_to)
        
        form = ManagementPickForm(gs, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Results saved')
            return http.HttpResponseRedirect(go_to)
    else:
        gs.update_results()
        messages.success(request, 'Scores automatically updated!')
        form = ManagementPickForm(gs)
        
    
    return '@manage/weekly_results.html', {'form': form, 'week': gs, 'management': True}


#-------------------------------------------------------------------------------
@management_user_required
@picker_adapter
def manage_playoffs(request, league, season, *args, **kws):
    playoff = get_object_or_404(league.playoff_set, season=season)
    if request.method == 'POST':
        picks = playoff.admin
        picks.picks = dict([(k, v) for k,v in request.POST.items()])
        picks.save()
        return utils.redirect_reverse('picker-playoffs-results', season)
    
    return render(
        request, 
        '@picks/playoffs.html', 
        dict(_conference_playoff_context(playoff, None), management=True)
    )

#-------------------------------------------------------------------------------
@management_user_required
@picker_adapter
def manage_game(request, league, pk):
    game = get_object_or_404(Game, pk=pk)
    kickoff =  game.kickoff
    data = {'game': game, 'error': None }
    if request.method == 'POST':
        kickoff = request.POST.get('kickoff')
        try:
            if not kickoff:
                raise Exception('Invalid date')
            
            game.kickoff = kickoff = dt_parse(kickoff)
            game.save()
            
        except Exception:
            data['error'] = 'Invalid date'
    
    data['kickoff'] = kickoff
    return '@manage/game.html', data


#-------------------------------------------------------------------------------
@management_user_required
@picker_adapter
def manage_playoff_builder(request, league):
    return utils.basic_form_view(
        request,
        '@manage/playoff_builder.html',
        PlayoffBuilderForm,
        form_kws={'league': league}
    )
