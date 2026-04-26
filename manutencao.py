from flask import  jsonify, request
from main import app,con
import datetime
from function import  recalcular_total_manutencao




@app.route('/cadastrar_manutencao', methods=['POST'])
def cadastrar_manutencao():
    cur = con.cursor()
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400

        id_veiculo = dados.get('id_veiculo')
        data_manutencao = dados.get('data_manutencao')
        servicos = dados.get('servicos')

        if not id_veiculo or not data_manutencao or not servicos:
            return jsonify({'erro': 'Todos os campos (id_veiculo, data_manutencao, servicos) são obrigatórios.'}), 400
        try:
            data_manutencao = datetime.datetime.strptime(data_manutencao, '%d/%m/%Y %H:%M')
            agora = datetime.datetime.now()
            #criaçao de limite de 1 ano
            limite_data = agora + datetime.timedelta(days=365)
            if data_manutencao < agora:
                return jsonify({'erro':'Por acaso a humanidade criou uma máquina do tempo para voltar para o passado?'}), 400
            if data_manutencao > limite_data:
                return jsonify({'erro':'data muito distante o agendamentio premitido e no maximo um ano '})
        except ValueError:
            return jsonify({
                               'erro': 'Formato de data inválido. Use o formato certo (DD/MM/YYYY HH:MM), a gente não tá nos Estados Unidos.'}), 400
        cur.execute("SELECT ID_VEICULO FROM VEICULO WHERE ID_VEICULO = ?", (id_veiculo,))
        if not cur.fetchone():
            return jsonify({'erro': 'Veículo não encontrado.'}), 404
        cur.execute("""
                    INSERT INTO MANUTENCAO (ID_VEICULO, DATA_MANUTENCAO, VALOR_TOTAL)
                    VALUES (?, ?, 0.00) RETURNING ID_MANUTENCAO
                    """, (id_veiculo, data_manutencao))
        id_manutencao = cur.fetchone()[0]
        valor_total_calculado = 0.0
        for item in servicos:
            id_servico = item.get('id_servico')
            quantidade = item.get('quantidade', 1)
            cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))
            servico = cur.fetchone()

            valor_cobrado = float(servico[0])
            subtotal = valor_cobrado * quantidade
            valor_total_calculado += subtotal

            cur.execute("""
                        INSERT INTO ITEM_MANUTENCAO (ID_MANUTENCAO, ID_SERVICO, VALOR_COBRADO, QUANTIDADE)
                        VALUES (?, ?, ?, ?)
                        """, (id_manutencao, id_servico, valor_cobrado, quantidade))
        cur.execute("UPDATE MANUTENCAO SET VALOR_TOTAL = ? WHERE ID_MANUTENCAO = ?",
                    (valor_total_calculado, id_manutencao))
        con.commit()
        return jsonify({
            'mensagem': 'Manutenção agendada com sucesso!',
            'id_manutencao': id_manutencao,
            'valor_total': valor_total_calculado
        }), 201

    except Exception as e:
        return jsonify({'erro': f'Erro au cadastrar_manutencao{e}'}), 500
    finally:
        cur.close()

