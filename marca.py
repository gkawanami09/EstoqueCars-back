from flask import jsonify, request  # Importa recursos do Flask para respostas JSON e dados da requisicao.
import jwt  # Importa a biblioteca usada para tratar erros de token JWT.
from main import app, con  # Importa a aplicacao Flask e a conexao com o banco.


@app.route('/cadastrar_marca', methods=['POST'])  # Define a rota POST para cadastrar uma marca.
def cadastrar_marca():  # Cria a funcao responsavel pelo cadastro de marca.
    cur = con.cursor()  # Abre um cursor para executar comandos SQL.

    try:  # Inicia o bloco protegido do cadastro.
        marca = request.form.get('marca')  # Busca o nome da marca enviado no formulario.
        if not marca or marca.strip() == "":  # Verifica se a marca nao foi enviada ou esta vazia.
            return jsonify({'erro': 'O nome da marca é obrigatório.'}), 400  # Retorna erro de campo obrigatorio.

        nome_marca = marca.strip().upper()  # Remove espacos extras e converte o nome para maiusculo.

        cur.execute("SELECT ID_MARCA FROM MARCA WHERE LOWER(MARCA) = LOWER(?)", (nome_marca,))  # Procura marca com mesmo nome.
        if cur.fetchone():  # Verifica se a marca ja existe no banco.
            return jsonify({'erro': 'Essa marca já foi cadastrada.'}), 409  # Retorna conflito por cadastro duplicado.

        cur.execute("INSERT INTO MARCA (MARCA) VALUES (?)", (nome_marca,))  # Insere a nova marca no banco.
        con.commit()  # Confirma a insercao no banco.

        return jsonify({'mensagem': 'Marca cadastrada com sucesso!'}), 201  # Retorna sucesso com status de criado.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro no cadastro.
        con.rollback()  # Desfaz alteracoes pendentes em caso de erro.
        return jsonify({'erro': f'Erro ao cadastrar: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        cur.close()  # Fecha o cursor do banco.


@app.route('/editar_marca/<int:id_marca>', methods=['PUT'])  # Define a rota PUT para editar uma marca pelo id.
def editar_marca(id_marca):  # Cria a funcao responsavel pela edicao da marca.
    cur = con.cursor()  # Abre um cursor para executar comandos SQL.

    try:  # Inicia o bloco protegido da edicao.
        nova_marca = request.form.get('nova_marca')  # Busca o novo nome da marca no formulario.
        if not nova_marca:  # Verifica se o novo nome nao foi enviado.
            return jsonify({'erro': 'O nome da marca é obrigatório.'}), 400  # Retorna erro de campo obrigatorio.
        cur.execute("UPDATE MARCA SET MARCA = ? WHERE ID_MARCA = ?", (nova_marca.strip().upper(), id_marca))  # Atualiza a marca no banco.
        con.commit()  # Confirma a atualizacao no banco.

        return jsonify({'mensagem': 'Marca editada com sucesso!'}), 200  # Retorna sucesso da edicao.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro na edicao.
        return jsonify({'erro': f'Erro ao editar marca: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        cur.close()  # Fecha o cursor do banco.


@app.route('/deletar_marca/<int:id_marca>', methods=['DELETE'])  # Define a rota DELETE para apagar uma marca pelo id.
def deletar_marca(id_marca):  # Cria a funcao responsavel pela exclusao da marca.
    cur = con.cursor()  # Abre um cursor para executar comandos SQL.

    try:  # Inicia o bloco protegido da exclusao.
        cur.execute("SELECT ID_VEICULO FROM VEICULO WHERE ID_VEICULO = ?", (id_marca,))  # Busca veiculo com o id informado.

        if cur.fetchone():  # Verifica se existe veiculo que bloqueia a exclusao.
            return jsonify({'erro': 'Operação bloqueada'}), 409  # Retorna conflito quando a exclusao e bloqueada.

        cur.execute('DELETE FROM MARCA WHERE ID_MARCA = ?', (id_marca,))  # Exclui a marca pelo id.
        con.commit()  # Confirma a exclusao no banco.
        return jsonify({'mensagem': 'Marca deletada com sucesso!'}), 200  # Retorna sucesso da exclusao.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro na exclusao.
        return jsonify({'erro': f'Erro ao deletar marca: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        cur.close()  # Fecha o cursor do banco.


@app.route('/buscar_marca', methods=['POST'])  # Define a rota POST para buscar marcas.
def buscar_marca():  # Cria a funcao responsavel pela busca de marcas.
    cur = con.cursor()  # Abre um cursor para consultar o banco.

    try:  # Inicia o bloco protegido da busca.
        nome = request.form.get('nome')  # Busca o nome enviado como filtro.
        id_marca = request.form.get('id_marca')  # Busca o id enviado como filtro.
        listar_marcas = []  # Cria a lista que recebera as marcas encontradas.
        if nome:  # Verifica se a busca deve ser feita pelo nome.
            nome_formatado = nome.strip().upper()  # Remove espacos e converte o nome para maiusculo.

            cur.execute("SELECT ID_MARCA, MARCA FROM MARCA WHERE UPPER(MARCA) LIKE ?", (f'%{nome_formatado}%',))  # Busca marcas parecidas com o nome.
        elif id_marca:  # Verifica se a busca deve ser feita pelo id.
            cur.execute("SELECT ID_MARCA, MARCA FROM MARCA WHERE ID_MARCA = ?", (id_marca,))  # Busca a marca pelo id.
        else:  # Executa quando nenhum filtro foi informado.
            cur.execute("SELECT ID_MARCA, MARCA FROM MARCA")  # Busca todas as marcas.
        marcas = cur.fetchall()  # Recupera todas as marcas retornadas pela consulta.

        for marca in marcas:  # Percorre cada marca encontrada.
            listar_marcas.append({  # Adiciona a marca formatada na lista.
                'id_marca': marca[0],  # Inclui o id da marca.
                'nome': marca[1],  # Inclui o nome da marca.
            })  # Finaliza o dicionario da marca.
        if not listar_marcas:  # Verifica se nenhuma marca foi encontrada.
            return jsonify({'erro': 'Nenhuma marca encontrada com esse filtro.'}), 404  # Retorna erro de nao encontrado.

        return jsonify({'marca': listar_marcas}), 200  # Retorna a lista de marcas encontradas.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro na busca.
        return jsonify({'erro': f'Erro ao buscar marca: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        cur.close()  # Fecha o cursor do banco.
