from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class BaseModel(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), nullable=False, index=True)


class First(BaseModel):
    __table_name__ = 'first'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36))
    creator = db.Column(db.String, nullable=False, unique=True)
    firm_name = db.Column(db.String)
    number = db.Column(db.Integer)


class Second(BaseModel):
    __table_name__ = 'second'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36))
    name = db.Column(db.String)
    days = db.Column(db.Integer)
    personal = db.Column(db.String)


class Third(BaseModel):
    __table_name__ = 'third'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36))
    week = db.Column(db.String)
