# -*- coding: utf-8 -*-
import streamlit as st
import urllib.request
import json
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Tati Dalla - Mobile",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    h1 { color: #2C3E50; font-size: 24px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# BARRA LATERAL (MENU E SAÍDA)
# ==========================================
with st.sidebar:
    st.markdown("### 🍫 Tati Dalla")
    st.write("Painel de Gestão Mobile")
    st.divider()
    
    if st.button("🚪 Sair da Aplicação", use_container_width=True, type="primary"):
        st.warning("Sessão encerrada. Pode fechar esta aba do navegador.")
        st.stop()

st.title("🍫 Tati Dalla - Gestão Mobile (Turso + View)")

TURSO_URL = "https://brigaderia-jesraj.aws-us-east-1.turso.io/v2/pipeline"
AUTH_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3OTA2MTg4NjYsImlkIjoiMDFhMGM1NWEtMWYwMS03OTM1LWFmN2UtNjEyNzlkM2U3MTk0Iiwia2lkIjoiODRpRll2SGxCQ01qVGxyWXVMR0xfUUtWY3E0N1dmWUVxRUxBSTdSNkFqQSIsInJpZCI6IjZlNDA0MjNlLTNiYzYtNDhhOC1hM2FlLTRhMzgxZTE2NTY2NCJ9.93zsfeEeRie6x00h-6Wn1JFYuEpF8HEmEgz7LYVs10X8_JZbEXgeJ0mbGtf9TwCssmErTRxE7gxpx4fQ8ZhEBw"

