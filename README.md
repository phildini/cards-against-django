cards-against-django
====================

[![Build Status](https://travis-ci.org/phildini/cards-against-django.png?branch=master)](https://travis-ci.org/phildini/cards-against-django)
CAH done as a Django web app.


Vagrant
=======

Install [VirtualBox](https://www.virtualbox.org/)

$ gem install vagrant

$ vagrant up

$ vagrant ssh

The first time you log in, the database must be initialized:
$ syncdb

Start the app, from the Vagrant shell:
$ rs

Share and enjoy!

Sample manage shell snippets:

    # drop model tables (but not Django users/permissions)
    python manage.py sqlclear --settings=cah.settings.local cards | python manage.py dbshell --settings=cah.settings.local 
    # then syncdb


    $ python manage.py shell --settings=cah.settings.local
    
        import cards
        cards.models.BlackCard.objects.get(id=1)
        cards.models.WhiteCard.objects.all()
        b = cards.models.BlackCard.objects.get(id=93)
        b.replace_blanks((11, 94, 95))
        b.replace_blanks((11, 94))
        g = cards.models.Game.objects.get(id=1)

Dump any cards/cardset that have been created:

    python manage.py dumpdata --settings=cah.settings.local --indent=4 cards > cards/fixtures/initial_data.json
