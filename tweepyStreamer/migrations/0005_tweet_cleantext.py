# Generated by Django 3.2.9 on 2022-01-10 11:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tweepyStreamer', '0004_remove_tweet_htmlelement'),
    ]

    operations = [
        migrations.AddField(
            model_name='tweet',
            name='cleanText',
            field=models.CharField(default='none', max_length=4000),
            preserve_default=False,
        ),
    ]
