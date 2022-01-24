from django.db import models

class Tweet(models.Model):
    tweetId = models.CharField(max_length=100, primary_key=True)
    userId = models.CharField(max_length=100)
    text = models.CharField(max_length=4000)
    cleanText = models.CharField(max_length=4000)
    classPredicted = models.IntegerField()