# Importa recursos do módulo main.
from main import app, con  # Importa a aplicacao Flask e a conexao com o banco.
# Importa recursos do módulo flask.
from flask import jsonify, request  # Importa recursos para responder JSON e ler requisicoes.
# Importa módulos usados por este arquivo.
import jwt  # Importa a biblioteca usada para validar tokens JWT.


@app.route('/cadastrar_servico', methods=['POST'])  # Define a rota POST para cadastrar servicos.
# Declara a função cadastrar_servico usada neste fluxo.
def cadastrar_servico():  # Cria a funcao responsavel pelo cadastro de servico.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para executar comandos no banco.
    # Define token para uso nas próximas etapas.
    token = request.cookies.get('access_token')  # Tenta buscar o token salvo nos cookies.
    # Verifica esta condição antes de continuar o fluxo.
    if not token:  # Verifica se o token nao veio pelo cookie.
        # Define auth_header para uso nas próximas etapas.
        auth_header = request.headers.get('Authorization', '')  # Busca o cabecalho Authorization.
        # Verifica esta condição antes de continuar o fluxo.
        if auth_header.lower().startswith('bearer '):  # Confere se o cabecalho usa o formato Bearer.
            # Define token para uso nas próximas etapas.
            token = auth_header.split(' ', 1)[1].strip()  # Extrai o token depois da palavra Bearer.

    # Verifica esta condição antes de continuar o fluxo.
    if not token:  # Bloqueia a requisicao se nenhum token foi encontrado.
        # Retorna o resultado desta operação.
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401  # Retorna erro de nao autenticado.
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido para cadastro e validacao.
        # Define payload para uso nas próximas etapas.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])  # Decodifica e valida o JWT.
        # Define id_adm para uso nas próximas etapas.
        id_adm = payload['id_user']  # Recupera o id do usuario logado no token.
        # Executa este comando no banco de dados.
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))  # Busca o tipo do usuario.
        # Define usuarios para uso nas próximas etapas.
        usuarios = cur.fetchone()  # Recupera o primeiro usuario encontrado.

        # Verifica esta condição antes de continuar o fluxo.
        if not usuarios or usuarios[0] != 2:  # Verifica se o usuario existe e se e administrador.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Acesso restrito. Apenas administradores podem acessar.'}), 403  # Retorna acesso proibido.
        # Define nome_servico para uso nas próximas etapas.
        nome_servico = request.form.get('nome_servico')  # Lê o nome do servico enviado pelo formulario.
        # Define valor para uso nas próximas etapas.
        valor = request.form.get('valor')  # Lê o valor do servico enviado pelo formulario.

        # Verifica esta condição antes de continuar o fluxo.
        if not nome_servico or not valor:  # Valida se os campos obrigatorios foram preenchidos.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'O nome do serviço e o valor são obrigatórios.'}), 400  # Retorna erro de validacao.

        # Define nome_servico para uso nas próximas etapas.
        nome_servico = nome_servico.strip()  # Remove espacos extras do inicio e fim do nome.

        # Inicia uma operação protegida para permitir o tratamento de erros.
        try:  # Inicia a conversao do valor para numero.
            # Define valor para uso nas próximas etapas.
            valor = float(valor.replace(',', '.'))  # Troca virgula por ponto e converte para float.
            # Verifica esta condição antes de continuar o fluxo.
            if valor <= 0:  # Verifica se o valor informado e positivo.
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'O valor serviço deve ser maior que zero'}), 400  # Retorna erro para valor invalido.
        except ValueError:  # Captura erro quando o valor nao pode ser convertido.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Valor inválido. Digite apenas números.'}), 400  # Retorna erro de formato numerico.
        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_SERVICO FROM SERVICO WHERE LOWER(NOME_SERVICO) = LOWER(?)", (nome_servico,))  # Busca servico com nome igual.
        # Verifica esta condição antes de continuar o fluxo.
        if cur.fetchone():  # Verifica se ja existe um servico com o mesmo nome.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Serviço já cadastrado'}), 409  # Retorna conflito para cadastro duplicado.

        # Executa este comando no banco de dados.
        cur.execute("INSERT INTO SERVICO (NOME_SERVICO, VALOR) VALUES (?, ?)", (nome_servico, valor))  # Insere o servico no banco.
        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma a insercao no banco.

        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Serviço cadastrado com sucesso!'}), 201  # Retorna sucesso com status de criado.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente por gentileza.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro no cadastro.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao cadastrar: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final, mesmo com erro.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/atualizar_servico/<int:id_servico>', methods=['PUT'])  # Define a rota PUT para atualizar um servico.
