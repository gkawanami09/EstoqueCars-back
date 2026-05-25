from main import app, con
from flask import jsonify, request
import datetime, os
from function import gerar_pix

JUROS_PADRAO = 4

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
        cur.execute("""
            DELETE
            FROM RESERVA_VEICULO
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
        con.rollback()
        return jsonify({'erro': f'Erro ao cadastrar venda: {e}'}), 500
    finally:
        cur.close()

@app.route('/listar_pendencias_venda', methods=['GET'])
def listar_pendencias_venda():
    cur = con.cursor()
    try:
        cur.execute(
            """
            SELECT V.ID_VEICULO,
                   V.MODELO,
                   M.MARCA,
                   V.PRECO,
                   V.STATUS_ESTOQUE,
                   RV.ID_USUARIO,
                   U.NOME,
                   RV.DATA_RESERVA
            FROM RESERVA_VEICULO RV
            INNER JOIN VEICULO V
                ON V.ID_VEICULO = RV.ID_VEICULO
            LEFT JOIN MARCA M
                ON M.ID_MARCA = V.ID_MARCA
            LEFT JOIN USUARIO U
                ON U.ID_USUARIO = RV.ID_USUARIO
            WHERE COALESCE(V.STATUS_ESTOQUE, 0) = 3
            ORDER BY RV.DATA_RESERVA DESC
            """
        )
        pendencias = []
        for row in cur.fetchall():
            nome_veiculo = ' '.join(
                str(item or '').strip() for item in [row[2], row[1]] if str(item or '').strip()
            )
            pendencias.append({
                'id_veiculo': row[0],
                'modelo': row[1],
                'marca': row[2],
                'veiculo': nome_veiculo or row[1] or 'Veiculo',
                'preco': float(row[3] or 0),
                'status_estoque': row[4],
                'id_usuario_reserva': row[5],
                'nome_usuario_reserva': row[6],
                'data_reserva': row[7].isoformat() if hasattr(row[7], 'isoformat') else str(row[7]),
                'precisa_concluir_venda': True,
                'status_venda': 'RESERVADO_PENDENTE_CONCLUSAO',
                'mensagem_venda': 'Reservado: precisa concluir a venda.'
            })
        return jsonify({'pendencias_venda': pendencias}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao listar pendencias de venda: {e}'}), 500
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

@app.route('/pix_venda/<int:id_venda>', methods=['GET'])
def pix_venda(id_venda):
    cur = con.cursor()
    try:
        chave_pix = request.args.get('chave_pix')
        cur.execute("""
            SELECT CHAVE_PIX, NOME_EMPRESA
            FROM CONFIGURACAO
            WHERE ID_EMPRESA = 1
        """)
        config_pix = cur.fetchone()
        if not chave_pix and config_pix:
            chave_pix = config_pix[0]
        nome_recebedor_pix = (
            request.args.get('nome_recebedor_pix') or
            (config_pix[1] if config_pix else None) or
            app.config.get('PIX_NOME', 'ESTOQUE CARS')
        )
        cidade_recebedor_pix = request.args.get('cidade_recebedor_pix') or app.config.get('PIX_CIDADE', 'SAO PAULO')
        if not chave_pix:
            return jsonify({'erro': 'Chave PIX da empresa nao configurada.'}), 400
        cur.execute("""
            SELECT ID_VENDA,
                   FORMA_PAGAMENTO,
                   VALOR_RECEBIDO
            FROM VENDA
            WHERE ID_VENDA = ?
        """, (id_venda,))
        venda = cur.fetchone()
        if not venda:
            return jsonify({'erro': 'Venda nao encontrada.'}), 404
        if int(venda[1] or 0) != 0:
            return jsonify({'erro': 'Esta venda nao foi paga por Pix a vista.'}), 400
        valor_recebido = float(venda[2] or 0)
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
        return jsonify({
            'id_venda': id_venda,
            'pix_qrcode': f"/uploads/{caminho_pix.lstrip('/')}",
            'pix_copia_cola': pix_gerado.get('payload')
        }), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar Pix da venda: {e}'}), 500
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
            return jsonify({'erro': 'Chave PIX nao informada. Configure PIX_CHAVE no backend.'}), 400
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

@app.route('/pagar_parcela_pix/<int:id_item_parcelamento>', methods=['POST'])
def pagar_parcela_pix(id_item_parcelamento):
    cur = con.cursor()
    try:
        cur.execute("""
            SELECT I.ID_PARCELAMENTO,
                   I.SITUACAO_PARCELA,
                   P.ID_VENDA
            FROM ITEM_PARCELAMENTO I
            INNER JOIN PARCELAMENTO P
                ON P.ID_PARCELAMENTO = I.ID_PARCELAMENTO
            WHERE I.ID_ITEM_PARCELAMENTO = ?
        """, (id_item_parcelamento,))
        parcela = cur.fetchone()
        if not parcela:
            return jsonify({'erro': 'Parcela nao encontrada.'}), 404
        id_parcelamento = parcela[0]
        situacao_parcela = parcela[1]
        id_venda = parcela[2]
        if int(situacao_parcela or 0) != 1:
            cur.execute("""
                UPDATE ITEM_PARCELAMENTO
                SET SITUACAO_PARCELA = 1
                WHERE ID_ITEM_PARCELAMENTO = ?
            """, (id_item_parcelamento,))
        cur.execute("""
            SELECT COUNT(*)
            FROM ITEM_PARCELAMENTO
            WHERE ID_PARCELAMENTO = ?
              AND COALESCE(SITUACAO_PARCELA, 0) <> 1
        """, (id_parcelamento,))
        parcelas_pendentes = cur.fetchone()[0]
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
        con.commit()
        return jsonify({
            'mensagem': 'Parcela marcada como paga.',
            'id_venda': id_venda,
            'id_item_parcelamento': id_item_parcelamento,
            'situacao_parcela': 1,
            'parcela_paga': True,
            'compra_quitada': compra_quitada,
            'parcelas_pendentes': parcelas_pendentes
        }), 200
    except Exception as e:
        con.rollback()
        return jsonify({'erro': f'Erro ao pagar parcela: {e}'}), 500
    finally:
        cur.close()

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
