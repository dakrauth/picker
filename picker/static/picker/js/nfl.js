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
    function isOldIE() {
        var rv = false; // Return value assumes failure.
        if (navigator.appName == 'Microsoft Internet Explorer') {
            var ua = navigator.userAgent;
            var re  = new RegExp("MSIE ([0-9]{1,}[\.0-9]{0,})");
            if (re.exec(ua) != null) {
                rv = parseFloat( RegExp.$1 );
                return rv < 9.0;
            }
        }
        return false;
    }

    //--------------------------------------------------------------------------
    function joinKeyValuePairs(items) {
        var result = '';
        for(var key in items) {
            if(items.hasOwnProperty(key)) {
                result += ' ' + key + '"' + items[key] + '"';
            }
        }
        return result;
    }

    //--------------------------------------------------------------------------
    function showTeam(game, team, away) {
        var $parent = $('<td></td>'), 
            id      = game + team.abbr,
            $label  = $('<label for="' + id + '"></label>'),
            img     = '<img class="helmut" src="' + team.url + '" />',
            input   = '<input' + joinKeyValuePairs({
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
    function showGame(home, away) {
        var c = 'game_' + counter.next();
        return $('<tr></tr>')
            .append(away ? showTeam(c, away, true) : $('<td></td>'))
            .append(show_team(c, home));
    }

    //------------------------------------------------------------------
    function sortTeam(a, b) { return playoff_teams[a].seed - playoff_teams[b].seed; }

    //--------------------------------------------------------------------------
    var scoreStripHandler = function(scores_data) {
        var $scorestrip = $('.scorestrip').attr('data-load', ++score_calls);
        var html = [];
        var gm, away_class, home_class, bit;
        console.log(scores_data);
        if(scores_data && scores_data.games) {
            scores_data.games.sort(function(a, b) {
                return a.eid > b.eid ? 1 : -1;
            });
            scores_data.games.forEach(function(gm) {
                away_class = gm.winner == null ? '' : gm.away == gm.winner ? 'sc_win' : 'sc_loss';
                home_class = gm.winner == null ? '' : gm.home == gm.winner ? 'sc_win' : 'sc_loss';
                html.push('<div data-eid="' + gm.eid + '">');
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
            });
        }
        else {
            html.push('<p>Unable to load score strip</p>')
        }
        $scorestrip.html(html.join('\n'));

    };

    var numbersOnly = function(e) {
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
    };

    var NFLPlayOffs = function(teams, NFC, AFC, picks) {
        this.teams = teams;
        this.NFC = NFL;
        this.AFC = AFC;
        this.picks = picks;
        $('#points').keydown(numbersOnly);
    };
    NFLPlayOffs.prototype.buildWeek = function(wk, count) {
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
            nfc_seeds = [this.NFC[0], this.NFC[1]];
            afc_seeds = [this.AFC[0], this.AFC[1]];
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
            nfc_seeds.sort(sortTeam);
            afc_seeds.sort(sortTeam);

            for(i = 0, j = nfc_seeds.length - 1; i < j; i++, j--) {
                $tbody
                    .append(showGame(this.teams[nfc_seeds[i]], this.teams[nfc_seeds[j]]))
                    .append(showGame(this.teams[afc_seeds[i]], this.teams[afc_seeds[j]]));
            }
        }
        else {
            $tbody.append(showGame(this.teams[nfc_seeds[0]], this.teams[afc_seeds[0]]));
        }
    };
    NFLPlayOffs.prototype.render = function() {
        var $tbody = $('#wk1 tbody');
        var $doc = $(document);
        $.each([NFC, AFC], function(index, n) {
            $tbody.append(showGame(this.teams[n[2]], this.teams[n[5]]));
            $tbody.append(showGame(this.teams[n[3]], this.teams[n[4]]));
        });

        $doc
            .on('change', '#wk1 input:radio', function() { this.buildWeek(1, 4); })
            .on('change', '#wk2 input:radio', function() { this.buildWeek(2, 4); })
            .on('change', '#wk3 input:radio', function() { this.buildWeek(3, 2); })
            .on('change', '#wk4 input:radio', function() { this.buildWeek(4, null); });

        if(this.picks) {
            var game;
            for(var g = 1; g < 12; g++) {
                game = 'game_' + g;
                $('#' + game + this.picks[game]).click();
            }
            $('#points').val(this.picks['points']);
        }
    };

    return {
        //----------------------------------------------------------------------
        scores: function(scores_api_url) {
            var inner_func = function() {
                $.get(scores_api_url, scoreStripHandler);
                setTimeout(inner_func, 1000 * 60 * 5);
            };
            inner_func();
        },

        //----------------------------------------------------------------------
        playoffs: function(teams, NFC, AFC, picks) {
            var po;
            if(isOldIE()) {
                $('#wk1').before('<p class="error">Your version of Internet Explorer is insufficient, please upgrade to continue</p>');
                return
            }
            po = new NFLPlayOffs(teams, NFC, AFC, picks);
            po.render();
        }
    };
})(jQuery);
