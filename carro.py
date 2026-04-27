from main import app, con
from flask import request, jsonify
from validate_docbr import RENAVAM
import jwt
import os

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


renavam_validacao = RENAVAM()
#novo_renavam = renavam_validacao.generate()
#print(novo_renavam)

@app.route('/cadastrar_carro', methods=['POST'])
def cadastrar_carro():
    cur = con.cursor()


    try:


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

        if not all([id_categoria,id_marca,modelo,ano_fabricacao,ano_modelo,preco,placa,]):
            return jsonify({'erro':'Preencha todos os campos obrigatórios.'}),400
        print('renavam')
        if not renavam_validacao.validate(renavam):
            return jsonify({'erro':'RENAVAM inválido'}),400
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


    try:

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
        if not renavam_validacao.validate(renavam):
            return jsonify({'erro': 'RENAVAM inválido'}), 400
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
@app.route('/excluir_carro/<int:id_veiculo>', methods=['DELETE'])
def excluir_carro(id_veiculo):
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_MANUTENCAO FROM MANUTENCAO WHERE ID_VEICULO = ?", (id_veiculo,))
        if cur.fetchone():
            return jsonify({'erro': 'Operação bloqueada: Este veículo possui manutenções vinculadas.'}), 409

        cur.execute("DELETE FROM VEICULO WHERE ID_VEICULO = ?", (id_veiculo,))
        con.commit()

        nome_imagem = f'veico_{id_veiculo}.png'
        caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
        if os.path.isfile(caminho_foto):
            os.remove(caminho_foto)

        return jsonify({'mensagem': 'Carro excluído com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao excluir carro {e}'}), 500
    finally:
        cur.close()


@app.route('/listar_carro', methods=['GET'])
def listar_carro():
    cur = con.cursor()

    categoria = request.args.get('categoria')
    marca = request.args.get('marca')
    modelo = request.args.get('modelo')
    ano = request.args.get('ano')

    query = """
        SELECT
            V.ID_VEICULO,
            M.MARCA,
            V.MODELO,
            V.ANO_MODELO,
            V.COR,
            V.CAMBIO,
            V.PRECO,
            C.NOME_CATEGORIA
        FROM VEICULO V
        INNER JOIN MARCA M ON V.ID_MARCA = M.ID_MARCA
        INNER JOIN CATEGORIA C ON V.ID_CATEGORIA = C.ID_CATEGORIA
        WHERE 1=1
    """
    filtros = []

    if categoria:
        query += " AND UPPER(C.NOME_CATEGORIA) = UPPER(?)"
        filtros.append(categoria)
    if marca:
        query += " AND M.MARCA LIKE ?"
        filtros.append(f"%{marca}%")
    if modelo:
        query += " AND V.MODELO LIKE ?"
        filtros.append(f"%{modelo}%")
    if ano:
        query += " AND V.ANO_FABRICACAO = ?"
        filtros.append(ano)

    try:
        cur.execute(query, tuple(filtros))
        rows = cur.fetchall()

        carros = []
        for r in rows:
            id_veiculo = r[0]
            carros.append({
                "id": id_veiculo,
                "nome": f"{r[1]} {r[2]}",
                "modelo": r[2],
                "cor": r[4],
                "cambio": r[5],
                "preco": float(r[6]),
                "categoria": r[7],
                "imagem": f"/uploads/veico_{id_veiculo}.png"
            })

        return jsonify({"carros": carros}), 200

    except Exception as e:
        return jsonify({"erro": f"Erro ao listar carros: {e}"}), 500
    finally:
        cur.close()
