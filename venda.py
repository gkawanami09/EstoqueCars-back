# Importa o objeto app do Flask e a conexao com o banco de dados.
from main import app, con

# Importa jsonify para retornar JSON e request para ler dados enviados na requisicao.
from flask import jsonify, request

# Importa datetime para tratar datas e os para montar caminhos de arquivos.
import datetime, os

# Importa a funcao que gera o QR Code e o codigo copia e cola do PIX.
from function import gerar_pix

JUROS_PADRAO = 4


# Cria a rota que cadastra uma venda usando o metodo POST.
@app.route('/cadastrar_venda', methods=['POST'])
def cadastrar_venda():
    # Cria um cursor para executar comandos SQL no banco.
    cur = con.cursor()

    # Usa try para capturar erros durante o cadastro da venda.
    try:
        # Pega os dados enviados por formulario ou, se nao tiver formulario, pega JSON.
        dados = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})

        # Pega o ID do usuario enviado na requisicao.
        id_usuario = dados.get('id_usuario')
        # Pega o ID do veiculo enviado na requisicao.
        id_veiculo = dados.get('id_veiculo')
        # Pega a forma de pagamento escolhida.
        forma_pagamento = dados.get('forma_pagamento')
        # Pega a data da venda.
        data_venda = dados.get('data_venda')
        # Pega o valor total da venda.
        valor_venda = dados.get('valor_venda')
        # Pega o valor recebido na venda.
        valor_recebido = dados.get('valor_recebido')
        # Pega o status do pagamento.
        status_pagamento = dados.get('status_pagamento')
        # Pega comentarios opcionais da venda.
        comentarios = dados.get('comentarios')
        # Pega o desconto; se nao vier nada, usa 0.
        desconto = dados.get('desconto', 0)

        # Pega o arquivo de comprovante enviado, se existir.
        comprovante = request.files.get('comprovante')

        # Cria uma lista com todos os campos obrigatorios da venda.
        campos_obrigatorios = [
            id_usuario,        # ID do usuario que esta cadastrando a venda.
            id_veiculo,        # ID do veiculo que sera vendido.
            forma_pagamento,   # Forma de pagamento escolhida pelo cliente.
            data_venda,        # Data e horario em que a venda foi feita.
            valor_venda,       # Valor total da venda.
            valor_recebido,    # Valor que foi recebido no pagamento.
            status_pagamento   # Status do pagamento da venda.
        ]

        # Percorre a lista e verifica se algum campo esta vazio ou sem valor.
        if any(campo is None or (isinstance(campo, str) and not campo.strip()) for campo in campos_obrigatorios):
            # Se algum campo obrigatorio estiver vazio, retorna erro para o front-end.
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400

        # Converte a forma de pagamento para numero inteiro.
        forma_pagamento = int(forma_pagamento)
        # Converte o valor da venda para numero decimal.
        valor_venda = float(valor_venda)
        # Converte o valor recebido para numero decimal.
        valor_recebido = float(valor_recebido)
        # Converte o desconto para numero decimal; se vier vazio, usa 0.
        desconto = float(desconto or 0)

        # Inicia a chave PIX como vazia.
        chave_pix = None
        # Inicia o nome do recebedor PIX como vazio.
        nome_recebedor_pix = None
        # Inicia a cidade do recebedor PIX como vazia.
        cidade_recebedor_pix = None

        # Se a forma de pagamento for 0, o pagamento sera PIX.
        if forma_pagamento == 0:
            # Pega a chave PIX enviada ou a chave configurada no backend.
            chave_pix = dados.get('chave_pix') or app.config.get('PIX_CHAVE')
            # Pega o nome do recebedor enviado ou usa o nome padrao.
            nome_recebedor_pix = dados.get('nome_recebedor_pix') or app.config.get('PIX_NOME', 'ESTOQUE CARS')
            # Pega a cidade enviada ou usa a cidade padrao.
            cidade_recebedor_pix = dados.get('cidade_recebedor_pix') or app.config.get('PIX_CIDADE', 'SAO PAULO')

            # Verifica se a chave PIX existe.
            if not chave_pix:
                # Retorna erro se nao houver chave PIX.
                return jsonify({'erro': 'Chave PIX nao informada. Envie "chave_pix" ou configure PIX_CHAVE no backend.'}), 400

        # Verifica se o desconto passou do limite permitido.
        if desconto > 10:
            # Retorna erro se o desconto for maior que 10%.
            return jsonify({'erro' : 'Seu desconto esta muito alto, ele pode ser ate 10%'})

        # Verifica se o desconto e negativo.
        if desconto < 0:
            # Retorna erro se o desconto for menor que 0.
            return jsonify({'erro' : 'O desconto deve ser maior ou igual a 0'})

        # Converte a data da venda de texto para objeto datetime.
        data_venda = datetime.datetime.strptime(data_venda, '%d/%m/%Y %H:%M')

        # Consulta o veiculo no banco para saber se ele existe e qual e o status dele.
        cur.execute(
            """
            SELECT ID_VEICULO, STATUS_ESTOQUE
            FROM VEICULO
            WHERE ID_VEICULO = ?
            """, (id_veiculo,)
        )

        # Pega o primeiro veiculo encontrado na consulta.
        veiculo = cur.fetchone()

        # Verifica se o veiculo nao foi encontrado.
        if not veiculo:
            # Retorna erro se nao existir veiculo com esse ID.
            return jsonify({'erro' : 'Veiculo nao encontrado'})

        # Pega o status do estoque do veiculo.
        status = veiculo[1]

        # Status 2 significa que o veiculo ja foi vendido.
        if status == 2:
            # Retorna erro para impedir vender um veiculo ja vendido.
            return jsonify({'erro' : 'Este veiculo ja foi vendido.'})

        # Status 3 significa que o veiculo esta indisponivel.
        if status == 3:
            # Retorna erro para impedir vender um veiculo indisponivel.
            return jsonify({'erro' : 'Este veiculo esta indisponivel no momento.'})

        # Consulta o usuario no banco para saber se ele existe.
        cur.execute(
            """
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
            """, (id_usuario,)
        )

        # Pega o primeiro usuario encontrado na consulta.
        usuario = cur.fetchone()

        # Verifica se o usuario nao foi encontrado.
        if not usuario:
            # Retorna erro se nao existir usuario com esse ID.
            return jsonify({'error' : 'Usuario nao encontrado'})

        # Verifica se foi enviado um comprovante.
        if comprovante:
            # Define o nome do arquivo do comprovante.
            nome_imagem = f'comprovante_{id_veiculo}.png'
            # Monta o caminho onde o comprovante sera salvo.
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            # Salva o arquivo de comprovante na pasta de uploads.
            comprovante.save(caminho_foto)

        # Insere a venda no banco e retorna o ID da venda criada.
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

        # Pega o ID da venda que acabou de ser cadastrada.
        id_venda = cur.fetchone()[0]

        # Atualiza o status do veiculo para vendido.
        cur.execute(
        """
        UPDATE VEICULO
        SET STATUS_ESTOQUE = 2
        WHERE ID_VEICULO = ?
        """, (id_veiculo,)
        )

        # Define o valor que sera usado no PIX.
        valor_pix = valor_recebido

        # Inicia a URL do QR Code PIX como vazia.
        pix_qrcode = None
        # Inicia o codigo copia e cola do PIX como vazio.
        pix_copia_cola = None

        # Se a venda for paga por PIX, gera o QR Code e o copia e cola.
        if forma_pagamento == 0:
            # Cria um identificador unico para o PIX da venda.
            txid_pix = f'VENDA{id_venda}'
            # Chama a funcao responsavel por gerar o PIX.
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_pix,
                pasta='pix',
                txid=txid_pix
            )
            # Pega o caminho da imagem do QR Code e troca barras invertidas por barras normais.
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            # Monta a URL que o front-end pode usar para mostrar o QR Code.
            pix_qrcode = f"/uploads/{caminho_pix.lstrip('/')}"
            # Pega o codigo copia e cola do PIX.
            pix_copia_cola = pix_gerado.get('payload')

        # Se a forma de pagamento for 1, o pagamento sera parcelado.
        if forma_pagamento == 1:
            # Verifica se os dados obrigatorios do parcelamento foram enviados.
            if (
                dados.get('valor_parcelado') is None or
                (isinstance(dados.get('valor_parcelado'), str) and not dados.get('valor_parcelado').strip()) or
                dados.get('quantidade_parcelas') is None or
                (isinstance(dados.get('quantidade_parcelas'), str) and not dados.get('quantidade_parcelas').strip())
            ):
                # Retorna erro se faltar valor da parcela ou quantidade de parcelas.
                return jsonify({'erro': 'valor_parcelado e quantidade_parcelas sao obrigatorios para pagamento parcelado'}), 400

            # Converte o valor de cada parcela para numero decimal.
            valor_parcela = float(dados.get('valor_parcelado'))
            # Converte a quantidade de parcelas para numero inteiro.
            quantidade_parcelas = int(dados.get('quantidade_parcelas'))
            # Calcula o valor total do parcelamento.
            valor_total_parcelado = valor_parcela * quantidade_parcelas
            # Chama uma procedure do banco para inserir as parcelas.
            cur.execute(
            """
             EXECUTE PROCEDURE pr_insere_parcelas(?, ?, ?, ?)
            """, (valor_parcela, quantidade_parcelas, valor_total_parcelado, id_venda))

        # Confirma todas as alteracoes feitas no banco.
        con.commit()

        # Cria a resposta de sucesso.
        resposta = {'mensagem': 'Venda cadastrada com sucesso'}

        # Se foi gerado QR Code PIX, adiciona ele na resposta.
        if pix_qrcode:
            resposta['pix_qrcode'] = pix_qrcode

        # Se foi gerado copia e cola PIX, adiciona ele na resposta.
        if pix_copia_cola:
            resposta['pix_copia_cola'] = pix_copia_cola

        # Retorna a resposta em JSON com status 201, que significa criado com sucesso.
        return jsonify(resposta), 201

    # Captura qualquer erro que acontecer no cadastro.
    except Exception as e:
        # Retorna erro 500 com a mensagem do erro.
        return jsonify({'erro' : f'Erro ao cadastrar veiculo {e}'}), 500

    # O finally sempre executa, tendo erro ou nao.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para listar vendas de um usuario usando GET.
