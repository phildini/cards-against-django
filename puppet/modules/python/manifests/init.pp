class python {
    $root_dir = "/home/vagrant"
    $venv_dir = "${ root_dir }/venv"
    $src_dir = "${ root_dir }/src"

    package { "python-pip":
        ensure => "latest",
    }

    package { "python-virtualenv":
        ensure => "latest",
    }

    package { "virtualenvwrapper":
        ensure => "latest",
        provider => "pip",
        require => Package["python-pip"],
    }

    exec { "virtualenv":
        command => "mkdir -p ${ venv_dir } && virtualenv ${ venv_dir }",
        path => [ "/bin", "/usr/bin", "/usr/sbin", "/usr/local/bin" ],
        cwd => "/tmp",
        creates => "${ venv_dir }/bin/activate",
        user => "vagrant",
        require => Package['python-virtualenv'],
    }

    $base_requirements = "${ src_dir }/requirements/_base.txt"
    $requirements = "${ src_dir }/requirements/local.txt"

    file { $base_requirements:
        ensure => present,
        audit => content,
        replace => false,
    }

    file { $requirements:
        ensure => present,
        audit => content,
        replace => false,
    }

    exec { "install-requirements":
        provider => "shell",
        command => "${ venv_dir }/bin/pip install -r $requirements",
        timeout => 1800,
        user => "vagrant",
        subscribe => [
            File[$base_requirements],
            File[$requirements],
        ],
        require => [
            Exec['virtualenv'],
            Package['postgresql-server-dev-9.1'],
        ]
    }
}