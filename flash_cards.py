import math
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash

app = Flask(__name__)
app.config.from_object(__name__)
page_size = 10

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'db', 'cards.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('CARDS_SETTINGS', silent=True)


def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    db = get_db()
    with app.open_resource('data/schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


# -----------------------------------------------------------

# Uncomment and use this to initialize database, then comment it
#   You can rerun it to pave the database and start over
#  @app.route('/initdb')
#        def initdb():
#        init_db()
#       return 'Initialized the database.'


@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('general'))
    else:
        return redirect(url_for('login'))


@app.route('/cards')
def cards():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    query = '''
        SELECT id, type, front, back, known, imageBase64Back, imageBase64Front, tag
        FROM cards
        ORDER BY id DESC limit '''+str(page_size)+''' offset 0
    '''
    cur = db.execute(query)
    cards = cur.fetchall()

    total_card_number=get_total_card_number()
    page_number= int(math.ceil(total_card_number[0] / page_size))

    return render_template('cards.html', cards=cards, filter_name="all", total_card_number=total_card_number, page="1", page_size=page_number)

@app.route('/searchcards')
def searchcards():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    content = request.args.get('searchText')
    db = get_db()
    query = '''
        SELECT id, type, front, back, known, imageBase64Back, imageBase64Front, tag
        FROM cards
        WHERE front like ? 
        or back like ?
        ORDER BY id DESC
    '''
    params = ('%' + content + '%', '%' + content + '%')
    cur = db.execute(query, params)
    cards = cur.fetchall()

    return render_template('search-result.html', cards=cards)

def get_total_card_number():
    db = get_db()
    querycount = '''
            SELECT COUNT(id)
            FROM cards
        '''
    cur = db.execute(querycount)
    return cur.fetchone();

@app.route('/filter_cards/<filter_name>/<filter_value>/<page>')
def filter_cards(filter_name, filter_value, page):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    filters = {
        "all":      "where 1 = 1",
        "general":  "where type = 1",
        "code":     "where type = 2",
        "known":    "where known = 1",
        "unknown":  "where known = 0",
        "notag":    "where tag = '' or tag is null ",
        "page":     " "
    }

    query = filters.get(filter_name)

    if not query:
        query = ""
    #     return redirect(url_for('cards'))

    if filter_name == "tag" and filter_value != "-":
        query = query + "where tag = '" + filter_value + "'"

    offset = ((int(page))-1)*page_size
    if page:
        query = query + "  ORDER BY id DESC limit "+str(page_size)+" offset "+str(offset),

    db = get_db()
    fullquery = "SELECT id, type, front, back, known, imageBase64Back, imageBase64Front, tag FROM cards " + query[0]

    cur = db.execute(fullquery)
    cards = cur.fetchall()

    if (filter_name == "tag" and filter_value == "-") or filter_name == "all":
        card_number= get_total_card_number()[0]
    else:
        card_number=len(cards)

    page_number= int(math.ceil(card_number / page_size))

    return render_template('cards.html', cards=cards, filter_name=filter_name, tag_name=filter_value, page=page, page_size=page_number)


@app.route('/tags')
def tags():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    querytags ='''
        SELECT
            name,
            COUNT(cards.tag)
        FROM
        tags
        LEFT JOIN cards ON cards.tag = tags.name
        GROUP BY
        tags.name
    '''
    db = get_db()
    cur = db.execute(querytags)
    result = cur.fetchall()
    tags = []
    tagCounts = []
    for row in result:
        tags.append(row[0])
        tagCounts.append(str(row[1]))

    notagcardscountsql = '''
        SELECT count(0) 
        FROM cards
        WHERE tag is null or tag=''
        '''
    cur = db.execute(notagcardscountsql)
    notagcardscount = cur.fetchone()
    db.close()

    return render_template('tags.html', tags=tags, tagCounts=tagCounts, notagcardscount=notagcardscount[0])


@app.route('/add', methods=['POST'])
def add_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('INSERT INTO cards (type, front, back, imageBase64Back, imageBase64Front, tag) VALUES (?, ?, ?, ?, ?, ?)',
               [request.form['type'],
                request.form['front'],
                request.form['back'],
                request.form['imageBase64Back'],
                request.form['imageBase64Front'],
                request.form['tag']
                ])

    if request.form['tag'].strip():
        querytag = '''
            SELECT id, name
            FROM tags
            WHERE name = ?
        '''
        cur = db.execute(querytag, [request.form['tag']])
        result = cur.fetchone()

        if not result:
            db.execute('INSERT INTO tags (name) VALUES (?)',
                       [request.form['tag']])

    db.commit()
    db.close()
    flash('New card was successfully added.')
    return redirect(url_for('cards'))