# Declara a função atualizar_servico usada neste fluxo.
def atualizar_servico(id_servico):  # Cria a funcao que atualiza servico pelo id.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para usar o banco.
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido da atualizacao.
        # Define nome_servico para uso nas próximas etapas.
        nome_servico = request.form.get('nome_servico')  # Lê o novo nome do servico.
        # Define valor_novo para uso nas próximas etapas.
        valor_novo = request.form.get('valor')  # Lê o novo valor do servico.

        # Verifica esta condição antes de continuar o fluxo.
        if not nome_servico or not valor_novo:  # Verifica se todos os campos foram enviados.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Por favor, adicione todos os campos.'}), 400  # Retorna erro de campos faltando.

        # Executa este comando no banco de dados.
        cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Busca o valor atual do servico.
        # Define resultado para uso nas próximas etapas.
        resultado = cur.fetchone()  # Recupera o resultado da consulta.

        # Verifica esta condição antes de continuar o fluxo.
        if not resultado:  # Verifica se o servico nao foi encontrado.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Serviço não encontrado.'}), 404  # Retorna erro de nao encontrado.

        # Define valor_antigo para uso nas próximas etapas.
        valor_antigo = resultado[0]  # Guarda o valor antigo do servico.

        # Verifica esta condição antes de continuar o fluxo.
        if float(valor_novo) != float(valor_antigo):  # Verifica se houve mudanca no valor.
            # Executa este comando no banco de dados.
            cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)", (id_servico, valor_antigo))  # Salva o valor antigo no historico.

        # Executa este comando no banco de dados.
        cur.execute("UPDATE SERVICO SET NOME_SERVICO = ?, VALOR = ? WHERE ID_SERVICO = ?", (nome_servico, valor_novo, id_servico))  # Atualiza nome e valor.

        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma a atualizacao no banco.
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Serviço atualizado e histórico registrado!'}), 200  # Retorna sucesso da atualizacao.

    except Exception as e:  # Captura qualquer erro na atualizacao.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/buscar_servico', methods=['POST'])  # Define a rota POST para buscar servicos.
