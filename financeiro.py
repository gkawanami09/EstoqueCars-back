# Importa funções do Flask para responder em JSON e ler dados da requisição.
from flask import jsonify, request

# Importa a conexão com o banco e a aplicação Flask principal.
from main import con, app

# Importa o módulo de expressões regulares, caso seja necessário neste arquivo.
import re

# Importa funções auxiliares usadas para tratar dados financeiros e veículos.
from function import (
    dados_requisicao,
    texto_tipo,
    normalizar_tipo,
    normalizar_data,
    descricao_com_veiculo,
    montar_financeiro_com_veiculo,
)


# Cria a rota de cadastro financeiro usando o método POST.
@app.route('/cadastro_financeiro', methods=['POST'])
def cadastro_financeiro():
    # Abre um cursor para executar comandos no banco de dados.
    cur = con.cursor()
    try:
        # Busca os dados enviados na requisição.
        dados = dados_requisicao()

        # Lê a descrição, aceitando tanto "descricao" quanto "descrição", e remove espaços extras.
        descricao = str(dados.get('descricao') or dados.get('descrição') or "").strip()

        # Normaliza o tipo para o código usado pelo sistema.
        tipo = normalizar_tipo(dados.get('tipo'))

        # Lê o valor informado na requisição.
        valor = dados.get('valor')

        # Lê a data, aceitando os nomes "data" ou "data_financeiro".
        data_financeiro = dados.get('data') or dados.get('data_financeiro')

        # Lê o ID do veículo, quando a transação estiver ligada a um veículo.
        id_veiculo = dados.get('id_veiculo')

        # Verifica se a descrição foi preenchida.
        if not descricao:
            # Retorna erro quando a descrição estiver vazia.
            return jsonify({'erro': 'Descrição é obrigatória.'}), 400

        # Verifica se o tipo foi informado e reconhecido.
        if tipo is None:
            # Retorna erro quando o tipo não for válido.
            return jsonify({'erro': 'Tipo é obrigatório. Use receita/entrada ou despesa/saída.'}), 400

        # Verifica se o valor foi enviado e não está vazio.
        if valor is None or str(valor).strip() == "":
            # Retorna erro quando o valor não foi informado.
            return jsonify({'erro': 'Valor é obrigatório.'}), 400

        # Converte o valor para float e aceita vírgula como separador decimal.
        valor = float(str(valor).replace(",", "."))

        # Valida se o valor é maior que zero.
        if valor <= 0:
            # Retorna erro quando o valor for zero ou negativo.
            return jsonify({'erro': 'Valor deve ser maior que zero.'}), 400

        # Normaliza a data para o formato esperado pelo banco/sistema.
        data_financeiro = normalizar_data(data_financeiro)

        # Complementa a descrição com dados do veículo, se um id_veiculo foi informado.
        descricao = descricao_com_veiculo(cur, descricao, id_veiculo)

        # Busca o próximo ID financeiro usando o maior ID atual mais 1.
        cur.execute("SELECT COALESCE(MAX(ID_FINANCEIRO), 0) + 1 FROM FINANCEIRO")

        # Recupera o ID calculado pela consulta anterior.
        id_financeiro = cur.fetchone()[0]

        # Insere a nova transação financeira no banco de dados.
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

        # Confirma a gravação da transação no banco.
        con.commit()

        # Retorna os dados cadastrados com status HTTP 201.
        return jsonify({
            'mensagem': 'Transação financeira cadastrada com sucesso.',
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

    # Captura erros de validação/conversão, como valor ou data inválidos.
    except ValueError as e:
        # Desfaz qualquer alteração feita antes do erro.
        con.rollback()

        # Retorna a mensagem do erro com status HTTP 400.
        return jsonify({'erro': str(e)}), 400

    # Captura qualquer erro inesperado no cadastro.
    except Exception as e:
        # Desfaz qualquer alteração feita antes do erro.
        con.rollback()

        # Retorna uma mensagem de erro genérica com status HTTP 500.
        return jsonify({'erro': f'Erro ao cadastrar financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para listar todas as transações financeiras.
@app.route('/listar_financeiro', methods=['GET'])
def listar_financeiro():
    # Abre um cursor para executar consultas no banco.
    cur = con.cursor()
    try:
        # Consulta todas as transações financeiras.
        cur.execute(
            """
            SELECT ID_FINANCEIRO,
                   DESCRICAO,
                   TIPO,
                   DATA_FINANCEIRO,
                   VALOR
            FROM FINANCEIRO
            ORDER BY DATA_FINANCEIRO DESC, ID_FINANCEIRO DESC
            """
        )

        # Monta cada registro com possíveis dados de veículo associados.
        transacoes = [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]

        # Retorna a lista de transações encontradas.
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
        # Consulta transações financeiras com TIPO igual a 0, que representa receita.
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

        # Retorna as receitas já formatadas com possíveis dados de veículo.
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
        # Consulta transações financeiras com TIPO igual a 1, que representa despesa.
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

        # Retorna as despesas já formatadas com possíveis dados de veículo.
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
        # Consulta apenas tipo e valor, pois o resumo precisa somar receitas e despesas.
        cur.execute(
            """
            SELECT TIPO,
                   VALOR
            FROM FINANCEIRO
            """
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

            # Qualquer outro tipo é somado como despesa.
            else:
                despesas += float(valor or 0)

        # Retorna o total de receitas, despesas, saldo e lucro líquido.
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


# Cria a rota para editar uma transação financeira pelo ID.
@app.route('/editar_financeiro/<int:id_financeiro>', methods=['PUT'])
def editar_financeiro(id_financeiro):
    # Abre um cursor para executar comandos no banco de dados.
    cur = con.cursor()
    try:
        # Busca os dados enviados na requisição.
        dados = dados_requisicao()

        # Lê a descrição, aceitando tanto "descricao" quanto "descrição", e remove espaços extras.
        descricao = str(dados.get('descricao') or dados.get('descrição') or "").strip()

        # Normaliza o tipo para o código usado pelo sistema.
        tipo = normalizar_tipo(dados.get('tipo'))

        # Lê o valor informado na requisição.
        valor = dados.get('valor')

        # Lê a data, aceitando os nomes "data" ou "data_financeiro".
        data_financeiro = dados.get('data') or dados.get('data_financeiro')

        # Lê o ID do veículo, quando a transação estiver ligada a um veículo.
        id_veiculo = dados.get('id_veiculo')

        # Verifica se a descrição foi preenchida.
        if not descricao:
            # Retorna erro quando a descrição estiver vazia.
            return jsonify({'erro': 'Descrição é obrigatória.'}), 400

        # Verifica se o tipo foi informado e reconhecido.
        if tipo is None:
            # Retorna erro quando o tipo não for válido.
            return jsonify({'erro': 'Tipo é obrigatório. Use receita/entrada ou despesa/saída.'}), 400

        # Verifica se o valor foi enviado e não está vazio.
        if valor is None or str(valor).strip() == "":
            # Retorna erro quando o valor não foi informado.
            return jsonify({'erro': 'Valor é obrigatório.'}), 400

        # Converte o valor para float e aceita vírgula como separador decimal.
        valor = float(str(valor).replace(",", "."))

        # Valida se o valor é maior que zero.
        if valor <= 0:
            # Retorna erro quando o valor for zero ou negativo.
            return jsonify({'erro': 'Valor deve ser maior que zero.'}), 400

        # Normaliza a data para o formato esperado pelo banco/sistema.
        data_financeiro = normalizar_data(data_financeiro)

        # Complementa a descrição com dados do veículo, se um id_veiculo foi informado.
        descricao = descricao_com_veiculo(cur, descricao, id_veiculo)

        # Verifica se existe uma transação financeira com o ID informado.
        cur.execute("SELECT ID_FINANCEIRO FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))

        # Se não encontrar o registro, retorna erro 404.
        if not cur.fetchone():
            return jsonify({'erro': 'Transação financeira não encontrada.'}), 404

        # Atualiza os dados da transação financeira existente.
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

        # Confirma a edição no banco.
        con.commit()

        # Retorna mensagem de sucesso.
        return jsonify({'mensagem': 'Transação financeira editada com sucesso.'}), 200

    # Captura erros de validação/conversão, como valor ou data inválidos.
    except ValueError as e:
        # Retorna a mensagem do erro com status HTTP 400.
        return jsonify({'erro': str(e)}), 400

    # Captura qualquer erro inesperado na edição.
    except Exception as e:
        # Retorna uma mensagem de erro genérica com status HTTP 500.
        return jsonify({'erro': f'Erro ao editar financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para excluir uma transação financeira pelo ID.
@app.route('/excluir_financeiro/<int:id_financeiro>', methods=['DELETE'])
def excluir_financeiro(id_financeiro):
    # Abre um cursor para executar comandos no banco de dados.
    cur = con.cursor()
    try:
        # Verifica se existe uma transação financeira com o ID informado.
        cur.execute("SELECT ID_FINANCEIRO FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))

        # Se não encontrar o registro, retorna erro 404.
        if not cur.fetchone():
            return jsonify({'erro': 'Transação financeira não encontrada.'}), 404

        # Exclui a transação financeira encontrada.
        cur.execute("DELETE FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))

        # Confirma a exclusão no banco.
        con.commit()

        # Retorna mensagem de sucesso.
        return jsonify({'mensagem': 'Transação financeira excluída com sucesso.'}), 200

    # Captura qualquer erro inesperado na exclusão.
    except Exception as e:
        # Retorna uma mensagem de erro genérica com status HTTP 500.
        return jsonify({'erro': f'Erro ao excluir financeiro: {e}'}), 500

    # Executa sempre, dando certo ou dando erro.
    finally:
        # Fecha o cursor do banco.
        cur.close()
