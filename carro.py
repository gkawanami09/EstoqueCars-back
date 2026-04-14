from main import app, con
from flask import request, jsonify
import jwt
import os

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


@app.route('/cadastrar_carro', methods=['POST'])
def cadastrar_carro():
    cur = con.cursor()
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_adm = payload['id_user']
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))
        usuarios = cur.fetchone()
        if not usuarios or usuarios[0] != 2:
            return jsonify({'erro': 'Acesso restrito. Apenas Administradores pode acessar'}), 403

        id_categoria = request.form.get('id_categoria')
        id_marca = request.form.get('id_marca')
        modelo = request.form.get('modelo')
        ano_fabricacao = request.form.get('ano_fabricacao')
        ano_modelo = request.form.get('ano_modelo')
        quilometragem = request.form.get('quilometragem')
        cor = request.form.get('cor')
        cambio = request.form.get('cambio')
        preco = request.form.get('preco')
        descricao = request.form.get('descricao')
        estado_conservacao = request.form.get('estado_conservacao')
        status_documento = request.form.get('status_documento')
        status_estoque = request.form.get('status_estoque')
        placa = request.form.get('placa')
        renavam = request.form.get('renavam')
        foto_veiculo = request.files.get('foto_veiculo')

        if not all([id_categoria,id_marca,modelo,ano_fabricacao,ano_modelo,preco,placa,renavam]):
            return jsonify({'erro':'Preencha todos os campos obrigatórios.'}),400
        if len(str(renavam)) != 11:
            return jsonify({'erro':'O RENAVAM deve conter 11 dígitos.'}), 400

        cur.execute("SELECT PLACA, RENAVAM FROM VEICULO WHERE PLACA = ? OR RENAVAM = ?",(placa,renavam))
        conflito = cur.fetchone()
        if conflito:
            if conflito[0] == placa:
                return jsonify({'erro':'Placa já cadastrada'}),409
            if conflito[1] == renavam:
                return jsonify({'erro':'Renavam já cadastrado'}),409

        cur.execute("""
                    INSERT INTO VEICULO (ID_CATEGORIA, ID_MARCA, MODELO, ANO_FABRICACAO, ANO_MODELO,
                                         QUILOMETRAGEM, COR, CAMBIO, PRECO, DESCRICAO,
                                         ESTADO_CONSERVACAO, STATUS_DOCUMENTO, STATUS_ESTOQUE, PLACA, RENAVAM)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                            ?) RETURNING ID_VEICULO 
                     """, (
                        id_categoria, id_marca, modelo, ano_fabricacao, ano_modelo,
                        quilometragem, cor, cambio, preco, descricao,
                        estado_conservacao, status_documento, status_estoque, placa, renavam
                    ))

        resultado_id = cur.fetchone()
        id_veiculo = resultado_id[0]

        if foto_veiculo:
            nome_imagem = f'veico_{id_veiculo}.png'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            foto_veiculo.save(caminho_foto)

        con.commit()
        return jsonify({'mensagem': 'Carro cadastrado com sucesso!'}), 201

    except jwt.ExpiredSignatureError:
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"erro": "Token inválido ou adulterado."}), 401
    except Exception as e:
        con.rollback()
        return jsonify({'erro': f'Erro ao cadastrar carro: {e}'}), 500
    finally:
        cur.close()

@app.route('/editar_carro/<int:id_veiculo>', methods=['PUT'])
def editar_carro(id_veiculo):
    cur = con.cursor()
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({'erro': 'Acesso negado. Token não encontrado.'}), 401

    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_adm = payload['id_user']

        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO = ?", (id_adm,))
        usuarios = cur.fetchone()
        if not usuarios or usuarios[0] != 2:
            return jsonify({'erro': 'Acesso restrito. Apenas Administradores podem acessar.'}), 403


        cur.execute("SELECT ID_VEICULO FROM VEICULO WHERE ID_VEICULO = ?", (id_veiculo,))
        if not cur.fetchone():
            return jsonify({'erro': 'Carro não encontrado.'}), 404

        id_categoria = request.form.get('id_categoria')
        id_marca = request.form.get('id_marca')
        modelo = request.form.get('modelo')
        ano_fabricacao = request.form.get('ano_fabricacao')
        ano_modelo = request.form.get('ano_modelo')
        quilometragem = request.form.get('quilometragem')
        cor = request.form.get('cor')
        cambio = request.form.get('cambio')
        preco = request.form.get('preco')
        descricao = request.form.get('descricao')
        estado_conservacao = request.form.get('estado_conservacao')
        status_documento = request.form.get('status_documento')
        status_estoque = request.form.get('status_estoque')
        placa = request.form.get('placa')
        renavam = request.form.get('renavam')
        foto_veiculo = request.files.get('foto_veiculo')

        if not all([id_categoria,id_marca,modelo,ano_fabricacao,ano_modelo,preco,placa,renavam]):
            return jsonify({'erro':'Preencha todos os campos obrigatórios.'}),400
        if len(str(renavam)) != 11:
            return jsonify({'erro':'O RENAVAM deve conter 11 dígitos.'}), 400

        cur.execute("SELECT PLACA, RENAVAM FROM VEICULO WHERE (PLACA = ? OR RENAVAM = ?) AND ID_VEICULO != ?", (placa, renavam, id_veiculo))
        conflito = cur.fetchone()
        if conflito:
            if conflito[0] == placa:
                return jsonify({'erro':'Placa já cadastrada em outro veículo.'}),409
            if conflito[1] == renavam:
                return jsonify({'erro':'Renavam já cadastrado em outro veículo.'}),409

        cur.execute("""
            UPDATE VEICULO SET 
                ID_CATEGORIA = ?, ID_MARCA = ?, MODELO = ?, ANO_FABRICACAO = ?, ANO_MODELO = ?, 
                QUILOMETRAGEM = ?, COR = ?, CAMBIO = ?, PRECO = ?, DESCRICAO = ?, 
                ESTADO_CONSERVACAO = ?, STATUS_DOCUMENTO = ?, STATUS_ESTOQUE = ?, PLACA = ?, RENAVAM = ?
            WHERE ID_VEICULO = ?
        """, (
            id_categoria, id_marca, modelo, ano_fabricacao, ano_modelo,
            quilometragem, cor, cambio, preco, descricao,
            estado_conservacao, status_documento, status_estoque, placa, renavam,
            id_veiculo
        ))

        if foto_veiculo:
            nome_imagem = f'veico_{id_veiculo}.png'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            foto_veiculo.save(caminho_foto)

        con.commit()
        return jsonify({'mensagem': 'Carro atualizado com sucesso!'}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"erro": "Token inválido ou adulterado."}), 401
    except Exception as e:
        return jsonify({'erro': f'Erro ao editar carro: {e}'}), 500
    finally:
        cur.close()


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
        
        cur.execute('DELETE FROM MARCA WHERE ID_MARCA = ?', (id_marca,))
        con.commit()
        return jsonify({'mensagem':'Marca deletada com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao deletar marca: {e}'}), 500
    finally:
        cur.close()