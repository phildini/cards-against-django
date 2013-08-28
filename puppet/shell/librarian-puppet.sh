#!/bin/sh

# Librarian-puppet setup script
# Based on https://github.com/purple52/librarian-puppet-vagrant/

# Directory in which librarian-puppet should manage its modules directory
PUPPET_DIR=/vagrant/puppet/librarian_modules
# PUPPET_DIR=/etc/puppet/

# NB: librarian-puppet might need git installed. If it is not already installed
# in your basebox, this will manually install it at this point using apt or yum

$(which git > /dev/null 2>&1)
FOUND_GIT=$?
if [ "$FOUND_GIT" -ne '0' ]; then
  echo 'Attempting to install git.'
  apt-get -qq -y update
  apt-get -qq -y install git
  echo 'git installed.'
else
  echo 'git found.'
fi

if [ ! -d "$PUPPET_DIR" ]; then
  mkdir -p $PUPPET_DIR
fi
cp /vagrant/puppet/Puppetfile $PUPPET_DIR

if [ "$(gem search -i librarian-puppet)" = "false" ]; then
  echo 'installing librarian dependencies...'
  gem install puppet --no-rdoc --no-ri
  gem install librarian-puppet --no-rdoc --no-ri
  cd $PUPPET_DIR && librarian-puppet install --clean
else
  echo 'updating librarian dependencies...'
  cd $PUPPET_DIR && librarian-puppet update
fi
