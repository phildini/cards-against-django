# Class: postgres
#
#
class postgres {
    package { "postgresql":
        ensure => installed,
    }
    package { "postgresql-contrib":
        ensure => installed,
        require => Package['postgresql'],
    }
}
