import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import json
import os
import hashlib
import sqlite3
import requests
from io import StringIO
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse as urlparse
import os

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

# Usuários e senhas 
usuarios = {
    "admin": make_hashes("admin123"),
    "vendedor": make_hashes("vendas123")
}

def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Usuário")
    password = st.sidebar.text_input("Senha", type='password')
    
    if st.sidebar.button("Entrar"):
        if username in usuarios and check_hashes(password, usuarios[username]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.sidebar.success(f"Bem-vindo, {username}!")
            st.rerun()
        else:
            st.sidebar.error("Usuário ou senha inválidos")
    return False

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# =========================================
# 🗄️ SISTEMA DE BANCO DE DADOS (SQLite/PostgreSQL)
# =========================================

def get_database_url():
    """Obtém a URL do banco de dados do ambiente"""
    # Para Render.com e outros serviços em nuvem
    if 'DATABASE_URL' in os.environ:
        return os.environ['DATABASE_URL']
    # Para desenvolvimento local
    else:
        return 'sqlite:///fardamentos.db'

def get_connection():
    """Retorna conexão com o banco de dados"""
    try:
        # Tenta PostgreSQL primeiro (Render)
        database_url = get_database_url()
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://')
        conn = psycopg2.connect(database_url, sslmode='require')
        return conn
    except:
        # Fallback para SQLite local
        return sqlite3.connect('fardamentos.db', check_same_thread=False)

def init_db():
    """Inicializa o banco de dados"""
    conn = get_connection()
    
    try:
        cursor = conn.cursor()
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL UNIQUE
            )
        ''')
        
        # Tabela de clientes (SEM campo escola fixo)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_cadastro TEXT
            )
        ''')
        
        # Tabela de relação cliente-escola
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cliente_escolas (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER,
                escola_id INTEGER,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (escola_id) REFERENCES escolas(id)
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                categoria TEXT,
                tamanho TEXT,
                cor TEXT,
                preco REAL,
                estoque INTEGER,
                descricao TEXT,
                data_cadastro TEXT,
                escola_id INTEGER,
                FOREIGN KEY (escola_id) REFERENCES escolas(id)
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER,
                escola_id INTEGER,
                status TEXT DEFAULT 'Pendente',
                data_pedido TEXT,
                data_entrega_prevista TEXT,
                quantidade_total INTEGER,
                valor_total REAL,
                observacoes TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id),
                FOREIGN KEY (escola_id) REFERENCES escolas(id)
            )
        ''')
        
        # Tabela de itens do pedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL,
                subtotal REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        ''')
        
        # Inserir escolas padrão
        escolas_padrao = ["Municipal", "Desperta", "São Tadeu"]
        for escola in escolas_padrao:
            cursor.execute("INSERT INTO escolas (nome) VALUES (%s) ON CONFLICT (nome) DO NOTHING", (escola,))
        
        conn.commit()
        st.success("✅ Banco de dados inicializado com sucesso!")
        
    except Exception as e:
        st.error(f"❌ Erro ao inicializar banco: {str(e)}")
    finally:
        conn.close()

# Inicializar banco na primeira execução
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# =========================================
# 🔧 FUNÇÕES DO BANCO DE DADOS
# =========================================

# CLIENTES
def adicionar_cliente(nome, telefone, email, escolas_ids):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        data_cadastro = datetime.now().strftime("%d/%m/%Y")
        cursor.execute(
            "INSERT INTO clientes (nome, telefone, email, data_cadastro) VALUES (%s, %s, %s, %s) RETURNING id",
            (nome, telefone, email, data_cadastro)
        )
        cliente_id = cursor.fetchone()[0]
        
        for escola_id in escolas_ids:
            cursor.execute(
                "INSERT INTO cliente_escolas (cliente_id, escola_id) VALUES (%s, %s)",
                (cliente_id, escola_id)
            )
        
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, 
               STRING_AGG(e.nome, ', ') as escolas
        FROM clientes c
        LEFT JOIN cliente_escolas ce ON c.id = ce.cliente_id
        LEFT JOIN escolas e ON ce.escola_id = e.id
        GROUP BY c.id
        ORDER BY c.nome
    ''')
    clientes = cursor.fetchall()
    conn.close()
    return clientes

def excluir_cliente(cliente_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verificar se tem pedidos
        cursor.execute("SELECT COUNT(*) FROM pedidos WHERE cliente_id = %s", (cliente_id,))
        if cursor.fetchone()[0] > 0:
            return False, "Cliente possui pedidos e não pode ser excluído"
        
        # Excluir relações e cliente
        cursor.execute("DELETE FROM cliente_escolas WHERE cliente_id = %s", (cliente_id,))
        cursor.execute("DELETE FROM clientes WHERE id = %s", (cliente_id,))
        conn.commit()
        return True, "Cliente excluído com sucesso"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# PEDIDOS
def listar_pedidos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, c.nome as cliente, e.nome as escola
        FROM pedidos p
        JOIN clientes c ON p.cliente_id = c.id
        JOIN escolas e ON p.escola_id = e.id
        ORDER BY p.id DESC
    ''')
    pedidos = cursor.fetchall()
    conn.close()
    return pedidos

