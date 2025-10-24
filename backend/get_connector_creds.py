from database import SessionLocal
from models import Connector

db = SessionLocal()
c = db.query(Connector).filter_by(id=1).first()
cfg = c.connection_config
print(f"Server: {cfg.get('server')}")
print(f"Database: {cfg.get('database')}")
print(f"Username: {cfg.get('username')}")
print(f"Password: {cfg.get('password')}")
db.close()

