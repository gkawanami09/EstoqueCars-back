# Importa recursos do módulo flask.
from flask import Flask, jsonify, request, make_response, render_template
# Importa recursos do módulo flask_bcrypt.
from flask_bcrypt import generate_password_hash, check_password_hash
# Importa módulos usados por este arquivo.
import os
# Importa módulos usados por este arquivo.
import datetime
# Importa módulos usados por este arquivo.
import threading
# Importa módulos usados por este arquivo.
import jwt
# Importa recursos do módulo function.
from function import verificar_senha, enviando_email, gerar_codigo, gerar_token, atualizar_historico_senhas
# Importa recursos do módulo main.
from main import app, con

# Verifica esta condição antes de continuar o fluxo.
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    # Executa makedirs nesta etapa do fluxo.
    os.makedirs(app.config['UPLOAD_FOLDER'])


# Declara a função obter_token_requisicao usada neste fluxo.
def obter_token_requisicao():
    # Define token para uso nas próximas etapas.
    token = request.cookies.get('access_token')
    # Verifica esta condição antes de continuar o fluxo.
    if token:
        # Retorna o resultado desta operação.
        return token

    # Define auth_header para uso nas próximas etapas.
    auth_header = request.headers.get('Authorization', '')
    # Verifica esta condição antes de continuar o fluxo.
    if auth_header.lower().startswith('bearer '):
        # Retorna o resultado desta operação.
        return auth_header.split(' ', 1)[1].strip()

    # Retorna o resultado desta operação.
    return request.headers.get('X-Access-Token')


@app.route('/criar_usuario', methods=['POST'])      #adicionar campo de tipo no front
# Declara a função criar_usuario usada neste fluxo.
def criar_usuario():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define tipo para uso nas próximas etapas.
        tipo = request.form.get('tipo', 0)
        # Define nome para uso nas próximas etapas.
        nome = request.form.get('nome').lower()
        # Define telefone para uso nas próximas etapas.
        telefone = request.form.get('telefone')
        # Define email para uso nas próximas etapas.
        email = request.form.get('email')
        # Define senha para uso nas próximas etapas.
        senha = request.form.get('senha')
        # Define cpf para uso nas próximas etapas.
        cpf = request.form.get('cpf')
        # Define foto_perfil para uso nas próximas etapas.
        foto_perfil = request.files.get('foto_perfil')
        
        # Verifica esta condição antes de continuar o fluxo.
        if not nome or nome.split() == None:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Nome é obrigatório.'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if not email or not senha:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Email e senha são obrigatórios.'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if not cpf:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'CPF é obrigatório.'}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if not telefone:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Telefone é obrigatório.'}), 400

        # Define erro_senha para uso nas próximas etapas.
        erro_senha = verificar_senha(senha)
        # Verifica esta condição antes de continuar o fluxo.
        if erro_senha:
            # Retorna o resultado desta operação.
            return jsonify({'erro': erro_senha}), 400
        # Executa este comando no banco de dados.
        cur.execute("""
                    SELECT EMAIL, CPF, TELEFONE
                    FROM USUARIO
                    WHERE EMAIL = ?
                       OR CPF = ?
                       OR TELEFONE = ?
                    """, (email, cpf, telefone))

        # Define conflito para uso nas próximas etapas.
        conflito = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if conflito:
            # Verifica esta condição antes de continuar o fluxo.
            if conflito[0] == email:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'E-mail já cadastrado'}), 409
            # Verifica esta condição antes de continuar o fluxo.
            if conflito[1] == cpf:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Cpf já cadastrado'}), 409
            # Verifica esta condição antes de continuar o fluxo.
            if conflito[2] == telefone:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Telefone já cadastrado'}), 409

        # Define senha_hash para uso nas próximas etapas.
        senha_hash = generate_password_hash(senha)
        # Define codigo_ativacao para uso nas próximas etapas.
        codigo_ativacao = gerar_codigo()
        
        
        # Define query para uso nas próximas etapas.
        query = """INSERT INTO USUARIO (NOME,
                                        EMAIL,
                                        TELEFONE,
                                        SENHA_HASH,
                                        CPF,
                                        CODIGO_ATIVACAO,
                                        TIPO_USUARIO,
                                        SITUACAO)"""
                                            
                                            
        # Verifica esta condição antes de continuar o fluxo.
        if tipo == 0:
            # Define query para uso nas próximas etapas.
            query = query + """VALUES (?, ?, ?, ?, ?, ?, 0, 2) """
        else:
            # Define query para uso nas próximas etapas.
            query = query + """VALUES (?, ?, ?, ?, ?, NULL, 1, 0) """
                
                
        # Executa este comando no banco de dados.
        cur.execute(query, (nome.capitalize(), email, telefone, senha_hash, cpf, codigo_ativacao))
        
                                            

        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ?", (email,))
        # Define id_usuario para uso nas próximas etapas.
        id_usuario = cur.fetchone()[0]

        # Verifica esta condição antes de continuar o fluxo.
        if foto_perfil:
            # Define nome_imagem para uso nas próximas etapas.
            nome_imagem = f'{id_usuario}.jpg'
            # Define caminho_foto para uso nas próximas etapas.
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            # Executa save nesta etapa do fluxo.
            foto_perfil.save(caminho_foto)

        # Confirma no banco todas as alterações realizadas.
        con.commit()
        
        # Verifica esta condição antes de continuar o fluxo.
        if tipo == 0:
            # Define assunto para uso nas próximas etapas.
            assunto = "Confirme seu cadastro - Estoque Cars"

            # Define template_html para uso nas próximas etapas.
            template_html = render_template('email_cadastro.html', nome=nome, codigo=codigo_ativacao)

            # Define thread para uso nas próximas etapas.
            thread = threading.Thread(target=enviando_email, args=(email, assunto, template_html))
            # Executa start nesta etapa do fluxo.
            thread.start()

            # Retorna o resultado desta operação.
            return jsonify({'erro': 0, 'mensagem': 'Usuário criado com sucesso! Para ativar, verifique o seu e-mail.'}), 201
        

        # Retorna o resultado desta operação.
        return jsonify({'mensagem' : 'Vendedor cadastrado com sucesso!'})

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao criar: {e}'}), 500

    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/confirmar_email', methods=['POST'])