@app.route('/listar_vendas_usuario', methods=['GET'])
def listar_vendas_usuario():
    # Cria um cursor para executar comandos SQL.
    cur = con.cursor()

    # Usa try para capturar erros durante a listagem.
    try:
        # Pega o ID do usuario enviado pela URL.
        id_usuario = request.args.get('id_usuario')

        # Verifica se o ID do usuario nao foi enviado.
        if not id_usuario:
            # Retorna erro se faltar o ID do usuario.
            return jsonify({'erro': 'id_usuario e obrigatorio'}), 400

        # Consulta as vendas do usuario, juntando dados do veiculo, marca e parcelas.
        cur.execute(
            """
            SELECT V.ID_VENDA,
                   V.ID_USUARIO,
                   V.ID_VEICULO,
                   V.FORMA_PAGAMENTO,
                   V.DATA_VENDA,
                   V.VALOR_VENDA,
                   V.VALOR_RECEBIDO,
                   V.STATUS_PAGAMENTO,
                   VE.MODELO,
                   M.MARCA,
                   P.QUANTIDADE_PARCELAS
            FROM VENDA V
            LEFT JOIN VEICULO VE
                ON VE.ID_VEICULO = V.ID_VEICULO
            LEFT JOIN MARCA M
                ON M.ID_MARCA = VE.ID_MARCA
            LEFT JOIN PARCELAMENTO P
                ON P.ID_VENDA = V.ID_VENDA
            WHERE V.ID_USUARIO = ?
            ORDER BY V.DATA_VENDA DESC
            """,
            (id_usuario,)
        )

        # Cria uma lista vazia para guardar as vendas formatadas.
        vendas = []

        # Percorre todas as vendas retornadas pelo banco.
        for row in cur.fetchall():
            # Monta o nome do veiculo juntando marca e modelo.
            nome_veiculo = ' '.join(str(item or '').strip() for item in [row[9], row[8]] if str(item or '').strip())

            # Adiciona uma venda formatada na lista.
            vendas.append({
                'id_venda': row[0],              # ID da venda.
                'id_usuario': row[1],            # ID do usuario.
                'id_veiculo': row[2],            # ID do veiculo.
                'forma_pagamento': row[3],       # Forma de pagamento.
                'data_venda': row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4]),  # Data formatada.
                'valor_venda': float(row[5] or 0),      # Valor total da venda.
                'valor_recebido': float(row[6] or 0),   # Valor recebido.
                'status_pagamento': row[7],      # Status do pagamento.
                'modelo': row[8],                # Modelo do veiculo.
                'marca': row[9],                 # Marca do veiculo.
                'veiculo': nome_veiculo or row[8] or 'Veiculo',  # Nome completo do veiculo.
                'quantidade_parcelas': row[10]   # Quantidade de parcelas, se houver.
            })

        # Retorna a lista de vendas em JSON.
        return jsonify({'vendas': vendas}), 200

    # Captura erros que acontecerem durante a listagem.
    except Exception as e:
        # Retorna erro 500 com a mensagem do erro.
        return jsonify({'erro': f'Erro ao listar vendas do usuario {e}'}), 500

    # Sempre executa ao final.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para listar e gerar PIX das parcelas de uma venda.
