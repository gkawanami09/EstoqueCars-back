from main import app,con
from flask import jsonify,request
import jwt



@app.route('/cadastrar_servico', methods=['POST'])
def cadastrar_servico():
    cur = con.cursor()
    token = request.cookies.get('access_token')
    if not token:
        return jsonify({"erro": "Acesso negado. Token não encontrado."}), 401
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        id_adm = payload['id_user']
        cur.execute("SELECT TIPO_USUARIO FROM USUARIO WHERE ID_USUARIO= ?", (id_adm,))
        usuarios = cur.fetchone()

        if not usuarios or usuarios[0] != 2:
            return jsonify({'erro': 'Acesso restrito. Apenas administradores podem acessar.'}), 403
        nome_servico = request.form.get('nome_servico')
        valor = request.form.get('valor')

        if not nome_servico or not valor:
            return jsonify({'erro':'O nome do serviço e o valor são obrigatórios.'}),400

        nome_servico = nome_servico.strip()

        try:
            valor = float(valor.replace(',','.'))
            if valor <= 0:
                return jsonify({'erro':'O valor serviço deve ser maior que zero'}),400
        except ValueError:
            return jsonify({'erro':'Valor inválido. Digite apenas números.'}),400
        cur.execute("""SELECT ID_SERVICO FROM SERVICO WHERE LOWER(NOME_SERVICO)= LOWER(?)""", (nome_servico,))
        if cur.fetchone():
            return jsonify({'erro':'Serviço já cadastrado'})

        cur.execute("INSERT INTO SERVICO (NOME_SERVICO, VALOR) VALUES (?, ?)", (nome_servico, valor))
        con.commit()

        return jsonify({'mensagem':'Serviço cadastrado com sucesso!'}), 201

    except Exception as e:
        return jsonify({'erro':f'Erro ao cadastrar: {e}'}), 500
    finally:
        cur.close()


@app.route('/atualizar_servico/<int:id_servico>', methods=['PUT'])
def atualizar_servico(id_servico):
    cur = con.cursor()
    try:
        nome_servico = request.form.get('nome_servico')
        valor_novo = request.form.get('valor')



        if not nome_servico or not valor_novo:
            return jsonify({'erro': 'Por favor, adicione todos os campos.'}), 400


        cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))
        resultado = cur.fetchone()

        if not resultado:
            return jsonify({'erro': 'Serviço não encontrado.'}), 404

        valor_antigo = resultado[0]

        if float(valor_novo) != float(valor_antigo):
            cur.execute("""
                INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) 
                VALUES (?, ?)
            """, (id_servico, valor_antigo))


        cur.execute("""
            UPDATE SERVICO SET NOME_SERVICO = ?, VALOR = ? 
            WHERE ID_SERVICO = ? 
        """, (nome_servico, valor_novo, id_servico))

        con.commit()
        return jsonify({'mensagem': 'Serviço atualizado e histórico registrado!'}), 200

    except Exception as e:
        return jsonify({'erro': f'Erro ao atualizar: {e}'}), 500
    finally:
        cur.close()

@app.route('/buscar_servico', methods=['POST'])
def buscar_servico():
    cur = con.cursor()
    dados = request.get_json()
    descricao = dados.get('descricao')
    id_servico = dados.get('id_servico')
    valor_unitario = dados.get('valor_unitario')


    try:

        lista_servicos = []

        if descricao:
            descricao = descricao.upper()
            cur.execute("""
                SELECT ID_SERVICO, NOME_SERVICO, VALOR
                FROM SERVICO 
                WHERE UPPER(NOME_SERVICO) LIKE ?
            """, (f'%{descricao}%',))

        elif id_servico:
            cur.execute("""
                SELECT ID_SERVICO, NOME_SERVICO, VALOR
                FROM SERVICO 
                WHERE ID_SERVICO = ?
            """, (id_servico,))

        elif valor_unitario:
            valor_unitario = float(valor_unitario)
            cur.execute("""
                SELECT ID_SERVICO, NOME_SERVICO, VALOR
                FROM SERVICO 
                WHERE VALOR = ?
            """, (valor_unitario,))

        else:
            cur.execute("""
                SELECT ID_SERVICO, NOME_SERVICO, VALOR
                FROM SERVICO
            """)

        servicos = cur.fetchall()

        for servico in servicos:
            id_servico_banco = servico[0]
            descricao_banco = servico[1]
            valor_atual = servico[2]

            cur.execute("""
                SELECT VALOR_UNITARIO
                FROM HISTORICO_SERVICO
                WHERE ID_SERVICO = ?
                ORDER BY DATA_HISTORICO DESC
            """, (id_servico_banco,))

            historico = cur.fetchone()

            valor_porcentagem = 0

            if historico:
                valor_historico = historico[0]

                if valor_historico != 0:
                    valor_porcentagem = (valor_atual - valor_historico) / valor_historico * 100
                    valor_porcentagem = round(valor_porcentagem, 2)

            lista_servicos.append({
                'id_servico': id_servico_banco,
                'descricao': descricao_banco,
                'valor_unitario': valor_atual,
                'valor_porcentagem': valor_porcentagem
            })

        if not lista_servicos:
            return jsonify({'mensagem': 'Serviço não encontrado'}), 404

        return jsonify({'servicos': lista_servicos}), 200

    except Exception as e:
        return jsonify({'mensagem': f'Erro ao listar serviços: {e}'}), 500
    finally:
        cur.close()



