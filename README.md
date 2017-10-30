# Fibbage Telegram Bot
Use this Telegram bot to play with your friends through Telegram. You can try [the one I hosted on PythonAnywhere](https://t.me/fibbagebot), even though most of the time it's locked for use.
The bot has been created using Python 3.6 and uses webhooks to receive messages through the Telegram API, while running on PythonAnywhere.

#### List of dependencies
* Telepot for Telegram API - [link](https://github.com/nickoala/telepot)
* Flask, urllib3 for webhooks

#### Additional setup
The questions list I use in my bot has been removed, since it contains all the answers and has been translated to Italian. Every question has been extracted and parsed from the first two Fibbage games using a Python script to analyze all the JSON files of the game. So, in order to make this bot run, you'll need a questions file containing a questions_list like this:
```python
questions_list = [("Here's the question", "Correct answer"), ("Second question", "Correct answer")]
```