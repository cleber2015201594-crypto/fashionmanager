import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import psycopg2
import urllib.parse
import sqlite3

# =========================================
# 🎨 CONFIGURAÇÃO DO APP
# =========================================

st.set_page_config(
    page_title="FashionManager Pro",
    page_icon="👕",
    layout="wide"
)

# CSS personalizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #6A0DAD;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🗃️ CONEXÃO COM BANCO
# =========================================

def get_db_type():
    return 'postgresql' if os.environ.get('DATABASE_URL') else 'sqlite'

def get_placeholder():
    return '%s' if get_db_type() == 'postgresql' else '?'

def get_connection():
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            parsed_url = urllib.parse.urlparse(database_url)
            conn = psycopg2.connect(
                database=parsed_url.path[1:],
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port,
                sslmode='require'
            )
            return conn
        else:
            conn = sqlite3.connect('local.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
            
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        if get_db_type() == 'postgresql':
            # Tabelas PostgreSQL
            tables = [
                '''CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''',
                '''CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
                )''',
                '''CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER REFERENCES escolas(id),
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''',
                '''CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )'''
            ]
            
            for table in tables:
                cur.execute(table)
            
            # Inserir dados iniciais
            cur.execute('INSERT INTO usuarios (username, password, nome, tipo) VALUES (%s, %s, %s, %s) ON CONFLICT (username) DO NOTHING', 
                       ('admin', 'admin123', 'Administrador', 'admin'))
            cur.execute('INSERT INTO escolas (nome, endereco, telefone) VALUES (%s, %s, %s) ON CONFLICT (nome) DO NOTHING', 
                       ('Escola Principal', 'Endereço padrão', '(11) 99999-9999'))
                
        else:
            # Tabelas SQLite
            tables = [
                '''CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''',
                '''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
                )''',
                '''CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (escola_id) REFERENCES escolas (id)
                )''',
                '''CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )'''
            ]
            
            for table in tables:
                cur.execute(table)
            
            cur.execute('INSERT OR IGNORE INTO usuarios (username, password, nome, tipo) VALUES (?, ?, ?, ?)', 
                       ('admin', 'admin123', 'Administrador', 'admin'))
            cur.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone) VALUES (?, ?, ?)', 
                       ('Escola Principal', 'Endereço padrão', '(11) 99999-9999'))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def check_login(username, password):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        cur.execute(f'SELECT password, nome, tipo FROM usuarios WHERE username = {placeholder}', (username,))
        result = cur.fetchone()
        
        if result:
            if hasattr(result, '_asdict'):
                result_dict = result._asdict()
            elif hasattr(result, 'keys'):
                result_dict = dict(zip([desc[0] for desc in cur.description], result))
            else:
                result_dict = {'password': result[0], 'nome': result[1], 'tipo': result[2]}
            
            if result_dict['password'] == password:
                return True, result_dict['nome'], result_dict['tipo']
        
        return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        if conn:
            conn.close()

