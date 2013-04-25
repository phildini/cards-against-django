$(document).ready(function(){
    $('.draggable').draggable();
    $('.droppable').droppable({
        drop: function(event, ui) {
            $(this).css("color", "red");
        }
    });
});