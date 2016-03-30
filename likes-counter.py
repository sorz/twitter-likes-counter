#!/usr/bin/env python3
from functools import wraps
from collections import Counter
from flask import Flask, redirect, request, session, url_for, render_template
from twython import Twython, TwythonError


app = Flask(__name__)
app.config.from_object('configs')

twitter = Twython(app.config.get('APP_KEY'), app.config.get('APP_SECRET'))

def token_required(authorized=True):
    def decorator(view):
        @wraps(view)
        def decorated_function(*args, **kwargs):
            if authorized and not session.get('authorized', False):
                return redirect(url_for('auth'))

            tw = Twython(app.config.get('APP_KEY'),
                         app.config.get('APP_SECRET'),
                         session.get('oauth_token', ''),
                         session.get('oauth_token_secret', ''))
            try:
                return view(tw, *args, **kwargs)
            except TwythonError as e:
                if e.error_code == 401:
                    return redirect(url_for('auth'))
                raise e
        return decorated_function
    return decorator


@app.route('/')
def home():
    return 'Hello, world!~'


@app.route('/auth/')
def auth():
    auth = twitter.get_authentication_tokens(
            callback_url=app.config.get('CALLBACK'))
    session['oauth_token'] = auth['oauth_token']
    session['oauth_token_secret'] = auth['oauth_token_secret']
    session['authorized'] = False
    return redirect(auth['auth_url'])


@app.route('/callback/')
@token_required(authorized=False)
def callback(tw):
    if 'denied' in request.args:
        return 'access denied.'
    if 'oauth_verifier' not in request.args:
        return 'no argument found.'

    token = tw.get_authorized_tokens(request.args['oauth_verifier'])
    session['authorized'] = True
    session['oauth_token'] = token['oauth_token']
    session['oauth_token_secret'] = token['oauth_token_secret']
    return redirect(url_for('count_likes'))


@app.route('/count-likes/')
@token_required()
def count_likes(tw):
    users = {}
    counter = Counter()
    max_id = None
    for i in range(5):
        likes = tw.get_favorites(count=200, max_id=max_id)
        if len(likes) < 2:
            break
        max_id = likes[-1]['id']
        users.update({like['user']['id_str']: like['user'] for like in likes})
        counter.update([like['user']['id_str'] for like in likes])

    top_users = [(count, users[uid]) for uid, count in counter.most_common(15)]
    return render_template('count-likes.html', top_users=top_users)


if __name__ == '__main__':
    app.run('::1', 8080)