@app.route('/addfromextension', methods=['POST'])
def add_card_for_extension():
    db = get_db()
    json = request.json
    db.execute('INSERT INTO cards (type, front, back, imageBase64Back, imageBase64Front, tag) VALUES (?, ?, ?, ?, ?, ?)',
               [json['type'],
                json['front'],
                json['back'],
                json['imageBase64Back'],
                json['imageBase64Front'],
                json['tag']
                ])

    if json['tag'].strip():
        querytag = '''
            SELECT id, name
            FROM tags
            WHERE name = ?
        '''
        cur = db.execute(querytag, [json['tag']])
        result = cur.fetchone()

        if not result:
            db.execute('INSERT INTO tags (name) VALUES (?)',
                       [json['tag']])

    db.commit()
    db.close()
    flash('New card was successfully added.')
    return


@app.route('/edit/<card_id>')
def edit(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    query = '''
        SELECT id, type, front, back, imageBase64Back, imageBase64Front, known, tag
        FROM cards
        WHERE id = ?
    '''
    cur = db.execute(query, [card_id])
    card = cur.fetchone()
    db.close()

    return render_template('edit.html', card=card, tags=session['tags'])


@app.route('/edit_card', methods=['POST'])
def edit_card():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    selected = request.form.getlist('known')
    known = bool(selected)
    db = get_db()
    command = '''
        UPDATE cards
        SET
          type = ?,
          front = ?,
          back = ?,
          known = ?,
          imageBase64Back = ?,
          imageBase64Front = ?,
          tag = ?
        WHERE id = ?
    '''
    db.execute(command,
               [request.form['type'],
                request.form['front'],
                request.form['back'],
                known,
                request.form['imageBase64Back'],
                request.form['imageBase64Front'],
                request.form['tag'],
                request.form['card_id']
                ])

    if not get_tag_by_id(request.form['tag']):
        db.execute('INSERT INTO tags (name) VALUES (?)',
                   [request.form['tag']])

    db.commit()
    db.close()
    flash('Card saved.')
    return redirect(url_for('cards'))


@app.route('/delete/<card_id>')
def delete(card_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('DELETE FROM cards WHERE id = ?', [card_id])
    db.commit()
    db.close()
    flash('Card deleted.')
    return redirect(url_for('cards'))

@app.route('/general')
@app.route('/general/<card_id>')
def general(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return memorize("general", card_id)


@app.route('/add')
def add():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('add.html', tags=session['tags'])


@app.route('/code')
@app.route('/code/<card_id>')
def code(card_id=None):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return memorize("code", card_id)


def memorize(card_type, card_id):
    if card_type == "general":
        type = 1
    elif card_type == "code":
        type = 2
    else:
        return redirect(url_for('cards'))

    if card_id:
        card = get_card_by_id(card_id)
    else:
        card = get_card(type)
    if not card:
        flash("You've learned all the " + card_type + " cards.")
        return redirect(url_for('cards'))
    short_answer = (len(card['back']) < 75)

    session['tags']=get_tags()

    return render_template('memorize.html',
                           card=card,
                           card_type=card_type,
                           short_answer=short_answer)


def get_tags():
    db = get_db();
    querytags = '''
            SELECT id, name
            FROM tags
        '''
    cur = db.execute(querytags)
    result = cur.fetchall()
    db.close()

    tags = []
    for row in result:
        tags.append(row[1])

    return tags


def get_tag_by_id(tag_id):
    if tag_id.strip():
        querytag = '''
                SELECT id, name
                FROM tags
                WHERE name = ?
            '''
        db = get_db()
        cur = db.execute(querytag, [request.form['tag'].strip()])
        return cur.fetchone()

def get_card(type):
    db = get_db()

    query = '''
      SELECT
        id, type, front, back, imageBase64Back, imageBase64Front, known
      FROM cards
      WHERE
        type = ?
        and known = 0
      ORDER BY RANDOM()
      LIMIT 1
    '''

    cur = db.execute(query, [type])
    return cur.fetchone()


def get_card_by_id(card_id):
    db = get_db()

    query = '''
      SELECT
        id, type, front, back, known, imageBase64Back, imageBase64Front,
      FROM cards
      WHERE
        id = ?
      LIMIT 1
    '''

    cur = db.execute(query, [card_id])
    return cur.fetchone()


@app.route('/mark_known/<card_id>/<card_type>')
def mark_known(card_id, card_type):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db = get_db()
    db.execute('UPDATE cards SET known = 1 WHERE id = ?', [card_id])
    db.commit()
    flash('Card marked as known.')
    return redirect(url_for(card_type))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username or password!'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid username or password!'
        else:
            session['logged_in'] = True
            session.permanent = True  # stay logged in
            return redirect(url_for('cards'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("You've logged out")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0')
