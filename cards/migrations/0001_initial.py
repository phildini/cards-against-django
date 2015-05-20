# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import model_utils.fields
import jsonfield.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BlackCard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=255)),
                ('draw', models.SmallIntegerField(default=0)),
                ('pick', models.SmallIntegerField(default=1)),
                ('watermark', models.CharField(max_length=100, null=True)),
            ],
            options={
                'db_table': 'black_cards',
            },
        ),
        migrations.CreateModel(
            name='CardSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('active', models.BooleanField(default=True)),
                ('name', models.CharField(unique=True, max_length=255)),
                ('base_deck', models.BooleanField(default=True)),
                ('description', models.CharField(max_length=255)),
                ('weight', models.SmallIntegerField(default=0)),
                ('black_card', models.ManyToManyField(to='cards.BlackCard', db_table=b'card_set_black_card')),
            ],
            options={
                'db_table': 'card_set',
            },
        ),
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(unique=True, max_length=140)),
                ('game_state', models.CharField(max_length=140)),
                ('is_active', models.BooleanField(default=True)),
                ('gamedata', jsonfield.fields.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('name', models.CharField(max_length=140)),
                ('player_data', jsonfield.fields.JSONField(blank=True)),
                ('wins', models.IntegerField(blank=True)),
                ('game', models.ForeignKey(to='cards.Game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StandardSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('winner', models.BooleanField(default=False)),
                ('complete_submission', models.TextField(null=True, blank=True)),
                ('blackcard', models.ForeignKey(to='cards.BlackCard', null=True)),
                ('game', models.ForeignKey(to='cards.Game', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SubmittedCard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('card_type', models.CharField(default=b'1', max_length=1, choices=[(b'1', b'White Card'), (b'2', b'Black Card')])),
                ('text', models.CharField(max_length=255)),
                ('submitter', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='WhiteCard',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(max_length=255)),
                ('watermark', models.CharField(max_length=100, null=True)),
            ],
            options={
                'db_table': 'white_cards',
            },
        ),
        migrations.AddField(
            model_name='standardsubmission',
            name='submissions',
            field=models.ManyToManyField(to='cards.WhiteCard', null=True),
        ),
        migrations.AddField(
            model_name='cardset',
            name='white_card',
            field=models.ManyToManyField(to='cards.WhiteCard', db_table=b'card_set_white_card'),
        ),
    ]
