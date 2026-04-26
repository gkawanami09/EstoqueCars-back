from flask import  jsonify, request
import jwt
from main import app,con



@app.route('/cadastrar_marca', methods=['POST'])
def cadastrar_marca():
    cur = con.cursor()
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({'erro':'Acesso negado. Token não econtrado.'}),401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_adm = payload['id_user']

        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))
        usuarios = cur.fetchone()

        if not usuarios or usuarios[0] != 2:
            return jsonify({'erro': 'Acesso restrito. Apenas Administradores pode acessar'}), 403


        marca = request.form.get('marca')
        if not marca or marca.strip() == "":
            return jsonify({'erro': 'O nome da marca é obrigatório.'}), 400

        nome_marca = marca.strip().upper()


        cur.execute("SELECT ID_MARCA FROM MARCA WHERE LOWER(MARCA) = LOWER(?)", (nome_marca,))
        if cur.fetchone():
            return jsonify({'erro': 'Essa marca já foi cadastrada.'}), 409


        cur.execute("INSERT INTO MARCA (MARCA) VALUES (?)", (nome_marca,))
        con.commit()

        return jsonify({'mensagem': 'Marca cadastrada com sucesso!'}), 201

    except jwt.ExpiredSignatureError:
        return jsonify({"erro": "Sessão expirada."}), 401
    except Exception as e:
        con.rollback()
        return jsonify({'erro': f'Erro ao cadastrar: {e}'}), 500
    finally:
        cur.close()

@app.route('/editar_marca/<int:id_marca>',methods=['PUT'])
def editar_marca(id_marca):
    cur = con.cursor()
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({'erro':'Acesso negado. Token não econtrado.'}),401
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_adm = payload['id_user']
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))

        usuarios = cur.fetchone()

        if not usuarios or usuarios[0] != 2:
            return jsonify({'erro': 'Acesso restrito. Apenas Administradores pode acessar'}), 403

        nova_marca = request.form.get('nova_marca')
        if not nova_marca:
            return jsonify({'erro':'o nome da marca e obrigatorio'}),400
        cur.execute("UPDATE MARCA SET MARCA = ? WHERE ID_MARCA = ?",(nova_marca.strip().upper(),id_marca))
        con.commit()

        return jsonify({'mensagem': 'Marca editada com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao editar marca: {e}'}), 500
    finally:
        cur.close()

@app.route('/deletar_marca/<int:id_marca>',methods=['DELETE'])
def deletar_marca(id_marca):
    cur = con.cursor()


    try:


        cur.execute("""SELECT ID_VEICULO FROM VEICULO WHERE ID_VEICULO = ?""",(id_marca,))
        if cur.fetchone():
            return jsonify({'erro':'operacao bloaqueada'}),409

        cur.execute('DELETE FROM MARCA WHERE ID_MARCA = ?', (id_marca,))
        con.commit()
        return jsonify({'mensagem':'Marca deletada com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao deletar marca: {e}'}), 500
    finally:
        cur.close()

@app.route('/buscar_marca',methods=['POST'])
def buscar_marca():
    cur = con.cursor()
    try:
        nome = request.form.get('nome')
        id_marca = request.form.get('id_marca')
        listar_marcas = []
        if nome:
            nome_formatado = nome.strip().upper()

            cur.execute(""" SELECT ID_MARCA, MARCA FROM MARCA WHERE UPPER(MARCA) LIKE ?""", (f'%{nome_formatado}%',))
        elif id_marca:
            cur.execute("""SELECT ID_MARCA, MARCA FROM MARCA WHERE ID_MARCA = ?""",(id_marca,))
        else:
            cur.execute("""SELECT ID_MARCA, MARCA FROM MARCA""")
        marcas = cur.fetchall()

        for marca in marcas:
            listar_marcas.append({
                'id_marca': marca[0],
                'nome': marca[1],
            })
        if not listar_marcas:
            return jsonify({'erro':'Nehuma marca encontrafa co  esse filtro'}), 404

        return jsonify({'marca': listar_marcas}), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao buscar marca: {e}'}), 500
    finally:
        cur.close()
