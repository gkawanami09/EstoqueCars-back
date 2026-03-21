import cur
from flask import Flask, jsonify, request, Response, make_response
from flask_bcrypt import generate_password_hash, check_password_hash
import os
import datetime
import threading
import jwt
from function import verificar_senha, enviando_email, gerar_codigo
from main import app, con

# [ ] 1. AUTH/JWT: Adicionar token no /login, expirar em 10min e criar /logout.
# [ ] 2. SEGURANÇA: Bloquear login após 3 erros e criar /desbloquear (admin).
# [ ] 3. EMAIL: Exigir confirmação de e-mail p/ login (enviar no cadastro).
# [ ] 4. SENHAS: Proibir repetição das últimas 3 senhas (editar/recuperar).


if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/criar_usuario', methods=['POST'])
def criar_usuario():
    try:

        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        senha = request.form.get('senha')
        cpf = request.form.get('cpf')
        foto_prefil = request.files.get('foto_prefil')

        erro_senha = verificar_senha(senha)

        if not nome or not nome:
            return jsonify({'erro':'Esse campo e obrigatório.'}),400
        if not email or not senha:
            return jsonify({'erro': 'Email e senha são obrigatórios.'}), 400

        if erro_senha:
            return jsonify({'erro': erro_senha}), 400

        if foto_prefil:
            nome_imagem = f'{email}.jpg'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            foto_prefil.save(caminho_foto)

        senha_hash = generate_password_hash(senha)

        cur = con.cursor()
        cur.execute("""SELECT ID_USUARIO FROM USUARIO WHERE EMAIL = ? """, (email,))
        if cur.fetchone():
            return jsonify({'erro': 'Email já cadastrado.'}), 409

        cur.execute("""INSERT INTO USUARIO (NOME, EMAIL, TELEFONE, SENHA_HASH, CPF) VALUES (?, ?, ?, ?, ?)""",
                    (nome, email, telefone, senha_hash, cpf))

        con.commit()

        return jsonify({'mensagem': 'Usuário criado com sucesso!'}), 201

    except Exception as e:
        return jsonify({'erro': f'Erro ao criar: {e}'}), 500

    finally:
        if  cur:
            cur.close()


