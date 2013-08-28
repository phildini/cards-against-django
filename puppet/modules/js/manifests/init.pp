# Class: js
#
#
class js {
    # include nodejs

    class { 'nodejs':
      manage_repo => true,
      version => 'latest'
    }

    package { 'socket.io':
        ensure => present,
        provider => "npm",
        require => Package['nodejs']
    }

    file { '/etc/init/socketio.conf':
      owner => 'vagrant',
      group => 'vagrant',
      mode  => '0644',
      source => 'puppet:///modules/js/socketio.dev',
      require => Package['socket.io'],
    }

    file { '/etc/init.d/socketio':
      ensure => link,
      target => '/etc/init/socketio.conf',
      require => File['/etc/init/socketio.conf']
    }

    # Ensure that the service is running.
    service { 'socketio':
      ensure => running,
      provider => 'upstart',
      require => [
        File['/etc/init.d/socketio'],
      ]
    }
}
