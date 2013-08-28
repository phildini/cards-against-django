# Class: nginx
#
#
class nginx {
    apt::ppa { 'ppa:nginx/stable': }

    package { "nginx":
        ensure => 'latest',
        require => Apt::Ppa['ppa:nginx/stable'],
    }

    service { 'nginx':
      ensure => running,
      enable => true,
      require => Package['nginx']
    }

    file { "/etc/nginx/sites-available/default":
        ensure => file,
        source => 'puppet:///modules/nginx/default',
        require => Package['nginx'],
        notify => Service['nginx'],
    }

}