def executar_consulta_turso(sql_query):
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql_query}},
            {"type": "close"}
        ]
    }
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        req = urllib.request.Request(TURSO_URL, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            res_json = json.loads(response.read().decode('utf-8'))
            for step in res_json.get("results", []):
                if step.get("type") == "ok":
                    result_data = step.get("response", {}).get("result", {})
                    cols = [col["name"] for col in result_data.get("cols", [])]
                    rows_raw = result_data.get("rows", [])
                    
                    dados_formatados = []
                    for row in rows_raw:
                        linha_valores = [cell.get("value") if isinstance(cell, dict) else cell for cell in row]
                        dados_formatados.append(linha_valores)
                        
                    return pd.DataFrame(dados_formatados, columns=cols)
    except Exception as e:
        st.error(f"Erro de conexão com o Turso: {e}")
    return pd.DataFrame()

aba1, aba2, aba3 = st.tabs(["📦 Estoque", "📋 Pedidos", "🔮 Previsão"])

# ==========================================
# ABA 1: ESTOQUE ATUAL (Usando a View)
# ==========================================
with aba1:
    st.subheader("Estoque Atual")
    try:
        query_produtos = """
            SELECT produto_nome AS Produto, estoque_atual AS Estoque 
            FROM vw_estoque_atual 
            WHERE mostra_estoque = 's' OR mostra_estoque = 'S' OR mostra_estoque IS NULL OR mostra_estoque = ''
            ORDER BY Produto ASC
        """
        df_produtos = executar_consulta_turso(query_produtos)

        if not df_produtos.empty:
            pesquisa = st.text_input("🔍 Buscar produto...", "", key="pesq_estoque")
            if pesquisa:
                df_produtos = df_produtos[df_produtos['Produto'].str.contains(pesquisa, case=False, na=False)]

            st.dataframe(df_produtos, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhum produto cadastrado com exibição de estoque.")
    except Exception as e:
        st.error(f"Erro ao carregar estoque: {e}")

# ==========================================
# ABA 2: PEDIDOS PENDENTES (Com Total de Doces e Tabela de Produtos)
# ==========================================
with aba2:
    st.subheader("Pedidos Pendentes")
    try:
        df_pedidos = executar_consulta_turso("""
            SELECT 
                p.id_pedido AS Pedido, 
                c.nome AS Cliente, 
                p.dt_entrega AS Entrega, 
                p.valor_total AS Total, 
                p.situacao AS Status,
                (SELECT COALESCE(SUM(d.quantidade), 0) FROM detalhes_pedido d WHERE d.id_pedido = p.id_pedido) AS Total_Doces
            FROM pedidos p
            LEFT JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE p.situacao != 'Entregue' OR p.situacao IS NULL
            ORDER BY p.dt_entrega ASC
        """)

        if not df_pedidos.empty:
            for index, row in df_pedidos.iterrows():
                id_ped_val = row.get('Pedido')
                cliente_val = row.get('Cliente', 'Cliente não identificado')
                entrega_val = row.get('Entrega', '')
                total_val = row.get('Total', 0)
                status_val = row.get('Status', '')
                total_doces_val = row.get('Total_Doces', 0)

                dt_fmt = datetime.strptime(str(entrega_val).strip(), "%Y-%m-%d").strftime("%d/%m/%Y") if entrega_val else ""
                
                try:
                    val_float = float(total_val) if total_val is not None else 0.0
                except ValueError:
                    val_float = 0.0
                val_fmt = f"R$ {val_float:.2f}".replace(".", ",")

                # Título com ID, Cliente, Entrega, Quantidade total de doces e Valor Total
                with st.expander(f"Pedido #{id_ped_val} | {cliente_val} | Entrega: {dt_fmt} | Qtd Doces: {total_doces_val} | Total: {val_fmt}"):
                    st.write(f"**Cliente:** {cliente_val}")
                    st.write(f"**Data de Entrega:** {dt_fmt}")
                    st.write(f"**Quantidade Total de Doces:** {total_doces_val}")
                    st.write(f"**Valor Total:** {val_fmt}")
                    st.write(f"**Status:** {status_val}")
                    
                    st.divider()
                    st.markdown("##### 🍫 Lista de Produtos do Pedido")
                    
                    query_detalhes = f"""
                        SELECT 
                            pr.produto AS Produto, 
                            d.quantidade AS Qtd, 
                            d.preco_unit AS Preço_Unit, 
                            d.subtotal AS Subtotal
                        FROM detalhes_pedido d
                        JOIN produtos pr ON d.id_produto = pr.id_produto
                        WHERE d.id_pedido = {id_ped_val}
                    """
                    df_det = executar_consulta_turso(query_detalhes)
                    
                    if not df_det.empty:
                        st.dataframe(df_det, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhum item detalhado encontrado para este pedido.")

                    st.divider()
                    st.markdown("##### 💳 Formas de Pagamento / Parcelas")
                    
                    query_parcelas = f"""
                        SELECT 
                            numero_parcela AS Parc, 
                            valor AS Valor, 
                            data_vencimento AS Vencimento, 
                            forma_pagamento AS Forma, 
                            status AS Status
                        FROM parcelas_pedido
                        WHERE id_pedido = {id_ped_val}
                        ORDER BY numero_parcela ASC
                    """
                    df_parc = executar_consulta_turso(query_parcelas)

                    if not df_parc.empty:
                        st.dataframe(df_parc, hide_index=True, use_container_width=True)
                    else:
                        st.info("Nenhuma parcela/forma de pagamento registrada.")

        else:
            st.success("Não há pedidos pendentes no momento! 🎉")
    except Exception as e:
        st.error(f"Erro ao carregar pedidos: {e}")

# ==========================================
# ABA 3: PREVISÃO DE ESTOQUE (Usando a View)
# ==========================================
with aba3:
    st.subheader("Previsão baseada em Pedidos")
    st.info("Selecione os pedidos abaixo para calcular a demanda e o estoque necessário:")

    try:
        df_pedidos_pend = executar_consulta_turso("""
            SELECT p.id_pedido, c.nome, p.dt_entrega, p.valor_total 
            FROM pedidos p
            LEFT JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE p.situacao = 'Pendente'
            ORDER BY p.dt_entrega ASC
        """)
        
        df_totais_doces = executar_consulta_turso("SELECT id_pedido, SUM(quantidade) AS total FROM detalhes_pedido GROUP BY id_pedido")
        
        totais_doces = {}
        if not df_totais_doces.empty and 'id_pedido' in df_totais_doces.columns:
            for _, r in df_totais_doces.iterrows():
                totais_doces[r['id_pedido']] = r.get('total', 0)

        if not df_pedidos_pend.empty:
            ids_selecionados = []

            for index, row in df_pedidos_pend.iterrows():
                id_ped = row.get('id_pedido')
                cliente = row.get('nome')
                dt_entrega = row.get('dt_entrega')
                valor_total = row.get('valor_total')

                nome_cli = cliente if cliente else "Cliente não identificado"
                total_d = totais_doces.get(id_ped, 0)
                if total_d is None:
                    total_d = 0
                
                dt_fmt = datetime.strptime(str(dt_entrega).strip(), "%Y-%m-%d").strftime("%d/%m/%Y") if dt_entrega else ""
                val_fmt = f"R$ {float(valor_total):.2f}".replace(".", ",") if valor_total else "R$ 0,00"
                
                if st.checkbox(f"Pedido #{id_ped} | {nome_cli}\nEntrega: {dt_fmt} | Doces: {total_d} | Total: {val_fmt}", key=f"chk_ped_{id_ped}"):
                    ids_selecionados.append(id_ped)

            st.divider()
            st.markdown("### 📊 Resultado da Previsão")

            if ids_selecionados:
                ids_str = ','.join(map(str, ids_selecionados))
                query_prev = f"""
                    SELECT 
                        dp.id_produto,
                        pr.produto AS Produto, 
                        COALESCE(e.estoque_atual, 0) AS Estoque_Atual,
                        SUM(dp.quantidade) AS Qtd_Pedida
                    FROM detalhes_pedido dp
                    JOIN produtos pr ON dp.id_produto = pr.id_produto
                    LEFT JOIN vw_estoque_atual e ON pr.id_produto = e.id_produto
                    WHERE dp.id_pedido IN ({ids_str})
                    GROUP BY dp.id_produto, pr.produto
                    ORDER BY pr.produto ASC
                """
                df_prev = executar_consulta_turso(query_prev)

                if not df_prev.empty:
                    if 'id_produto' in df_prev.columns:
                        df_prev = df_prev.drop(columns=['id_produto'])
                    
                    df_prev['Estoque_Atual'] = pd.to_numeric(df_prev['Estoque_Atual'], errors='coerce').fillna(0).astype(int)
                    df_prev['Qtd_Pedida'] = pd.to_numeric(df_prev['Qtd_Pedida'], errors='coerce').fillna(0).astype(int)
                    
                    df_prev['Previsão (Saldo)'] = df_prev['Estoque_Atual'] - df_prev['Qtd_Pedida']
                    st.dataframe(df_prev, hide_index=True, use_container_width=True)
                else:
                    st.warning("Nenhum item encontrado para os pedidos selecionados.")
            else:
                st.info("Nenhum pedido selecionado acima.")
        else:
            st.success("Nenhum pedido pendente encontrado para previsão.")

    except Exception as e:
        st.error(f"Erro ao carregar previsão: {e}")
