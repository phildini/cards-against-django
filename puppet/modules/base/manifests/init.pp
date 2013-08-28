class base {
  class { 'apt':
    always_apt_update => true,
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
