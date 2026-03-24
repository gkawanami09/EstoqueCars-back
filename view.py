from tempfile import template
from flask import Flask, jsonify, request, Response, make_response,render_template
from flask_bcrypt import generate_password_hash, check_password_hash
import os
import datetime
import threading
import jwt
from function import verificar_senha, enviando_email, gerar_codigo, gerar_token,verificar_senha_repetida
from main import app, con

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/criar_usuario', methods=['POST'])
def criar_usuario():
    cur = con.cursor()
    try:
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        senha = request.form.get('senha')
        cpf = request.form.get('cpf')
        foto_perfil = request.files.get('foto_perfil')

        erro_senha = verificar_senha(senha)

        if not nome:
            return jsonify({'erro': 'Esse campo é obrigatório.'}), 400
        if not email or not senha:
            return jsonify({'erro': 'Email e senha são obrigatórios.'}), 400

        if erro_senha:
            return jsonify({'erro': erro_senha}), 400

        if foto_perfil:
            nome_imagem = f'{email}.jpg'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            foto_perfil.save(caminho_foto)

        senha_hash = generate_password_hash(senha)
        codigo_ativacao = gerar_codigo()

        cur.execute("""SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ? """, (email,))
        if cur.fetchone():
            return jsonify({'erro': 'Email já cadastrado.'}), 409


        cur.execute("""INSERT INTO USUARIO (NOME, EMAIL, TELEFONE, SENHA_HASH, CPF, SITUACAO, CODIGO_ATIVACAO) 
                               VALUES (?, ?, ?, ?, ?, 3, ?)""",
                    (nome, email, telefone, senha_hash, cpf, codigo_ativacao))
        con.commit()

        assunto = "Confirme seu cadastro - Estoque Cars"

        template_html = render_template('email_cadastro.html', nome=nome, codigo=codigo_ativacao)

        thread = threading.Thread(target=enviando_email, args=(email, assunto, template_html))
        thread.start()

        return jsonify({'mensagem': 'Usuário criado com sucesso! Para ativar, verifique o seu e-mail.'}), 201

    except Exception as e:
        return jsonify({'erro': f'Erro ao criar: {e}'}), 500

    finally:
        cur.close()


