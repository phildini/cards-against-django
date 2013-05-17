cards-against-django
====================

CAH done as a Django web app.

Steps to run:

1. clone the repo

2. in the repo dir:

        virtualenv .  # one time setup
        . bin/activate

3. install dependencies:

        pip install -r requirements/local.txt

    Optional dependencies:
    
        easy_install django-debug-toolbar

4. set secure key:

        export CAH_KEY='[some crypto-ish key of your choosing]'

5. one time database setup:

        python manage.py syncdb --settings=cah.settings.local

6. start test/debug server:

        python manage.py runserver --settings=cah.settings.local 0.0.0.0:8000

7. share and enjoy.

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