# Declara a função confirmar_email usada neste fluxo.
def confirmar_email():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json()
        # Define email para uso nas próximas etapas.
        email = dados.get('email')
        # Define codigo para uso nas próximas etapas.
        codigo = dados.get('codigo')

        # Verifica esta condição antes de continuar o fluxo.
        if not email or not codigo:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'E-mail e código são obrigatórios.'}), 400

        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ? AND CODIGO_ATIVACAO = ?", (email, codigo))

        # Verifica esta condição antes de continuar o fluxo.
        if not cur.fetchone():
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Código inválido ou e-mail incorreto.'}), 400

        # Executa este comando no banco de dados.
        cur.execute("UPDATE USUARIO SET SITUACAO = 0, CODIGO_ATIVACAO = NULL WHERE EMAIL = ?", (email,))
        # Confirma no banco todas as alterações realizadas.
        con.commit()

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'E-mail confirmado com sucesso! Você já pode fazer login.'}), 200

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao confirmar e-mail: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/editar_usuario/<int:id_usuario>', methods=['POST'])
# Declara a função editar_usuario usada neste fluxo.
def editar_usuario(id_usuario):
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Executa este comando no banco de dados.
        cur.execute("SELECT NOME, TELEFONE, EMAIL, CPF FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        # Define usuario_atual para uso nas próximas etapas.
        usuario_atual = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario_atual:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário não encontrado.'}), 404

        # Define nome para uso nas próximas etapas.
        nome = request.form.get('nome') or usuario_atual[0]
        # Define telefone para uso nas próximas etapas.
        telefone = request.form.get('telefone') or usuario_atual[1]
        # Define email para uso nas próximas etapas.
        email = request.form.get('email') or usuario_atual[2]
        # Define cpf para uso nas próximas etapas.
        cpf = request.form.get('cpf') or usuario_atual[3]
        # Define senha para uso nas próximas etapas.
        senha = request.form.get('senha')
        # Define foto_perfil para uso nas próximas etapas.
        foto_perfil = request.files.get('foto_perfil')

        # Executa este comando no banco de dados.
        cur.execute("""
                    SELECT EMAIL, CPF, TELEFONE
                    FROM USUARIO
                    WHERE (EMAIL = ? OR CPF = ? OR TELEFONE = ?)
                      AND ID_USUARIO != ?
                    """, (email, cpf, telefone, id_usuario))

        # Define conflito para uso nas próximas etapas.
        conflito = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if conflito:
            # Verifica esta condição antes de continuar o fluxo.
            if conflito[0] == email:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'E-mail já está sendo usado'}), 409
            # Verifica esta condição antes de continuar o fluxo.
            if conflito[1] == cpf:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Cpf já está sendo usado '}), 409
            # Verifica esta condição antes de continuar o fluxo.
            if conflito[2] == telefone:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Telefone já está sendo usado '}), 409

        # Verifica esta condição antes de continuar o fluxo.
        if senha:
            # Define erro_senha para uso nas próximas etapas.
            erro_senha = verificar_senha(senha)
            # Verifica esta condição antes de continuar o fluxo.
            if erro_senha:
                # Retorna o resultado desta operação.
                return jsonify({'erro': erro_senha}), 400

            # Verifica esta condição antes de continuar o fluxo.
            if atualizar_historico_senhas(id_usuario, senha, cur):
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Você não pode reutilizar suas últimas 3 senhas.'}), 400

            # Define senha_hash para uso nas próximas etapas.
            senha_hash = generate_password_hash(senha)

            # Executa este comando no banco de dados.
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
            # Executa este comando no banco de dados.
            cur.execute("""
                        UPDATE USUARIO
                        SET NOME     = ?,
                            TELEFONE = ?,
                            EMAIL    = ?,
                            CPF      = ?
                        WHERE ID_USUARIO = ?
                        """, (nome, telefone, email, cpf, id_usuario))

        # Verifica esta condição antes de continuar o fluxo.
        if foto_perfil:
            # Define nome_imagem para uso nas próximas etapas.
            nome_imagem = f'{id_usuario}.jpg'
            # Define caminho_foto para uso nas próximas etapas.
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            # Executa save nesta etapa do fluxo.
            foto_perfil.save(caminho_foto)

        # Confirma no banco todas as alterações realizadas.
        con.commit()
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Usuario editado com sucesso!'}), 200

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao editar: {e}'}), 500
    finally:
        # Verifica esta condição antes de continuar o fluxo.
        if cur:
            # Fecha o recurso utilizado nesta operação.
            cur.close()