def excluir_pedido(pedido_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Restaurar estoque
        cursor.execute('SELECT produto_id, quantidade FROM pedido_itens WHERE pedido_id = %s', (pedido_id,))
        itens = cursor.fetchall()
        
        for produto_id, quantidade in itens:
            cursor.execute("UPDATE produtos SET estoque = estoque + %s WHERE id = %s", (quantidade, produto_id))
        
        # Excluir itens e pedido
        cursor.execute("DELETE FROM pedido_itens WHERE pedido_id = %s", (pedido_id,))
        cursor.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        
        conn.commit()
        return True, "Pedido excluído com sucesso"
    except Exception as e:
        conn.rollback()
        return False, f"Erro: {str(e)}"
    finally:
        conn.close()

# PRODUTOS E ESCOLAS
def listar_produtos():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.*, e.nome as escola_nome 
        FROM produtos p 
        LEFT JOIN escolas e ON p.escola_id = e.id
        ORDER BY p.nome
    ''')
    produtos = cursor.fetchall()
    conn.close()
    return produtos

def listar_escolas():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM escolas ORDER BY nome")
    escolas = cursor.fetchall()
    conn.close()
    return escolas

# =========================================
# 🚀 CONFIGURAÇÃO PRINCIPAL
# =========================================

st.set_page_config(
    page_title="Sistema de Fardamentos",
    page_icon="👕",
    layout="wide"
)

# Logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.write(f"👤 Usuário: **{st.session_state.username}**")

# Menu
menu_options = ["📊 Dashboard", "📦 Pedidos", "👥 Clientes", "👕 Fardamentos", "📦 Estoque", "📈 Relatórios"]
menu = st.sidebar.radio("Navegação", menu_options)

# =========================================
# 📱 PÁGINAS DO SISTEMA
# =========================================

if menu == "📊 Dashboard":
    st.title("📊 Dashboard - Sistema de Fardamentos")
    
    # Carregar dados
    pedidos = listar_pedidos()
    clientes = listar_clientes()
    produtos = listar_produtos()
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Total Pedidos", len(pedidos))
    with col2:
        st.metric("👥 Total Clientes", len(clientes))
    with col3:
        st.metric("👕 Produtos", len(produtos))
    with col4:
        baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("⚠️ Alerta Estoque", baixo_estoque)
    
    # Ações rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📝 Novo Pedido", use_container_width=True):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()
    with col2:
        if st.button("👥 Cadastrar Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    with col3:
        if st.button("👕 Cadastrar Produto", use_container_width=True):
            st.session_state.menu = "👕 Fardamentos"
            st.rerun()

elif menu == "👥 Clientes":
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2, tab3 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes", "🗑️ Excluir Cliente"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        with st.form("form_cliente"):
            nome = st.text_input("👤 Nome completo*", placeholder="Digite o nome completo do cliente")
            telefone = st.text_input("📞 Telefone", placeholder="(11) 99999-9999")
            email = st.text_input("📧 Email", placeholder="cliente@email.com")
            
            escolas = listar_escolas()
            escolas_selecionadas = st.multiselect(
                "🏫 Escolas do cliente*",
                options=[e[1] for e in escolas],
                help="Selecione todas as escolas que o cliente frequenta"
            )
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente", type="primary")
            
            if submitted:
                if nome and escolas_selecionadas:
                    escolas_ids = [e[0] for e in escolas if e[1] in escolas_selecionadas]
                    sucesso, msg = adicionar_cliente(nome, telefone, email, escolas_ids)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome e pelo menos uma escola são obrigatórios!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Escolas': cliente[5] or 'Nenhuma',
                    'Data Cadastro': cliente[4]
                })
            
            df = pd.DataFrame(dados)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Estatísticas
            st.subheader("📊 Estatísticas")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total de Clientes", len(clientes))
            with col2:
                escolas_count = df['Escolas'].str.split(',').explode().nunique()
                st.metric("Escolas Ativas", escolas_count)
        else:
            st.info("📭 Nenhum cliente cadastrado ainda")
    
    with tab3:
        st.header("🗑️ Excluir Cliente")
        clientes = listar_clientes()
        
        if clientes:
            cliente_opcoes = [f"{c[1]} (ID: {c[0]}) - Escolas: {c[5]}" for c in clientes]
            cliente_selecionado = st.selectbox(
                "Selecione o cliente para excluir:",
                options=cliente_opcoes,
                key="excluir_cliente"
            )
            
            if cliente_selecionado:
                cliente_id = int(cliente_selecionado.split("ID: ")[1].split(")")[0])
                
                st.warning("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
                st.info("📋 **Restrições:** Clientes com pedidos ativos não podem ser excluídos")
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("🗑️ Confirmar Exclusão", type="primary"):
                        sucesso, msg = excluir_cliente(cliente_id)
                        if sucesso:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("📭 Nenhum cliente cadastrado")

elif menu == "📦 Pedidos":
    st.title("📦 Gestão de Pedidos")
    
    tab1, tab2, tab3 = st.tabs(["📝 Novo Pedido", "📋 Listar Pedidos", "🗑️ Excluir Pedido"])
    
    with tab3:
        st.header("🗑️ Excluir Pedido")
        pedidos = listar_pedidos()
        
        if pedidos:
            pedido_opcoes = [f"ID: {p[0]} - {p[8]} - R$ {p[7]:.2f} - Status: {p[3]}" for p in pedidos]
            pedido_selecionado = st.selectbox(
                "Selecione o pedido para excluir:",
                options=pedido_opcoes,
                key="excluir_pedido"
            )
            
            if pedido_selecionado:
                pedido_id = int(pedido_selecionado.split("ID: ")[1].split(" - ")[0])
                
                st.warning("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
                st.success("✅ **Estoque será restaurado automaticamente**")
                
                if st.button("🗑️ Confirmar Exclusão do Pedido", type="primary"):
                    sucesso, msg = excluir_pedido(pedido_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("📭 Nenhum pedido cadastrado")

elif menu == "👕 Fardamentos":
    st.title("👕 Gestão de Fardamentos")
    st.info("🚀 Em desenvolvimento...")
    
elif menu == "📦 Estoque":
    st.title("📦 Controle de Estoque")
    st.info("🚀 Em desenvolvimento...")
    
elif menu == "📈 Relatórios":
    st.title("📈 Relatórios Detalhados")
    st.info("🚀 Em desenvolvimento...")

# =========================================
# 🎯 RODAPÉ E INFORMAÇÕES
# =========================================

st.sidebar.markdown("---")
st.sidebar.header("🌐 Informações do Sistema")

with st.sidebar.expander("📊 Status do Banco"):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM clientes")
        total_clientes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM pedidos")
        total_pedidos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM produtos")
        total_produtos = cursor.fetchone()[0]
        
        conn.close()
        
        st.write(f"👥 Clientes: {total_clientes}")
        st.write(f"📦 Pedidos: {total_pedidos}")
        st.write(f"👕 Produtos: {total_produtos}")
        st.success("✅ Banco conectado!")
        
    except Exception as e:
        st.error(f"❌ Erro no banco: {str(e)}")

st.sidebar.markdown("---")
st.sidebar.info("👕 Sistema de Fardamentos v2.0\n\n🚀 **Banco de Dados Ativo**")

# Botão para recarregar
if st.sidebar.button("🔄 Recarregar Dados"):
    st.rerun()
