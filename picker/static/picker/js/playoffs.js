var Playoffs = (function() {
    var counter = (function() {
        var i = 0;
        return {
            next:    function()  { return ++i; },
            reduce:  function(n) { i -= n; }
        };
    })();
    
    var _teams;
    
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
    function sortf(a, b) { return _teams[a].seed - _teams[b].seed; }
    
    //-----------------------------------------------------------------
    function build_week(wk, count, NFC, AFC) {
        var $wk = $('#wk' + wk + ' input:checked');
        if($wk.length == count) {
            var next_week = wk + 1,
                next      = 'wk' + next_week,
                nfc_seeds = [], 
                afc_seeds = [],
                i, j;
            
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
                    $tbody.append(show_game(_teams[nfc_seeds[i]], _teams[nfc_seeds[j]]));
                    $tbody.append(show_game(_teams[afc_seeds[i]], _teams[afc_seeds[j]]));
                };
            }
            else {
                $tbody.append(show_game(_teams[nfc_seeds[0]], _teams[afc_seeds[0]]));
            }
        }
    }

    return {
        
        //--------------------------------------------------------------
        init: function(teams, NFC, AFC, picks) {
            
            var $tbody = $('#wk1 tbody');
            var ie7    = is_ie7();
            
            _teams = teams;
            if(ie7) {
                $('#wk1').before('<p class="error">Please consider upgrading your version of Internet Explorer for a better experience</p>');
            }
            $.each([NFC, AFC], function(index, n) {
                $tbody.append(show_game(_teams[n[2]], _teams[n[5]]));
                $tbody.append(show_game(_teams[n[3]], _teams[n[4]]));
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
                    if(ie7) {
                        if(g == 4)       { build_week(1,4, NFC, AFC); }
                        else if(g == 8)  { build_week(2,4, NFC, AFC); }
                        else if(g == 10) { build_week(3,2, NFC, AFC); }
                    }
                }
                $('#points').val(picks['points']);
            }
        }
    };
})();