@app.route('/login', methods=['POST'])
# Declara a função login usada neste fluxo.
def login():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json(silent=True) or {}
        # Define email para uso nas próximas etapas.
        email = str(dados.get('email') or '').strip()
        # Define senha para uso nas próximas etapas.
        senha = dados.get('senha')

        # Verifica esta condição antes de continuar o fluxo.
        if not email or not senha:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Preencha todos os campos'}), 400

        # Executa este comando no banco de dados.
        cur.execute(
            """SELECT ID_USUARIO, NOME, SENHA_HASH, SITUACAO, ERRO, TIPO_USUARIO
               FROM USUARIO
               WHERE LOWER(EMAIL) = LOWER(?)""",
            (email,))
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Email não cadastrado'}), 400

        # Define id_usuario para uso nas próximas etapas.
        id_usuario = usuario[0]
        # Define nomeBruto para uso nas próximas etapas.
        nomeBruto = usuario[1]
        # Define nome para uso nas próximas etapas.
        nome = nomeBruto.strip().split()[0]
        # Define senha_hash para uso nas próximas etapas.
        senha_hash = usuario[2]
        # Define situacao para uso nas próximas etapas.
        situacao = usuario[3]
        # Define erro para uso nas próximas etapas.
        erro = usuario[4]
        # Define tipo para uso nas próximas etapas.
        tipo = usuario[5]

        # Verifica esta condição antes de continuar o fluxo.
        if situacao == 1 and tipo != 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuario bloqueado'}), 401

        # Verifica esta condição antes de continuar o fluxo.
        if situacao == 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Por favor, confirme seu e-mail antes de fazer login.'}), 403

        # Verifica esta condição antes de continuar o fluxo.
        if check_password_hash(senha_hash, senha):
            # Executa este comando no banco de dados.
            cur.execute(
                "UPDATE USUARIO SET ERRO = 0 WHERE ID_USUARIO = ?",
                (id_usuario,)
            )
            # Confirma no banco todas as alterações realizadas.
            con.commit()
            # Define token para uso nas próximas etapas.
            token = gerar_token(id_usuario)

            # Define resp para uso nas próximas etapas.
            resp = make_response(jsonify({
                'id_usuario': id_usuario,
                'id_user': id_usuario,
                'nome': nome,
                'tipo_usuario': tipo,
                'token': token,
                'mensagem': 'Logado com sucesso!'
            }), 200)

            # Executa set_cookie nesta etapa do fluxo.
            resp.set_cookie(
                'access_token', token,
                httponly=True,
                secure=False,
                samesite="Lax",
                path="/",
                max_age=3600
            )
            # Retorna o resultado desta operação.
            return resp
        else:
            # Verifica esta condição antes de continuar o fluxo.
            if tipo == 2:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Email ou Senha está incorreta'}), 401
            # Executa este comando no banco de dados.
            cur.execute(
                "UPDATE USUARIO SET ERRO = ERRO + 1 WHERE ID_USUARIO = ?",
                (id_usuario,)
            )
            # Confirma no banco todas as alterações realizadas.
            con.commit()

            # Executa este comando no banco de dados.
            cur.execute(
                "SELECT ERRO FROM USUARIO WHERE ID_USUARIO = ?",
                (id_usuario,)
            )
            # Define erro_atual para uso nas próximas etapas.
            erro_atual = cur.fetchone()[0]
            # Verifica esta condição antes de continuar o fluxo.
            if erro_atual >= 3:
                # Executa este comando no banco de dados.
                cur.execute(
                    "UPDATE USUARIO SET SITUACAO = 1 WHERE ID_USUARIO = ?",
                    (id_usuario,)
                )
                # Confirma no banco todas as alterações realizadas.
                con.commit()
                # Retorna o resultado desta operação.
                return jsonify({
                                   'erro': 'Usuário bloqueado por excesso de tentativas. Entre em contato com o suporte para desbloquear sua conta.'}), 401

            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Email ou Senha está incorreta'}), 401

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao login: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/enviar_email', methods=['POST'])
# Declara a função enviar_email usada neste fluxo.
def enviar_email():
    # Define dados para uso nas próximas etapas.
    dados = request.get_json()
    # Define assunto para uso nas próximas etapas.
    assunto = dados.get('assunto')
    # Define destinatario para uso nas próximas etapas.
    destinatario = dados.get('destinatario')
    # Define mensagem_texto para uso nas próximas etapas.
    mensagem_texto = dados.get('mensagem')

    # Verifica esta condição antes de continuar o fluxo.
    if not assunto or not destinatario or not mensagem_texto:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Os campos assunto, mensagem e destinatario são obrigatórios.'}), 400

    # Define template_html para uso nas próximas etapas.
    template_html = render_template('email_generico.html', mensagem_texto=mensagem_texto)

    # Define thread para uso nas próximas etapas.
    thread = threading.Thread(target=enviando_email, args=(destinatario, assunto, template_html))
    # Executa start nesta etapa do fluxo.
    thread.start()

    # Retorna o resultado desta operação.
    return jsonify({'mensagem': 'E-mail adicionado na fila de envio com sucesso!'}), 200


