from main import app, con
from flask import jsonify, request
from main import app
import datetime, os

#PIP INSTALL pixqrcode



@app.route('/cadastrar_venda', methods=['POST'])
def cadastrar_venda():
    cur = con.cursor()
    try:
        dados = request.form

        id_usuario = dados.get('id_usuario')
        id_veiculo = dados.get('id_veiculo')
        forma_pagamento = dados.get('forma_pagamento')
        data_venda = dados.get('data_venda')
        valor_venda = dados.get('valor_venda')
        valor_recebido = dados.get('valor_recebido')
        status_pagamento = dados.get('status_pagamento')
        comentarios = dados.get('comentarios')
        desconto = dados.get('desconto', 0)
        
        comprovante = request.files.get('comprovante')
        
        if (
            not id_usuario or
            not id_veiculo or
            not forma_pagamento or
            not data_venda or
            not valor_venda or
            not valor_recebido or
            not status_pagamento
        ):
            return jsonify({'erro': 'Todos os campos obrigatórios devem estar preenchidos'}), 400

        forma_pagamento = int(forma_pagamento)
        valor_venda = float(valor_venda)
        valor_recebido = float(valor_recebido)
        desconto = float(desconto)
        
        
        if desconto > 10:
            return jsonify({'erro' : 'Seu desconto está muito alto, ele pode ser até 10%'})
        if desconto < 0:
            return jsonify({'erro' : 'O desconto deve ser maior ou igual à 0'})
        
        
        data_venda = datetime.datetime.strptime(data_venda, '%d/%m/%Y %H:%M')
        
        cur.execute(
            """
            SELECT ID_VEICULO, STATUS_ESTOQUE
            FROM VEICULO
            WHERE ID_VEICULO = ?
            """, (id_veiculo,)   
        )
        veiculo = cur.fetchone()
        
        if not veiculo:
            return jsonify({'erro' : 'Veículo não encontrado'})
        status = veiculo[1]
        
        if status == 2:
            return jsonify({'erro' : 'Este veículo já foi vendido.'})
        
        if status == 3:
            return jsonify({'erro' : 'Este veículo esta indisponível no momento.'})
        
        cur.execute(
            """
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?     
            """, (id_usuario,)
        )
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({'error' : 'Usuário não encontrado'})
        
        if comprovante:
            nome_imagem = f'comprovante_{id_veiculo}.png'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            comprovante.save(caminho_foto)
        
        cur.execute(
        """
        INSERT INTO VENDA(ID_USUARIO,
                          ID_VEICULO,
                          FORMA_PAGAMENTO,
                          DATA_VENDA,
                          VALOR_VENDA,
                          VALOR_RECEBIDO,
                          STATUS_PAGAMENTO,
                          COMENTARIOS,
                          DESCONTOS)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING ID_VENDA   
        """, (id_usuario, id_veiculo, forma_pagamento, data_venda, valor_venda, valor_recebido, status_pagamento, comentarios, desconto))
        
        id_venda = cur.fetchone()[0]
        cur.execute(
        """
        UPDATE VEICULO 
        SET STATUS_ESTOQUE = 2
        WHERE ID_VEICULO = ?    
        """, (id_veiculo,)
        )    
        
        
        if forma_pagamento == 1:
            valor_parcela = float(dados.get('valor_parcelado'))
            quantidade_parcelas = int(dados.get('quantidade_parcelas'))
            valor_total_parcelado = valor_parcela * quantidade_parcelas
            cur.execute(
            """
             EXECUTE PROCEDURE pr_insere_parcelas(?, ?, ?, ?)
            """, (valor_parcela, quantidade_parcelas, valor_total_parcelado, id_venda))
        
            con.commit()
        
        return jsonify({'mensagem' : 'Venda cadastrada com sucesso'}), 201
    except Exception as e:
        return jsonify({'erro' : f'Erro ao cadastrar veículo {e}'}), 500
    finally:
        cur.close()
        

@app.route('/listar_venda', methods=['GET'])
def listar_venda():
    return jsonify({'mensagem':'listar_venda em desenvolvimento'})

@app.route('/editar_venda', methods=['PUT'])
def editar_venda():
    return jsonify({'mensagem':'editar venda em desenvolvimento'})

@app.route('/deletar_venda', methods=['DELETE'])
def deletar_venda():
    return jsonify({'mensagem': 'deletar venda em desenvolvimento'})