@app.route('/deletar_servico/<int:id_servico>',methods=['DELETE'])
def deletar_servico(id_servico):
    cur = con.cursor()
    try:
        cur.execute("""SELECT ID_ITEM FROM ITEM_MANUTENCAO WHERE ID_SERVICO = ?""",(id_servico,))
        if cur.fetchone():
            return jsonify({'erro':'Operação bloqueada: Este serviço já está vinculado a uma manutenção no histórico.'}), 409
        cur.execute("""DELETE FROM SERVICO WHERE ID_SERVICO = ?""",(id_servico,))
        con.commit()
        return jsonify({'mensagem':'Serviço deletado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao deletar servico {e}'})
    finally:
        cur.close()


@app.route('/reajustar_servicos', methods=['PUT'])
def reajustar_servicos():
    cur = con.cursor()
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({'erro': 'Envie os dados no formato JSON.'}), 400

        porcentagem = dados.get('porcentagem')
        id_servico = dados.get('id_servico')

        if porcentagem is None:
            return jsonify({'erro': 'A porcentagem de reajuste é obrigatória.'}), 400

        try:
            porcentagem = float(porcentagem)
            if porcentagem <= 0:
                return jsonify({'erro': 'A porcentagem deve ser maior que zero.'}), 400
        except ValueError:
            return jsonify({'erro': 'Porcentagem inválida. Digite apenas números.'}), 400

        if id_servico:

            cur.execute("SELECT VALOR FROM SERVICO WHERE ID_SERVICO = ?", (id_servico,))
            resultado = cur.fetchone()

            if not resultado:
                return jsonify({'erro': 'Serviço não encontrado.'}), 404

            valor_antigo = float(resultado[0])
            novo_valor = round(valor_antigo * (1 + (porcentagem / 100)), 2)

            cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)", (id_servico, valor_antigo))
            cur.execute("UPDATE SERVICO SET VALOR = ? WHERE ID_SERVICO = ?", (novo_valor, id_servico))
            
            mensagem = 'Serviço reajustado com sucesso!'
        else:
          
            cur.execute("SELECT ID_SERVICO, VALOR FROM SERVICO")
            servicos = cur.fetchall()

            if not servicos:
                return jsonify({'erro': 'Nenhum serviço cadastrado para reajustar.'}), 404

            for servico in servicos:
                id_srv = servico[0]
                valor_antigo = float(servico[1])
                novo_valor = round(valor_antigo * (1 + (porcentagem / 100)), 2)

                cur.execute("INSERT INTO HISTORICO_SERVICO (ID_SERVICO, VALOR_UNITARIO) VALUES (?, ?)", (id_srv, valor_antigo))
                cur.execute("UPDATE SERVICO SET VALOR = ? WHERE ID_SERVICO = ?", (novo_valor, id_srv))
            
            mensagem = 'Todos os serviços foram reajustados com sucesso!'

        con.commit()
        return jsonify({'mensagem': mensagem}), 200
    except Exception as e:
        return jsonify({'erro': f'Erro ao reajustar serviços: {e}'}), 500
    finally:
        cur.close()