@app.route('/confirmar_email', methods=['POST'])
def confirmar_email():
    cur = con.cursor()
    try:
        dados = request.get_json()
        email = dados.get('email')
        codigo = dados.get('codigo')

        if not email or not codigo:
            return jsonify({'erro': 'E-mail e código são obrigatórios.'}), 400

        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ? AND CODIGO_ATIVACAO = ?", (email, codigo))

        if not cur.fetchone():
            return jsonify({'erro': 'Código inválido ou e-mail incorreto.'}), 400

        cur.execute("UPDATE USUARIO SET SITUACAO = 0, CODIGO_ATIVACAO = NULL WHERE EMAIL = ?", (email,))
        con.commit()

        return jsonify({'mensagem': 'E-mail confirmado com sucesso! Você já pode fazer login.'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao confirmar e-mail: {e}'}), 500
    finally:
        cur.close()


@app.route('/editar_usuario/<int:id_usuario>', methods=['POST'])
def editar_usuario(id_usuario):
    try:
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        senha = request.form.get('senha')
        cpf = request.form.get('cpf')
        foto_perfil = request.files.get('foto_perfil')

        cur = con.cursor()

        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        if not cur.fetchone():
            return jsonify({'erro': 'Usuário não encontrado.'}), 404

        if senha:
            erro_senha = verificar_senha(senha)
            if erro_senha:
                return jsonify({'erro': erro_senha}), 400


            if verificar_senha_repetida(id_usuario, senha, cur):
                return jsonify({'erro': 'Você não pode reutilizar suas últimas 3 senhas.'}), 400


            cur.execute("SELECT SENHA_HASH FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
            senha_atual_banco = cur.fetchone()[0]

            cur.execute("SELECT SENHA_NOVA FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
            historico = cur.fetchone()

            if historico:
                cur.execute("UPDATE SENHA SET SENHA_NOVISSIMA = ?, SENHA_NOVA = ? WHERE ID_USUARIO = ?",
                            (historico[0], senha_atual_banco, id_usuario))
            else:
                cur.execute("INSERT INTO SENHA (ID_USUARIO, SENHA_NOVA) VALUES (?, ?)",
                            (id_usuario, senha_atual_banco))


            senha_hash = generate_password_hash(senha)

            cur.execute("""
                        UPDATE USUARIO
                        SET NOME       = ?,
                            TELEFONE   = ?,
                            EMAIL      = ?,
                            CPF        = ?,
                            SENHA_HASH = ?
                        WHERE ID_USUARIO = ?
                        """, (nome, telefone, email, cpf, senha_hash, id_usuario))

        else:
            cur.execute("""
                        UPDATE USUARIO
                        SET NOME     = ?,
                            TELEFONE = ?,
                            EMAIL    = ?,
                            CPF      = ?
                        WHERE ID_USUARIO = ?
                        """, (nome, telefone, email, cpf, id_usuario))

        if foto_perfil:
            nome_imagem = f'perfil_{id_usuario}.jpg'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            foto_perfil.save(caminho_foto)

        con.commit()
        return jsonify({'mensagem': 'Usuario editado com sucesso!'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao editar: {e}'}), 500
    finally:
        if cur:
            cur.close()


@app.route('/login', methods=['POST'])
def login():
    cur = con.cursor()
    try:
        dados = request.get_json()
        email = dados.get('email')
        senha = dados.get('senha')

        if not email or not senha:
            return jsonify({'erro': 'Preencha todos os campos'}), 400

        cur.execute(
            """SELECT ID_USUARIO, NOME, SENHA_HASH, SITUACAO, ERRO, TIPO_USUARIO FROM USUARIO WHERE EMAIL = ?""",
            (email,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro': 'Email não cadastrado'}), 400

        id_usuario = usuario[0]
        nome = usuario[1]
        senha_hash = usuario[2]
        situacao = usuario[3]
        erro = usuario[4]
        tipo = usuario[5]

        if situacao == 1 and tipo != 2:
            return jsonify({'erro': 'Usuario bloqueado'}), 401

        if situacao == 2:
            return jsonify({'erro': 'Por favor, confirme seu e-mail antes de fazer login.'}), 403

        if check_password_hash(senha_hash, senha):
            cur.execute(
                "UPDATE USUARIO SET ERRO = 0 WHERE ID_USUARIO = ?",
                (id_usuario,)
            )
            con.commit()
            token = gerar_token(id_usuario)

            resp = make_response(jsonify({'mensagem': 'Logado com sucesso!'}), 200)
            resp.set_cookie(
                'access_token', token,
                httponly=True,
                secure=False,
                samesite="Lax",
                path="/",
                max_age=600
            )
            return resp
        else:
            if tipo == 2:
                return jsonify({'erro': 'Email ou Senha está incorreta'}), 401
            cur.execute(
                "UPDATE USUARIO SET ERRO = ERRO + 1 WHERE ID_USUARIO = ?",
                (id_usuario,)
            )
            con.commit()

            cur.execute(
                "SELECT ERRO FROM USUARIO WHERE ID_USUARIO = ?",
                (id_usuario,)
            )
            erro_atual = cur.fetchone()[0]
            if erro_atual >= 3:
                cur.execute(
                    "UPDATE USUARIO SET SITUACAO = 1 WHERE ID_USUARIO = ?",
                    (id_usuario,)
                )
                con.commit()
                return jsonify({'erro': 'Usuario bloqueado'}), 401

            return jsonify({'erro': 'Email ou Senha está incorreta'}), 401
    except Exception as e:
        return jsonify({'erro': f'Erro ao login: {e}'}), 500
    finally:
        cur.close()


@app.route('/enviar_email', methods=['POST'])
def enviar_email():
    dados = request.get_json()
    assunto = dados.get('assunto')
    destinatario = dados.get('destinatario')
    mensagem_texto = dados.get('mensagem')

    if not assunto or not destinatario or not mensagem_texto:
        return jsonify({'erro': 'Os campos assunto, mensagem e destinatario são obrigatórios.'}), 400

    template_html = render_template('email_generico.html', mensagem_texto=mensagem_texto)

    thread = threading.Thread(target=enviando_email, args=(destinatario, assunto, template_html))
    thread.start()

    return jsonify({'mensagem': 'E-mail adicionado na fila de envio com sucesso!'}), 200


@app.route('/codigo_verificacao', methods=['POST'])
def codigo_verificacao():
    try:
        dados = request.get_json()
        email = dados.get('email')

        if not email:
            return jsonify({'erro': 'O e-mail é obrigatório.'}), 400

        cur = con.cursor()
        cur.execute("SELECT ID_USUARIO, NOME FROM USUARIO WHERE TRIM(EMAIL) = ?", (email,))
        usuario = cur.fetchone()

        if usuario is None:
            return jsonify({'erro': 'Usuário não encontrado. Verifique o e-mail digitado.'}), 404

        id_usuario = usuario[0]
        nome = usuario[1]

        codigo = gerar_codigo()

        cur.execute("INSERT INTO RECUPERAR_SENHA (ID_USUARIO, CODIGO) VALUES (?, ?)", (id_usuario, codigo))
        con.commit()


        assunto = "Recuperação de Senha - Estoque Cars"
        template_html = render_template('email_recuperacao.html', nome=nome, codigo=codigo)

        thread = threading.Thread(target=enviando_email, args=(email, assunto, template_html))
        thread.start()

        return jsonify({'mensagem': 'Código de recuperação enviado para o seu e-mail.'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao solicitar recuperação: {e}'}), 500
    finally:
        cur.close()


@app.route('/recuperar_senha', methods=['POST'])
def recuperar_senha():
    try:
        dados = request.get_json()
        email = dados.get('email')
        codigo = dados.get('codigo')
        nova_senha = dados.get('nova_senha')

        if not email or not codigo or not nova_senha:
            return jsonify({'erro': 'E-mail, código e nova senha são obrigatórios.'}), 400

        erro_senha = verificar_senha(nova_senha)
        if erro_senha:
            return jsonify({'erro_senha': erro_senha}), 400

        cur = con.cursor()
        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ?", (email,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        id_usuario = usuario[0]


        if verificar_senha_repetida(id_usuario, nova_senha, cur):
            return jsonify({'erro': 'Você não pode reutilizar suas últimas 3 senhas.'}), 400

        cur.execute("""
            SELECT ID_RECUPERA 
            FROM RECUPERAR_SENHA 
            WHERE ID_USUARIO = ? AND CODIGO = ? AND USADO_EM IS NULL
        """, (id_usuario, codigo))

        recuperacao = cur.fetchone()

        if not recuperacao:
            return jsonify({'erro': 'Código inválido'}), 400

        id_recupera = recuperacao[0]

        cur.execute("SELECT SENHA_HASH FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        senha_atual_banco = cur.fetchone()[0]

        cur.execute("SELECT SENHA_NOVA FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
        historico = cur.fetchone()

        if historico:
            cur.execute("UPDATE SENHA SET SENHA_NOVISSIMA = ?, SENHA_NOVA = ? WHERE ID_USUARIO = ?",
                        (historico[0], senha_atual_banco, id_usuario))
        else:
            cur.execute("INSERT INTO SENHA (ID_USUARIO, SENHA_NOVA) VALUES (?, ?)",
                        (id_usuario, senha_atual_banco))


        senha_hash = generate_password_hash(nova_senha)

        cur.execute(
            "UPDATE USUARIO SET SENHA_HASH = ? WHERE ID_USUARIO = ?",
            (senha_hash, id_usuario)
        )

        agora = datetime.datetime.now()

        cur.execute(
            "UPDATE RECUPERAR_SENHA SET USADO_EM = ? WHERE ID_RECUPERA = ?",
            (agora, id_recupera)
        )

        con.commit()
        return jsonify({'mensagem': 'Senha redefinida com sucesso!'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao redefinir senha: {e}'}), 500
    finally:
        cur.close()


@app.route('/listar_usuario', methods=['GET'])
def listar_usuario():
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({"mensagem" : "token de autenticação necessária"}), 401
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_usuario = payload['id_usuario']
    except jwt.ExpiredSignatureError:
        return jsonify({"mensagem" : "token expirado"}),401
    except jwt.InvalidTokenError:
        return jsonify({"mensagem" : "token invalido"}),401
    try:
        cur = con.cursor()
        cur.execute("SELECT ID_USUARIO, NOME, EMAIL, CPF, TELEFONE FROM USUARIO")
        usuarios = cur.fetchall()

        lista_usuarios = []
        for u in usuarios:
            lista_usuarios.append({
                'id_usuario': u[0],
                'nome': u[1],
                'email': u[2],
                'telefone': u[4],
                'cpf': u[3]
            })
        return jsonify(lista_usuarios), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar usuarios: {e}'}), 500
    finally:
        cur.close()


@app.route('/buscar_usuario/<string:nome>', methods=['GET'])
def buscar_usuario(nome):
    try:
        cur = con.cursor()
        cur.execute(
            "SELECT NOME, EMAIL, CPF, TELEFONE FROM USUARIO WHERE LOWER(NOME) LIKE LOWER(?)",
            (f"%{nome}%",)
        )
        usuario = cur.fetchall()

        if not usuario:
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        dados = []
        for u in usuario:
            dados.append({
                'nome': u[0],
                'email': u[1],
                'cpf': u[2],
                'telefone': u[3]
            })

        return jsonify(usuario), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao buscar usuário: {e}'}), 500
    finally:
        cur.close()


@app.route('/excluir_usuario/<int:id_usuario>', methods=['DELETE'])
def excluir_usuario(id_usuario):
    try:
        cur = con.cursor()

        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_usuario,))
        if not cur.fetchone():
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        cur.execute("DELETE FROM RECUPERAR_SENHA WHERE ID_USUARIO = ?", (id_usuario,))
        cur.execute("DELETE FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
        cur.execute("DELETE FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        con.commit()

        nome_imagem = f'perfil{id_usuario}.jpg'
        caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
        if os.path.exists(caminho_foto):
            os.remove(caminho_foto)

        return jsonify({'mensagem': 'Usuário removido com sucesso'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao excluir usuário: {e}'}), 500
    finally:
        cur.close()


@app.route('/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({'mensagem': 'Logout realizado'}), 200)
    resp.delete_cookie(
        'access_token',
        path='/',
        samesite='Lax',
        secure=False
    )
    return resp


@app.route('/desbloquear_usuario/<int:id_bloqueado>', methods=['PUT'])
def desbloquear_usuario(id_bloqueado):
    #  Verificar se o token existe nos cookies
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401

    try:
        #  Decodificar o token para saber quem está tentando desbloquear
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_adm = payload['id_usuario']

        cur = con.cursor()
        
        # Verificar no banco se esse id_adm realmente é um Administrador (tipo 2)
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_adm,))
        usuario_logado = cur.fetchone()

        if not usuario_logado or usuario_logado[0] != 2:
            return jsonify({'erro': 'Acesso restrito apenas para administradores.'}), 403

        # Se chegou aqui, é ADM. Agora verifica se o usuário a ser desbloqueado existe
        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_bloqueado,))
        if not cur.fetchone():
            return jsonify({'erro': 'Usuário alvo não encontrado.'}), 404

        #  Executa o desbloqueio
        cur.execute("UPDATE USUARIO SET SITUACAO = 0, ERRO = 0 WHERE ID_USUARIO = ?", (id_bloqueado,))
        con.commit()

        return jsonify({'mensagem': 'Usuário desbloqueado com sucesso!'}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401
    except Exception as e:
        return jsonify({'erro': f'Erro ao desbloquear: {e}'}), 500
    finally:
        cur.close()