@app.route('/codigo_verificacao', methods=['POST'])
# Declara a função codigo_verificacao usada neste fluxo.
def codigo_verificacao():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json()
        # Define email para uso nas próximas etapas.
        email = dados.get('email')

        # Verifica esta condição antes de continuar o fluxo.
        if not email:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O e-mail é obrigatório.'}), 400

        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_USUARIO, NOME, SITUACAO FROM USUARIO WHERE TRIM(EMAIL) = ?", (email,))
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if usuario is None:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário não encontrado. Verifique o e-mail digitado.'}), 404

        # Define id_usuario para uso nas próximas etapas.
        id_usuario = usuario[0]
        # Define nome para uso nas próximas etapas.
        nome = usuario[1]
        # Define situacao para uso nas próximas etapas.
        situacao = usuario[2]

        # Verifica esta condição antes de continuar o fluxo.
        if situacao == 1:
            # Retorna o resultado desta operação.
            return jsonify(
                {'erro': 'Usuario bloqueado. Entre em contato com o suporte para desbloquear sua conta.'}), 404

        # Define codigo para uso nas próximas etapas.
        codigo = gerar_codigo()

        # Executa este comando no banco de dados.
        cur.execute("INSERT INTO RECUPERAR_SENHA (ID_USUARIO, CODIGO) VALUES (?, ?)", (id_usuario, codigo))
        # Confirma no banco todas as alterações realizadas.
        con.commit()

        # Define assunto para uso nas próximas etapas.
        assunto = "Recuperação de Senha - Estoque Cars"
        # Define template_html para uso nas próximas etapas.
        template_html = render_template('email_recuperacao.html', nome=nome, codigo=codigo)

        # Define thread para uso nas próximas etapas.
        thread = threading.Thread(target=enviando_email, args=(email, assunto, template_html))
        # Executa start nesta etapa do fluxo.
        thread.start()

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Código de recuperação enviado para o seu e-mail.'}), 200

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao solicitar recuperação: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/recuperar_senha', methods=['POST'])
# Declara a função recuperar_senha usada neste fluxo.
def recuperar_senha():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define dados para uso nas próximas etapas.
        dados = request.get_json()
        # Define email para uso nas próximas etapas.
        email = dados.get('email')
        # Define codigo para uso nas próximas etapas.
        codigo = dados.get('codigo')
        # Define nova_senha para uso nas próximas etapas.
        nova_senha = dados.get('nova_senha')

        # Verifica esta condição antes de continuar o fluxo.
        if not email or not codigo:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'E-mail e código são obrigatórios.'}), 400

        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ?", (email,))
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        # Define id_usuario para uso nas próximas etapas.
        id_usuario = usuario[0]

        # Executa este comando no banco de dados.
        cur.execute("""
                    SELECT ID_RECUPERA
                    FROM RECUPERAR_SENHA
                    WHERE ID_USUARIO = ?
                      AND CODIGO = ?
                      AND USADO_EM IS NULL
                    """, (id_usuario, codigo))

        # Define recuperacao para uso nas próximas etapas.
        recuperacao = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not recuperacao:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Código inválido'}), 400

        # Define id_recupera para uso nas próximas etapas.
        id_recupera = recuperacao[0]

        # Verifica esta condição antes de continuar o fluxo.
        if not nova_senha:
            # Retorna o resultado desta operação.
            return jsonify({'mensagem': 'Código válido', "valido": True}), 200

        # Define erro_senha para uso nas próximas etapas.
        erro_senha = verificar_senha(nova_senha)

        # Verifica esta condição antes de continuar o fluxo.
        if erro_senha:
            # Retorna o resultado desta operação.
            return jsonify({'erro_senha': erro_senha}), 400
        # Verifica esta condição antes de continuar o fluxo.
        if atualizar_historico_senhas(id_usuario, nova_senha, cur):
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Você não pode reutilizar suas últimas 3 senhas.'}), 400

        # Define senha_hash para uso nas próximas etapas.
        senha_hash = generate_password_hash(nova_senha)

        # Executa este comando no banco de dados.
        cur.execute(
            "UPDATE USUARIO SET SENHA_HASH = ? ,ERRO = 0 , SITUACAO = 0 WHERE ID_USUARIO = ?",
            (senha_hash, id_usuario)
        )

        # Define agora para uso nas próximas etapas.
        agora = datetime.datetime.now()

        # Executa este comando no banco de dados.
        cur.execute(
            "UPDATE RECUPERAR_SENHA SET USADO_EM = ? WHERE ID_RECUPERA = ?",
            (agora, id_recupera)
        )

        # Confirma no banco todas as alterações realizadas.
        con.commit()
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Senha redefinida com sucesso!', "validade": False}), 200

    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao redefinir senha: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/listar_usuario', methods=['GET'])
