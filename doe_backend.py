import traceback
import base64
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Permite CORS de qualquer origem

ELASTIC_USER = os.getenv('ELASTIC_USER')
ELASTIC_PASSWORD = os.getenv('ELASTIC_PASSWORD')
ELASTIC_INDEX_ENDPOINT = os.getenv('ELASTIC_INDEX_ENDPOINT')

# Configuração básica do logging
logging.basicConfig(level=logging.INFO)

def _build_cors_prelight_response():
    response = jsonify()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


@app.route('/search', methods=['GET', 'OPTIONS'])
def search():
    if request.method == 'OPTIONS':
        return _build_cors_prelight_response()

    texto_pesquisa = request.args.get('texto_pesquisa')
    numDoe = request.args.get('numDoe')
    postDateInicial = request.args.get('postDateInicial')
    postDateFinal = request.args.get('postDateFinal')
    tipoOrdenacao = request.args.get('tipoOrdenacao', 'relevancia')
    tipoBuscaTextual = request.args.get('tipoBuscaTextual', 'e') # "ou"  => busca com operador | "e"   => busca com operador   |  "frase" => busca pela frase exata

    # Pega o parâmetro 'size' da requisição, com um valor padrão de 10
    size = request.args.get('size', 50)

     # Certifica-se de que o valor de 'size' é um número inteiro
    try:
        size = int(size)
    except ValueError:
        return jsonify({"error": "O parâmetro 'size' deve ser um número inteiro válido"}), 400

    # Definindo o corpo da pesquisa dinamicamente com base nos parâmetros recebidos
    must_clauses = []

    if texto_pesquisa:
        if tipoBuscaTextual == "ou":
            # Busca utilizando operador OR (padrão) – retorna documentos que contenham qualquer termo
            must_clauses.append({
                "match": {
                    "texto_page_doe": {
                        "query": texto_pesquisa,
                        "operator": "or"
                    }
                }
            })
        elif tipoBuscaTextual == "frase":
            # Busca exata pela frase
            must_clauses.append({
                "match_phrase": {
                    "texto_page_doe": texto_pesquisa
                }
            })
        elif tipoBuscaTextual == "e":
            # Busca utilizando operador AND – retorna documentos que contenham todos os termos
            must_clauses.append({
                "match": {
                    "texto_page_doe": {
                        "query": texto_pesquisa,
                        "operator": "and"
                    }
                }
            })

    if numDoe:
        try:
            # Tenta converter numDoe para inteiro, se falhar, o campo será ignorado
            numDoe_int = int(numDoe)
            must_clauses.append({
                "term": {
                    "metadados.numDoe": numDoe_int
                }
            })
        except ValueError:
            # Se a conversão falhar, simplesmente ignoramos esse campo
            logging.info("Valor inválido para numDoe, ignorando este campo na pesquisa.")

    if postDateInicial or postDateFinal:
        range_query = {
            "range": {
                "metadados.postDate": {
                    "format": "yyyy-MM-dd"  
                }
            }
        }
        if postDateInicial:
            range_query["range"]["metadados.postDate"]["gte"] = postDateInicial
        if postDateFinal:
            range_query["range"]["metadados.postDate"]["lte"] = postDateFinal
        must_clauses.append(range_query)

    # Se nenhum critério de busca foi fornecido, retornar um erro
    if not must_clauses:
        return jsonify({"error": "Pelo menos um parâmetro de busca é obrigatório"}), 400
    
    # Definindo a ordenação com base no tipoOrdenacao
    sort = []
    if tipoOrdenacao == 'date_asc':
        sort.append({"metadados.postDate": {"order": "asc"}})
    elif tipoOrdenacao == 'date_desc':
        sort.append({"metadados.postDate": {"order": "desc"}})

    query = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "highlight": {
            "fields": {
                "texto_page_doe": {
                    "number_of_fragments": 5,  
                    "fragment_size": 200,  
                    "order": "score"     
                }
            }
        },
        "_source": ["metadados"],
         "size": size # Define o número de resultados retornados
    }

    # Adiciona o campo de ordenação à query se houver algum critério de ordenação
    if sort:
        query["sort"] = sort

    print(f"Query: {query}")

    try:
        authorization = base64.b64encode((ELASTIC_USER+":"+ELASTIC_PASSWORD).encode(encoding="utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {authorization}",
            "Content-Type": "application/json",
        }
        response = requests.post(ELASTIC_INDEX_ENDPOINT, json=query, headers=headers)
        response.raise_for_status()
        result = response.json()

        # Extrair os metadados e highlights dos documentos que correspondem à busca
        hits = result.get("hits", {}).get("hits", [])
        documentos = [
            {
                "metadados": hit["_source"]["metadados"],
                "highlight": hit.get("highlight", {}).get("texto_page_doe", [])
            }
            for hit in hits
        ]

        return jsonify({"documentos": documentos})

    except requests.RequestException as e:
        logging.error(f"Erro ao realizar a pesquisa no Elasticsearch: {e}")
        traceback.print_exc()
        return jsonify({"error": "Erro ao realizar a pesquisa"}), 500

# Novo endpoint para testar a API
@app.route('/version', methods=['GET'])
def version():
    return "1.0.6!", 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
