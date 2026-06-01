from flask import jsonify, request
from main import con, app
import re
from function import dados_requisicao, texto_tipo, filtros_financeiro, normalizar_tipo, normalizar_data, descricao_com_veiculo,montar_financeiro_com_veiculo





@app.route('/cadastro_financeiro', methods=['POST'])
def cadastro_financeiro():
    cur = con.cursor()
    try:
        dados = dados_requisicao()
        descricao = str(dados.get('descricao') or dados.get('descrição') or "").strip()
        tipo = normalizar_tipo(dados.get('tipo'))
        valor = dados.get('valor')
        data_financeiro = dados.get('data') or dados.get('data_financeiro')
        id_veiculo = dados.get('id_veiculo')

        if not descricao:
            return jsonify({'erro': 'Descrição é obrigatória.'}), 400

        if tipo is None:
            return jsonify({'erro': 'Tipo é obrigatório. Use receita/entrada ou despesa/saída.'}), 400

        if valor is None or str(valor).strip() == "":
            return jsonify({'erro': 'Valor é obrigatório.'}), 400

        valor = float(str(valor).replace(",", "."))

        if valor <= 0:
            return jsonify({'erro': 'Valor deve ser maior que zero.'}), 400

        data_financeiro = normalizar_data(data_financeiro)
        descricao = descricao_com_veiculo(cur, descricao, id_veiculo)

        cur.execute("SELECT COALESCE(MAX(ID_FINANCEIRO), 0) + 1 FROM FINANCEIRO")
        id_financeiro = cur.fetchone()[0]

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
        con.commit()

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

    except ValueError as e:
        con.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        con.rollback()
        return jsonify({'erro': f'Erro ao cadastrar financeiro: {e}'}), 500
    finally:
        cur.close()


@app.route('/listar_financeiro', methods=['GET'])
def listar_financeiro():
    cur = con.cursor()
    try:
        sql_where, params = filtros_financeiro()
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

        transacoes = [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]
        return jsonify({'transacoes': transacoes}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar financeiro: {e}'}), 500
    finally:
        cur.close()


@app.route('/listar_receitas', methods=['GET'])
def listar_receitas():
    cur = con.cursor()
    try:
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
        return jsonify({'receitas': [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar receitas: {e}'}), 500
    finally:
        cur.close()


@app.route('/listar_despesas', methods=['GET'])
def listar_despesas():
    cur = con.cursor()
    try:
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
        return jsonify({'despesas': [montar_financeiro_com_veiculo(cur, registro) for registro in cur.fetchall()]}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar despesas: {e}'}), 500
    finally:
        cur.close()


@app.route('/resumo_financeiro', methods=['GET'])
def resumo_financeiro():
    cur = con.cursor()
    try:
        sql_where, params = filtros_financeiro()
        cur.execute(
            f"""
            SELECT TIPO,
                   VALOR
            FROM FINANCEIRO
            {sql_where}
            """,
            params
        )
        receita = 0
        despesas = 0

        for tipo, valor in cur.fetchall():
            if int(tipo or 0) == 0:
                receita += float(valor or 0)
            else:
                despesas += float(valor or 0)

        return jsonify({
            'receitas': receita,
            'despesas': despesas,
            'saldo': receita - despesas,
            'lucro_liquido': receita - despesas
        }), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar resumo financeiro: {e}'}), 500
    finally:
        cur.close()


@app.route('/editar_financeiro/<int:id_financeiro>', methods=['PUT'])
def editar_financeiro(id_financeiro):
    cur = con.cursor()
    try:
        dados = dados_requisicao()
        descricao = str(dados.get('descricao') or dados.get('descrição') or "").strip()
        tipo = normalizar_tipo(dados.get('tipo'))
        valor = dados.get('valor')
        data_financeiro = dados.get('data') or dados.get('data_financeiro')
        id_veiculo = dados.get('id_veiculo')

        if not descricao:
            return jsonify({'erro': 'Descrição é obrigatória.'}), 400

        if tipo is None:
            return jsonify({'erro': 'Tipo é obrigatório. Use receita/entrada ou despesa/saída.'}), 400

        if valor is None or str(valor).strip() == "":
            return jsonify({'erro': 'Valor é obrigatório.'}), 400

        valor = float(str(valor).replace(",", "."))

        if valor <= 0:
            return jsonify({'erro': 'Valor deve ser maior que zero.'}), 400

        data_financeiro = normalizar_data(data_financeiro)
        descricao = descricao_com_veiculo(cur, descricao, id_veiculo)

        cur.execute("SELECT ID_FINANCEIRO FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))
        if not cur.fetchone():
            return jsonify({'erro': 'Transação financeira não encontrada.'}), 404

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
        con.commit()

        return jsonify({'mensagem': 'Transação financeira editada com sucesso.'}), 200
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        return jsonify({'erro': f'Erro ao editar financeiro: {e}'}), 500
    finally:
        cur.close()


@app.route('/excluir_financeiro/<int:id_financeiro>', methods=['DELETE'])
def excluir_financeiro(id_financeiro):
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_FINANCEIRO FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))
        if not cur.fetchone():
            return jsonify({'erro': 'Transação financeira não encontrada.'}), 404

        cur.execute("DELETE FROM FINANCEIRO WHERE ID_FINANCEIRO = ?", (id_financeiro,))
        con.commit()

        return jsonify({'mensagem': 'Transação financeira excluída com sucesso.'}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao excluir financeiro: {e}'}), 500
    finally:
        cur.close()
