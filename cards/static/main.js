$(document).ready(function(){
    var numFields = $('.field').length;

    $('.field').hide();

    for (var i=0; i <numFields; i++) {
        var element = '<div ' + 'id=' + i + ' class="box droppable">This is a box</div>'
        $('#submission-area').append(element);
    }

    $('.draggable').draggable({
        revert: 'invalid'
    });
    $('.droppable').droppable({
        drop: function(event, ui) {
            $(this).css("color", "red");
            $(ui.draggable).css("color", "green");
            selector = $("label:contains('" + $(ui.draggable).text() + "') > input")
            // debugger;
            document.getElementById($(selector)[$(this)[0].id].id).checked = true;

        }
    });
});