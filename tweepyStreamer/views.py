import ast
import ctypes
import threading
import requests
from django.http import JsonResponse
from django.shortcuts import render
from .models import Tweet
from django.conf import settings
import torch
import json
import os
from time import sleep
from tweepy import Stream
import datetime
from bs4 import BeautifulSoup
from urllib.parse import quote
import re

Tweet.objects.all().delete()
print('[!] Deleted all records in database.')

threads = []

class Thread(threading.Thread):

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)

    def get_id(self):
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id

    def raise_exception(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                         ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Killing thread ', self.get_id())

class StreamListener(Stream):
    def on_data(self, data):
        try:
            data = json.loads(data)

            if not data['text'].startswith('RT'):
                greek_chars = [char for char in data['text'] if char in settings.GREEK_CHARACTERS]
                if len(greek_chars) >= 5:
                    tweet = {}
                    tweet['id'] = data['id_str']
                    tweet['userId'] = data['user']['id_str']
                    if 'extended_tweet' in data:
                        tweet['text'] = data['extended_tweet']['full_text']
                    else:
                        tweet['text'] = data['text']

                    with open('tweepyStreamer\\data\\raw_data.txt', 'a', encoding='utf-8') as f:
                        f.write(str(tweet) + '\n')
            return True
        except Exception as e:
            print('[!] Error: ' + str(e))
            with open('tweepyStreamer\\data\\logs.txt', 'a', encoding='utf-8') as f:
                f.write('[' + str(datetime.datetime.now()) + '] [Streamer] ' + str(e) + '\n')

    def on_limit(self, track):
        print('[!] Limit: ' + track)
        sleep(10)

    def on_error(self, status):
        print('[!] Error: ' + str(status))
        return False


def startProcesses(term, advanced, hideBadWords):
    Tweet.objects.all().delete()
    print('[!] Deleted all records in database.')

    global threads

    if len(threads) > 0:
        for thread in threads:
            thread.raise_exception()
            thread.join()
        threads = []

    if os.path.exists("tweepyStreamer\\data\\raw_data.txt"):
        os.remove("tweepyStreamer\\data\\raw_data.txt")
        print('[!] Deleted raw_data.txt.')

    if len(threads) == 0:
        streamThread = Thread(target=streamer, args=(term,advanced,))
        streamThread.start()
        threads.append(streamThread)

        classifierThread = Thread(target=classifyTweets, args=(hideBadWords,))
        classifierThread.start()
        threads.append(classifierThread)


def stopProcesses():
    global threads

    if len(threads) > 0:
        for thread in threads:
            thread.raise_exception()
            thread.join()
        threads = []

    print('[!] Stoppped all processes.')


def streamer(terms, advanced):
    print('[*] Streamer is on.')

    streamer = StreamListener(settings.CONSUMER_KEY, settings.CONSUMER_SECRET, settings.OAUTH_TOKEN, settings.OAUTH_TOKEN_SECRET)
    list_terms = terms.split(' ')
    extra_words = []

    if len(advanced) > 0:
        print('[*] User chose Advanced Search.')
        for term in list_terms:
            encodedWord = quote(term)
            res = requests.get('https://el.wiktionary.org/wiki/' + encodedWord)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, 'html.parser')

                span = soup.findAll('span', {'id': 'κλίσεις_των_άρθρων'})  # λειτουργει για αρθρα
                if len(span) > 0:
                    table = soup.findAll('table', {'id': 'κλίσεις;_clear:both'})
                    articles = table[0].findAll('a')
                    for article in articles:
                        if len(article.get_text()) > 1 and '—' not in article.get_text():
                            extra_words.append(article.get_text().split(' ')[0])
                    continue

                personalPronoun = bool(
                    re.search('Προσωπικές αντωνυμίες', str(soup)))  # λειτουργει για προσωπικες αντωνυμιες
                if personalPronoun:
                    table = soup.findAll('table', {'class': 'wikitable'})
                    if len(table) > 0:
                        pps = table[0].findAll('a')
                        for pp in pps:
                            if bool(re.search('<td>', str(pp.parent))):
                                if len(pp.get_text()) > 1 and '—' not in pp.get_text():
                                    extra_words.append(pp.get_text().split(' ')[0])
                    continue

                tds = soup.findAll('td', {'align': 'left', 'valign': None,
                                          'colspan': None})  # λειτουργει για επιθετα, ουσιαστικα, αοριστα αρθρα, δεικτικές αντωνυμιες, αναφορικες αντωνυμιες
                if len(tds) > 0:
                    for td in tds:
                        if bool(re.search('a', str(td))) and not bool(re.search('img', str(td))):
                            if len(td.get_text()) > 1 and '—' not in td.get_text():
                                if '&\xa0' in td.get_text():
                                    sep = td.get_text().replace('&\xa0', ' ').split(' ')
                                    for word in sep:
                                        clean = word.replace('\n', '')
                                        extra_words.append(clean)
                                else:
                                    clean = td.get_text().replace('\n', '')
                                    extra_words.append(clean.split(' ')[0])
                    continue

    list_terms = list_terms + extra_words
    list_terms = list(dict.fromkeys(list_terms))
    print('[*] Starting streamer with term(s) ' , list_terms)
    streamer.filter(track=list_terms)


