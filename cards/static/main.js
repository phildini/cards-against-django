$(function(){
    var numFields = $('.field').length;

    $('.field li').addClass('choice');

    // for (var i=0; i <numFields; i++) {
    //     var element = '<div ' + 'id=' + i + ' class="box droppable">This is a box</div>'
    //     $('#submission-area').append(element);
    // }

    // $('.draggable').draggable({
    //     revert: 'invalid'
    // });
    // $('.droppable').droppable({
    //     drop: function(event, ui) {
    //         $(this).css("color", "red");
    //         $(ui.draggable).css("color", "green");
    //         var selection_html = $(ui.draggable).html();
    //         var selection_text;
    //         if (selection_html.toLowerCase().indexOf('<strong>') > 1) {
    //             selection_text = $(ui.draggable).find('strong').first().contents().text();
    //         }
    //         else {
    //             selection_text = $(ui.draggable).text();
    //         }
    //         selector = $("label:contains('" + selection_text + "') > input")
    //         // debugger;
    //         document.getElementById($(selector)[$(this)[0].id].id).checked = true;
    //         $(this).droppable('option', 'accept', ui.draggable);

    //     }
    // });

    window.LongPolling = (function($) {
        var _timeout = null,
            _options = {},
            doLongPoll = function() {
                $.ajax({
                    url: '/game/' + _options.gameId + '/checkready',
                    data: {}
                }).done(function(res) {
                    if (res.isReady) {
                        window.location.reload(true);
                    }
                });
            };

        return {
            startLongPolling: function(options) {
                _options = $.extend({}, options);
                _timeout = window.setInterval(doLongPoll, 5000);
            },
            stopLongPolling: function() {
                window.clearInterval(_timeout);
            }
        };
    }(jQuery));
});