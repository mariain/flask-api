from sqlalchemy import Column, Integer, String, ForeignKey, ARRAY, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import relationship, sessionmaker
from passlib.apps import custom_app_context as pwd_context
import random, string, os
from itsdangerous import(TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired)
from flask import request

Base = declarative_base()
secret_key = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))

class User(Base):
    __tablename__ = 'user'
    __table_args__ = {'schema':'api'}
    id = Column(Integer, primary_key=True)
    username = Column(String(32), index=True)
    password_hash = Column(String(64))
    email = Column(String)
    avatar = Column(String)
    about = Column(String)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=3600 * 4):
        s = Serializer(secret_key, expires_in = expiration)
        return s.dumps({'id': self.id })
    
    @staticmethod
    def verify_auth_token(token):
        s = Serializer(secret_key)
        try:
        	data = s.loads(token)
        except SignatureExpired:
    		#Valid Token, but expired
            return None
        except BadSignature:
    		#Invalid Token
            return None
        
        user_id = data['id']
        return user_id

class Post(Base):
    __tablename__ = 'post'
    __table_args__ = {'schema':'api'}
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("api.user.id"))
    text = Column(String)
    likes = Column(ARRAY(Integer))
    created_at = Column(DateTime)

    user = relationship("User")

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        if (self.likes):
            return {
                'id' : self.id,
                'user_id' : self.user_id,
                'text' : self.text,
                'likes' : len(self.likes),
                'created_at' : self.created_at,
                'author': {'username': self.user.username, 'avatar': "http://" + request.host + "/static/images/" + self.user.avatar},
                'liked' : True if self.user_id in self.likes else False
            }
        else:
            return {
                'id' : self.id,
                'user_id' : self.user_id,
                'text' : self.text,
                'likes' : 0,
                'created_at' : self.created_at,
                'author': {'username': self.user.username, 'avatar': "http://" + request.host + "/static/images/" + self.user.avatar},
                'liked' : False
            }            


        

if os.environ.get('HEROKU') is not None:
    engine = create_engine(''.join(["postgresql+psycopg2://",os.environ.get('DATABASE_URL').split('//')[1]]))
else:   
    engine = create_engine(os.environ.get('FLASK_API_DB'))
Base.metadata.create_all(engine)
