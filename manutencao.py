from flask import jsonify, request  # Importa recursos para responder JSON e ler dados da requisicao.
from main import app, con  # Importa a aplicacao Flask e a conexao com o banco.
import jwt  # Importa a biblioteca usada para tratar erros de token JWT.
import datetime  # Importa recursos para trabalhar com datas e horarios.
from function import recalcular_total_manutencao  # Importa a funcao que recalcula o total da manutencao.


@app.route('/cadastrar_manutencao', methods=['POST'])
def cadastrar_manutencao():
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    try:
        # Lê os dados enviados em JSON.
        dados = request.get_json()

        # Verifica se o corpo da requisicao veio vazio.
        if not dados:
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400

        # Recupera o id do veiculo.
        id_veiculo = dados.get('id_veiculo')

        # Recupera a data da manutencao.
        data_manutencao = dados.get('data_manutencao')

        # Recupera a lista de servicos da manutencao.
        servicos = dados.get('servicos')

        # Verifica se todos os campos obrigatorios vieram.
        if not id_veiculo or not data_manutencao or not servicos:
            return jsonify({
                'erro': 'Todos os campos (id_veiculo, data_manutencao, servicos) são obrigatórios.'
            }), 400

        try:
            # Converte a data recebida para datetime.
            data_manutencao = datetime.datetime.strptime(data_manutencao, '%d/%m/%Y %H:%M')

            # Guarda a data e hora atual.
            agora = datetime.datetime.now()

            # Calcula a data maxima permitida para agendamento.
            limite_data = agora + datetime.timedelta(days=365)

            # Verifica se a data informada esta no passado.
            if data_manutencao < agora:
                return jsonify({
                    'erro': 'Por acaso a humanidade criou uma máquina do tempo para voltar para o passado?'
                }), 400

            # Verifica se a data ultrapassa o limite permitido.
            if data_manutencao > limite_data:
                return jsonify({
                    'erro': 'Data muito distante, o agendamento permitido é no máximo um ano.'
                })

        except ValueError:
            # Retorna erro quando a data nao esta no formato esperado.
            return jsonify({'erro': 'Formato de data inválido. Use o formato (DD/MM/YYYY HH:MM).'}), 400

        # Busca o veiculo informado.
        cur.execute(  # Consulta se o veiculo informado existe.
            """
            SELECT ID_VEICULO -- Seleciona o id do veiculo.
            FROM VEICULO -- Define a tabela de veiculos.
            WHERE ID_VEICULO = ? -- Filtra pelo id do veiculo informado.
            """,
            (id_veiculo,)
        )

        # Verifica se o veiculo nao existe.
        if not cur.fetchone():
            return jsonify({'erro': 'Veículo não encontrado.'}), 404

        # Cadastra a manutencao com valor inicial zerado.
        cur.execute(  # Insere a manutencao e retorna o id gerado.
            """
            INSERT INTO MANUTENCAO ( -- Insere um novo registro na tabela de manutencao.
                ID_VEICULO, -- Informa o veiculo da manutencao.
                DATA_MANUTENCAO, -- Informa a data agendada.
                VALOR_TOTAL -- Informa o valor total inicial.
            )
            VALUES (?, ?, 0.00) -- Define os valores que serao gravados.
            RETURNING ID_MANUTENCAO -- Retorna o id gerado pela insercao.
            """,
            (id_veiculo, data_manutencao)
        )

        # Recupera o id da manutencao criada.
        id_manutencao = cur.fetchone()[0]

        # Inicia o total calculado da manutencao.
        valor_total_calculado = 0.0

        # Percorre cada servico recebido.
        for item in servicos:
            # Recupera o id do servico do item.
            id_servico = item.get('id_servico')

            # Recupera a quantidade ou usa 1 como padrao.
            quantidade = item.get('quantidade', 1)

            # Busca o valor atual do servico.
            cur.execute(  # Consulta o valor atual do servico.
                """
                SELECT VALOR -- Seleciona o valor atual do servico.
                FROM SERVICO -- Define a tabela de servicos.
                WHERE ID_SERVICO = ? -- Filtra pelo id do servico informado.
                """,
                (id_servico,)
            )

            # Recupera o servico encontrado.
            servico = cur.fetchone()

            # Converte o valor do servico para float.
            valor_cobrado = float(servico[0])

            # Calcula o subtotal do item.
            subtotal = valor_cobrado * quantidade

            # Soma o subtotal ao valor total.
            valor_total_calculado += subtotal

            # Insere o item da manutencao.
            cur.execute(  # Insere o servico como item da manutencao.
                """
                INSERT INTO ITEM_MANUTENCAO ( -- Insere um item na manutencao.
                    ID_MANUTENCAO, -- Informa a manutencao ligada ao item.
                    ID_SERVICO, -- Informa o servico realizado.
                    VALOR_COBRADO, -- Informa o valor cobrado no momento.
                    QUANTIDADE -- Informa a quantidade do servico.
                )
                VALUES (?, ?, ?, ?) -- Define os valores que serao gravados.
                """,
                (id_manutencao, id_servico, valor_cobrado, quantidade)
            )

        # Atualiza o valor total da manutencao.
        cur.execute(  # Atualiza o valor total da manutencao cadastrada.
            """
            UPDATE MANUTENCAO -- Define a tabela que sera atualizada.
            SET VALOR_TOTAL = ? -- Atualiza o valor total da manutencao.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao cadastrada.
            """,
            (valor_total_calculado, id_manutencao)
        )

        # Confirma o cadastro no banco.
        con.commit()

        # Retorna os dados da manutencao criada.
        return jsonify({
            'mensagem': 'Manutenção agendada com sucesso!',
            'id_manutencao': id_manutencao,
            'valor_total': valor_total_calculado
        }), 201

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao cadastrar manutenção: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/editar_manutencao/<int:id_manutencao>', methods=['PUT'])
def editar_manutencao(id_manutencao):
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    try:
        # Lê os dados enviados em JSON.
        dados = request.get_json()

        # Verifica se o corpo JSON veio vazio.
        if not dados:
            return jsonify({'erro': 'Envie os dados em json'}), 400

        # Recupera o id do veiculo.
        id_veiculo = dados.get('id_veiculo')

        # Recupera a data enviada.
        data_manutencao = dados.get('data_manutencao')

        # Recupera a lista de servicos enviada.
        servico = dados.get('servico')

        # Verifica se todos os campos obrigatorios vieram.
        if not id_veiculo or not data_manutencao or not servico:
            return jsonify({'erro': 'Por favor todos os campos sao obrigatorios'}), 400

        # Busca a data atual da manutencao.
        cur.execute(  # Consulta a data atual da manutencao.
            """
            SELECT DATA_MANUTENCAO -- Seleciona a data agendada da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pelo id da manutencao.
            """,
            (id_manutencao,)
        )

        # Recupera a manutencao encontrada.
        manutencao = cur.fetchone()

        # Verifica se a manutencao nao existe.
        if not manutencao:
            return jsonify({'erro': 'Manutenção não encontrada'}), 404

        # Guarda a data antiga da manutencao.
        data_antiga = manutencao[0]

        # Guarda a data e hora atual.
        agora = datetime.datetime.now()

        # Bloqueia edicao de manutencao passada.
        if data_antiga < agora:
            return jsonify({'erro': 'Não é possível editar uma manutenção que já ocorreu.'}), 403

        try:
            # Converte a nova data para datetime.
            data_nova = datetime.datetime.strptime(dados['data_nova'], '%d/%m/%Y  %H:%M')

            # Calcula o limite maximo de 1 ano.
            limite_futuro = agora + datetime.timedelta(days=365)

            # Verifica se a nova data esta no passado.
            if data_nova < agora:
                return jsonify({'erro': 'A nova data não pode ser no passado.'}), 400

            # Verifica se a nova data passa de 1 ano.
            if data_nova > limite_futuro:
                return jsonify({'erro': 'A nova data não pode ser mais de um ano no futuro.'}), 400

        except ValueError:
            # Retorna erro quando o formato da data e invalido.
            return jsonify({'erro': 'Formato de data inválido. Use DD/MM/YYYY HH:MM.'}), 400

        # Atualiza veiculo e data da manutencao.
        cur.execute(  # Atualiza veiculo e data da manutencao.
            """
            UPDATE MANUTENCAO -- Define a tabela que sera atualizada.
            SET ID_VEICULO = ?, -- Atualiza o veiculo da manutencao.
                DATA_MANUTENCAO = ? -- Atualiza a data da manutencao.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao informada.
            """,
            (id_veiculo, data_nova, id_manutencao)
        )

        # Remove os itens antigos da manutencao.
        cur.execute(  # Remove os itens antigos da manutencao.
            """
            DELETE -- Remove registros da tabela.
            FROM ITEM_MANUTENCAO -- Define a tabela dos itens de manutencao.
            WHERE ID_MANUTENCAO = ? -- Filtra pelos itens da manutencao informada.
            """,
            (id_manutencao,)
        )

        # Reinicia o total calculado.
        valor_total_calculado = 0.0

        # Percorre os novos itens de servico.
        for item in servico:
            # Recupera o id do servico.
            id_servico = item.get('id_servico')

            # Recupera a quantidade ou usa 1.
            quantidade = item.get('quantidade', 1)

            # Busca o valor do servico.
            cur.execute(  # Consulta o valor do servico informado.
                """
                SELECT VALOR -- Seleciona o valor atual do servico.
                FROM SERVICO -- Define a tabela de servicos.
                WHERE ID_SERVICO = ? -- Filtra pelo id do servico informado.
                """,
                (id_servico,)
            )

            # Recupera o servico encontrado.
            servicos = cur.fetchone()

            # Verifica se o servico nao existe.
            if not servicos:
                return jsonify({'erro': f'Serviço de ID {id_servico} não existe.'}), 404

            # Converte o valor cobrado para float.
            valor_cobrado = float(servicos[0])

            # Calcula o subtotal do item.
            subtotal = valor_cobrado * quantidade

            # Soma o subtotal ao total.
            valor_total_calculado += subtotal

            # Insere o novo item da manutencao.
            cur.execute(  # Insere o novo item da manutencao editada.
                """
                INSERT INTO ITEM_MANUTENCAO ( -- Insere um novo item na manutencao.
                    ID_MANUTENCAO, -- Informa a manutencao ligada ao item.
                    ID_SERVICO, -- Informa o servico do item.
                    VALOR_COBRADO, -- Informa o valor cobrado pelo servico.
                    QUANTIDADE -- Informa a quantidade do servico.
                )
                VALUES (?, ?, ?, ?) -- Define os valores que serao gravados.
                """,
                (id_manutencao, id_servico, valor_cobrado, quantidade)
            )

        # Atualiza o valor total da manutencao.
        cur.execute(  # Atualiza o valor total apos editar os itens.
            """
            UPDATE MANUTENCAO -- Define a tabela que sera atualizada.
            SET VALOR_TOTAL = ? -- Atualiza o valor total recalculado.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao editada.
            """,
            (valor_total_calculado, id_manutencao)
        )

        # Confirma a edicao no banco.
        con.commit()

        # Retorna os dados atualizados.
        return jsonify({
            'mensagem': 'Manutenção atualizada com sucesso!',
            'id_manutencao': id_manutencao,
            'novo_valor_total': valor_total_calculado
        }), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return {'erro': f'Erro ao editar a manutenção: {e}'}, 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/deletar_manutencao/<int:id_manutencao>', methods=['DELETE'])
