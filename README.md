# Review Doctor Slack Bot

![Review doctor photo](./assets/review_doctor_preview.webp)

## Description

A Slack Bot integrated with OpenAI to help Software teams manage requests for code reviews.

[![SlackBot with OpenAI](http://img.youtube.com/vi/4-Ozlsgy4Es/0.jpg)](https://youtu.be/4-Ozlsgy4Es?si=I6pMNIDM0NytwzQ5 "SlackBot with OpenAI")

## Features

- [x] Summarize requests for code reviews

## Development

### Setup

1. Clone the repository
2. Change directory: `cd review-doctor`
3. Install dependencies: `pip install -r requirements.txt` or better yet `poetry init`
4. Copy `.env.sample` to `.env` and fill in the values
5. Run the bot: `python app.py`
6. Run ngrok: `ngrok http 5000`
7. Copy the ngrok URL and paste it in the Slack App's Command URL

Another important step is to run `pre-commit install` to install the pre-commit hooks.

Uses `Python 3.11.4` at the time of writing. `Poetry` is used for dependency management.
