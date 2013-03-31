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

4. set secure key:

        export CAH_KEY='[some crypto-ish key of your choosing]'

5. start test/debug server:

        cd src
        python manage.py runserver --settings=cah.settings.local 0.0.0.0:8000

6. share and enjoy.