def login_page():
    st.markdown("<h1 class='main-header'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("🔐 **Faça login para continuar**")
        
        username = st.text_input("👤 Usuário")
        password = st.text_input("🔒 Senha", type='password')
        
        if st.button("🚀 Entrar", use_container_width=True):
            if username and password:
                success, message, user_type = check_login(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = message
                    st.session_state.user_type = user_type
                    st.success(f"✅ Bem-vindo, {message}!")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("⚠️ Preencha todos os campos")
        
        st.markdown("---")
        st.markdown("**Usuário de teste:**")
        st.markdown("👤 **admin** | 🔒 **admin123**")

# =========================================
# 📊 FUNÇÕES BÁSICAS DO SISTEMA
# =========================================

def adicionar_escola(nome, endereco, telefone):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        cur.execute(f'INSERT INTO escolas (nome, endereco, telefone) VALUES ({placeholder}, {placeholder}, {placeholder})', 
                   (nome, endereco, telefone))
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM escolas ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        cur.execute(f'INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})', 
                   (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos(escola_id=None):
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            cur.execute(f'SELECT * FROM produtos WHERE escola_id = {placeholder} ORDER BY nome', (escola_id,))
        else:
            cur.execute('SELECT * FROM produtos ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        cur.execute(f'INSERT INTO clientes (nome, telefone, email) VALUES ({placeholder}, {placeholder}, {placeholder})', 
                   (nome, telefone, email))
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 🎯 INICIALIZAÇÃO
# =========================================

if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =========================================
# 🎨 MENU PRINCIPAL
# =========================================

with st.sidebar:
    st.markdown(f"**👤 {st.session_state.user_name}**")
    st.markdown(f"**🎯 {st.session_state.user_type}**")
    st.markdown("---")
    
    menu = st.radio("Navegação", [
        "📊 Dashboard",
        "🏫 Escolas", 
        "👥 Clientes",
        "👕 Produtos"
    ])
    
    st.markdown("---")
    if st.button("🚪 Sair"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# =========================================
# 📊 DASHBOARD
# =========================================

if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        escolas_count = len(listar_escolas())
        st.metric("🏫 Escolas", escolas_count)
    
    with col2:
        clientes_count = len(listar_clientes())
        st.metric("👥 Clientes", clientes_count)
    
    with col3:
        produtos_count = len(listar_produtos())
        st.metric("👕 Produtos", produtos_count)
    
    with col4:
        st.metric("📦 Pedidos", 0)
    
    st.subheader("🚀 Ações Rápidas")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("➕ Nova Escola", use_container_width=True):
            st.session_state.menu = "🏫 Escolas"
            st.rerun()
    
    with col2:
        if st.button("👕 Novo Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with col3:
        if st.button("👥 Novo Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()

# =========================================
# 🏫 ESCOLAS
# =========================================

elif menu == "🏫 Escolas":
    st.markdown("<h1 class='main-header'>🏫 Gestão de Escolas</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Escolas", "➕ Cadastrar Escola"])
    
    with tab1:
        st.subheader("📋 Lista de Escolas")
        escolas = listar_escolas()
        
        if escolas:
            for escola in escolas:
                with st.expander(f"🏫 {escola[1]}"):
                    st.write(f"📍 **Endereço:** {escola[2] or 'Não informado'}")
                    st.write(f"📞 **Telefone:** {escola[3] or 'Não informado'}")
                    st.write(f"📅 **Cadastro:** {escola[4]}")
        else:
            st.info("📝 Nenhuma escola cadastrada")
    
    with tab2:
        st.subheader("➕ Cadastrar Nova Escola")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola*")
            endereco = st.text_input("Endereço")
            telefone = st.text_input("Telefone")
            
            if st.form_submit_button("✅ Cadastrar Escola"):
                if nome:
                    success, msg = adicionar_escola(nome, endereco, telefone)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")

# =========================================
# 👥 CLIENTES
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista de Clientes", "➕ Cadastrar Cliente"])
    
    with tab1:
        st.subheader("📋 Lista de Clientes")
        clientes = listar_clientes()
        
        if clientes:
            for cliente in clientes:
                with st.expander(f"👤 {cliente[1]}"):
                    st.write(f"📞 **Telefone:** {cliente[2] or 'Não informado'}")
                    st.write(f"📧 **Email:** {cliente[3] or 'Não informado'}")
                    st.write(f"📅 **Cadastro:** {cliente[4]}")
        else:
            st.info("📝 Nenhum cliente cadastrado")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Cliente")
        with st.form("novo_cliente"):
            nome = st.text_input("Nome completo*")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            
            if st.form_submit_button("✅ Cadastrar Cliente"):
                if nome:
                    success, msg = adicionar_cliente(nome, telefone, email)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")

# =========================================
# 👕 PRODUTOS
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Gestão de Produtos</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📋 Lista de Produtos", "➕ Cadastrar Produto", "📊 Estatísticas"])
    
    with tab1:
        st.subheader("📋 Lista de Produtos")
        
        escolas = listar_escolas()
        escola_options = {0: "Todas as escolas"}
        for escola in escolas:
            escola_options[escola[0]] = escola[1]
        
        escola_id = st.selectbox("Filtrar por escola", options=list(escola_options.keys()), 
                               format_func=lambda x: escola_options[x])
        
        produtos = listar_produtos(escola_id if escola_id != 0 else None)
        
        if produtos:
            for produto in produtos:
                with st.expander(f"👕 {produto[1]}"):
                    escola_nome = next((escola[1] for escola in escolas if escola[0] == produto[7]), "N/A")
                    st.write(f"🏫 **Escola:** {escola_nome}")
                    st.write(f"📁 **Categoria:** {produto[2] or 'Não informada'}")
                    st.write(f"📏 **Tamanho:** {produto[3] or 'Não informado'}")
                    st.write(f"🎨 **Cor:** {produto[4] or 'Não informada'}")
                    st.write(f"💵 **Preço:** R$ {float(produto[5]):.2f}" if produto[5] else "💵 **Preço:** R$ 0.00")
                    st.write(f"📊 **Estoque:** {produto[6] or 0} unidades")
        else:
            st.info("📝 Nenhum produto cadastrado")
    
    with tab2:
        st.subheader("➕ Cadastrar Novo Produto")
        escolas = listar_escolas()
        
        if not escolas:
            st.error("❌ É necessário cadastrar uma escola primeiro.")
        else:
            with st.form("novo_produto"):
                col1, col2 = st.columns(2)
                
                with col1:
                    nome = st.text_input("Nome do Produto*")
                    categoria = st.selectbox("Categoria*", ["Camisetas", "Calças", "Agasalhos", "Acessórios"])
                    tamanho = st.selectbox("Tamanho*", ["P", "M", "G", "GG", "Único"])
                
                with col2:
                    cor = st.text_input("Cor*", "Branco")
                    preco = st.number_input("Preço R$*", min_value=0.0, value=29.90)
                    estoque = st.number_input("Estoque*", min_value=0, value=10)
                    escola_id = st.selectbox("Escola*", options=[e[0] for e in escolas], 
                                           format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
                
                if st.form_submit_button("✅ Cadastrar Produto"):
                    if nome and cor and escola_id:
                        success, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Campos obrigatórios: Nome, Cor e Escola")
    
    with tab3:
        st.subheader("📊 Estatísticas de Produtos")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            total_produtos = len(listar_produtos())
            st.metric("Total de Produtos", total_produtos)
        with col2:
            produtos_todos = listar_produtos()
            total_estoque = sum(p[6] for p in produtos_todos if p[6])
            st.metric("Estoque Total", total_estoque)
        with col3:
            produtos_baixo_estoque = len([p for p in produtos_todos if p[6] and p[6] < 5])
            st.metric("Produtos com Estoque Baixo", produtos_baixo_estoque)
        
        # Gráfico simples
        st.subheader("📈 Distribuição por Categoria")
        produtos = listar_produtos()
        if produtos:
            categorias = {}
            for produto in produtos:
                cat = produto[2] or "Sem categoria"
                categorias[cat] = categorias.get(cat, 0) + 1
            
            if categorias:
                df = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
                fig = px.pie(df, values='Quantidade', names='Categoria', title='Produtos por Categoria')
                st.plotly_chart(fig, use_container_width=True)

# =========================================
# 🎯 RODAPÉ
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("👕 **FashionManager Pro**")
st.sidebar.markdown("v1.0 • Sistema Básico vitor")