# Declara a função buscar_servico usada neste fluxo.
def buscar_servico():  # Cria a funcao responsavel pela busca.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para consultas no banco.
    # Define dados para uso nas próximas etapas.
    dados = request.get_json()  # Lê o corpo JSON enviado na requisicao.
    # Define descricao para uso nas próximas etapas.
    descricao = dados.get('descricao')  # Recupera a descricao usada como filtro.
    # Define id_servico para uso nas próximas etapas.
    id_servico = dados.get('id_servico')  # Recupera o id usado como filtro.
    # Define valor_unitario para uso nas próximas etapas.
    valor_unitario = dados.get('valor_unitario')  # Recupera o valor usado como filtro.

    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido da busca.

        # Define lista_servicos para uso nas próximas etapas.
        lista_servicos = []  # Cria a lista que recebera os servicos formatados.

        # Verifica esta condição antes de continuar o fluxo.
        if descricao:  # Verifica se a busca deve ser feita pela descricao.
            # Define descricao para uso nas próximas etapas.
            descricao = descricao.upper()  # Converte a descricao para maiusculas.
            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO WHERE UPPER(NOME_SERVICO) LIKE ?", (f'%{descricao}%',))  # Busca servicos pelo nome.

        # Verifica esta condição antes de continuar o fluxo.
        elif id_servico:  # Verifica se a busca deve ser feita pelo id.
            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Busca servico pelo id.

        # Verifica esta condição antes de continuar o fluxo.
        elif valor_unitario:  # Verifica se a busca deve ser feita pelo valor.
            # Define valor_unitario para uso nas próximas etapas.
            valor_unitario = float(valor_unitario)  # Converte o valor recebido para float.
            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO WHERE VALOR = ?", (valor_unitario,))  # Busca servicos pelo valor.

        else:  # Executa quando nenhum filtro foi informado.
            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO")  # Busca todos os servicos.

        # Define servicos para uso nas próximas etapas.
        servicos = cur.fetchall()  # Recupera todos os servicos retornados pela consulta.

        # Percorre os itens necessários para executar esta etapa.
        for servico in servicos:  # Percorre cada servico encontrado.
            # Define id_servico_banco para uso nas próximas etapas.
            id_servico_banco = servico[0]  # Guarda o id do servico.
            # Define descricao_banco para uso nas próximas etapas.
            descricao_banco = servico[1]  # Guarda o nome do servico.
            # Define valor_atual para uso nas próximas etapas.
            valor_atual = servico[2]  # Guarda o valor atual do servico.

            # Executa este comando no banco de dados.
            cur.execute("SELECT VALOR_UNITARIO FROM HISTORICO_SERVICO WHERE ID_SERVICO = ? ORDER BY DATA_HISTORICO DESC", (id_servico_banco,))  # Busca o ultimo valor historico.

            # Define historico para uso nas próximas etapas.
            historico = cur.fetchone()  # Recupera o ultimo registro de historico.

            # Define valor_porcentagem para uso nas próximas etapas.
            valor_porcentagem = 0  # Define a porcentagem padrao quando nao ha historico.

            # Verifica esta condição antes de continuar o fluxo.
            if historico:  # Verifica se existe historico para o servico.
                # Define valor_historico para uso nas próximas etapas.
                valor_historico = historico[0]  # Guarda o valor anterior do servico.

                # Verifica esta condição antes de continuar o fluxo.
                if valor_historico != 0:  # Evita divisao por zero.
                    # Define valor_porcentagem para uso nas próximas etapas.
                    valor_porcentagem = (valor_atual - valor_historico) / valor_historico * 100  # Calcula a variacao percentual.
                    # Define valor_porcentagem para uso nas próximas etapas.
                    valor_porcentagem = round(valor_porcentagem, 2)  # Arredonda a porcentagem para duas casas.

            # Executa append nesta etapa do fluxo.
            lista_servicos.append({  # Adiciona o servico formatado na lista.
                'id_servico': id_servico_banco,  # Inclui o id do servico.
                'descricao': descricao_banco,  # Inclui a descricao do servico.
                'valor_unitario': valor_atual,  # Inclui o valor atual.
                'valor_porcentagem': valor_porcentagem  # Inclui a variacao percentual.
            })  # Finaliza o dicionario do servico.

        # Verifica esta condição antes de continuar o fluxo.
        if not lista_servicos:  # Verifica se nenhum servico foi encontrado.
            # Retorna o resultado desta operação.
            return jsonify({'mensagem': 'Serviço não encontrado'}), 404  # Retorna mensagem de nao encontrado.

        # Retorna o resultado desta operação.
        return jsonify({'servicos': lista_servicos}), 200  # Retorna a lista de servicos encontrados.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer erro na listagem.
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': f'Erro ao listar serviços: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da busca.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/deletar_servico/<int:id_servico>', methods=['DELETE'])  # Define a rota DELETE para apagar servico.
# Declara a função deletar_servico usada neste fluxo.
def deletar_servico(id_servico):  # Cria a funcao que deleta servico pelo id.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para executar comandos no banco.
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido da exclusao.
        # Executa este comando no banco de dados.
        cur.execute("SELECT ID_ITEM FROM ITEM_MANUTENCAO WHERE ID_SERVICO = ?", (id_servico,))  # Verifica vinculo com manutencao.
        # Verifica esta condição antes de continuar o fluxo.
        if cur.fetchone():  # Confere se existe item de manutencao usando o servico.
            # Retorna o resultado desta operação.
            return jsonify(  # Monta a resposta de bloqueio da exclusao.
                {'erro': 'Operação bloqueada: Este serviço já está vinculado a uma manutenção no histórico.'}  # Explica o motivo do bloqueio.
            ), 409  # Retorna conflito porque o servico esta vinculado.
        # Executa este comando no banco de dados.
        cur.execute("DELETE FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Apaga o servico pelo id.
        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma a exclusao no banco.
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': 'Serviço deletado com sucesso!'}), 200  # Retorna sucesso da exclusao.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer erro na exclusao.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao deletar servico {e}'})  # Retorna erro com detalhes.
    finally:  # Executa ao final da exclusao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.


