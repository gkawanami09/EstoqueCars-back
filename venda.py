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
    cur = con.cursor()

    try:
        dados = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})

        id_usuario = dados.get('id_usuario')
        id_veiculo = dados.get('id_veiculo')
        forma_pagamento = dados.get('forma_pagamento')
        data_venda = dados.get('data_venda')
        valor_venda = dados.get('valor_venda')
        valor_recebido = dados.get('valor_recebido')
        status_pagamento = dados.get('status_pagamento')
        comentarios = dados.get('comentarios')
        desconto = dados.get('desconto', 0)
        comprovante = request.files.get('comprovante')

        campos_obrigatorios = [
            id_usuario,
            id_veiculo,
            forma_pagamento,
            data_venda,
            valor_venda,
            valor_recebido,
            status_pagamento
        ]

        if any(campo is None or (isinstance(campo, str) and not campo.strip()) for campo in campos_obrigatorios):
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400

        forma_pagamento = int(forma_pagamento)
        valor_venda = float(valor_venda)
        valor_recebido = float(valor_recebido)
        desconto = float(desconto or 0)

        if desconto > 10:
            return jsonify({'erro': 'Seu desconto esta muito alto, ele pode ser ate 10%'}), 400

        if desconto < 0:
            return jsonify({'erro': 'O desconto deve ser maior ou igual a 0'}), 400

        data_venda = datetime.datetime.strptime(data_venda, '%d/%m/%Y %H:%M')

        cur.execute("""
            SELECT ID_VEICULO, STATUS_ESTOQUE
            FROM VEICULO
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))

        veiculo = cur.fetchone()

        if not veiculo:
            return jsonify({'erro': 'Veiculo nao encontrado'}), 404

        status_estoque = int(veiculo[1] or 0)

        if status_estoque == 2:
            return jsonify({'erro': 'Este veiculo ja foi vendido.'}), 400

        # Status 1 = em estoque.
        # Status 3 = reservado. Pode virar venda.
        if status_estoque not in [1, 3]:
            return jsonify({'erro': 'Este veiculo nao esta disponivel para venda.'}), 400

        cur.execute("""
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
        """, (id_usuario,))

        usuario = cur.fetchone()

        if not usuario:
            return jsonify({'erro': 'Usuario nao encontrado'}), 404

        chave_pix = None
        nome_recebedor_pix = None
        cidade_recebedor_pix = None

        if forma_pagamento == 0:
            chave_pix = (
                dados.get('chave_pix') or
                dados.get('chave_pix_empresa') or
                dados.get('pix_chave')
            )

            cur.execute("""
                SELECT CHAVE_PIX, NOME_EMPRESA
                FROM CONFIGURACAO
                WHERE ID_EMPRESA = 1
            """)

            config_pix = cur.fetchone()

            if not chave_pix and config_pix:
                chave_pix = config_pix[0]

            nome_recebedor_pix = (
                dados.get('nome_recebedor_pix') or
                (config_pix[1] if config_pix else None) or
                app.config.get('PIX_NOME', 'ESTOQUE CARS')
            )

            cidade_recebedor_pix = (
                dados.get('cidade_recebedor_pix') or
                app.config.get('PIX_CIDADE', 'SAO PAULO')
            )

            if not chave_pix:
                return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400

        valor_parcela = None
        quantidade_parcelas = None
        valor_total_parcelado = None

        if forma_pagamento == 1:
            if (
                dados.get('valor_parcelado') is None or
                (isinstance(dados.get('valor_parcelado'), str) and not dados.get('valor_parcelado').strip()) or
                dados.get('quantidade_parcelas') is None or
                (isinstance(dados.get('quantidade_parcelas'), str) and not dados.get('quantidade_parcelas').strip())
            ):
                return jsonify({'erro': 'valor_parcelado e quantidade_parcelas sao obrigatorios para pagamento parcelado'}), 400

            valor_parcela = float(dados.get('valor_parcelado'))
            quantidade_parcelas = int(dados.get('quantidade_parcelas'))
            valor_total_parcelado = valor_parcela * quantidade_parcelas

        if comprovante:
            nome_imagem = f'comprovante_{id_veiculo}.png'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            comprovante.save(caminho_foto)

        cur.execute("""
            INSERT INTO VENDA(
                ID_USUARIO,
                ID_VEICULO,
                FORMA_PAGAMENTO,
                DATA_VENDA,
                VALOR_VENDA,
                VALOR_RECEBIDO,
                STATUS_PAGAMENTO,
                COMENTARIOS,
                DESCONTOS
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING ID_VENDA
        """, (
            id_usuario,
            id_veiculo,
            forma_pagamento,
            data_venda,
            valor_venda,
            valor_recebido,
            status_pagamento,
            comentarios,
            desconto
        ))

        id_venda = cur.fetchone()[0]

        cur.execute("""
            UPDATE VEICULO
            SET STATUS_ESTOQUE = 2
            WHERE ID_VEICULO = ?
        """, (id_veiculo,))

        pix_qrcode = None
        pix_copia_cola = None

        if forma_pagamento == 0:
            txid_pix = f'VENDA{id_venda}'

            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_recebido,
                pasta='pix',
                txid=txid_pix
            )

            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            pix_qrcode = f"/uploads/{caminho_pix.lstrip('/')}"
            pix_copia_cola = pix_gerado.get('payload')

        if forma_pagamento == 1:
            cur.execute("""
                EXECUTE PROCEDURE pr_insere_parcelas(?, ?, ?, ?)
            """, (
                valor_parcela,
                quantidade_parcelas,
                valor_total_parcelado,
                id_venda
            ))

        con.commit()

        resposta = {
            'mensagem': 'Venda cadastrada com sucesso',
            'id_venda': id_venda
        }

        if pix_qrcode:
            resposta['pix_qrcode'] = pix_qrcode

        if pix_copia_cola:
            resposta['pix_copia_cola'] = pix_copia_cola

        return jsonify(resposta), 201

    except Exception as e:
        return jsonify({'erro': f'Erro ao cadastrar venda: {e}'}), 500

    finally:
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
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT NOME_EMPRESA, CNPJ, TELEFONE_EMPRESA, EMAIL_CONTATO, 
                   TAXA_JURO, COR_PRIMARIA, COR_SECUNDARIA, FONTE_VISUAL,
                   CHAVE_PIX
            FROM CONFIGURACAO WHERE ID_EMPRESA = 1
        """)

        config = cur.fetchone()

        if not config:
            return jsonify({'erro': ''}), 404

        taxa_juro = float(config[4] or 0)
        if taxa_juro <= 0:
            taxa_juro = JUROS_PADRAO

        dados = {
            'nome_empresa': config[0],
            'cnpj': config[1],
            'telefone_empresa': config[2],
            'email_contato': config[3],
            'taxa_juro': taxa_juro,
            'taxa_juros': taxa_juro,
            'cor_primaria': config[5] or '#FFFFFF',
            'cor_secundaria': config[6] or '#000000',
            'fonte_visual': config[7] or 'Arial',
            'chave_pix': config[8] or '',
            'chave_pix_empresa': config[8] or '',
            'pix_chave': config[8] or '',
            'logo_url': f"http://seu-servidor.com/uploads/logo_empresa.png"
        }

        return jsonify(dados), 200

    except Exception as e:
        return jsonify({'erro': f'Erro na configuracoes {e}'}), 500

    finally:
        cur.close()
@app.route('/configuracoes', methods=['PUT'])
def atualizar_configuracoes():
    cur = con.cursor()

    try:
        dados = request.form

        nome_empresa = dados.get('nome_empresa')
        cnpj = dados.get('cnpj')
        telefone = dados.get('telefone_empresa')
        email = dados.get('email_contato')
        chave_pix = dados.get('chave_pix') or dados.get('chave_pix_empresa') or dados.get('pix_chave') or ''

        taxa_juro = float(dados.get('taxa_juro') or dados.get('taxa_juros') or JUROS_PADRAO)

        if taxa_juro < 0:
            return jsonify({'erro': 'A taxa de juros nao pode ser negativa'}), 400

        if taxa_juro == 0:
            taxa_juro = JUROS_PADRAO

        cor_primaria = dados.get('cor_primaria')
        cor_secundaria = dados.get('cor_secundaria')
        fonte_visual = dados.get('fonte_visual')

        logo = request.files.get('logo')

        if logo:
            caminho_logo = os.path.join(app.config['UPLOAD_FOLDER'], 'logo_empresa.png')
            logo.save(caminho_logo)

        cur.execute("""
            UPDATE CONFIGURACAO 
            SET NOME_EMPRESA=?, CNPJ=?, TELEFONE_EMPRESA=?, EMAIL_CONTATO=?, 
                TAXA_JURO=?, COR_PRIMARIA=?, COR_SECUNDARIA=?, FONTE_VISUAL=?,
                CHAVE_PIX=?
            WHERE ID_EMPRESA = 1
        """, (
            nome_empresa,
            cnpj,
            telefone,
            email,
            taxa_juro,
            cor_primaria,
            cor_secundaria,
            fonte_visual,
            chave_pix
        ))

        con.commit()

        return jsonify({'mensagem': 'Configuracoes atualizadas com sucesso!'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500

    finally:
        cur.close()