@app.route('/listar_pix_parcelas/<int:id_venda>', methods=['GET'])
def listar_pix_parcelas(id_venda):
    # Cria um cursor para executar comandos SQL.
    cur = con.cursor()

    # Usa try para capturar erros durante a geracao dos PIX das parcelas.
    try:
        # Pega a chave PIX da URL ou da configuracao do backend.
        chave_pix = request.args.get('chave_pix') or app.config.get('PIX_CHAVE')
        # Pega o nome do recebedor PIX da URL ou usa o padrao.
        nome_recebedor_pix = request.args.get('nome_recebedor_pix') or app.config.get('PIX_NOME', 'ESTOQUE CARS')
        # Pega a cidade do recebedor PIX da URL ou usa o padrao.
        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix') or app.config.get('PIX_CIDADE', 'SAO PAULO')

        # Verifica se existe chave PIX configurada.
        if not chave_pix:
            # Retorna erro se nao houver chave PIX.
            return jsonify({'erro': 'Chave PIX nao informada. Configure PIX_CHAVE no backend.'}), 400

        # Consulta as parcelas da venda no banco.
        cur.execute("""
            SELECT P.ID_PARCELAMENTO,
                   P.ID_VENDA,
                   I.ID_ITEM_PARCELAMENTO,
                   I.NUMERO_PARCELA,
                   I.VALOR_PARCELA,
                   I.DATA_VENCIMENTO,
                   I.SITUACAO_PARCELA
            FROM PARCELAMENTO P
            INNER JOIN ITEM_PARCELAMENTO I
                ON I.ID_PARCELAMENTO = P.ID_PARCELAMENTO
            WHERE P.ID_VENDA = ?
            ORDER BY I.NUMERO_PARCELA
        """, (id_venda,))

        # Pega todas as linhas retornadas pela consulta.
        linhas = cur.fetchall()

        # Verifica se nenhuma parcela foi encontrada.
        if not linhas:
            # Retorna erro 404 se a venda nao tiver parcelas.
            return jsonify({'erro': 'Nenhuma parcela encontrada para esta venda.'}), 404

        # Cria uma lista vazia para guardar as parcelas formatadas.
        parcelas = []

        # Percorre cada parcela encontrada.
        for linha in linhas:
            # Pega o ID do item da parcela.
            id_item_parcelamento = linha[2]
            # Pega o numero da parcela.
            numero_parcela = linha[3]
            # Pega o valor da parcela e converte para decimal.
            valor_parcela = float(linha[4] or 0)
            # Pega a data de vencimento da parcela.
            data_vencimento = linha[5]
            # Pega a situacao da parcela.
            situacao_parcela = linha[6]

            # Cria um identificador unico para o PIX da parcela.
            txid_pix = f'PARC{id_item_parcelamento}'

            # Gera o PIX da parcela.
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_parcela,
                pasta='parcelas',
                txid=txid_pix
            )

            # Pega o caminho da imagem gerada e normaliza as barras.
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')

            # Adiciona a parcela formatada na lista de parcelas.
            parcelas.append({
                'id_item_parcelamento': id_item_parcelamento,  # ID do item da parcela.
                'numero_parcela': numero_parcela,              # Numero da parcela.
                'valor_parcela': valor_parcela,                # Valor da parcela.
                'data_vencimento': data_vencimento.strftime('%d/%m/%Y') if hasattr(data_vencimento, 'strftime') else str(data_vencimento),  # Data formatada.
                'situacao_parcela': situacao_parcela,          # Situacao da parcela.
                'pix_qrcode': f"/uploads/{caminho_pix.lstrip('/')}",  # URL do QR Code PIX.
                'pix_copia_cola': pix_gerado.get('payload')    # Codigo PIX copia e cola.
            })

        # Retorna todas as parcelas com os dados de PIX.
        return jsonify({'parcelas': parcelas}), 200

    # Captura erros durante a geracao do PIX das parcelas.
    except Exception as e:
        # Retorna erro 500 com a mensagem do erro.
        return jsonify({'erro': f'Erro ao gerar Pix das parcelas: {e}'}), 500

    # Sempre executa ao final.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para marcar uma parcela como paga depois que o Pix for copiado.
