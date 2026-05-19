from main import app, con
from flask import jsonify, request
import datetime, os
from function import gerar_pix

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

        if (
            id_usuario is None or (isinstance(id_usuario, str) and not id_usuario.strip()) or
            id_veiculo is None or (isinstance(id_veiculo, str) and not id_veiculo.strip()) or
            forma_pagamento is None or (isinstance(forma_pagamento, str) and not forma_pagamento.strip()) or
            data_venda is None or (isinstance(data_venda, str) and not data_venda.strip()) or
            valor_venda is None or (isinstance(valor_venda, str) and not valor_venda.strip()) or
            valor_recebido is None or (isinstance(valor_recebido, str) and not valor_recebido.strip()) or
            status_pagamento is None or (isinstance(status_pagamento, str) and not status_pagamento.strip())
        ):
            return jsonify({'erro': 'Todos os campos obrigatorios devem estar preenchidos'}), 400


        forma_pagamento = int(forma_pagamento)
        valor_venda = float(valor_venda)
        valor_recebido = float(valor_recebido)
        desconto = float(desconto or 0)

        chave_pix = None
        nome_recebedor_pix = None
        cidade_recebedor_pix = None

        if forma_pagamento == 0:
            chave_pix = dados.get('chave_pix') or app.config.get('PIX_CHAVE')
            nome_recebedor_pix = dados.get('nome_recebedor_pix') or app.config.get('PIX_NOME', 'ESTOQUE CARS')
            cidade_recebedor_pix = dados.get('cidade_recebedor_pix') or app.config.get('PIX_CIDADE', 'SAO PAULO')

            if not chave_pix:
                return jsonify({'erro': 'Chave PIX nao informada. Envie "chave_pix" ou configure PIX_CHAVE no backend.'}), 400

        if desconto > 10:
            return jsonify({'erro' : 'Seu desconto esta muito alto, ele pode ser ate 10%'})
        if desconto < 0:
            return jsonify({'erro' : 'O desconto deve ser maior ou igual a 0'})

        data_venda = datetime.datetime.strptime(data_venda, '%d/%m/%Y %H:%M')

        cur.execute(
            """
            SELECT ID_VEICULO, STATUS_ESTOQUE
            FROM VEICULO
            WHERE ID_VEICULO = ?
            """, (id_veiculo,)
        )
        veiculo = cur.fetchone()

        if not veiculo:
            return jsonify({'erro' : 'Veiculo nao encontrado'})
        status = veiculo[1]

        if status == 2:
            return jsonify({'erro' : 'Este veiculo ja foi vendido.'})

        if status == 3:
            return jsonify({'erro' : 'Este veiculo esta indisponivel no momento.'})

        cur.execute(
            """
            SELECT ID_USUARIO
            FROM USUARIO
            WHERE ID_USUARIO = ?
            """, (id_usuario,)
        )
        usuario = cur.fetchone()
        if not usuario:
            return jsonify({'error' : 'Usuario nao encontrado'})

        if comprovante:
            nome_imagem = f'comprovante_{id_veiculo}.png'
            caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], nome_imagem)
            comprovante.save(caminho_foto)

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

        id_venda = cur.fetchone()[0]
        cur.execute(
        """
        UPDATE VEICULO
        SET STATUS_ESTOQUE = 2
        WHERE ID_VEICULO = ?
        """, (id_veiculo,)
        )

        valor_pix = valor_recebido

        pix_qrcode = None
        pix_copia_cola = None
        if forma_pagamento == 0:
            txid_pix = f'VENDA{id_venda}'
            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_pix,
                pasta='pix',
                txid=txid_pix
            )
            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')
            pix_qrcode = f"/uploads/{caminho_pix.lstrip('/')}"
            pix_copia_cola = pix_gerado.get('payload')

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
            cur.execute(
            """
             EXECUTE PROCEDURE pr_insere_parcelas(?, ?, ?, ?)
            """, (valor_parcela, quantidade_parcelas, valor_total_parcelado, id_venda))

        con.commit()

        resposta = {'mensagem': 'Venda cadastrada com sucesso'}
        if pix_qrcode:
            resposta['pix_qrcode'] = pix_qrcode
        if pix_copia_cola:
            resposta['pix_copia_cola'] = pix_copia_cola
        return jsonify(resposta), 201
    except Exception as e:
        return jsonify({'erro' : f'Erro ao cadastrar veiculo {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_vendas_usuario', methods=['GET'])
def listar_vendas_usuario():
    cur = con.cursor()
    try:
        id_usuario = request.args.get('id_usuario')

        if not id_usuario:
            return jsonify({'erro': 'id_usuario e obrigatorio'}), 400

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

        vendas = []
        for row in cur.fetchall():
            nome_veiculo = ' '.join(str(item or '').strip() for item in [row[9], row[8]] if str(item or '').strip())
            vendas.append({
                'id_venda': row[0],
                'id_usuario': row[1],
                'id_veiculo': row[2],
                'forma_pagamento': row[3],
                'data_venda': row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4]),
                'valor_venda': float(row[5] or 0),
                'valor_recebido': float(row[6] or 0),
                'status_pagamento': row[7],
                'modelo': row[8],
                'marca': row[9],
                'veiculo': nome_veiculo or row[8] or 'Veiculo',
                'quantidade_parcelas': row[10]
            })

        return jsonify({'vendas': vendas}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar vendas do usuario {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_pix_parcelas/<int:id_venda>', methods=['GET'])
def listar_pix_parcelas(id_venda):
    cur = con.cursor()
    try:
        chave_pix = request.args.get('chave_pix') or app.config.get('PIX_CHAVE')
        nome_recebedor_pix = request.args.get('nome_recebedor_pix') or app.config.get('PIX_NOME', 'ESTOQUE CARS')
        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix') or app.config.get('PIX_CIDADE', 'SAO PAULO')

        if not chave_pix:
            return jsonify({'erro': 'Chave PIX não informada. Configure PIX_CHAVE no backend.'}), 400

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

        linhas = cur.fetchall()

        if not linhas:
            return jsonify({'erro': 'Nenhuma parcela encontrada para esta venda.'}), 404

        parcelas = []

        for linha in linhas:
            id_item_parcelamento = linha[2]
            numero_parcela = linha[3]
            valor_parcela = float(linha[4] or 0)
            data_vencimento = linha[5]
            situacao_parcela = linha[6]

            txid_pix = f'PARC{id_item_parcelamento}'

            pix_gerado = gerar_pix(
                chave=chave_pix,
                nome=nome_recebedor_pix,
                cidade=cidade_recebedor_pix,
                valor=valor_parcela,
                pasta='parcelas',
                txid=txid_pix
            )

            caminho_pix = str(pix_gerado.get('imagem', '')).replace('\\', '/')

            parcelas.append({
                'id_item_parcelamento': id_item_parcelamento,
                'numero_parcela': numero_parcela,
                'valor_parcela': valor_parcela,
                'data_vencimento': data_vencimento.strftime('%d/%m/%Y') if hasattr(data_vencimento, 'strftime') else str(data_vencimento),
                'situacao_parcela': situacao_parcela,
                'pix_qrcode': f"/uploads/{caminho_pix.lstrip('/')}",
                'pix_copia_cola': pix_gerado.get('payload')
            })

        return jsonify({'parcelas': parcelas}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Pix das parcelas: {e}'}), 500

    finally:
        cur.close()

@app.route('/configuracoes', methods=['GET'])
def obter_configuracoes():
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT NOME_EMPRESA, CNPJ, TELEFONE_EMPRESA, EMAIL_CONTATO, 
                   TAXA_JURO, COR_PRIMARIA, COR_SECUNDARIA, FONTE_VISUAL
            FROM CONFIGURACAO WHERE ID_EMPRESA = 1
        """)
        config = cur.fetchone()
        
        if not config:
            return jsonify({'erro': ''}), 404
            
        dados = {
            'nome_empresa': config[0],
            'cnpj': config[1],
            'telefone_empresa': config[2],
            'email_contato': config[3],
            'taxa_juro': float(config[4] or 0),
            'taxa_juros': float(config[4] or 0),
            'cor_primaria': config[5] or '#FFFFFF',
            'cor_secundaria': config[6] or '#000000',
            'fonte_visual': config[7] or 'Arial',
            # A URL da logo fica fixa, pois ela � salva direto no backend sempre com este nome:
            'logo_url': f"http://seu-servidor.com/uploads/logo_empresa.png" 
        }
        
        return jsonify(dados), 200
    except Exception as e:
        return jsonify({'erro': f'Erro na configuaracoes{e}'}), 500
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
        taxa_juro = float(dados.get('taxa_juro') or dados.get('taxa_juros') or 0)

        if taxa_juro < 0:
            return jsonify({'erro': 'A taxa de juros nao pode ser negativa'}), 400
        cor_primaria = dados.get('cor_primaria')
        cor_secundaria = dados.get('cor_secundaria')
        fonte_visual = dados.get('fonte_visual')
        
        # 1. Processamento do Upload da Logo (Salva apenas fisicamente na pasta)
        logo = request.files.get('logo')
        if logo:
            # Salva sempre com o mesmo nome para sobrescrever a antiga
            caminho_logo = os.path.join(app.config['UPLOAD_FOLDER'], 'logo_empresa.png')
            logo.save(caminho_logo)

        
        cur.execute("""
            UPDATE CONFIGURACAO 
            SET NOME_EMPRESA=?, CNPJ=?, TELEFONE_EMPRESA=?, EMAIL_CONTATO=?, 
                TAXA_JURO=?, COR_PRIMARIA=?, COR_SECUNDARIA=?, FONTE_VISUAL=?
            WHERE ID_EMPRESA = 1
        """, (nome_empresa, cnpj, telefone, email, taxa_juro, cor_primaria, cor_secundaria, fonte_visual))

        con.commit()
        return jsonify({'mensagem': 'Configurações atualizadas com sucesso!'}), 200

    except Exception as e :
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500
    finally:
        cur.close()


