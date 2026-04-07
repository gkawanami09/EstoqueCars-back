from main import app, con

@app.route('/cadastrar_carro', methods=['POST'])
def cadastrar_carro():
    cur = con.cursor()
