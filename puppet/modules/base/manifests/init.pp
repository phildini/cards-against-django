class base {
  exec { 'apt-get update':
    command => '/usr/bin/apt-get update';
  }

  file {
    '/home/vagrant/.bashrc':
      owner => 'vagrant',
      group => 'vagrant',
      mode  => '0644',
      source => 'puppet:///modules/base/bashrc';
  }

  file {
    '/home/vagrant/.bash_aliases':
      owner => 'vagrant',
      group => 'vagrant',
      mode  => '0644',
      source => 'puppet:///modules/base/bash_aliases';
  }

  file {
    '/home/vagrant/.bash_env':
      owner => 'vagrant',
      group => 'vagrant',
      mode  => '0644',
      source => 'puppet:///modules/base/bash_env';
  }
}
