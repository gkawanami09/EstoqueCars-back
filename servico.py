from main import app, con  # Importa a aplicacao Flask e a conexao com o banco.
from flask import jsonify, request  # Importa recursos para responder JSON e ler requisicoes.
import jwt  # Importa a biblioteca usada para validar tokens JWT.


@app.route('/cadastrar_servico', methods=['POST'])  # Define a rota POST para cadastrar servicos.
def cadastrar_servico():  # Cria a funcao responsavel pelo cadastro de servico.
    cur = con.cursor()  # Abre um cursor para executar comandos no banco.
    token = request.cookies.get('access_token')  # Tenta buscar o token salvo nos cookies.
    if not token:  # Verifica se o token nao veio pelo cookie.
        auth_header = request.headers.get('Authorization', '')  # Busca o cabecalho Authorization.
        if auth_header.lower().startswith('bearer '):  # Confere se o cabecalho usa o formato Bearer.
            token = auth_header.split(' ', 1)[1].strip()  # Extrai o token depois da palavra Bearer.

    if not token:  # Bloqueia a requisicao se nenhum token foi encontrado.
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401  # Retorna erro de nao autenticado.
    try:  # Inicia o bloco protegido para cadastro e validacao.
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])  # Decodifica e valida o JWT.
        id_adm = payload['id_user']  # Recupera o id do usuario logado no token.
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))  # Busca o tipo do usuario.
        usuarios = cur.fetchone()  # Recupera o primeiro usuario encontrado.

        if not usuarios or usuarios[0] != 2:  # Verifica se o usuario existe e se e administrador.
            return jsonify({'erro': 'Acesso restrito. Apenas administradores podem acessar.'}), 403  # Retorna acesso proibido.
        nome_servico = request.form.get('nome_servico')  # Lê o nome do servico enviado pelo formulario.
        valor = request.form.get('valor')  # Lê o valor do servico enviado pelo formulario.

        if not nome_servico or not valor:  # Valida se os campos obrigatorios foram preenchidos.
            return jsonify({'erro': 'O nome do serviço e o valor são obrigatórios.'}), 400  # Retorna erro de validacao.

        nome_servico = nome_servico.strip()  # Remove espacos extras do inicio e fim do nome.

        try:  # Inicia a conversao do valor para numero.
            valor = float(valor.replace(',', '.'))  # Troca virgula por ponto e converte para float.
            if valor <= 0:  # Verifica se o valor informado e positivo.
                return jsonify({'erro': 'O valor serviço deve ser maior que zero'}), 400  # Retorna erro para valor invalido.
        except ValueError:  # Captura erro quando o valor nao pode ser convertido.
            return jsonify({'erro': 'Valor inválido. Digite apenas números.'}), 400  # Retorna erro de formato numerico.
        cur.execute("SELECT ID_SERVICO FROM SERVICO WHERE LOWER(NOME_SERVICO) = LOWER(?)", (nome_servico,))  # Busca servico com nome igual.
        if cur.fetchone():  # Verifica se ja existe um servico com o mesmo nome.
            return jsonify({'erro': 'Serviço já cadastrado'}), 409  # Retorna conflito para cadastro duplicado.

        cur.execute("INSERT INTO SERVICO (NOME_SERVICO, VALOR) VALUES (?, ?)", (nome_servico, valor))  # Insere o servico no banco.
        con.commit()  # Confirma a insercao no banco.

        return jsonify({'mensagem': 'Serviço cadastrado com sucesso!'}), 201  # Retorna sucesso com status de criado.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente por gentileza.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        return jsonify({'erro': 'Token inválido'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer outro erro no cadastro.
        return jsonify({'erro': f'Erro ao cadastrar: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final, mesmo com erro.
        cur.close()  # Fecha o cursor do banco.


@app.route('/atualizar_servico/<int:id_servico>', methods=['PUT'])  # Define a rota PUT para atualizar um servico.
def atualizar_servico(id_servico):  # Cria a funcao que atualiza servico pelo id.
    cur = con.cursor()  # Abre um cursor para usar o banco.
    try:  # Inicia o bloco protegido da atualizacao.
        nome_servico = request.form.get('nome_servico')  # Lê o novo nome do servico.
        valor_novo = request.form.get('valor')  # Lê o novo valor do servico.

        if not nome_servico or not valor_novo:  # Verifica se todos os campos foram enviados.
            return jsonify({'erro': 'Por favor, adicione todos os campos.'}), 400  # Retorna erro de campos faltando.

        cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Busca o valor atual do servico.
        resultado = cur.fetchone()  # Recupera o resultado da consulta.

        if not resultado:  # Verifica se o servico nao foi encontrado.
            return jsonify({'erro': 'Serviço não encontrado.'}), 404  # Retorna erro de nao encontrado.

        valor_antigo = resultado[0]  # Guarda o valor antigo do servico.

        if float(valor_novo) != float(valor_antigo):  # Verifica se houve mudanca no valor.
            cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)", (id_servico, valor_antigo))  # Salva o valor antigo no historico.

        cur.execute("UPDATE SERVICO SET NOME_SERVICO = ?, VALOR = ? WHERE ID_SERVICO = ?", (nome_servico, valor_novo, id_servico))  # Atualiza nome e valor.

        con.commit()  # Confirma a atualizacao no banco.
        return jsonify({'mensagem': 'Serviço atualizado e histórico registrado!'}), 200  # Retorna sucesso da atualizacao.

    except Exception as e:  # Captura qualquer erro na atualizacao.
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        cur.close()  # Fecha o cursor do banco.


@app.route('/buscar_servico', methods=['POST'])  # Define a rota POST para buscar servicos.
def buscar_servico():  # Cria a funcao responsavel pela busca.
    cur = con.cursor()  # Abre um cursor para consultas no banco.
    dados = request.get_json()  # Lê o corpo JSON enviado na requisicao.
    descricao = dados.get('descricao')  # Recupera a descricao usada como filtro.
    id_servico = dados.get('id_servico')  # Recupera o id usado como filtro.
    valor_unitario = dados.get('valor_unitario')  # Recupera o valor usado como filtro.

    try:  # Inicia o bloco protegido da busca.

        lista_servicos = []  # Cria a lista que recebera os servicos formatados.

        if descricao:  # Verifica se a busca deve ser feita pela descricao.
            descricao = descricao.upper()  # Converte a descricao para maiusculas.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO WHERE UPPER(NOME_SERVICO) LIKE ?", (f'%{descricao}%',))  # Busca servicos pelo nome.

        elif id_servico:  # Verifica se a busca deve ser feita pelo id.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Busca servico pelo id.

        elif valor_unitario:  # Verifica se a busca deve ser feita pelo valor.
            valor_unitario = float(valor_unitario)  # Converte o valor recebido para float.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO WHERE VALOR = ?", (valor_unitario,))  # Busca servicos pelo valor.

        else:  # Executa quando nenhum filtro foi informado.
            cur.execute("SELECT ID_SERVICO, NOME_SERVICO, VALOR FROM SERVICO")  # Busca todos os servicos.

        servicos = cur.fetchall()  # Recupera todos os servicos retornados pela consulta.

        for servico in servicos:  # Percorre cada servico encontrado.
            id_servico_banco = servico[0]  # Guarda o id do servico.
            descricao_banco = servico[1]  # Guarda o nome do servico.
            valor_atual = servico[2]  # Guarda o valor atual do servico.

            cur.execute("SELECT VALOR_UNITARIO FROM HISTORICO_SERVICO WHERE ID_SERVICO = ? ORDER BY DATA_HISTORICO DESC", (id_servico_banco,))  # Busca o ultimo valor historico.

            historico = cur.fetchone()  # Recupera o ultimo registro de historico.

            valor_porcentagem = 0  # Define a porcentagem padrao quando nao ha historico.

            if historico:  # Verifica se existe historico para o servico.
                valor_historico = historico[0]  # Guarda o valor anterior do servico.

                if valor_historico != 0:  # Evita divisao por zero.
                    valor_porcentagem = (valor_atual - valor_historico) / valor_historico * 100  # Calcula a variacao percentual.
                    valor_porcentagem = round(valor_porcentagem, 2)  # Arredonda a porcentagem para duas casas.

            lista_servicos.append({  # Adiciona o servico formatado na lista.
                'id_servico': id_servico_banco,  # Inclui o id do servico.
                'descricao': descricao_banco,  # Inclui a descricao do servico.
                'valor_unitario': valor_atual,  # Inclui o valor atual.
                'valor_porcentagem': valor_porcentagem  # Inclui a variacao percentual.
            })  # Finaliza o dicionario do servico.

        if not lista_servicos:  # Verifica se nenhum servico foi encontrado.
            return jsonify({'mensagem': 'Serviço não encontrado'}), 404  # Retorna mensagem de nao encontrado.

        return jsonify({'servicos': lista_servicos}), 200  # Retorna a lista de servicos encontrados.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer erro na listagem.
        return jsonify({'mensagem': f'Erro ao listar serviços: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da busca.
        cur.close()  # Fecha o cursor do banco.


@app.route('/deletar_servico/<int:id_servico>', methods=['DELETE'])  # Define a rota DELETE para apagar servico.
def deletar_servico(id_servico):  # Cria a funcao que deleta servico pelo id.
    cur = con.cursor()  # Abre um cursor para executar comandos no banco.
    try:  # Inicia o bloco protegido da exclusao.
        cur.execute("SELECT ID_ITEM FROM ITEM_MANUTENCAO WHERE ID_SERVICO = ?", (id_servico,))  # Verifica vinculo com manutencao.
        if cur.fetchone():  # Confere se existe item de manutencao usando o servico.
            return jsonify(  # Monta a resposta de bloqueio da exclusao.
                {'erro': 'Operação bloqueada: Este serviço já está vinculado a uma manutenção no histórico.'}  # Explica o motivo do bloqueio.
            ), 409  # Retorna conflito porque o servico esta vinculado.
        cur.execute("DELETE FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Apaga o servico pelo id.
        con.commit()  # Confirma a exclusao no banco.
        return jsonify({'mensagem': 'Serviço deletado com sucesso!'}), 200  # Retorna sucesso da exclusao.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer erro na exclusao.
        return jsonify({'erro': f'Erro ao deletar servico {e}'})  # Retorna erro com detalhes.
    finally:  # Executa ao final da exclusao.
        cur.close()  # Fecha o cursor do banco.


@app.route('/reajustar_servicos', methods=['PUT'])  # Define a rota PUT para reajustar servicos.
def reajustar_servicos():  # Cria a funcao responsavel pelo reajuste.
    cur = con.cursor()  # Abre um cursor para comandos no banco.
    try:  # Inicia o bloco protegido do reajuste.
        dados = request.get_json()  # Lê os dados JSON da requisicao.
        if not dados:  # Verifica se o corpo JSON foi enviado.
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400  # Retorna erro quando nao ha JSON.

        porcentagem = dados.get('porcentagem')  # Recupera a porcentagem de reajuste.
        id_servico = dados.get('id_servico')  # Recupera o id do servico, se enviado.

        if porcentagem is None:  # Verifica se a porcentagem foi informada.
            return jsonify({'erro': 'A porcentagem de reajuste é obrigatória.'}), 400  # Retorna erro de campo obrigatorio.

        try:  # Inicia a validacao numerica da porcentagem.
            porcentagem = float(porcentagem)  # Converte a porcentagem para float.
            if porcentagem <= 0:  # Verifica se a porcentagem e positiva.
                return jsonify({'erro': 'A porcentagem deve ser maior que zero.'}), 400  # Retorna erro para porcentagem invalida.
        except ValueError:  # Captura erro se a porcentagem nao for numerica.
            return jsonify({'erro': 'Porcentagem inválida. Digite apenas números.'}), 400  # Retorna erro de formato numerico.

        if id_servico:  # Verifica se o reajuste sera aplicado a um unico servico.

            cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))  # Busca o valor atual do servico.
            resultado = cur.fetchone()  # Recupera o resultado da consulta.

            if not resultado:  # Verifica se o servico informado nao existe.
                return jsonify({'erro': 'Serviço não encontrado.'}), 404  # Retorna erro de nao encontrado.

            valor_antigo = float(resultado[0])  # Guarda o valor antigo como numero.
            novo_valor = round(valor_antigo * (1 + (porcentagem / 100)), 2)  # Calcula o novo valor reajustado.

            cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)",  # Prepara registro do historico.
                        (id_servico, valor_antigo))  # Salva id do servico e valor antigo.
            cur.execute("UPDATE SERVICO SET VALOR = ? WHERE ID_SERVICO = ?", (novo_valor, id_servico))  # Atualiza o valor do servico.

            mensagem = 'Serviço reajustado com sucesso!'  # Define a mensagem para reajuste individual.
        else:  # Executa quando o reajuste deve ser aplicado em todos os servicos.

            cur.execute("SELECT ID_SERVICO, VALOR FROM SERVICO")  # Busca todos os servicos e seus valores.
            servicos = cur.fetchall()  # Recupera todos os servicos cadastrados.

            if not servicos:  # Verifica se nao ha servicos cadastrados.
                return jsonify({'erro': 'Nenhum serviço cadastrado para reajustar.'}), 404  # Retorna erro de lista vazia.

            for servico in servicos:  # Percorre cada servico cadastrado.
                id_srv = servico[0]  # Guarda o id do servico atual.
                valor_antigo = float(servico[1])  # Guarda o valor antigo do servico atual.
                novo_valor = round(valor_antigo * (1 + (porcentagem / 100)), 2)  # Calcula o novo valor reajustado.

                cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)",  # Prepara registro historico.
                            (id_srv, valor_antigo))  # Salva o valor antigo no historico.
                cur.execute("UPDATE SERVICO SET VALOR = ? WHERE ID_SERVICO = ?", (novo_valor, id_srv))  # Atualiza o valor do servico.

            mensagem = 'Todos os serviços foram reajustados com sucesso!'  # Define a mensagem para reajuste geral.

        con.commit()  # Confirma todas as alteracoes no banco.
        return jsonify({'mensagem': mensagem}), 200  # Retorna a mensagem de sucesso.

    except jwt.ExpiredSignatureError:  # Captura token expirado.
        return jsonify({'erro': 'Sessão expirada. Faça login novamente.'}), 401  # Retorna erro de sessao expirada.
    except jwt.InvalidTokenError:  # Captura token invalido.
        return jsonify({'erro': 'Token inválido ou adulterado.'}), 401  # Retorna erro de token invalido.
    except Exception as e:  # Captura qualquer erro no reajuste.
        return jsonify({'erro': f'Erro ao reajustar serviços: {e}'}), 500  # Retorna erro interno com detalhes.
    finally:  # Executa ao final da requisicao.
        cur.close()  # Fecha o cursor do banco.
