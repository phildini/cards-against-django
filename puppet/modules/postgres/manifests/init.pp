# Class: postgres
#
#
class postgres {
    package { "python-dev":
        ensure => latest,
    }
    package { "postgresql-server-dev-9.1":
        ensure => latest,
        require => Package['python-dev'],
    }

    class { 'postgresql':
    }

    class { 'postgresql::server':
      locale  => 'en_US.UTF-8',
      acl => ['local all cah md5'],
    }

    postgresql::db { 'cah':
      password => 'cah',
      encoding => 'UTF8',
    }
}