def deletar_manutencao(id_manutencao):
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    try:
        # Busca a data da manutencao.
        cur.execute(  # Consulta a data da manutencao antes de excluir.
            """
            SELECT DATA_MANUTENCAO -- Seleciona a data agendada da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao informada.
            """,
            (id_manutencao,)
        )

        # Recupera a manutencao encontrada.
        manutecao = cur.fetchone()

        # Verifica se a manutencao nao existe.
        if not manutecao:
            return jsonify({'erro': 'Não foi possível encontrar a manutenção'}), 404

        # Guarda a data agendada.
        data_agendada = manutecao[0]

        # Bloqueia exclusao de historico ja ocorrido.
        if data_agendada < datetime.datetime.now():
            return jsonify({'erro': 'Não é possível excluir o histórico de uma manutenção que já aconteceu.'}), 403

        # Remove primeiro os itens, pois eles dependem da manutencao.
        cur.execute(
            """
            DELETE
            FROM ITEM_MANUTENCAO
            WHERE ID_MANUTENCAO = ?
            """,
            (id_manutencao,)
        )

        # Exclui a manutencao pelo id.
        cur.execute(  # Exclui a manutencao pelo id informado.
            """
            DELETE -- Remove registros da tabela.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao informada.
            """,
            (id_manutencao,)
        ),

        # Confirma a exclusao no banco.
        con.commit()

        # Retorna sucesso da exclusao.
        return jsonify({'mensagem': 'Agendamento de manutenção cancelado e excluído com sucesso!'}), 201

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao deletar a manutencao {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/buscar_manutencao', methods=['POST'])
def buscar_manutencao():
    # Abre um cursor para consultar o banco.
    cur = con.cursor()

    try:
        # Lê os dados enviados em JSON.
        dados = request.get_json()

        # Verifica se o corpo JSON veio vazio.
        if not dados:
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400

        # Recupera o id da manutencao usado como filtro.
        id_manutencao = dados.get('id_manutencao')

        # Recupera o id do veiculo usado como filtro.
        id_veiculo = dados.get('id_veiculo')

        # Busca manutencao pelo id.
        if id_manutencao:
            cur.execute(  # Busca a manutencao pelo id informado.
                """
                SELECT M.ID_MANUTENCAO, -- Seleciona o id da manutencao.
                       MA.MARCA, -- Seleciona a marca do veiculo.
                       V.MODELO, -- Seleciona o modelo do veiculo.
                       V.PLACA, -- Seleciona a placa do veiculo.
                       M.DATA_MANUTENCAO, -- Seleciona a data da manutencao.
                       M.VALOR_TOTAL -- Seleciona o valor total da manutencao.
                FROM MANUTENCAO M -- Define a tabela principal de manutencoes.
                         INNER JOIN VEICULO V ON M.ID_VEICULO = V.ID_VEICULO -- Junta a manutencao com o veiculo.
                         INNER JOIN MARCA MA ON V.ID_MARCA = MA.ID_MARCA -- Junta o veiculo com a marca.
                WHERE M.ID_MANUTENCAO = ? -- Filtra pelo id da manutencao.
                """,
                (id_manutencao,)
            )

        # Busca manutencoes pelo veiculo.
        elif id_veiculo:
            cur.execute(  # Busca manutencoes vinculadas ao veiculo.
                """
                SELECT M.ID_MANUTENCAO, -- Seleciona o id da manutencao.
                       MA.MARCA, -- Seleciona a marca do veiculo.
                       V.MODELO, -- Seleciona o modelo do veiculo.
                       V.PLACA, -- Seleciona a placa do veiculo.
                       M.DATA_MANUTENCAO, -- Seleciona a data da manutencao.
                       M.VALOR_TOTAL -- Seleciona o valor total da manutencao.
                FROM MANUTENCAO M -- Define a tabela principal de manutencoes.
                         INNER JOIN VEICULO V ON M.ID_VEICULO = V.ID_VEICULO -- Junta a manutencao com o veiculo.
                         INNER JOIN MARCA MA ON V.ID_MARCA = MA.ID_MARCA -- Junta o veiculo com a marca.
                WHERE M.ID_VEICULO = ? -- Filtra pelo id do veiculo.
                ORDER BY M.DATA_MANUTENCAO DESC -- Ordena da manutencao mais recente para a mais antiga.
                """,
                (id_veiculo,)
            )

        # Retorna erro se nenhum filtro obrigatorio foi informado.
        else:
            return jsonify({'erro': 'Informe id_manutencao ou id_veiculo para realizar a busca.'}), 400

        # Recupera todas as manutencoes encontradas.
        manutencoes = cur.fetchall()

        # Verifica se nenhuma manutencao foi encontrada.
        if not manutencoes:
            return jsonify({'erro': 'Nenhuma manutenção encontrada.'}), 404

        # Cria a lista final da resposta.
        lista_final = []

        # Percorre cada manutencao encontrada.
        for m in manutencoes:
            # Guarda o id da manutencao atual.
            id_manut = m[0]

            # Busca os itens da manutencao.
            cur.execute(  # Busca os itens da manutencao encontrada.
                """
                SELECT S.NOME_SERVICO, -- Seleciona o nome do servico.
                       IM.QUANTIDADE, -- Seleciona a quantidade do servico.
                       IM.VALOR_COBRADO -- Seleciona o valor cobrado pelo servico.
                FROM ITEM_MANUTENCAO IM -- Define a tabela principal dos itens de manutencao.
                         INNER JOIN SERVICO S ON IM.ID_SERVICO = S.ID_SERVICO -- Junta o item com a tabela de servicos.
                WHERE IM.ID_MANUTENCAO = ? -- Filtra os itens pela manutencao informada.
                """,
                (id_manut,)
            )

            # Recupera todos os itens encontrados.
            itens = cur.fetchall()

            # Cria a lista de servicos da manutencao.
            lista_servicos = []

            # Percorre cada item da manutencao.
            for item in itens:
                lista_servicos.append({
                    'servico': item[0],
                    'quantidade': item[1],
                    'valor_unitario': float(item[2]),
                    'subtotal': float(item[1] * item[2])
                })

            # Guarda a data vinda do banco.
            data_db = m[4]

            # Formata a data no padrao brasileiro.
            data_br = data_db.strftime('%d/%m/%Y %H:%M')

            # Adiciona a manutencao formatada na resposta.
            lista_final.append({
                'id_manutencao': id_manut,
                'marca': m[1],
                'modelo': m[2],
                'placa': m[3],
                'data': data_br,
                'valor_total': float(m[5]),
                'servicos_realizados': lista_servicos
            })

        # Retorna a lista final de manutencoes.
        return jsonify(lista_final), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao buscar manutenção: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/listar_manutencao', methods=['GET'])
def listar_manutencao():
    # Abre um cursor para consultar o banco.
    cur = con.cursor()

    try:
        # Busca todas as manutencoes.
        cur.execute(  # Busca todas as manutencoes cadastradas.
            """
            SELECT M.ID_MANUTENCAO, -- Seleciona o id da manutencao.
                   MA.MARCA, -- Seleciona a marca do veiculo.
                   V.MODELO, -- Seleciona o modelo do veiculo.
                   V.PLACA, -- Seleciona a placa do veiculo.
                   M.DATA_MANUTENCAO, -- Seleciona a data da manutencao.
                   M.VALOR_TOTAL -- Seleciona o valor total da manutencao.
            FROM MANUTENCAO M -- Define a tabela principal de manutencoes.
                     INNER JOIN VEICULO V ON M.ID_VEICULO = V.ID_VEICULO -- Junta a manutencao com o veiculo.
                     INNER JOIN MARCA MA ON V.ID_MARCA = MA.ID_MARCA -- Junta o veiculo com a marca.
            ORDER BY M.DATA_MANUTENCAO DESC -- Ordena da manutencao mais recente para a mais antiga.
            """
        )

        # Recupera as manutencoes encontradas.
        manutencoes = cur.fetchall()

        # Verifica se nao ha manutencoes cadastradas.
        if not manutencoes:
            return jsonify({'mensagem': 'Nenhuma manutenção encontrada.'}), 404

        # Cria a lista final da resposta.
        lista_final = []

        # Percorre cada manutencao encontrada.
        for m in manutencoes:
            # Guarda o id da manutencao atual.
            id_manut = m[0]

            # Busca os itens da manutencao.
            cur.execute(  # Busca os itens da manutencao listada.
                """
                SELECT S.NOME_SERVICO, -- Seleciona o nome do servico.
                       IM.QUANTIDADE, -- Seleciona a quantidade do servico.
                       IM.VALOR_COBRADO -- Seleciona o valor cobrado pelo servico.
                FROM ITEM_MANUTENCAO IM -- Define a tabela principal dos itens de manutencao.
                         INNER JOIN SERVICO S ON IM.ID_SERVICO = S.ID_SERVICO -- Junta o item com a tabela de servicos.
                WHERE IM.ID_MANUTENCAO = ? -- Filtra os itens pela manutencao atual.
                """,
                (id_manut,)
            )

            # Recupera os itens encontrados.
            itens = cur.fetchall()

            # Cria a lista de servicos da manutencao.
            lista_servicos = []

            # Percorre cada item encontrado.
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

            # Formata a data no padrao brasileiro.
            data_br = m[4].strftime('%d/%m/%Y %H:%M')

            # Adiciona a manutencao formatada na lista final.
            lista_final.append({
                'id_manutencao': id_manut,
                'marca': m[1],
                'modelo': m[2],
                'placa': m[3],
                'data': data_br,
                'valor_total': float(m[5]),
                'servicos_realizados': lista_servicos
            })

        # Retorna todas as manutencoes formatadas.
        return jsonify(lista_final), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao listar manutenções: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/adicionar_item_manutencao', methods=['POST'])
def adicionar_item_manutencao():
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    try:
        # Lê os dados enviados em JSON.
        dados = request.get_json()

        # Recupera o id da manutencao.
        id_manutencao = dados['id_manutencao']

        # Recupera o id do servico.
        id_servico = dados.get('id_servico')

        # Recupera a quantidade do item.
        quantidade = dados.get('quantidade')

        # Verifica se campos obrigatorios foram enviados.
        if not id_manutencao or not id_servico:
            return jsonify({'erro': 'Campo obrigatório'}), 400

        # Converte a quantidade para inteiro.
        quantidade = int(quantidade)

        # Busca a data da manutencao.
        cur.execute(  # Consulta a data da manutencao antes de adicionar item.
            """
            SELECT DATA_MANUTENCAO -- Seleciona a data agendada da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao informada.
            """,
            (id_manutencao,)
        ),

        # Recupera a manutencao encontrada.
        manutencao = cur.fetchone()

        # Verifica se a manutencao nao existe.
        if not manutencao:
            return jsonify({'erro': 'Manutenção não encontrada'}), 400

        # Bloqueia alteracao de manutencao passada.
        if manutencao[0] < datetime.datetime.now():
            return jsonify({'erro': 'Não é possível alterar uma manutenção no passado'}), 400

        # Busca o valor do servico.
        cur.execute(  # Consulta o valor do servico que sera adicionado.
            """
            SELECT VALOR -- Seleciona o valor atual do servico.
            FROM SERVICO -- Define a tabela de servicos.
            WHERE ID_SERVICO = ? -- Filtra pelo id do servico informado.
            """,
            (id_servico,)
        ),

        # Recupera o servico encontrado.
        servico = cur.fetchone()

        # Verifica se o servico nao existe.
        if not servico:
            return jsonify({'erro': f'Serviço de id{id_servico} não exite'}), 400

        # Converte o valor do servico para float.
        valor = float(servico[0])

        # Insere o item na manutencao.
        cur.execute(  # Insere um novo item na manutencao.
            """
            INSERT INTO ITEM_MANUTENCAO ( -- Insere um novo item na manutencao.
                ID_MANUTENCAO, -- Informa a manutencao ligada ao item.
                ID_SERVICO, -- Informa o servico do item.
                VALOR_COBRADO, -- Informa o valor cobrado pelo servico.
                QUANTIDADE -- Informa a quantidade do servico.
            )
            VALUES (?, ?, ?, ?) -- Define os valores que serao gravados.
            """,
            (id_manutencao, id_servico, valor, quantidade)
        )

        # Recalcula o total da manutencao.
        novo_total = recalcular_total_manutencao(id_manutencao, cur)

        # Confirma a inclusao no banco.
        con.commit()

        # Retorna o novo total com status criado.
        return jsonify({
            'mensagem': 'Item adicionado com sucesso!',
            'novo_total': novo_total
        }), 201

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao adicionar item na manutenção: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/editar_item_manutencao/<int:id_item>', methods=['PUT'])
def editar_item_manutencao(id_item):
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    try:
        # Lê os dados enviados em JSON.
        dados = request.get_json()

        # Recupera a nova quantidade.
        quantidade = dados.get('quantidade')

        # Verifica se a quantidade foi enviada.
        if not quantidade:
            return jsonify({'erro': 'Quantidade é obrigatória'}), 400

        # Converte a quantidade para inteiro.
        quantidade = int(quantidade)

        # Busca a manutencao do item.
        cur.execute(  # Consulta a manutencao vinculada ao item.
            """
            SELECT ID_MANUTENCAO -- Seleciona o id da manutencao ligada ao item.
            FROM ITEM_MANUTENCAO -- Define a tabela dos itens de manutencao.
            WHERE ID_ITEM = ? -- Filtra pelo id do item.
            """,
            (id_item,)
        )

        # Recupera o item encontrado.
        item = cur.fetchone()

        # Verifica se o item nao existe.
        if not item:
            return jsonify({'erro': 'Item não encontrado'}), 404

        # Guarda o id da manutencao do item.
        id_manutencao = item[0]

        # Busca a data da manutencao.
        cur.execute(  # Consulta a data da manutencao do item.
            """
            SELECT DATA_MANUTENCAO -- Seleciona a data agendada da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao do item.
            """,
            (id_manutencao,)
        )

        # Recupera a manutencao encontrada.
        manutencao = cur.fetchone()

        # Bloqueia edicao de item passado.
        if manutencao[0] < datetime.datetime.now():
            return jsonify({'erro': 'Não pode editar item de manutenção passada'}), 403

        # Atualiza a quantidade do item.
        cur.execute(  # Atualiza a quantidade do item.
            """
            UPDATE ITEM_MANUTENCAO -- Define a tabela que sera atualizada.
            SET QUANTIDADE = ? -- Atualiza a quantidade do item.
            WHERE ID_ITEM = ? -- Filtra pelo id do item.
            """,
            (quantidade, id_item)
        )

        # Recalcula o total da manutencao.
        novo_total = recalcular_total_manutencao(id_manutencao, cur)

        # Confirma a atualizacao no banco.
        con.commit()

        # Retorna o novo total da manutencao.
        return jsonify({
            'mensagem': 'Item atualizado com sucesso!',
            'novo_total': novo_total
        }), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao editar item manutenção: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/excluir_item_manutencao/<int:id_item>', methods=['DELETE'])
def excluir_item_manutencao(id_item):
    # Abre um cursor para executar comandos SQL.
    cur = con.cursor()

    try:
        # Busca a manutencao do item.
        cur.execute(  # Consulta a manutencao vinculada ao item.
            """
            SELECT ID_MANUTENCAO -- Seleciona o id da manutencao ligada ao item.
            FROM ITEM_MANUTENCAO -- Define a tabela dos itens de manutencao.
            WHERE ID_ITEM = ? -- Filtra pelo id do item.
            """,
            (id_item,)
        )

        # Recupera o item encontrado.
        item = cur.fetchone()

        # Verifica se o item nao existe.
        if not item:
            return jsonify({'erro': 'Item não encontrado'}), 404

        # Guarda o id da manutencao do item.
        id_manutencao = item[0]

        # Busca a data da manutencao.
        cur.execute(  # Consulta a data da manutencao do item.
            """
            SELECT DATA_MANUTENCAO -- Seleciona a data agendada da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao do item.
            """,
            (id_manutencao,)
        )

        # Recupera a data encontrada.
        data = cur.fetchone()

        # Verifica se a manutencao nao existe.
        if not data:
            return jsonify({'erro': 'Manutenção não encontrada'}), 404

        # Bloqueia exclusao de item passado.
        if data[0] < datetime.datetime.now():
            return jsonify({'erro': 'Não pode excluir item de manutenção passada'}), 403

        # Exclui o item pelo id.
        cur.execute(  # Exclui o item da manutencao.
            """
            DELETE -- Remove registros da tabela.
            FROM ITEM_MANUTENCAO -- Define a tabela dos itens de manutencao.
            WHERE ID_ITEM = ? -- Filtra pelo id do item.
            """,
            (id_item,)
        )

        # Recalcula o total da manutencao.
        novo_total = recalcular_total_manutencao(id_manutencao, cur)

        # Confirma a exclusao no banco.
        con.commit()

        # Retorna o novo total da manutencao.
        return jsonify({
            'mensagem': 'Item excluído com sucesso!',
            'novo_total': novo_total
        }), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao excluir item manutenção: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/listar_item_manutencao/<int:id_manutencao>', methods=['GET'])
def listar_item_manutencao(id_manutencao):
    # Abre um cursor para consultar o banco.
    cur = con.cursor()

    try:
        # Verifica se a manutencao existe.
        cur.execute(  # Verifica se a manutencao existe.
            """
            SELECT ID_MANUTENCAO -- Seleciona o id da manutencao.
            FROM MANUTENCAO -- Define a tabela de manutencoes.
            WHERE ID_MANUTENCAO = ? -- Filtra pela manutencao informada.
            """,
            (id_manutencao,)
        )

        # Retorna erro se a manutencao nao foi encontrada.
        if not cur.fetchone():
            return jsonify({'erro': 'Manutenção não encontrada'}), 404

        # Busca os itens da manutencao.
        cur.execute(  # Busca todos os itens da manutencao.
            """
            SELECT IM.ID_ITEM, -- Seleciona o id do item da manutencao.
                   IM.ID_MANUTENCAO, -- Seleciona o id da manutencao ligada ao item.
                   IM.ID_SERVICO, -- Seleciona o id do servico ligado ao item.
                   S.NOME_SERVICO, -- Seleciona o nome do servico.
                   IM.QUANTIDADE, -- Seleciona a quantidade do servico.
                   IM.VALOR_COBRADO -- Seleciona o valor cobrado pelo servico.
            FROM ITEM_MANUTENCAO IM -- Define a tabela principal dos itens de manutencao.
                     INNER JOIN SERVICO S ON IM.ID_SERVICO = S.ID_SERVICO -- Junta o item com a tabela de servicos.
            WHERE IM.ID_MANUTENCAO = ? -- Filtra os itens pela manutencao informada.
            ORDER BY IM.ID_ITEM -- Ordena os itens pelo id.
            """,
            (id_manutencao,)
        )

        # Recupera todos os itens encontrados.
        itens = cur.fetchall()

        # Verifica se nao ha itens para a manutencao.
        if not itens:
            return jsonify({'mensagem': 'Nenhum item foi encontrado'}), 404

        # Cria a lista final de itens.
        lista_itens = []

        # Percorre cada item encontrado.
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

        # Retorna a lista de itens.
        return jsonify({'itens': lista_itens}), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao listar item manutencao {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()


@app.route('/historico_servico/<int:id_servico>', methods=['GET'])
def listar_historico_servico(id_servico):
    # Abre um cursor para consultar o banco.
    cur = con.cursor()

    try:
        # Busca o historico do servico.
        cur.execute(  # Busca o historico de alteracoes do servico.
            """
            SELECT S.NOME_SERVICO, -- Seleciona o nome do servico.
                   H.VALOR_UNITARIO, -- Seleciona o valor antigo registrado.
                   H.DATA_HISTORICO -- Seleciona a data da alteracao.
            FROM HISTORICO_SERVICO H -- Define a tabela principal do historico.
                     INNER JOIN SERVICO S ON H.ID_SERVICO = S.ID_SERVICO -- Junta o historico com a tabela de servicos.
            WHERE H.ID_SERVICO = ? -- Filtra pelo id do servico.
            ORDER BY H.DATA_HISTORICO DESC -- Ordena do historico mais recente para o mais antigo.
            """,
            (id_servico,)
        )

        # Recupera todos os registros de historico.
        historico = cur.fetchall()

        # Verifica se nao ha historico para o servico.
        if not historico:
            return jsonify({'mensagem': 'Nenhum histórico encontrado para este serviço.'}), 404

        # Cria a lista de historico formatado.
        lista_h = []

        # Percorre cada registro do historico.
        for registro in historico:
            lista_h.append({
                'servico': registro[0],
                'valor_antigo': float(registro[1]),
                'data_alteracao': registro[2].strftime('%d/%m/%Y %H:%M')
            })

        # Retorna o historico do servico.
        return jsonify({'id_servico': id_servico, 'historico': lista_h}), 200

    except jwt.ExpiredSignatureError:
        # Retorna erro quando o token expirou.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401

    except jwt.InvalidTokenError:
        # Retorna erro quando o token e invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401

    except Exception as e:
        # Retorna erro interno com detalhes.
        return jsonify({'erro': f'Erro ao buscar histórico: {e}'}), 500

    finally:
        # Fecha o cursor do banco.
        cur.close()