@app.route('/reajustar_servicos', methods=['PUT'])  # Define a rota PUT para reajustar servicos.
# Declara a função reajustar_servicos usada neste fluxo.
def reajustar_servicos():  # Cria a funcao responsavel pelo reajuste.
    # Define cur para uso nas próximas etapas.
    cur = con.cursor()  # Abre um cursor para comandos no banco.
    # Inicia uma operação protegida para permitir o tratamento de erros.
    try:  # Inicia o bloco protegido do reajuste.
        # Define dados para uso nas próximas etapas.
        dados = request.get_json()  # Lê os dados JSON da requisicao.
        # Verifica esta condição antes de continuar o fluxo.
        if not dados:  # Verifica se o corpo JSON foi enviado.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400  # Retorna erro quando nao ha JSON.

        # Define porcentagem para uso nas próximas etapas.
        porcentagem = dados.get('porcentagem')  # Recupera a porcentagem de reajuste.
        # Define id_servico para uso nas próximas etapas.
        id_servico = dados.get('id_servico')  # Recupera o id do servico, se enviado.

        # Verifica esta condição antes de continuar o fluxo.
        if porcentagem is None:  # Verifica se a porcentagem foi informada.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'A porcentagem de reajuste é obrigatória.'}), 400  # Retorna erro de campo obrigatorio.

        # Inicia uma operação protegida para permitir o tratamento de erros.
        try:  # Inicia a validacao numerica da porcentagem.
            # Define porcentagem para uso nas próximas etapas.
            porcentagem = float(porcentagem)  # Converte a porcentagem para float.
            # Verifica esta condição antes de continuar o fluxo.
            if porcentagem <= 0:  # Verifica se a porcentagem e positiva.
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'A porcentagem deve ser maior que zero.'}), 400  # Retorna erro para porcentagem invalida.
        except ValueError:  # Captura erro se a porcentagem nao for numerica.
            # Retorna o resultado desta operação.
            return jsonify({'erro': 'Porcentagem inválida. Digite apenas números.'}), 400  # Retorna erro de formato numerico.

        # Verifica esta condição antes de continuar o fluxo.
        if id_servico:  # Verifica se o reajuste sera aplicado a um unico servico.

            # Executa este comando no banco de dados.
            cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Busca o valor atual do servico.
            # Define resultado para uso nas próximas etapas.
            resultado = cur.fetchone()  # Recupera o resultado da consulta.

            # Verifica esta condição antes de continuar o fluxo.
            if not resultado:  # Verifica se o servico informado nao existe.
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Serviço não encontrado.'}), 404  # Retorna erro de nao encontrado.

            # Define valor_antigo para uso nas próximas etapas.
            valor_antigo = float(resultado[0])  # Guarda o valor antigo como numero.
            # Define novo_valor para uso nas próximas etapas.
            novo_valor = round(valor_antigo * (1 + (porcentagem / 100)), 2)  # Calcula o novo valor reajustado.

            # Executa este comando no banco de dados.
            cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)",  # Prepara registro do historico.
                        (id_servico, valor_antigo))  # Salva id do servico e valor antigo.
            # Executa este comando no banco de dados.
            cur.execute("UPDATE SERVICO SET VALOR = ? WHERE ID_SERVICO = ?", (novo_valor, id_servico))  # Atualiza o valor do servico.

            # Define mensagem para uso nas próximas etapas.
            mensagem = 'Serviço reajustado com sucesso!'  # Define a mensagem para reajuste individual.
        else:  # Executa quando o reajuste deve ser aplicado em todos os servicos.

            # Executa este comando no banco de dados.
            cur.execute("SELECT ID_SERVICO, VALOR FROM SERVICO")  # Busca todos os servicos e seus valores.
            # Define servicos para uso nas próximas etapas.
            servicos = cur.fetchall()  # Recupera todos os servicos cadastrados.

            # Verifica esta condição antes de continuar o fluxo.
            if not servicos:  # Verifica se nao ha servicos cadastrados.
                # Retorna o resultado desta operação.
                return jsonify({'erro': 'Nenhum serviço cadastrado para reajustar.'}), 404  # Retorna erro de lista vazia.

            # Percorre os itens necessários para executar esta etapa.
            for servico in servicos:  # Percorre cada servico cadastrado.
                # Define id_srv para uso nas próximas etapas.
                id_srv = servico[0]  # Guarda o id do servico atual.
                # Define valor_antigo para uso nas próximas etapas.
                valor_antigo = float(servico[1])  # Guarda o valor antigo do servico atual.
                # Define novo_valor para uso nas próximas etapas.
                novo_valor = round(valor_antigo * (1 + (porcentagem / 100)), 2)  # Calcula o novo valor reajustado.

                # Executa este comando no banco de dados.
                cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)",  # Prepara registro historico.
                            (id_srv, valor_antigo))  # Salva o valor antigo no historico.
                # Executa este comando no banco de dados.
                cur.execute("UPDATE SERVICO SET VALOR = ? WHERE ID_SERVICO = ?", (novo_valor, id_srv))  # Atualiza o valor do servico.

            # Define mensagem para uso nas próximas etapas.
            mensagem = 'Todos os serviços foram reajustados com sucesso!'  # Define a mensagem para reajuste geral.

        # Confirma no banco todas as alterações realizadas.
        con.commit()  # Confirma todas as alteracoes no banco.
        # Retorna o resultado desta operação.
        return jsonify({'mensagem': mensagem}), 200  # Retorna a mensagem de sucesso.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        # Retorna o resultado desta operação.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer erro no reajuste.
        # Retorna o resultado desta operação.
        return jsonify({'erro': f'Erro ao reajustar serviços: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        # Fecha o recurso utilizado nesta operação.
        cur.close()  # Fecha o cursor do banco.