@app.route('/pagar_parcela_pix/<int:id_item_parcelamento>', methods=['POST'])
def pagar_parcela_pix(id_item_parcelamento):
    # Cria um cursor para executar comandos SQL.
    cur = con.cursor()

    # Usa try para capturar erros e manter o banco consistente.
    try:
        # Busca a parcela, o parcelamento e a venda vinculada.
        cur.execute("""
            SELECT I.ID_PARCELAMENTO,
                   I.SITUACAO_PARCELA,
                   P.ID_VENDA
            FROM ITEM_PARCELAMENTO I
            INNER JOIN PARCELAMENTO P
                ON P.ID_PARCELAMENTO = I.ID_PARCELAMENTO
            WHERE I.ID_ITEM_PARCELAMENTO = ?
        """, (id_item_parcelamento,))

        # Pega a parcela encontrada.
        parcela = cur.fetchone()

        # Retorna erro se o id nao existir.
        if not parcela:
            return jsonify({'erro': 'Parcela nao encontrada.'}), 404

        # Separa os dados necessarios para atualizar a parcela e a venda.
        id_parcelamento = parcela[0]
        situacao_parcela = parcela[1]
        id_venda = parcela[2]

        # Marca a parcela como paga quando ainda estiver pendente.
        if int(situacao_parcela or 0) != 1:
            cur.execute("""
                UPDATE ITEM_PARCELAMENTO
                SET SITUACAO_PARCELA = 1
                WHERE ID_ITEM_PARCELAMENTO = ?
            """, (id_item_parcelamento,))

        # Conta quantas parcelas continuam pendentes no mesmo parcelamento.
        cur.execute("""
            SELECT COUNT(*)
            FROM ITEM_PARCELAMENTO
            WHERE ID_PARCELAMENTO = ?
              AND COALESCE(SITUACAO_PARCELA, 0) <> 1
        """, (id_parcelamento,))

        # Pega a quantidade de pendencias.
        parcelas_pendentes = cur.fetchone()[0]

        # Se nao existe mais pendencia, quita parcelamento e venda.
        compra_quitada = parcelas_pendentes == 0
        if compra_quitada:
            cur.execute("""
                UPDATE PARCELAMENTO
                SET SITUACAO_PARCELAMENTO = 1
                WHERE ID_PARCELAMENTO = ?
            """, (id_parcelamento,))

            cur.execute("""
                UPDATE VENDA
                SET STATUS_PAGAMENTO = 0
                WHERE ID_VENDA = ?
            """, (id_venda,))

        # Confirma as alteracoes no banco.
        con.commit()

        # Retorna o novo estado para o front atualizar a tela.
        return jsonify({
            'mensagem': 'Parcela marcada como paga.',
            'id_venda': id_venda,
            'id_item_parcelamento': id_item_parcelamento,
            'situacao_parcela': 1,
            'parcela_paga': True,
            'compra_quitada': compra_quitada,
            'parcelas_pendentes': parcelas_pendentes
        }), 200

    # Retorna erro se algo falhar.
    except Exception as e:
        con.rollback()
        return jsonify({'erro': f'Erro ao pagar parcela: {e}'}), 500

    # Fecha o cursor no final.
    finally:
        cur.close()


