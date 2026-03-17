from flask import Flask, jsonify, request, Response, make_response
from flask_bcrypt import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import threading
from function import verificar_senha, enviando_email
from main import app, con



if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/criar_usuario', methods=['POST'])
def criar_usuario():
    cur = None
    try:
        dados = request.get_json()
        nome = dados.get('nome')
        telefone = dados.get('telefone')
        email = dados.get('email')
        senha = dados.get('senha')
        cpf = dados.get('cpf')

        erro_senha = verificar_senha(senha)

        if erro_senha:
            return jsonify({'erro': erro_senha}), 400

        senha_hash = generate_password_hash(senha)

        cur = con.cursor()

        cur.execute("""SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ? """, (email,))
        if cur.fetchone():
            return jsonify({'erro': 'Email já cadastrado'}), 409

        cur.execute("""INSERT INTO USUARIO (NOME, EMAIL, TELEFONE, SENHA_HASH, CPF) VALUES (?, ?, ?, ?, ?)""",
                    (nome, email, telefone, senha_hash, cpf))

        con.commit()

        return jsonify({'mensagem': 'Usuário criado com sucesso!'}), 201

    except Exception as e:
        return jsonify({'erro': f'Erro ao criar: {e}'}), 500

    finally:
       if cur:
           cur.close()

@app.route('/login', methods=['POST'])
def login():
    try:
        dados = request.get_json()
        email = dados.get('email')
        senha = dados.get('senha')

        if not email or not senha:
            return jsonify({'erro': 'Email ou senha incorreto'}), 400

        cur = con.cursor()

        cur.execute("""SELECT ID_USUARIO, NOME, SENHA_HASH FROM USUARIO WHERE EMAIL = ?""", (email,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro': 'Email ou senha incorreto'}), 400

        id_usuario = usuario[0]
        nome = usuario[1]
        senha_hash = usuario[2]

        if check_password_hash(senha_hash, senha):
            return jsonify({'messagem': 'Login realizado com sucesso','usuario':{
                'id': id_usuario,
                'nome': nome,
            }}),200
        else:
            return jsonify({'erro': 'Email ou Senha esta incorreta'}), 401
    except Exception as e:
        return jsonify({'erro': f'Erro ao login: {e}'}), 500
    finally:
        if cur:
            cur.close()

@app.route('/enviar_email', methods=['POST'])
def enviar_email():
    dados = request.get_json()
    assunto = dados.get('assunto')
    destinatario = dados.get('destinatario')
    mensagem = dados.get('mensagem')

    if not assunto or not destinatario or not mensagem:
        return jsonify({'erro': 'Os campos assunto, mensagem e destinatario são obrigatórios.'}), 400


    thread = threading.Thread(target=enviando_email, args=(destinatario, assunto, mensagem))
    thread.start()

    return jsonify({'mensagem': 'E-mail adicionado à fila de envio com sucesso!'}), 200
