# Generated by Django 3.2.9 on 2022-01-04 22:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tweepyStreamer', '0003_alter_tweet_classpredicted'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tweet',
            name='htmlElement',
        ),
    ]