# Cria a rota para buscar as configuracoes da empresa.
@app.route('/configuracoes', methods=['GET'])
def obter_configuracoes():
    # Cria um cursor para executar comandos SQL.
    cur = con.cursor()

    # Usa try para capturar erros durante a busca das configuracoes.
    try:
        # Consulta as configuracoes da empresa de ID 1.
        cur.execute("""
            SELECT NOME_EMPRESA, CNPJ, TELEFONE_EMPRESA, EMAIL_CONTATO, 
                   TAXA_JURO, COR_PRIMARIA, COR_SECUNDARIA, FONTE_VISUAL
            FROM CONFIGURACAO WHERE ID_EMPRESA = 1
        """)

        # Pega a primeira configuracao encontrada.
        config = cur.fetchone()

        # Verifica se nao encontrou configuracao.
        if not config:
            # Retorna erro 404 se nao existir configuracao.
            return jsonify({'erro': ''}), 404

        # Usa juros padrao quando a configuracao estiver vazia ou zerada.
        taxa_juro = float(config[4] or 0)
        if taxa_juro <= 0:
            taxa_juro = JUROS_PADRAO

        # Monta o dicionario com os dados da configuracao.
        dados = {
            'nome_empresa': config[0],              # Nome da empresa.
            'cnpj': config[1],                      # CNPJ da empresa.
            'telefone_empresa': config[2],          # Telefone da empresa.
            'email_contato': config[3],             # Email de contato.
            'taxa_juro': taxa_juro,                 # Taxa de juros.
            'taxa_juros': taxa_juro,                # Mesmo valor, com outro nome para compatibilidade.
            'cor_primaria': config[5] or '#FFFFFF', # Cor primaria da interface.
            'cor_secundaria': config[6] or '#000000', # Cor secundaria da interface.
            'fonte_visual': config[7] or 'Arial',   # Fonte usada na interface.
            'logo_url': f"http://seu-servidor.com/uploads/logo_empresa.png"  # URL da logo da empresa.
        }

        # Retorna as configuracoes em JSON.
        return jsonify(dados), 200

    # Captura erros durante a busca das configuracoes.
    except Exception as e:
        # Retorna erro 500 com a mensagem do erro.
        return jsonify({'erro': f'Erro na configuaracoes{e}'}), 500

    # Sempre executa ao final.
    finally:
        # Fecha o cursor do banco.
        cur.close()