@app.route('/editar_manutencao/<int:id_manutencao>', methods=['PUT'])
def editar_manutencao(id_manutencao):
    cur = con.cursor()
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro':'envie os dados em json'}), 400
        id_veiculo = dados.get('id_veiculo')
        data_manutencao = dados.get('data_manutencao')
        servico = dados.get('servico')

        if not id_veiculo or not data_manutencao or not servico:
            return jsonify({'erro':'Por favor todos os campos sao obrigatorios'}), 400

        cur.execute("""SELECT ID_MANUTECAO FROM MANUTENCAO WHERE ID_MANUTENCAO = ?""",(id_manutencao,))
        manutencao = cur.fetchone()

        if not manutencao:
            return jsonify({'erro':'manutencao nso encontrado'}), 404

        data_antiga = manutencao[0]
        agora = datetime.datetime.now()

        if data_antiga < agora:
            return jsonify({'erro':''}), 403

        try:
            data_nova = datetime.datetime.strptime(dados['data_nova'], '%d/%m/%Y  %H:%M')
            limite_futuro = agora + datetime.timedelta(days=365)

            if data_nova < agora:
                return jsonify({'erro':''}), 400

            if data_nova > limite_futuro:
                return jsonify({'erro':''}), 400
        except ValueError:
            return jsonify({'erro':''}), 400

        cur.execute("""UPDATE MANUTENCAO SET ID_VEICULO = ?, SERVICO = ? WHERE ID_MANUTENCAO = ?""",(id_veiculo,data_nova, id_manutencao))

        cur.execute("""DELETE FROM ITEM_MANUTENCAO WHERE ID_MANUTENCAO = ?""",(id_manutencao,))

        valor_total_calculado = 0.0

        for item in servico:
            id_servico = item.get('id_servico')
            quantidade = item.get('quantidade', 1)

            cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))
            servicos = cur.fetchone()

        if not servicos:
            return jsonify({'erro': f'Operação cancelada. Serviço de ID {id_servico} não existe.'}), 404

        valor_cobrado = float(servicos[0])
        subtotal = valor_cobrado * quantidade
        valor_total_calculado += subtotal

        cur.execute("""
                    INSERT INTO ITEM_MANUTENCAO (ID_MANUTENCAO, ID_SERVICO, VALOR_COBRADO, QUANTIDADE)
                    VALUES (?, ?, ?, ?)
                    """, (id_manutencao, id_servico, valor_cobrado, quantidade))

        cur.execute("UPDATE MANUTENCAO SET VALOR_TOTAL = ? WHERE ID_MANUTENCAO = ?",
                    (valor_total_calculado, id_manutencao))

        con.commit()

        return jsonify({
            'mensagem': 'Manutenção atualizada com sucesso!',
            'id_manutencao': id_manutencao,
            'novo_valor_total': valor_total_calculado
        }), 200
    except Exception as e:
        return {'erro': f'Erro ao editar a manutencao{e}'}, 500
    finally:
        cur.close()

@app.route('/deletar_manutencao/<int:id_manutencao>', methods=['DELETE'])
def deletar_manutencao(id_manutencao):
    cur = con.cursor()
    try:
        cur.execute("""SELECT DATA_MANUTENCAO FROM MANUTENCAO WHERE ID_MANUTENCAO = ?""",(id_manutencao,))
        manutecao = cur.fetchone()

        if not manutecao:
            return  jsonify({'erro':'nao foi possivel entrontar a Manutecao'}), 404
        data_agendada = manutecao[0]
        agora = datetime.datetime.now()

        if data_agendada < agora:
            return jsonify({'erro':'nao e possivel excluir o historico de uma manutencao que ja aconteceu.'}) , 403

        cur.execute("""DELETE FROM MANUTENCAO WHERE ID_MANUTENCAO = ?""",(id_manutencao,)),
        con.commit()

        return jsonify({'messagem':'agendamento de manutenção cancelado e excluído com sucesso!'}), 201
    except Exception as e:
        return jsonify({'erro':f'Erro ao deletar a manutencao {e}'}), 500
    finally:
        cur.close()


@app.route('/buscar_manutencao', methods=['POST'])
def buscar_manutencao():
    cur = con.cursor()
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400

        id_manutencao = dados.get('id_manutencao')
        id_veiculo = dados.get('id_veiculo')
        if id_manutencao:
            cur.execute("""
                        SELECT M.ID_MANUTENCAO, MA.MARCA, V.MODELO, V.PLACA, M.DATA_MANUTENCAO, M.VALOR_TOTAL
                        FROM MANUTENCAO M
                                 INNER JOIN VEICULO V ON M.ID_VEICULO = V.ID_VEICULO
                                 INNER JOIN MARCA MA ON V.ID_MARCA = MA.ID_MARCA
                        WHERE M.ID_MANUTENCAO = ?
                        """, (id_manutencao,))

        elif id_veiculo:
            cur.execute("""
                        SELECT M.ID_MANUTENCAO, MA.MARCA, V.MODELO, V.PLACA, M.DATA_MANUTENCAO, M.VALOR_TOTAL
                        FROM MANUTENCAO M
                                 INNER JOIN VEICULO V ON M.ID_VEICULO = V.ID_VEICULO
                                 INNER JOIN MARCA MA ON V.ID_MARCA = MA.ID_MARCA
                        WHERE M.ID_VEICULO = ?
                        ORDER BY M.DATA_MANUTENCAO DESC
                        """, (id_veiculo,))

        else:
            return jsonify({'erro': 'Informe id_manutencao ou id_veiculo para realizar a busca.'}), 400

        manutencoes = cur.fetchall()

        if not manutencoes:
            return jsonify({'erro': 'Nenhuma manutenção encontrada.'}), 404

        lista_final = []

        for m in manutencoes:
            id_manut = m[0]

            cur.execute("""
                        SELECT S.NOME_SERVICO, IM.QUANTIDADE, IM.VALOR_COBRADO
                        FROM ITEM_MANUTENCAO IM
                                 INNER JOIN SERVICO S ON IM.ID_SERVICO = S.ID_SERVICO
                        WHERE IM.ID_MANUTENCAO = ?
                        """, (id_manut,))

            itens = cur.fetchall()
            lista_servicos = []

            for item in itens:
                lista_servicos.append({
                    'servico': item[0],
                    'quantidade': item[1],
                    'valor_unitario': float(item[2]),
                    'subtotal': float(item[1] * item[2])
                })
            data_db = m[4]
            data_br = data_db.strftime('%d/%m/%Y %H:%M')

            lista_final.append({
                'id_manutencao': id_manut,
                'marca': m[1],
                'modelo': m[2],
                'placa': m[3],
                'data': data_br,
                'valor_total': float(m[5]),
                'servicos_realizados': lista_servicos
            })

        return jsonify(lista_final), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao buscar manutenção: {e}'}), 500
    finally:
        cur.close()


