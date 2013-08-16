var io = require('socket.io').listen(8080);
var redis = require('socket.io/node_modules/redis');

var sub = redis.createClient(process.env.REDIS_PORT, process.env.REDIS_HOST);

sub.subscribe('games');

io.sockets.on('connection', function (socket) {

    socket.on('room', function(room){
        socket.join(room);
    })
    sub.on('message', function(channel, message){
        console.log(message);
        io.sockets.in(message).emit('reload', 'hello');
    });
});