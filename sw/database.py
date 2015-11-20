import enum
from sqlalchemy import (Column, Integer, String, Enum, BigInteger, DateTime,
                        LargeBinary, ForeignKey, func, create_engine)
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError


KeyType = enum.Enum('KeyType', 'publickey tfa readonly')

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    salt = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    user_check = Column(String(6), nullable=False)
    itercount = Column(Integer, nullable=False)
    deactivated_at = Column(DateTime)


class UserKey(Base):
    __tablename__ = 'user_key'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    key = Column(String, unique=True, nullable=False, index=True)
    key_type = Column(Enum(*(e.name for e in KeyType)), index=True)
    last_nonce = Column(BigInteger)
    deactivated_at = Column(DateTime)

    user = relationship(User, backref="keys")


class WalletBlob(Base):
    __tablename__ = 'wallet_blob'

    id = Column(String(36), primary_key=True)
    user_id = Column(String, ForeignKey(User.id), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    blob = Column(LargeBinary)
    updates_left = Column(Integer)


class CosignerWallet(Base):
    __tablename__ = 'cosigner_wallet'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    wallet = Column(LargeBinary, nullable=False)
    # Limit server-managed cosigners to 1 (at max) per wallet.
    wallet_id = Column(String(36), ForeignKey(WalletBlob.id), nullable=False,
                       unique=True)


def setup_engine(**cfg):
    return create_engine(**cfg)

def session_factory(engine, **cfg):
    return sessionmaker(bind=engine, **cfg)

def get_session(session_factory):
    return scoped_session(session_factory)


if __name__ == "__main__":
    import os
    import json

    configpath = os.getenv('DEGLET_CONFIG')
    if not configpath:
        raise Exception("DEGLET_CONFIG not specified in the environment")
    mod = json.load(open(configpath))
    engine = setup_engine(**mod['api_database']['engine'])

    Base.metadata.bind = engine
    Base.metadata.create_all()
