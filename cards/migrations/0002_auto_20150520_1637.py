# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cards', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cardset',
            name='black_card',
            field=models.ManyToManyField(to='cards.BlackCard', db_table='card_set_black_card'),
        ),
        migrations.AlterField(
            model_name='cardset',
            name='white_card',
            field=models.ManyToManyField(to='cards.WhiteCard', db_table='card_set_white_card'),
        ),
        migrations.AlterField(
            model_name='submittedcard',
            name='card_type',
            field=models.CharField(max_length=1, choices=[('1', 'White Card'), ('2', 'Black Card')], default='1'),
        ),
    ]
