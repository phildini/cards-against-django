# Class: redis
#
#
class redis {
    package { "redis-server":
        ensure => "latest",
    }
}