@app.route('/listar_manutencao', methods=['GET'])
def listar_manutencao():
    cur = con.cursor()
    try:
        cur.execute("""
                    SELECT M.ID_MANUTENCAO,
                           MA.MARCA,
                           V.MODELO,
                           V.PLACA,
                           M.DATA_MANUTENCAO,
                           M.VALOR_TOTAL
                    FROM MANUTENCAO M
                             INNER JOIN VEICULO V ON M.ID_VEICULO = V.ID_VEICULO
                             INNER JOIN MARCA MA ON V.ID_MARCA = MA.ID_MARCA
                    ORDER BY M.DATA_MANUTENCAO DESC
                    """)
        manutencoes = cur.fetchall()

        if not manutencoes:
            return jsonify({'messagem':'Nenhuma manutencao encontrada.'}), 404


        lista_final = []

        for m in manutencoes:
            id_manut = m[0]
            cur.execute("""
                        SELECT S.NOME_SERVICO, IM.QUANTIDADE, IM.VALOR_COBRADO
                        FROM ITEM_MANUTENCAO IM
                                 INNER JOIN SERVICO S ON IM.ID_SERVICO = S.ID_SERVICO
                        WHERE IM.ID_MANUTENCAO = ?
                        """, (id_manut,))

            itens = cur.fetchall()
            lista_servicos = []

            for item in itens:
                quantidade = item[1]
                valor_cobrado = float(item[2])
                subtotal = quantidade * valor_cobrado
                lista_servicos.append({
                    'servico': item[0],
                    'quantidade': quantidade,
                    'valor_unitario': valor_cobrado,
                    'subtotal': subtotal
                })
            data_br = m[4].strftime('%d/%m/%Y %H:%M')
            lista_final.append({
                'id_manutencao': id_manut,
                'marca': m[1],
                'modelo': m[2],
                'placa': m[3],
                'data': data_br,
                'valor_total': float(m[5]),
                'servicos_realizados': lista_servicos
            })
        return jsonify(lista_final), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar manutenções: {e}'}), 500
    finally:
        cur.close()

@app.route('/adicionar_item_manutencao', methods=['POST'])
def adicionar_item_manutencao():
    cur = con.cursor()
    try:
        dados = request.get_json()
        id_manutencao = dados['id_manutencao']
        id_servico = dados.get('id_servico')
        quantidade = dados.get('quantidade')

        if not id_manutencao and not id_servico:
            return jsonify({'erro':'compo obrigatorio'}), 400

        quantidade = int(quantidade)

        cur.execute("""SELECT DATA_MANUTENCAO 
                       FROM MANUTENCAO 
                       WHERE ID_MANUTENCAO = ?""",(id_manutencao,)),
        manutencao = cur.fetchone()

        if not manutencao:
            return jsonify({'erro':'manutencao nao encontrada'}), 400

        if manutencao[0] < datetime.datetime.now():
            return jsonify({'erro':'Não pode altera a manutencao no passado'}), 400

        cur.execute("""SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?""",(id_servico,)),
        servico = cur.fetchone()

        if not servico:
            return jsonify({'erro':'servico nao encontrado'}), 400

        valor = float(servico[0])

        cur.execute("""
                    INSERT INTO ITEM_MANUTENCAO
                        (ID_MANUTENCAO, ID_SERVICO, VALOR_COBRADO, QUANTIDADE)
                        
                    VALUES (?, ?, ?, ?)
                    """, (id_manutencao, id_servico, valor, quantidade))
        print('ola')

        print('passo')
        novo_total = recalcular_total_manutencao(id_manutencao,cur)
        print('passo2')

        con.commit()

        return jsonify({'mensagem':'Item adicionado com sucesso!',
                        'novo_total':novo_total}), 201

    except Exception as e:
        return jsonify({'erro':f'Erro ao adicionar a manutencao {e}'}), 500
    finally:
        cur.close()