# Declara a função listar_usuario usada neste fluxo.
def listar_usuario():
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_USUARIO, NOME, EMAIL, CPF, TELEFONE, TIPO_USUARIO, SITUACAO FROM USUARIO")
        # Define usuarios para uso nas próximas etapas.
        usuarios = cur.fetchall()

        # Define lista_usuarios para uso nas próximas etapas.
        lista_usuarios = []
        # Percorre os itens necessários para executar esta etapa.
        for u in usuarios:
            # Executa append nesta etapa do fluxo.
            lista_usuarios.append({
                'id_usuario': u[0],
                'nome': u[1],
                'email': u[2],
                'telefone': u[4],
                'cpf': u[3],
                'tipo_usuario': u[5],
                'situacao': u[6],
                'foto_perfil': f'/uploads/{u[0]}.jpg'
            })
        # Retorna o resultado desta operação.
        return jsonify(lista_usuarios), 200
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao listar usuarios: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/buscar_usuario/<string:nome>', methods=['GET'])
# Declara a função buscar_usuario usada neste fluxo.
def buscar_usuario(nome):
    # Define token para uso nas próximas etapas.
    token = obter_token_requisicao()
    # Verifica esta condição antes de continuar o fluxo.
    if not token:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Acesso negado. Token não encontrado.'}), 401
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:

        # Define payload para uso nas próximas etapas.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        # Define id_adm para uso nas próximas etapas.
        id_adm = payload['id_user']
        # Executa este comando no banco de dados.
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))
        # Define usuarios para uso nas próximas etapas.
        usuarios = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not usuarios or usuarios[0] != 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso restrito. Apenas administradores podem acessar.'}), 403

        # Executa este comando no banco de dados.
        cur.execute(
            "SELECT NOME, EMAIL, CPF, TELEFONE FROM USUARIO WHERE LOWER(NOME) LIKE LOWER(?)",
            (f"%{nome}%",)
        )
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchall()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário não encontrado'}), 404

        # Define dados para uso nas próximas etapas.
        dados = []
        # Percorre os itens necessários para executar esta etapa.
        for u in usuario:
            # Executa append nesta etapa do fluxo.
            dados.append({
                'nome': u[0],
                'email': u[1],
                'cpf': u[2],
                'telefone': u[3]
            })

        # Retorna o resultado desta operação.
        return jsonify(dados), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente por gentileza.'}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido'}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao buscar usuário: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/excluir_usuario/<int:id_usuario>', methods=['DELETE'])