@app.route('/editar_usuario/<int:id_usuario>', methods=['POST'])
def editar_usuario(id_usuario):
    try:
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        senha = request.form.get('senha')
        cpf = request.form.get('cpf')
        foto_prefil = request.files.get('foto_prefil')

        cur = con.cursor()

        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_usuario,))
        if not cur.fetchone():
            return jsonify({'erro': 'Usuário não encontrado.'}), 404

        if senha:
            erro_senha = verificar_senha(senha)
            if erro_senha:
                return jsonify({'erro': erro_senha}), 400

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


        if foto_prefil:
            nome_imagem = f'perfil_{id_usuario}.jpg'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            foto_prefil.save(caminho_foto)

        con.commit()

        return jsonify({'mensagem': 'Usuario editado com sucesssssssssso!'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao editar: {e}'}), 500

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
        #if id_user:
         #   if check_password_hash(id_user[1],senha):

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
        if 'cur' in locals():
            cur.close()


@app.route('/enviar_email', methods=['POST'])
def enviar_email():
    dados = request.get_json()
    assunto = dados.get('assunto')
    destinatario = dados.get('destinatario')
    mensagem_texto = dados.get('mensagem')



    if not assunto or not destinatario or not mensagem_texto:
        return jsonify({'erro': 'Os campos assunto, mensagem e destinatario são obrigatórios.'}), 400


    template_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: black; padding: 20px; margin: 0;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

          <h2 style="color: #EF4444; text-align: center;">Estoque Cars</h2>

          <p style="font-size: 16px; color: #555555; line-height: 1.5;">
            {mensagem_texto}
          </p>

          <div style="text-align: center; margin-top: 20px;">
              <img src="" alt="Logo do site Estoque cars" style="max-width: 100%; border-radius: 8px;">
          </div>

          <hr style="border: none; border-top: 1px solid #eeeeee; margin: 30px 0;">

          <p style="font-size: 12px; color: #999999; text-align: center;">
            Atenciosamente,<br>Equipe Estoque Cars<br>
          </p>
        </div>
      </body>
    </html>
    """


    thread = threading.Thread(target=enviando_email, args=(destinatario, assunto, template_html))
    thread.start()

    return jsonify({'mensagem': 'E-mail adicionado à fila de envio com sucesso!'}), 200


@app.route('/codigo_vereficacao', methods=['POST'])
def codigo_vereficacao():
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
        template_html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background-color: black; padding: 20px; margin: 0;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">

                  <h2 style="color: #EF4444; text-align: center;">Estoque Cars</h2>

                  <p style="font-size: 16px; color: #555555; line-height: 1.5;">
                    Olá {nome}, seu códgio de repuração é {codigo}<br>
                  </p>

                  <div style="text-align: center; margin-top: 20px;">
                      <img src="" alt="Logo da empresa " style="max-width: 100%; border-radius: 8px;">
                  </div>

                  <hr style="border: none; border-top: 1px solid #eeeeee; margin: 30px 0;">

                  <p style="font-size: 12px; color: #999999; text-align: center;">
                    Atenciosamente,<br>Equipe Estoque Cars<br>
                  </p>
                </div>
              </body>
            </html>
            """
        assunto = "Recuperação de Senha - Estoque Cars"


        thread = threading.Thread(target=enviando_email, args=(email, assunto, template_html))
        thread.start()

        return jsonify({'mensagem': 'Código de recuperação enviado para o seu e-mail.'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao solicitar recuperação: {str(e)}'}), 500
    finally:
        if 'cur' in locals():
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

        cur.execute("""
            SELECT ID_RECUPERA 
            FROM RECUPERAR_SENHA 
            WHERE ID_USUARIO = ? AND CODIGO = ? AND USADO_EM IS NULL
        """, (id_usuario, codigo))

        recuperacao = cur.fetchone()

        if not recuperacao:
            return jsonify({'erro': 'Código inválido'}), 400

        id_recupera = recuperacao[0]

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
        if 'cur' in locals():
            cur.close()

@app.route('/listar_usuarios', methods=['GET'])
def listar_usuarios():
    try:
        cur = con.cursor()
        cur.execute("SELECT ID_USUARIO, NOME, EMAIL,CPF, TELEFONE FROM USUARIO")
        usuario = cur.fetchall()

        listar_usuario=[]
        for usuario in usuario:
            listar_usuarios.append({
                'id_usuario': usuario[0],
                'nome': usuario[1],
                'email': usuario[2],
                'telefone': usuario[3],
                'cpf': usuario[4]
            })
        return jsonify(listar_usuario), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar usuarios: {e}'}), 500
    finally:
        if cur:
            cur.close()

@app.route('/buscar_usuario/<int:id_usuario>', methods=['GET'])
def buscar_usuario(id_usuario):
    try:
        cur = con.cursor()
        cur.execute("SELECT ID_USUARIO,NOME,EMAIL,CPF,TELEFONE FROM USUARIO WHERE ID_USUARIO = ?",(id_usuario,))
        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro':'usuario nao encontrado'}), 404

        dados_usuarios = {
            'id_usuario': usuario[0],
            'nome': usuario[1],
            'email': usuario[2],
            'telefone': usuario[3],
            'cpf': usuario[4]
        }

        return jsonify(dados_usuarios), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao buscar usuario: {e}'}), 500
    finally:
        if cur:
            cur.close()

@app.route('/excluir_usuario/<int:id_usuario>', methods=['DELETE'])
def excluir_usuario(id_usuario):
    try:
        cur = con.cursor()

        cur.execute("SELECT ID_USUARIO FROM USUARIO WHERE ID_USUARIO= ?",(id_usuario,))
        if not  cur.fetchone():
            return jsonify({'erro': 'usuario nao encontrado'}), 404

        cur.execute("DELETE FROM USUARIO WHERE ID_USUARIO = ?",(id_usuario,))
        con.commit()

        #nome_imagem = f'perfil{id_usuario}.jpg'
        #caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
       # if not os.path.exists(caminho_foto):
        #    os.remove(caminho_foto)

        return jsonify({'messagem': 'Usuário removido com sucesso'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao excluir usuario: {e}'}), 500
    finally:
        if cur:
            cur.close()
