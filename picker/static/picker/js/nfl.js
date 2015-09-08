;(function($, undefined) {
    var root = this;
    var score_calls = 0;
    
    //--------------------------------------------------------------------------
    var score_strip = function(scores_api_url) {
        $.get(scores_api_url, function(scores_data) {
            var $scorestrip = $('.scorestrip').attr('data-load', ++score_calls);
            var html = [];
            var game, away_class, home_class, bit;
            console.log(scores_data);
            if(scores_data && scores_data.games) {
                for(var i = 0; i < scores_data.games.length; i++) {
                    game = scores_data.games[i];
                    away_class = game.winner == null ? '' : game.away == game.winner ? 'sc_win' : 'sc_loss';
                    home_class = game.winner == null ? '' : game.home == game.winner ? 'sc_win' : 'sc_loss';
                    html.push('<div>');
                    html.push('<div class="' + away_class + '">' + game.away + (game.pos == game.home ? ' &bull;' : '') + ' <span>' + game.away_score + '</span></div>');
                    html.push('<div class="' + home_class + '">' + game.home + (game.pos == game.away ? ' &bull;' : '') + ' <span>' + game.home_score + '</span></div>');
                    html.push('<div class="time">');
                    
                    if(game.status == 'Pending') {
                        bit = game.day + ' ' + game.time;
                    }
                    else {
                        bit = game.status + (game.clock ? ' ' + game.clock: '');
                    }
                    
                    html.push('<a href="' + game.url + '" target="_blank">' + bit + '</a></div></div>');
                }
            }
            else {
                html.push('<p>Unable to load score strip</p>')
            }
            $scorestrip.html(html.join('\n'));
            
        });
        setTimeout(score_strip, 1000 * 60 * 5 + 10)
    };
    
    var make_row = function(team, score, has_pos, is_winner) {
        return $('<tr>').append(
            $('<th>')
                .addClass(is_winner ? 'bold' : null)
                .html(team + (has_pos ? ' &bull;' : ''))
        ).append($('<td>').text(score))
    };
    
    root.Picks = {
        //----------------------------------------------------------------------
        scores: score_strip,
        
        //----------------------------------------------------------------------
        teams: function() {
            var teams = 'ari atl bal buf car chi cin cle dal den det gb hou ind jac kc mia min ne no nyg nyj oak phi pit sd sf sea stl tb ten was'.split(' ');
            $('#teams-img').click(function(e) {
                var el = document.getElementById('fav-team');
                if(el) {
                    el.className = 'team-' + teams[Math.floor(e.offsetX / 30)];
                }
            });
        },
        
        //----------------------------------------------------------------------
        ie_sucks: function() {
            var text = [
                'Your browser <strong>sucks</strong>. Please consider switching to ',
                '<a href="http://www.google.com/chrome">Chrome<a>, ',
                '<a href="http://www.apple.com/safari/">Safari</a>, ',
                '<a href="http://www.mozilla.org/en-US/firefox/new/">Firefox</a>, ',
                'or <a href="http://windows.microsoft.com/en-US/internet-explorer/downloads/ie/">Internet Explorer 9+ (ew)</a>',
            ];

            $('body').find('div:first').prepend($('<div id="yuck">').html(text.join('')));
        }
    };
}).call(this, jQuery)
