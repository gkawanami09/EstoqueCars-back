from main import app,con
from flask import jsonify,request



#Rotas de Servico

@app.route('/cadastrar_servico', methods=['POST'])
def cadastrar_servico():
    cur = con.cursor()
    try:

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
            return jsonify({'erro':'Valor invalido.Digite apenas número '}),400
        cur.execute("""SELECT ID_SERVICO FROM SERVICO WHERE LOWER(NOME_SERVICO)= LOWER(?)""", (nome_servico,))
        if cur.fetchone():
            return jsonify({'erro':'Serviço já cadastrado'})

        cur.execute("INSERT INTO SERVICO (NOME_SERVICO, VALOR) VALUES (?, ?)", (nome_servico, valor))
        con.commit()

        return jsonify({'menssagem':'Seviço cadastrado com sucesso!'}), 201

    except Exception as e:
        return jsonify({'erro':f'Erro ao cadastrar: {e}'}), 500
    finally:
        cur.close()

@app.route('/atualizar_servico/<int:id_servico>',methods=['PUT'])
def atualizar_servico(id_servico):
    cur = con.cursor()
    try:
        nome_servico = request.form.get('nome_servico')
        valor = request.form.get('valor')
        if not nome_servico or not valor:
            return jsonify({'erro':'Porfavor adicione todos os cmapos'})

        cur.execute("""UPDATE SERVICO SET NOME_SERVICO = ?, VALOR = ? 
        WHERE ID_SERVICO = ? """,(nome_servico,valor,id_servico))
        con.commit()

        return jsonify({'messagem': f'Sucesso ao dar Erro ao atualizar o serviço '}), 201

    except Exception as e:
        return jsonify({'erro':f'Erro ao atualizar serviço {e}'}),500
    finally:
        cur.close()

@app.route('/listar_servico',methods=['GET'])
def listar_servico():
    cur = con.cursor()
    try:
        cur.execute("SELECT ID_SERVICO SERVICO,NOME_SERVICO,VALOR  FROM SERVICO ORDER BY NOME_SERVICO ASC")
        servico = cur.fetchall()

        lista_servico = []
        for s in servico:
            lista_servico.append({
                'servico': s[0],
                'nome_servico': s[1],
                'valor': float(s[2])
            })

        return jsonify(lista_servico), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao listar servico {e}'}), 500

@app.route('/deletar_servico/<int:id_servico>',methods=['DELETE'])
def deletar_servico(id_servico):
    cur = con.cursor()
    try:
        cur.execute("""SELECT ID_ITEM FROM ITEM_MANUTENCAO WHERE ID_SERVICO = ?""",(id_servico,))
        if cur.fetchone():
            return jsonify({'erro':'Operação bloqueada: Este servico ja esta vinculadoa a uma manuterncao no hisatorico'}), 409
        cur.execute("""DELETE FROM SERVICO WHERE ID_SERVICO = ?""",(id_servico,))
        con.commit()
        return jsonify({'messagem':'Serviço deletado com sucesso!'}), 200
    except Exception as e:
        return jsonify({'erro':f'Erro ao deletar servico {e}'})
    finally:
        cur.close()