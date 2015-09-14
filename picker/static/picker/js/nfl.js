;(function($, undefined) {
    var root = this;
    var score_calls = 0;
    
    //--------------------------------------------------------------------------
    var score_strip_handler = function(scores_data) {
        var $scorestrip = $('.scorestrip').attr('data-load', ++score_calls);
        var html = [];
        var gm, away_class, home_class, bit;
        console.log(scores_data);
        if(scores_data && scores_data.games) {
            for(var i = 0; i < scores_data.games.length; i++) {
                gm = scores_data.games[i];
                away_class = gm.winner == null ? '' : gm.away == gm.winner ? 'sc_win' : 'sc_loss';
                home_class = gm.winner == null ? '' : gm.home == gm.winner ? 'sc_win' : 'sc_loss';
                html.push('<div>');
                html.push('<div class="' + away_class + '">' + gm.away + (gm.pos == gm.home ? ' &bull;' : '') + ' <span>' + gm.away_score + '</span></div>');
                html.push('<div class="' + home_class + '">' + gm.home + (gm.pos == gm.away ? ' &bull;' : '') + ' <span>' + gm.home_score + '</span></div>');
                html.push('<div class="time">');
                
                if(gm.status == 'Pending') {
                    bit = gm.day + ' ' + gm.time;
                }
                else {
                    bit = gm.status + (gm.clock ? ' ' + gm.clock: '');
                }
                
                html.push('<a href="' + gm.url + '" target="_blank">' + bit + '</a></div></div>');
            }
        }
        else {
            html.push('<p>Unable to load score strip</p>')
        }
        $scorestrip.html(html.join('\n'));
        
    };
    
    //--------------------------------------------------------------------------
    var score_strip = function(scores_api_url) {
        var inner_func = function() {
            $.get(scores_api_url, score_strip_handler);
            setTimeout(inner_func, 1000 * 30 * 1);
        };
        inner_func();
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
