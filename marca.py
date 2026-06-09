# Importa recursos do módulo flask.
from flask import jsonify, request  # Importa recursos do Flask para respostas JSON e dados da requisicao.
# Importa módulos usados por este arquivo.
import jwt  # Importa a biblioteca usada para tratar erros de token JWT.
# Importa recursos do módulo main.
from main import app, con  # Importa a aplicacao Flask e a conexao com o banco.


@app.route('/cadastrar_marca', methods=['POST'])  # Define a rota POST para cadastrar uma marca.
# Declara a função cadastrar_marca usada neste fluxo.
def cadastrar_marca():  # Cria a funcao responsavel pelo cadastro de marca.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para executar comandos SQL.

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido do cadastro.
        # Define marca para uso nas próximas etapas.
        marca = request.form.get('marca')  # Busca o nome da marca enviado no formulario.
        # Verifica esta condição antes de continuar o fluxo.
        if not marca or marca.strip() == "":  # Verifica se a marca nao foi enviada ou esta vazia.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O nome da marca é obrigatório.'}), 400  # Retorna erro de campo obrigatorio.

        # Define nome_marca para uso nas próximas etapas.
        nome_marca = marca.strip().upper()  # Remove espacos extras e converte o nome para maiusculo.

        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_MARCA FROM MARCA WHERE LOWER(MARCA) = LOWER(?)", (nome_marca,))  # Procura marca com mesmo nome.
        # Verifica esta condição antes de continuar o fluxo.
        if cur.fetchone():  # Verifica se a marca ja existe no banco.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Essa marca já foi cadastrada.'}), 409  # Retorna conflito por cadastro duplicado.

        # Executa este comando no banco de dados.
        cur.execute("INSERT INTO MARCA (MARCA) VALUES (?)", (nome_marca,))  # Insere a nova marca no banco.
        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma a insercao no banco.

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Marca cadastrada com sucesso!'}), 201  # Retorna sucesso com status de criado.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro no cadastro.
        # Desfaz alterações parciais após uma falha.
        con.rollback()  # Desfaz alteracoes pendentes em caso de erro.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao cadastrar: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/editar_marca/<int:id_marca>', methods=['PUT'])  # Define a rota PUT para editar uma marca pelo id.
# Declara a função editar_marca usada neste fluxo.
def editar_marca(id_marca):  # Cria a funcao responsavel pela edicao da marca.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para executar comandos SQL.

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido da edicao.
        # Define nova_marca para uso nas próximas etapas.
        nova_marca = request.form.get('nova_marca')  # Busca o novo nome da marca no formulario.
        # Verifica esta condição antes de continuar o fluxo.
        if not nova_marca:  # Verifica se o novo nome nao foi enviado.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O nome da marca é obrigatório.'}), 400  # Retorna erro de campo obrigatorio.
        # Executa este comando no banco de dados.
        cur.execute("UPDATE MARCA SET MARCA = ? WHERE ID_MARCA = ?", (nova_marca.strip().upper(), id_marca))  # Atualiza a marca no banco.
        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma a atualizacao no banco.

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Marca editada com sucesso!'}), 200  # Retorna sucesso da edicao.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro na edicao.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao editar marca: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/deletar_marca/<int:id_marca>', methods=['DELETE'])  # Define a rota DELETE para apagar uma marca pelo id.
# Declara a função deletar_marca usada neste fluxo.
def deletar_marca(id_marca):  # Cria a funcao responsavel pela exclusao da marca.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para executar comandos SQL.

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido da exclusao.
        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_VEICULO FROM VEICULO WHERE ID_MARCA = ?", (id_marca,))  # Busca veiculo com a marca informada.

        # Verifica esta condição antes de continuar o fluxo.
        if cur.fetchone():  # Verifica se existe veiculo que bloqueia a exclusao.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Operação bloqueada: Esta marca possui veículos vinculados.'}), 409  # Retorna conflito quando a exclusao e bloqueada.

        # Executa este comando no banco de dados.
        cur.execute('DELETE FROM MARCA WHERE ID_MARCA = ?', (id_marca,))  # Exclui a marca pelo id.
        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma a exclusao no banco.
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Marca deletada com sucesso!'}), 200  # Retorna sucesso da exclusao.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro na exclusao.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao deletar marca: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/buscar_marca', methods=['POST'])  # Define a rota POST para buscar marcas.
# Declara a função buscar_marca usada neste fluxo.
def buscar_marca():  # Cria a funcao responsavel pela busca de marcas.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para consultar o banco.

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido da busca.
        # Define nome para uso nas próximas etapas.
        nome = request.form.get('nome')  # Busca o nome enviado como filtro.
        # Define id_marca para uso nas próximas etapas.
        id_marca = request.form.get('id_marca')  # Busca o id enviado como filtro.
        # Define listar_marcas para uso nas próximas etapas.
        listar_marcas = []  # Cria a lista que recebera as marcas encontradas.
        # Verifica esta condição antes de continuar o fluxo.
        if nome:  # Verifica se a busca deve ser feita pelo nome.
            # Define nome_formatado para uso nas próximas etapas.
            nome_formatado = nome.strip().upper()  # Remove espacos e converte o nome para maiusculo.

            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_MARCA, MARCA FROM MARCA WHERE UPPER(MARCA) LIKE ?", (f'%{nome_formatado}%',))  # Busca marcas parecidas com o nome.
        # Verifica esta condição antes de continuar o fluxo.
        elif id_marca:  # Verifica se a busca deve ser feita pelo id.
            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_MARCA, MARCA FROM MARCA WHERE ID_MARCA = ?", (id_marca,))  # Busca a marca pelo id.
        else:  # Executa quando nenhum filtro foi informado.
            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_MARCA, MARCA FROM MARCA")  # Busca todas as marcas.
        # Define marcas para uso nas próximas etapas.
        marcas = cur.fetchall()  # Recupera todas as marcas retornadas pela consulta.

        # Percorre os itens necessários para executar esta etapa.
        for marca in marcas:  # Percorre cada marca encontrada.
            # Executa append nesta etapa do fluxo.
            listar_marcas.append({  # Adiciona a marca formatada na lista.
                'id_marca': marca[0],  # Inclui o id da marca.
                'nome': marca[1],  # Inclui o nome da marca.
            })  # Finaliza o dicionario da marca.
        # Verifica esta condição antes de continuar o fluxo.
        if not listar_marcas:  # Verifica se nenhuma marca foi encontrada.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Nenhuma marca encontrada com esse filtro.'}), 404  # Retorna erro de nao encontrado.

        # Retorna o resultado desta operação.
        return jsonify({'marca': listar_marcas}), 200  # Retorna a lista de marcas encontradas.

    except jwt.ExpiredSignatureError:  # Captura erro de token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura erro de token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro na busca.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao buscar marca: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.
