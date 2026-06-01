# Importa funcoes do Flask para responder em JSON e ler dados da requisicao.
from flask import jsonify, request

# Importa a conexao com o banco e a aplicacao Flask principal.
from main import con, app

# Importa o modulo de expressoes regulares, caso seja necessario neste arquivo.
import re

# Importa funcoes auxiliares usadas para tratar dados financeiros e veiculos.
from function import dados_requisicao, texto_tipo, filtros_financeiro, normalizar_tipo, normalizar_data, descricao_com_veiculo,montar_financeiro_com_veiculo




# Cria a rota de cadastro financeiro usando o metodo POST.
@app.route('/cadastro_financeiro', methods=['POST'])
def cadastro_financeiro():
    # Abre um cursor para executar comandos no banco de dados.
    cur = con.cursor()
    try:
        # Busca os dados enviados na requisicao.
        dados = dados_requisicao()

        # Le a descricao, aceitando tanto "descricao" quanto "descrição", e remove espacos extras.
        descricao = str(dados.get('descricao') or dados.get('descriÃ§Ã£o') or "").strip()

        # Normaliza o tipo para o codigo usado pelo sistema.
        tipo = normalizar_tipo(dados.get('tipo'))

        # Le o valor informado na requisicao.
        valor = dados.get('valor')

        # Le a data, aceitando os nomes "data" ou "data_financeiro".
        data_financeiro = dados.get('data') or dados.get('data_financeiro')

        # Le o id do veiculo, quando a transacao estiver ligada a um veiculo.
        id_veiculo = dados.get('id_veiculo')

        # Verifica se a descricao foi preenchida.
        if not descricao:
            # Retorna erro quando a descricao estiver vazia.
            return jsonify({'erro': 'DescriÃ§Ã£o Ã© obrigatÃ³ria.'}), 400

        # Verifica se o tipo foi informado e reconhecido.
        if tipo is None:
            # Retorna erro quando o tipo nao for valido.
            return jsonify({'erro': 'Tipo Ã© obrigatÃ³rio. Use receita/entrada ou despesa/saÃ­da.'}), 400

        # Verifica se o valor foi enviado e nao esta vazio.
        if valor is None or str(valor).strip() == "":
            # Retorna erro quando o valor nao foi informado.
            return jsonify({'erro': 'Valor Ã© obrigatÃ³rio.'}), 400

        # Converte o valor para float e aceita virgula como separador decimal.
        valor = float(str(valor).replace(",", "."))

        # Valida se o valor e maior que zero.
        if valor <= 0:
            # Retorna erro quando o valor for zero ou negativo.
            return jsonify({'erro': 'Valor deve ser maior que zero.'}), 400

        # Normaliza a data para o formato esperado pelo banco/sistema.
        data_financeiro = normalizar_data(data_financeiro)

        # Complementa a descricao com dados do veiculo, se um id_veiculo foi informado.
        descricao = descricao_com_veiculo(cur, descricao, id_veiculo)

        # Busca o proximo ID financeiro usando o maior ID atual mais 1.
        cur.execute("SELECT COALESCE(MAX(ID_FINANCEIRO), 0) + 1 FROM FINANCEIRO")

        # Recupera o ID calculado pela consulta anterior.
        id_financeiro = cur.fetchone()[0]

        # Insere a nova transacao financeira no banco de dados.
        cur.execute(
            """
            INSERT INTO FINANCEIRO(
                ID_FINANCEIRO,
                DESCRICAO,
                TIPO,
                DATA_FINANCEIRO,
                VALOR
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (id_financeiro, descricao, tipo, data_financeiro, valor)
        )

        # Confirma a gravacao da transacao no banco.
        con.commit()

        # Retorna os dados cadastrados com status HTTP 201.
        return jsonify({
            'mensagem': 'TransaÃ§Ã£o financeira cadastrada com sucesso.',
            'financeiro': {
                'id': id_financeiro,
                'id_financeiro': id_financeiro,
                'descricao': descricao,
                'tipo': texto_tipo(tipo),
                'tipo_codigo': tipo,
                'data': str(data_financeiro),
                'data_financeiro': str(data_financeiro),
                'valor': valor
            }
        }), 201

    # Captura erros de validacao/conversao, como valor ou data invalidos.
    except ValueError as e:
        # Desfaz qualquer alteracao feita antes do erro.
        con.rollback()

        # Retorna a mensagem do erro com status HTTP 400.
        return jsonify({'erro': str(e)}), 400

    # Captura qualquer erro inesperado no cadastro.
    except Exception as e:
        # Desfaz qualquer alteracao feita antes do erro.
        con.rollback()

        # Retorna uma mensagem de erro generica com status HTTP 500.
        return jsonify({'erro': f'Erro ao cadastrar financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para listar todas as transacoes financeiras.
@app.route('/listar_financeiro', methods=['GET'])
def listar_financeiro():
    # Abre um cursor para executar consultas no banco.
    cur = con.cursor()
    try:
        # Monta os filtros financeiros conforme os parametros enviados na URL.
        sql_where, params = filtros_financeiro()

        # Consulta as transacoes financeiras aplicando os filtros.
        cur.execute(
            f"""
            SELECT ID_FINANCEIRO,
                   DESCRICAO,
                   TIPO,
                   DATA_FINANCEIRO,
                   VALOR
            FROM FINANCEIRO
            {sql_where}
            ORDER BY DATA_FINANCEIRO DESC, ID_FINANCEIRO DESC
            """,
            params
        )

        # Monta cada registro com possiveis dados de veiculo associados.
        transacoes = [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]

        # Retorna a lista de transacoes encontradas.
        return jsonify({'transacoes': transacoes}), 200

    # Captura erros inesperados na listagem.
    except Exception as e:
        # Retorna uma mensagem de erro com status HTTP 500.
        return jsonify({'erro': f'Erro ao listar financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para listar somente receitas.
@app.route('/listar_receitas', methods=['GET'])
def listar_receitas():
    # Abre um cursor para executar consultas no banco.
    cur = con.cursor()
    try:
        # Consulta transacoes financeiras com TIPO igual a 0, que representa receita.
        cur.execute(
            """
            SELECT ID_FINANCEIRO,
                   DESCRICAO,
                   TIPO,
                   DATA_FINANCEIRO,
                   VALOR
            FROM FINANCEIRO
            WHERE TIPO = 0
            ORDER BY DATA_FINANCEIRO DESC, ID_FINANCEIRO DESC
            """
        )

        # Retorna as receitas ja formatadas com possiveis dados de veiculo.
        return jsonify({'receitas': [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]}), 200

    # Captura erros inesperados na listagem de receitas.
    except Exception as e:
        # Retorna uma mensagem de erro com status HTTP 500.
        return jsonify({'erro': f'Erro ao listar receitas: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para listar somente despesas.
@app.route('/listar_despesas', methods=['GET'])
def listar_despesas():
    # Abre um cursor para executar consultas no banco.
    cur = con.cursor()
    try:
        # Consulta transacoes financeiras com TIPO igual a 1, que representa despesa.
        cur.execute(
            """
            SELECT ID_FINANCEIRO,
                   DESCRICAO,
                   TIPO,
                   DATA_FINANCEIRO,
                   VALOR
            FROM FINANCEIRO
            WHERE TIPO = 1
            ORDER BY DATA_FINANCEIRO DESC, ID_FINANCEIRO DESC
            """
        )

        # Retorna as despesas ja formatadas com possiveis dados de veiculo.
        return jsonify({'despesas': [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]}), 200

    # Captura erros inesperados na listagem de despesas.
    except Exception as e:
        # Retorna uma mensagem de erro com status HTTP 500.
        return jsonify({'erro': f'Erro ao listar despesas: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para gerar um resumo financeiro.
@app.route('/resumo_financeiro', methods=['GET'])
def resumo_financeiro():
    # Abre um cursor para executar consultas no banco.
    cur = con.cursor()
    try:
        # Monta os filtros financeiros conforme os parametros enviados na URL.
        sql_where, params = filtros_financeiro()

        # Consulta apenas tipo e valor, pois o resumo precisa somar receitas e despesas.
        cur.execute(
            f"""
            SELECT TIPO,
                   VALOR
            FROM FINANCEIRO
            {sql_where}
            """,
            params
        )

        # Inicializa o total de receitas.
        receita = 0

        # Inicializa o total de despesas.
        despesas = 0

        # Percorre todos os registros retornados pela consulta.
        for tipo, valor in cur.fetchall():
            # Se o tipo for 0, soma o valor como receita.
            if int(tipo or 0) == 0:
                receita += float(valor or 0)

            # Qualquer outro tipo e somado como despesa.
            else:
                despesas += float(valor or 0)

        # Retorna o total de receitas, despesas, saldo e lucro liquido.
        return jsonify({
            'receitas': receita,
            'despesas': despesas,
            'saldo': receita - despesas,
            'lucro_liquido': receita - despesas
        }), 200

    # Captura erros inesperados ao gerar o resumo.
    except Exception as e:
        # Retorna uma mensagem de erro com status HTTP 500.
        return jsonify({'erro': f'Erro ao gerar resumo financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para editar uma transacao financeira pelo ID.
@app.route('/editar_financeiro/<int:id_financeiro>', methods=['PUT'])
def editar_financeiro(id_financeiro):
    # Abre um cursor para executar comandos no banco de dados.
    cur = con.cursor()
    try:
        # Busca os dados enviados na requisicao.
        dados = dados_requisicao()

        # Le a descricao, aceitando tanto "descricao" quanto "descrição", e remove espacos extras.
        descricao = str(dados.get('descricao') or dados.get('descriÃ§Ã£o') or "").strip()

        # Normaliza o tipo para o codigo usado pelo sistema.
        tipo = normalizar_tipo(dados.get('tipo'))

        # Le o valor informado na requisicao.
        valor = dados.get('valor')

        # Le a data, aceitando os nomes "data" ou "data_financeiro".
        data_financeiro = dados.get('data') or dados.get('data_financeiro')

        # Le o id do veiculo, quando a transacao estiver ligada a um veiculo.
        id_veiculo = dados.get('id_veiculo')

        # Verifica se a descricao foi preenchida.
        if not descricao:
            # Retorna erro quando a descricao estiver vazia.
            return jsonify({'erro': 'DescriÃ§Ã£o Ã© obrigatÃ³ria.'}), 400

        # Verifica se o tipo foi informado e reconhecido.
        if tipo is None:
            # Retorna erro quando o tipo nao for valido.
            return jsonify({'erro': 'Tipo Ã© obrigatÃ³rio. Use receita/entrada ou despesa/saÃ­da.'}), 400

        # Verifica se o valor foi enviado e nao esta vazio.
        if valor is None or str(valor).strip() == "":
            # Retorna erro quando o valor nao foi informado.
            return jsonify({'erro': 'Valor Ã© obrigatÃ³rio.'}), 400

        # Converte o valor para float e aceita virgula como separador decimal.
        valor = float(str(valor).replace(",", "."))

        # Valida se o valor e maior que zero.
        if valor <= 0:
            # Retorna erro quando o valor for zero ou negativo.
            return jsonify({'erro': 'Valor deve ser maior que zero.'}), 400

        # Normaliza a data para o formato esperado pelo banco/sistema.
        data_financeiro = normalizar_data(data_financeiro)

        # Complementa a descricao com dados do veiculo, se um id_veiculo foi informado.
        descricao = descricao_com_veiculo(cur, descricao, id_veiculo)

        # Verifica se existe uma transacao financeira com o ID informado.
        cur.execute("SELECT ID_FINANCEIRO FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))

        # Se nao encontrar o registro, retorna erro 404.
        if not cur.fetchone():
            return jsonify({'erro': 'TransaÃ§Ã£o financeira nÃ£o encontrada.'}), 404

        # Atualiza os dados da transacao financeira existente.
        cur.execute(
            """
            UPDATE FINANCEIRO
            SET DESCRICAO = ?,
                TIPO = ?,
                DATA_FINANCEIRO = ?,
                VALOR = ?
            WHERE ID_FINANCEIRO = ?
            """,
            (descricao, tipo, data_financeiro, valor, id_financeiro)
        )

        # Confirma a edicao no banco.
        con.commit()

        # Retorna mensagem de sucesso.
        return jsonify({'mensagem': 'TransaÃ§Ã£o financeira editada com sucesso.'}), 200

    # Captura erros de validacao/conversao, como valor ou data invalidos.
    except ValueError as e:
        # Retorna a mensagem do erro com status HTTP 400.
        return jsonify({'erro': str(e)}), 400

    # Captura qualquer erro inesperado na edicao.
    except Exception as e:
        # Retorna uma mensagem de erro generica com status HTTP 500.
        return jsonify({'erro': f'Erro ao editar financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para excluir uma transacao financeira pelo ID.
@app.route('/excluir_financeiro/<int:id_financeiro>', methods=['DELETE'])
def excluir_financeiro(id_financeiro):
    # Abre um cursor para executar comandos no banco de dados.
    cur = con.cursor()
    try:
        # Verifica se existe uma transacao financeira com o ID informado.
        cur.execute("SELECT ID_FINANCEIRO FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))

        # Se nao encontrar o registro, retorna erro 404.
        if not cur.fetchone():
            return jsonify({'erro': 'TransaÃ§Ã£o financeira nÃ£o encontrada.'}), 404

        # Exclui a transacao financeira encontrada.
        cur.execute("DELETE FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))

        # Confirma a exclusao no banco.
        con.commit()

        # Retorna mensagem de sucesso.
        return jsonify({'mensagem': 'TransaÃ§Ã£o financeira excluÃ­da com sucesso.'}), 200

    # Captura qualquer erro inesperado na exclusao.
    except Exception as e:
        # Retorna uma mensagem de erro generica com status HTTP 500.
        return jsonify({'erro': f'Erro ao excluir financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()
