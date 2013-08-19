# Class: nginx
#
#
class nginx {
    package { "nginx":
        ensure => 'latest',
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