# Cria a rota para atualizar as configuracoes da empresa.
@app.route('/configuracoes', methods=['PUT'])
def atualizar_configuracoes():
    # Cria um cursor para executar comandos SQL.
    cur = con.cursor()

    # Usa try para capturar erros durante a atualizacao das configuracoes.
    try:
        # Pega os dados enviados pelo formulario.
        dados = request.form

        # Pega o nome da empresa.
        nome_empresa = dados.get('nome_empresa')
        # Pega o CNPJ da empresa.
        cnpj = dados.get('cnpj')
        # Pega o telefone da empresa.
        telefone = dados.get('telefone_empresa')
        # Pega o email de contato.
        email = dados.get('email_contato')
        # Pega a taxa de juros e converte para decimal; se nao vier nada, usa o padrao.
        taxa_juro = float(dados.get('taxa_juro') or dados.get('taxa_juros') or JUROS_PADRAO)

        # Verifica se a taxa de juros e negativa.
        if taxa_juro < 0:
            # Retorna erro se a taxa de juros for menor que 0.
            return jsonify({'erro': 'A taxa de juros nao pode ser negativa'}), 400

        # Se vier 0, mantem o juros padrao de 4%.
        if taxa_juro == 0:
            taxa_juro = JUROS_PADRAO

        # Pega a cor primaria da interface.
        cor_primaria = dados.get('cor_primaria')
        # Pega a cor secundaria da interface.
        cor_secundaria = dados.get('cor_secundaria')
        # Pega a fonte visual da interface.
        fonte_visual = dados.get('fonte_visual')

        # Pega o arquivo da logo enviado, se existir.
        logo = request.files.get('logo')

        # Verifica se uma logo foi enviada.
        if logo:
            # Monta o caminho da logo, sempre usando o mesmo nome para substituir a antiga.
            caminho_logo = os.path.join(app.config['UPLOAD_FOLDER'], 'logo_empresa.png')
            # Salva a logo na pasta de uploads.
            logo.save(caminho_logo)

        # Atualiza as configuracoes da empresa no banco.
        cur.execute("""
            UPDATE CONFIGURACAO 
            SET NOME_EMPRESA=?, CNPJ=?, TELEFONE_EMPRESA=?, EMAIL_CONTATO=?, 
                TAXA_JURO=?, COR_PRIMARIA=?, COR_SECUNDARIA=?, FONTE_VISUAL=?
            WHERE ID_EMPRESA = 1
        """, (nome_empresa, cnpj, telefone, email, taxa_juro, cor_primaria, cor_secundaria, fonte_visual))

        # Confirma a atualizacao no banco.
        con.commit()

        # Retorna mensagem de sucesso.
        return jsonify({'mensagem': 'Configuracoes atualizadas com sucesso!'}), 200

    # Captura erros durante a atualizacao das configuracoes.
    except Exception as e :
        # Retorna erro 500 com a mensagem do erro.
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500

    # Sempre executa ao final.
    finally:
        # Fecha o cursor do banco.
        cur.close()
