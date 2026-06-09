# Importa recursos do módulo flask.
from flask import Flask
# Importa módulos usados por este arquivo.
import fdb
# Importa recursos do módulo flask_cors.
from flask_cors import CORS


# Define app para uso nas próximas etapas.
app = Flask(__name__)

# Executa from_pyfile nesta etapa do fluxo.
app.config.from_pyfile('config.py')

# Define host para uso nas próximas etapas.
host = app.config['DB_HOST']
# Define database para uso nas próximas etapas.
database = app.config['DB_NAME']
# Define user para uso nas próximas etapas.
user = app.config['DB_USER']
# Define password para uso nas próximas etapas.
password = app.config['DB_PASSWORD']

# Executa CORS nesta etapa do fluxo.
CORS(
    app,
    origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    supports_credentials=True
)

# Inicia uma operação protegida para permitir o tratamento de erros.
try:
    # Define con para uso nas próximas etapas.
    con = fdb.connect(host=host, database=database, user=user, password=password)
    # Executa print nesta etapa do fluxo.
    print('Conectado com sucessso')
except Exception as e:
    # Executa print nesta etapa do fluxo.
    print(f'Erro ao conectar: ',e)

# Importa módulos usados por este arquivo.
import carro
# Importa módulos usados por este arquivo.
import marca
# Importa módulos usados por este arquivo.
import servico
# Importa módulos usados por este arquivo.
import manutencao
# Importa módulos usados por este arquivo.
import venda
# Importa módulos usados por este arquivo.
import financeiro
# Importa recursos do módulo view.
from view import *

# Verifica esta condição antes de continuar o fluxo.
if __name__ == '__main__':
    # Executa run nesta etapa do fluxo.
    app.run(host='0.0.0.0', port=5000)
