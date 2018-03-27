from models import Base, User, Post
from flask import Flask, jsonify, request, url_for, abort, g
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

from flask_httpauth import HTTPBasicAuth

from datetime import datetime
import math, os

per_page = 5
auth = HTTPBasicAuth()

if os.environ.get('HEROKU') is not None:
    engine = create_engine(''.join(["postgresql+psycopg2://",os.environ.get('DATABASE_URL').split('//')[1]]))
else:    
    engine = create_engine(os.environ.get('FLASK_API_DB'))
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()
app = Flask(__name__)

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'DELETE, GET, POST, PUT, PATCH'
        response.headers['Access-Control-Allow-Headers'] = 'authorization'
    return response

@auth.verify_password
def verify_password(username_or_token, password):
    #Try to see if it's a token first
    user_id = User.verify_auth_token(username_or_token)
    if user_id:
        user = session.query(User).filter_by(id = user_id).one()
    else:
        user = session.query(User).filter_by(username = username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True
    
@app.route('/token')
@auth.login_required
def get_auth_token():
    print(g.user.username)
    token = g.user.generate_auth_token()
    return jsonify({'token': token.decode('ascii')})

@app.route('/users', methods = ['POST'])
def new_user():
    username = request.json.get('username')
    email = request.json.get('email')
    password = request.json.get('password')
    if username is None or password is None:
        print("missing arguments")
        abort(400) 
        
    if session.query(User).filter_by(username = username).first() is not None:
        print("existing user")
        user = session.query(User).filter_by(username=username).first()
        return jsonify({'message':'user already exists'}), 200#, {'Location': url_for('get_user', id = user.id, _external = True)}
        
    user = User(username = username, email = email)
    user.hash_password(password)
    session.add(user)
    session.commit()
    return jsonify({ 'username': user.username }), 201#, {'Location': url_for('get_user', id = user.id, _external = True)}

@app.route('/users/<username>')
def get_user(username):
    user = session.query(User).filter_by(username = username).one()
    if not user:
        abort(400)
    return jsonify({'username': user.username, 'about': user.about, 'avatar': "http://" + request.host + "/static/images/" + user.avatar  })

@app.route('/users/me', methods = ['GET', 'PUT'])
@auth.login_required
def updateSetting():
    user = session.query(User).filter_by(id = g.user.id).one()
    if request.method == 'PUT':       
        user.username = request.json.get('username')
        user.about = request.json.get('about')
        session.add(user)
        session.commit()
        return "Updated a User with id %s" % id
    if request.method == 'GET':
        return jsonify({'username': user.username, 'about': user.about, 'avatar': "http://" + request.host + "/static/images/" + user.avatar})


@app.route('/users/me/avatar', methods = ['PUT'])
@auth.login_required
def updateAvatar():
    if request.method == 'PUT':
        user = session.query(User).filter_by(id = g.user.id).one()
        user.avatar = request.json.get('username')

        session.add(user)
        session.commit()
        return "Updated a User with id %s" % id

@app.route('/users/<username>/posts', methods = ['GET'])
@auth.login_required
def showUserPosts(username):
    if request.method == 'GET':
        current_page = request.args.get('page', '')
        if not current_page:
            current_page = 1
        if float(current_page).is_integer() == False:
            current_page = 1
        current_page = int(current_page)
        user = session.query(User).filter_by(username = username).one()
        posts = session.query(Post).filter_by(user_id = user.id).order_by(Post.created_at.desc())[(current_page - 1) * per_page : current_page * per_page ]
        total = session.query(Post).filter_by(user_id = user.id).count()
        return jsonify({'current_page': current_page, 'last_page': math.ceil(total/per_page), 'total': total, 'data': [p.serialize for p in posts]})


@app.route('/posts', methods = ['GET', 'POST'])
@auth.login_required
def showAllPosts():
    if request.method == 'GET':
        current_page = request.args.get('page', '')
        if not current_page:
            current_page = 1
        if float(current_page).is_integer() == False:
            current_page = 1
        current_page = int(current_page)
        posts = session.query(Post).order_by(Post.created_at.desc())[(current_page - 1) * per_page : current_page * per_page ]
        total = session.query(Post).count()
        return jsonify({'current_page': current_page, 'last_page': math.ceil(total/per_page), 'total': total, 'data': [p.serialize for p in posts]})
            
    if request.method == 'POST':
        text = request.json.get('text')
        newPost = Post(user_id = g.user.id, text = text, created_at = datetime.utcnow())
        session.add(newPost)
        session.commit()
        return jsonify(newPost.serialize)

@app.route('/posts/<int:id>/like', methods = ['PATCH'])
@auth.login_required
def likeUnlikePost(id):
    if request.method == 'PATCH':
        post = session.query(Post).filter_by(id = id).one()
        if not post.likes:
            post.likes = []
        post.likes = list(post.likes)    
        if g.user.id in post.likes:
            post.likes.remove(g.user.id)           
        else:  
            post.likes.append(g.user.id)
        session.add(post)
        session.commit()
        return "Updated a Post with id %s" % id

if __name__ == '__main__':
    app.debug = True
    #app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    app.run(host='0.0.0.0', port=5000)