def getEncodingOfText(sentence):
    tokens = {'input_ids': [], 'attention_mask': []}
    if sentence.startswith('“'):
        sentence = sentence[1:]
    toks = [tok for tok in sentence.split() if
            not (tok.startswith('http://') or tok.startswith('https://') or tok.startswith('@') or tok.startswith('#'))]
    sentence = ' '.join(toks)
    new_tokens = settings.TOKENIZER_GREEK.encode_plus(sentence, max_length=128, truncation=True, padding='max_length',
                                                      return_tensors='pt')
    tokens['input_ids'].append(new_tokens['input_ids'][0])
    tokens['attention_mask'].append(new_tokens['attention_mask'][0])
    tokens['input_ids'] = torch.stack(tokens['input_ids'])
    tokens['attention_mask'] = torch.stack(tokens['attention_mask'])
    return tokens


def getClassifiedTweet(tweet, model):
    tokens = getEncodingOfText(tweet)
    outputs = settings.MODEL_GREEK(**tokens)
    embeddings = outputs.last_hidden_state

    attention = tokens['attention_mask']
    mask = attention.unsqueeze(-1).expand(embeddings.shape).float()
    mask_embeddings = embeddings * mask
    summed = torch.sum(mask_embeddings, 1)
    counts = torch.clamp(mask.sum(1), min=1e-9)
    mean_pooled = summed / counts
    X_test = mean_pooled.detach().numpy()

    pred = model.predict(X_test)
    return pred[0]


def classifyTweets(hideBadWords):
    print('[*] Classifier is on.')

    if len(hideBadWords) > 0:
        print('[*] User asked for bad words to be censored.')

    while not os.path.exists('tweepyStreamer\\data\\raw_data.txt'):
        sleep(1)

    if os.path.exists('tweepyStreamer\\data\\raw_data.txt'):
        file = open('tweepyStreamer\\data\\raw_data.txt', 'r', encoding='utf-8')
        while True:
            try:
                line = file.readline()
                if len(line) != 0:

                    # get id, userId, text
                    data = ast.literal_eval(line)

                    # check if unknown words are more than the known words and if a word is considered curse
                    knownWords = 0
                    unknownWords = 0

                    # copy of original tweet - will remove swear words
                    # will be used for optimization
                    cleanText = data['text']

                    # clean tweet from special twitter characters, stopwords, punctuation marks and numbers
                    # will be used for classification
                    toks = [tok for tok in data['text'].split() if tok.isalpha() and tok.lower() not in settings.GREEK_STOPWORDS]

                    # clean tweet from special twitter characters
                    # will be used to determine if a tweet contains more special characters than actual text
                    words = [tok for tok in data['text'].split() if
                            not (tok.startswith('http://') or tok.startswith(
                                'https://') or tok.startswith('@') or tok.startswith('#'))]

                    # keep only special twitter characters
                    # will be used to determine if a tweet contains more special characters than actual text
                    specialCharacters = [tok for tok in data['text'].split() if
                            (tok.startswith('http://') or tok.startswith(
                                'https://') or tok == 'RT' or tok.startswith('@') or tok.startswith('#'))]

                    if len(specialCharacters) < len(words) and len(toks) > 0:
                        for i in range(len(toks)):
                            encodedWord = quote(toks[i])
                            res = requests.get(
                                'https://el.wiktionary.org/w/index.php?search=' + encodedWord + '&title=%CE%95%CE%B9%CE%B4%CE%B9%CE%BA%CF%8C:%CE%91%CE%BD%CE%B1%CE%B6%CE%AE%CF%84%CE%B7%CF%83%CE%B7&profile=advanced&fulltext=1&ns0=1')
                            if res.status_code == 200:
                                soup = BeautifulSoup(res.content, 'html.parser')
                                if soup.find("p", {"class": "mw-search-nonefound"}) != None:
                                    unknownWords += 1
                                else:
                                    knownWords += 1
                                    if len(hideBadWords) > 0:
                                        first3Results = soup.findAll("li", {"class": "mw-search-result"})[0:3]
                                        badWord = (bool(re.search('χυδαίο|υβριστικό|βρισιά', str(first3Results))) or bool(
                                            any(item in str(first3Results) for item in settings.SWEAR_WORDS))) and toks[i] not in settings.NON_SWEAR_WORDS
                                        if badWord:
                                            cleanText = cleanText.replace(toks[i], toks[i][0] + '*' * (len(toks[i]) - 1))

                        if unknownWords > knownWords:
                            raise ValueError('Too many unknown words: ' + str(data['text']))
                    else:
                        raise ValueError('Too many special characters and/or numbers: ' + str(data['text']))

                    # get class

                    textForClassification = ' '.join(toks)

                    isNeutral = int(getClassifiedTweet(textForClassification, settings.NN_SVC)) == 1
                    if isNeutral:
                        classPredicted = 1
                    else:
                        isPositive = int(getClassifiedTweet(textForClassification, settings.PN_LINEAR_SVC)) == 2
                        if isPositive:
                            classPredicted = 2
                        else:
                            classPredicted = 0

                    # prepare object and save
                    tweet = Tweet(data['id'], data['userId'], data['text'], cleanText, classPredicted)
                    tweet.save()
                else:
                    sleep(1)
            except Exception as e:
                print('[!] Error: ' + str(e))
                with open('tweepyStreamer\\data\\logs.txt', 'a', encoding='utf-8') as f:
                    f.write('[' + str(datetime.datetime.now()) + '] [Classifier] ' + str(e) + '\n')
                pass


def index(request):

    if request.method == "POST":
        if request.POST.get('term'):
            startProcesses(request.POST['term'], request.POST.getlist('advancedSearch'), request.POST.getlist('hideBadWords'))
        elif request.POST.get('stop'):
            print('[!] Stop button was pressed.')
            stopProcesses()

    return render(request, 'tweepyStreamer/index.html')


def getTweets(request):
    queryset = Tweet.objects.all()
    return JsonResponse({'tweets': list(queryset.values())})