# Declara a função excluir_usuario usada neste fluxo.
def excluir_usuario(id_usuario):
    # Define token para uso nas próximas etapas.
    token = obter_token_requisicao()
    # Verifica esta condição antes de continuar o fluxo.
    if not token:
        # Retorna o resultado desta operação.
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define payload para uso nas próximas etapas.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        # Define id_adm para uso nas próximas etapas.
        id_adm = payload['id_user']
        # Executa este comando no banco de dados.
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))
        # Define usuarios para uso nas próximas etapas.
        usuarios = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not usuarios or usuarios[0] != 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso restrito. Apenas administradores podem acessar.'}), 403

        # Verifica esta condição antes de continuar o fluxo.
        if id_adm == id_usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Operação não permitida. Você não pode excluir sua própria conta.'}), 403

        # Executa este comando no banco de dados.
        cur.execute("SELECT EMAIL FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário não encontrado'}), 404
        # Define email para uso nas próximas etapas.
        email = usuario[0]

        # Executa este comando no banco de dados.
        cur.execute("DELETE FROM RECUPERAR_SENHA WHERE ID_USUARIO = ?", (id_usuario,))
        # Executa este comando no banco de dados.
        cur.execute("DELETE FROM SENHA WHERE ID_USUARIO = ?", (id_usuario,))
        # Executa este comando no banco de dados.
        cur.execute("DELETE FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        # Confirma no banco todas as alterações realizadas.
        con.commit()

        # Remove tanto o nome atual quanto nomes antigos usados para fotos de perfil.
        nomes_imagem = [
            f'{id_usuario}.jpg',
            f'{id_usuario}.png',
            f'foto_perfil{id_usuario}.png',
            f'foto_perfil{id_usuario}.jpg',
            f'foto_perfil_{id_usuario}.jpg',
        ]
        for nome_imagem in nomes_imagem:
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Usuário removido com sucesso'}), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente por gentileza.'}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido'}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao excluir usuário: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()


@app.route('/logout', methods=['POST'])
# Declara a função logout usada neste fluxo.
def logout():
    # Define resp para uso nas próximas etapas.
    resp = make_response(jsonify({'mensagem': 'Logout realizado com sucesso'}), 200)
    # Executa delete_cookie nesta etapa do fluxo.
    resp.delete_cookie(
        'access_token',
        path='/',
        samesite='Lax',
        secure=False
    )
    # Retorna o resultado desta operação.
    return resp


@app.route('/desbloquear_usuario/<int:id_bloqueado>', methods=['PUT'])
# Declara a função desbloquear_usuario usada neste fluxo.
def desbloquear_usuario(id_bloqueado):
    # Define token para uso nas próximas etapas.
    token = obter_token_requisicao()
    # Verifica esta condição antes de continuar o fluxo.
    if not token:
        # Retorna o resultado desta operação.
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()


    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:

        # Define payload para uso nas próximas etapas.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        # Define id_adm para uso nas próximas etapas.
        id_adm = payload['id_user']
        # Executa este comando no banco de dados.
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_adm,))
        # Define usuario_logado para uso nas próximas etapas.
        usuario_logado = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario_logado or usuario_logado[0] != 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso restrito apenas para administradores.'}), 403



        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_bloqueado,))
        # Verifica esta condição antes de continuar o fluxo.
        if not cur.fetchone():
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário alvo não encontrado.'}), 404

        # Executa este comando no banco de dados.
        cur.execute("UPDATE USUARIO SET SITUACAO = 0, ERRO = 0 WHERE ID_USUARIO = ?", (id_bloqueado,))
        # Confirma no banco todas as alterações realizadas.
        con.commit()

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Usuário desbloqueado com sucesso!'}), 200

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({"erro": "Token inválido ou adulterado."}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao desbloquear: {e}'}), 500
    finally:
        # Verifica esta condição antes de continuar o fluxo.
        if cur:
            # Fecha o recurso utilizado nesta operação.
            cur.close()


@app.route('/bloquear_usuario/<int:id_bloqueado>', methods=['PUT'])
# Declara a função bloquear_usuario usada neste fluxo.
def bloquear_usuario(id_bloqueado):
    # Define token para uso nas próximas etapas.
    token = obter_token_requisicao()
    # Define dados para uso nas próximas etapas.
    dados = request.get_json()
    # Define mensagem_texto para uso nas próximas etapas.
    mensagem_texto = dados.get('mensagem')
    # Verifica esta condição antes de continuar o fluxo.
    if not token:
        # Retorna o resultado desta operação.
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401

    # Define cur para uso nas próximas etapas.
    cur = con.cursor()
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:
        # Define payload para uso nas próximas etapas.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        # Define id_adm para uso nas próximas etapas.
        id_adm = payload['id_user']

        # Executa este comando no banco de dados.
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_adm,))
        # Define usuario_logado para uso nas próximas etapas.
        usuario_logado = cur.fetchone()

        # Verifica esta condição antes de continuar o fluxo.
        if not usuario_logado or usuario_logado[0] != 2:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Apenas administradores podem bloquear usuário.'}), 403

        # impedir bloquear a si mesmo
        if id_adm == id_bloqueado:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Você não pode bloquear sua própria conta.'}), 400

        # verificar se existe
        cur.execute("SELECT ID_USUARIO, EMAIL, SITUACAO FROM USUARIO WHERE ID_USUARIO = ?", (id_bloqueado,))
        # Define usuario para uso nas próximas etapas.
        usuario = cur.fetchone()
        # Verifica esta condição antes de continuar o fluxo.
        if not usuario:
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Usuário não encontrado.'}), 404
        # Define email para uso nas próximas etapas.
        email = usuario[1]
        # Define situacao para uso nas próximas etapas.
        situacao = usuario[2]

        # Verifica esta condição antes de continuar o fluxo.
        if situacao == 0:
            # Verifica esta condição antes de continuar o fluxo.
            if not mensagem_texto:
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Os campos assunto e mensagem são obrigatórios.'}), 400

            # Define template_html para uso nas próximas etapas.
            template_html = render_template('email_generico.html', mensagem_texto=mensagem_texto)

            # Define thread para uso nas próximas etapas.
            thread = threading.Thread(target=enviando_email, args=(email, "Sua conta foi bloqueada" ,template_html))
            # Executa start nesta etapa do fluxo.
            thread.start()
            
            # bloquear
            cur.execute("UPDATE USUARIO SET SITUACAO = 1 WHERE ID_USUARIO = ?", (id_bloqueado,))
            # Confirma no banco todas as alterações realizadas.
            con.commit()

            # Retorna o resultado desta operação.
            return jsonify({'mensagem': 'Usuário bloqueado com sucesso!'}), 200
        # Retorna o resultado desta operação.
        return jsonify({'erro' : 'O usuário já está bloqueado!'})

    except jwt.ExpiredSignatureError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401
    except jwt.InvalidTokenError:
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401
    except Exception as e:
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao bloquear: {e}'}), 500
    finally:
        # Fecha o recurso utilizado nesta operação.
        cur.close()
