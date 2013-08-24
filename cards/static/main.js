window.LongPolling = (function($) {
    var _timeout = null,
        _options = {},
        doLongPoll = function() {
            $.ajax({
                url: '/game/' + _options.gameId + '/api',
                crossDomain: true
            }).done(function(res) {
                    var state = $(".data").data();
                    if (res.game_state != state.game_state) {
                        location.reload(true);
                    }
                    if (res.gamedata.round != state.round) {
                        location.reload(true);
                    }
                }
            );
        };

    return {
        startLongPolling: function(options) {
            _options = $.extend({}, options);
            _timeout = window.setInterval(doLongPoll, 30000);
        },
        stopLongPolling: function() {
            window.clearInterval(_timeout);
        }
    };
}(jQuery));
