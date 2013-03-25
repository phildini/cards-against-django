cards-against-django
====================

CAH done as a Django web app.

Steps to run:

1. clone the repo

2. in the repo dir, 'virtualenv .'

3. 'pip install -r requirements/local.txt'

4. export CAH_KEY=[some crypto-ish key of your choosing]

5. cd src && python manage.py runserver --settings=cah.settings.local

6. share and enjoy.