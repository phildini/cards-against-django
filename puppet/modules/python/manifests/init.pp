class python {
    package { "python-pip":
        ensure => 'latest',
    }

    package { "python-virtualenv":
        ensure => 'latest',
    }

    package { "virtualenvwrapper":
        ensure => 'latest',
        provider => 'pip',
        require => Package['python-pip'],
    }
}