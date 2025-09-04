# 🔎 API de Busca no Elasticsearch

Esta API em Flask permite realizar buscas avançadas em documentos armazenados no Elasticsearch.  
Suporta filtros por texto, número do DOE, intervalo de datas, ordenação e realce (`highlight`) nos resultados.

## 🚀 Funcionalidades
- Busca textual com operadores **AND**, **OR** e **frase exata**.
- Filtro por:
  - Número do DOE (`numDoe`)
  - Intervalo de datas (`postDateInicial` e `postDateFinal`)
- Ordenação por relevância ou data (`asc`/`desc`).
- Retorno de highlights dos trechos encontrados.
- Suporte a CORS para integração com frontends.
- Endpoint de versão para teste rápido.

## 📦 Requisitos
- Python 3.8+
- Bibliotecas:
  - Flask
  - flask-cors
  - requests

Instale as dependências com:
```bash
pip install -r requirements.txt
