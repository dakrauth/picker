;var Picker = (function($, undefined) {
    var score_calls = 0;
    var playoff_teams = null;
    
    //--------------------------------------------------------------------------
    var counter = (function() {
        var i = 0;
        return {
            next:    function()  { return ++i; },
            reduce:  function(n) { i -= n; }
        };
    })();
    
    //--------------------------------------------------------------------------
    function is_ie7() {
        var rv = false; // Return value assumes failure.
        if (navigator.appName == 'Microsoft Internet Explorer') {
            var ua = navigator.userAgent;
            var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
            if (re.exec(ua) != null) {
                rv = parseFloat( RegExp.$1 );
                return rv < 8.0;
            }
        }
        return false;
    }
    
    //--------------------------------------------------------------------------
    function kvps(items) {
        var result = '';
        for(var key in items) {
            if(items.hasOwnProperty(key)) {
                result += ' ' + key + '"' + items[key] + '"';
            }
        }
        return result;
    }
    
    //--------------------------------------------------------------------------
    function show_team(game, team, away) {
        var $parent = $('<td></td>'), 
            id      = game + team.abbr,
            $label  = $('<label for="' + id + '"></label>'),
            img     = '<img class="helmut" src="' + team.url + '" />',
            input   = '<input' + kvps({
                type: "radio",
                value: team.abbr,
                id: id,
                name: game,
                'data-conf': team.conf
            });
            
        if(!away) {
            $label.append(input + img);
            $parent.append($label);
        }
        
        $label.append('#' + team.seed + ' ' + team.name + ' (' + team.record + ')');
        if(away) {
            $label.append(img + input);
            $parent.addClass('away').append($label);
        }
        return $parent;
    }
    
    //------------------------------------------------------------------
    function show_game(home, away) {
        var c = 'game_' + counter.next();
        return $('<tr></tr>')
            .append(away ? show_team(c, away, true) : $('<td></td>'))
            .append(show_team(c, home));
    }
    
    //------------------------------------------------------------------
    function sortf(a, b) { return playoff_teams[a].seed - playoff_teams[b].seed; }
    
    //-----------------------------------------------------------------
    function build_week(wk, count, NFC, AFC) {
        var $wk = $('#wk' + wk + ' input:checked');
        var next_week = wk + 1,
            next      = 'wk' + next_week,
            nfc_seeds = [], 
            afc_seeds = [],
            i, j;
            
        if($wk.length !== count) {
            return;
        }
        
        for(i = next_week; i <= 4; i++) {
            var $temp = $('#wk' + i + ' tbody');
            counter.reduce($temp.find('tr').length);
            $temp.empty();
        }
        
        if(wk == 1) {
            nfc_seeds = [NFC[0], NFC[1]];
            afc_seeds = [AFC[0], AFC[1]];
        }
        
        $wk.each(function() {
            if($(this).attr('data-conf') == 'NFC') {
                nfc_seeds.push($(this).val());
            }
            else {
                afc_seeds.push($(this).val());
            }
        });
        
        $tbody = $('#' + next + ' tbody');
        if(nfc_seeds.length > 1) {
            nfc_seeds.sort(sortf);
            afc_seeds.sort(sortf);
            
            for(i = 0, j = nfc_seeds.length - 1; i < j; i++, j--) {
                $tbody
                    .append(show_game(playoff_teams[nfc_seeds[i]], playoff_teams[nfc_seeds[j]]))
                    .append(show_game(playoff_teams[afc_seeds[i]], playoff_teams[afc_seeds[j]]));
            };
        }
        else {
            $tbody.append(show_game(playoff_teams[nfc_seeds[0]], playoff_teams[afc_seeds[0]]));
        }
    }
    
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
    
    return {
        //----------------------------------------------------------------------
        scores: function(scores_api_url) {
            var inner_func = function() {
                $.get(scores_api_url, score_strip_handler);
                setTimeout(inner_func, 1000 * 30 * 1);
            };
            inner_func();
        },
        
        //----------------------------------------------------------------------
        ie_sucks: function() {
            $('body').find('div:first').prepend($('<div id="yuck">').html([
                'Your browser is too outdated to continue. Please consider switching to',
                '<a href="http://www.google.com/chrome">Chrome<a>,',
                '<a href="http://www.mozilla.org/en-US/firefox/new/">Firefox</a>,',
                '<a href="http://www.apple.com/safari/">Safari</a>, or',
                '<a href="http://windows.microsoft.com/en-US/internet-explorer/downloads/ie/">Internet Explorer 9+</a>'
            ].join(' ')));
        },
        
        //----------------------------------------------------------------------
        playoffs: function(teams, NFC, AFC, picks) {
            var $tbody = $('#wk1 tbody');
            playoff_teams = teams;
            if(is_ie7()) {
                $('#wk1').before('<p class="error">Your version of Internet Explorer is insufficient, please upgrade to continue</p>');
                return
            }

            $.each([NFC, AFC], function(index, n) {
                $tbody.append(show_game(playoff_teams[n[2]], playoff_teams[n[5]]));
                $tbody.append(show_game(playoff_teams[n[3]], playoff_teams[n[4]]));
            });

            $(document).on('change', '#wk1 input:radio', function() { build_week(1, 4, NFC, AFC); });
            $(document).on('change', '#wk2 input:radio', function() { build_week(2, 4, NFC, AFC); });
            $(document).on('change', '#wk3 input:radio', function() { build_week(3, 2, NFC, AFC); });
            $(document).on('change', '#wk4 input:radio', function() { build_week(4, null, NFC, AFC); });

            $('#points').keydown(function(e) {
                // Allow only backspace and delete
                if ( e.keyCode == 46 || e.keyCode == 8 ) {
                    // let it happen, don't do anything
                }
                else {
                    // Ensure that it is a number and stop the keypress
                    if ((e.keyCode < 48 || e.keyCode > 57) && (e.keyCode < 96 || e.keyCode > 105 )) {
                        e.preventDefault(); 
                    }   
                }
            });

            if(picks) {
                var game;
                for(var g = 1; g < 12; g++) {
                    game = 'game_' + g;
                    $('#' + game + picks[game]).click();
                }
                $('#points').val(picks['points']);
            }
        }
    };
})(jQuery)