@app.route('/editar_item_manutencao/<int:id_item>', methods=['PUT'])
def editar_item_manutencao(id_item):
    cur = con.cursor()
    try:
        dados = request.get_json()
        quantidade = dados.get('quantidade')

        if not quantidade:
            return jsonify({'erro': 'Quantidade é obrigatória'}), 400

        quantidade = int(quantidade)

        cur.execute("""
            SELECT ID_MANUTENCAO
            FROM ITEM_MANUTENCAO
            WHERE ID_ITEM = ?
        """, (id_item,))

        item = cur.fetchone()

        if not item:
            return jsonify({'erro': 'Item não encontrado'}), 404

        id_manutencao = item[0]

        cur.execute("""
            SELECT DATA_MANUTENCAO
            FROM MANUTENCAO
            WHERE ID_MANUTENCAO = ?
        """, (id_manutencao,))

        manutencao = cur.fetchone()

        if manutencao[0] < datetime.datetime.now():
            return jsonify({'erro': 'Não pode editar item de manutenção passada'}), 403

        cur.execute("""
            UPDATE ITEM_MANUTENCAO
            SET QUANTIDADE = ?
            WHERE ID_ITEM = ?
        """, (quantidade, id_item))

        novo_total = recalcular_total_manutencao(id_manutencao, cur)

        con.commit()

        return jsonify({
            'mensagem': 'Item atualizado com sucesso!',
            'novo_total': novo_total
        }), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao editar item manutenção: {e}'}), 500
    finally:
        cur.close()

@app.route('/excluir_item_manutencao/<int:id_item>', methods=['DELETE'])
def excluir_item_manutencao(id_item):
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT ID_MANUTENCAO 
            FROM ITEM_MANUTENCAO 
            WHERE ID_ITEM = ?
        """, (id_item,))

        item = cur.fetchone()

        if not item:
            return jsonify({'erro': 'Item não encontrado'}), 404

        id_manutencao = item[0]

        cur.execute("""
            SELECT DATA_MANUTENCAO 
            FROM MANUTENCAO 
            WHERE ID_MANUTENCAO = ?
        """, (id_manutencao,))

        data = cur.fetchone()

        if not data:
            return jsonify({'erro': 'Manutenção não encontrada'}), 404

        if data[0] < datetime.datetime.now():
            return jsonify({'erro': 'Não pode excluir item de manutenção passada'}), 403

        cur.execute("""
            DELETE FROM ITEM_MANUTENCAO 
            WHERE ID_ITEM = ?
        """, (id_item,))

        novo_total = recalcular_total_manutencao(id_manutencao, cur)

        con.commit()

        return jsonify({
            'mensagem': 'Item excluído com sucesso!',
            'novo_total': novo_total
        }), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao excluir item manutenção: {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_item_manutencao/<int:id_manutencao>', methods=['GET'])
def listar_item_manutencao(id_manutencao):
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT ID_MANUTENCAO 
            FROM MANUTENCAO 
            WHERE ID_MANUTENCAO = ?
        """, (id_manutencao,))

        if not cur.fetchone():
            return jsonify({'erro': 'Manutenção não encontrada'}), 404

        cur.execute("""
            SELECT 
                IM.ID_ITEM,
                IM.ID_MANUTENCAO,
                IM.ID_SERVICO,
                S.NOME_SERVICO,
                IM.QUANTIDADE,
                IM.VALOR_COBRADO
            FROM ITEM_MANUTENCAO IM
            INNER JOIN SERVICO S ON IM.ID_SERVICO = S.ID_SERVICO
            
            WHERE IM.ID_MANUTENCAO = ?
            ORDER BY IM.ID_ITEM
        """, (id_manutencao,))

        itens = cur.fetchall()

        if not itens:
            return jsonify({'mensagem': 'Nenhum item foi encontrado'}), 404

        lista_itens = []

        for item in itens:
            quantidade = int(item[4])
            valor_unitario = float(item[5])
            total = quantidade * valor_unitario

            lista_itens.append({
                'id_item': item[0],
                'id_manutencao': item[1],
                'id_servico': item[2],
                'nome_servico': item[3],
                'quantidade': quantidade,
                'valor_unitario': valor_unitario,
                'total': total
            })

        return jsonify({'itens': lista_itens}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao listar item manutencao {e}'}), 500
    finally:
        cur.close()