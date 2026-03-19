import os 
SECRET_KEY = "senha_muito_secreta"
DEBUG = True

DB_HOST = 'localhost'
DB_NAME = r'C:\Users\Usuario\Desktop\Back End - EstoqueCars\EstoqueCarsBanco.FDB'

DB_USER = 'sysdba'
DB_PASSWORD = 'sysdba'



UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')