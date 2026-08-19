from dotenv import load_dotenv
load_dotenv()

from app.database import engine

try:
    connection = engine.connect()
    print("Database Connected Successfully!")
    connection.close()
except Exception as e:
    print(e)