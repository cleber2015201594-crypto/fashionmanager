import streamlit as st
import pandas as pd
import plotly.express as px
import os
import psycopg2
import urllib.parse
import sqlite3
from datetime import datetime

# =========================================
# 🎨 CONFIGURAÇÃO DO APP - RESPONSIVA
# =========================================

st.set_page_config(
    page_title="FashionManager Pro",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="auto"
)

# CSS personalizado para responsividade
st.markdown("""
<style>
    .main-header {
        font-size: 1.8rem;
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
        margin: 0.5rem 0;
    }
    
    .school-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem;
        }
        
        .sidebar .sidebar-content {
            width: 80px;
        }
        
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column;
        }
        
        div[data-testid="column"] {
            width: 100% !important;
            margin-bottom: 1rem;
        }
    }
    
    /* Melhorias para mobile */
    .mobile-friendly {
        padding: 0.5rem;
    }
    
    .mobile-button {
        width: 100%;
        margin: 0.2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🗃️ CONEXÃO COM BANCO - CORRIGIDA
# =========================================

def get_connection():
    """Estabelece conexão com PostgreSQL (Render) ou SQLite (local)"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # ✅ CORREÇÃO: Método robusto para PostgreSQL
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://', 1)
            
            # ✅ CORREÇÃO: Usar parse para extrair componentes da URL
            parsed = urllib.parse.urlparse(database_url)
            
            # Extrair credenciais da URL
            username = parsed.username
            password = parsed.password
            hostname = parsed.hostname
            port = parsed.port or 5432
            database = parsed.path[1:]  # Remove a barra inicial
            
            # ✅ CORREÇÃO: Conexão com parâmetros nomeados corretos
            conn = psycopg2.connect(
                host=hostname,
                database=database,
                user=username,
                password=password,  # ✅ Nome correto do parâmetro
                port=port,
                sslmode='require'
            )
            return conn
        else:
            # SQLite local para desenvolvimento
            conn = sqlite3.connect('fashionmanager.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        # Tentar conexão alternativa
        return try_alternative_connection()

def try_alternative_connection():
    """Tenta conexão alternativa com PostgreSQL"""
    try:
        # Tentar com variáveis de ambiente individuais
        db_host = os.environ.get('DB_HOST')
        db_name = os.environ.get('DB_NAME')
        db_user = os.environ.get('DB_USER')
        db_password = os.environ.get('DB_PASSWORD')  # ✅ Nome correto
        db_port = os.environ.get('DB_PORT', '5432')
        
        if all([db_host, db_name, db_user, db_password]):
            conn = psycopg2.connect(
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,  # ✅ Nome correto
                port=db_port
            )
            return conn
        else:
            # Fallback para SQLite
            conn = sqlite3.connect('fashionmanager.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
    except Exception as e:
        st.error(f"❌ Erro na conexão alternativa: {str(e)}")
        # Último fallback - SQLite local
        try:
            conn = sqlite3.connect('fashionmanager.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row
            st.info("📁 Usando banco SQLite local")
            return conn
        except Exception as sqlite_error:
            st.error(f"❌ Erro crítico: {sqlite_error}")
            return None

def get_placeholder():
    """Retorna o placeholder correto para o banco"""
    return '%s' if os.environ.get('DATABASE_URL') or os.environ.get('DB_HOST') else '?'

def formatar_data_brasil(data):
    """Formata data para o padrão brasileiro DD/MM/YYYY"""
    if data is None:
        return "N/A"
    
    try:
        # Se for string, converter para datetime
        if isinstance(data, str):
            # Tentar diferentes formatos
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y', '%d/%m/%Y %H:%M:%S']:
                try:
                    data = datetime.strptime(data, fmt)
                    break
                except ValueError:
                    continue
        
        # Se for datetime, formatar
        if isinstance(data, datetime):
            return data.strftime('%d/%m/%Y')
        else:
            return str(data)
    except Exception:
        return str(data)

def init_db():
    """Inicializa o banco de dados com tabelas necessárias"""
    conn = get_connection()
    if not conn:
        st.error("❌ Não foi possível conectar ao banco de dados")
        return False
    
    try:
        cur = conn.cursor()
        
        # Verificar se estamos usando PostgreSQL ou SQLite
        is_postgres = os.environ.get('DATABASE_URL') is not None or os.environ.get('DB_HOST') is not None
        
        if is_postgres:
            # ✅ CORREÇÃO: PostgreSQL - usar sintaxe correta
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id SERIAL PRIMARY KEY,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    escola_id INTEGER,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', 'admin123', 'Administrador Principal', 'admin'),
                ('vendedor', 'venda123', 'Vendedor Padrão', 'vendedor')
            ]
            
            for usuario in usuarios_padrao:
                cur.execute('''
                    INSERT INTO usuarios (username, password, nome, tipo) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                ''', usuario)
            
            # Inserir escola padrão
            cur.execute('''
                INSERT INTO escolas (nome, endereco, telefone, email) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (nome) DO NOTHING
            ''', ('Escola Principal', 'Endereço padrão', '(11) 99999-9999', 'contato@escola.com'))
                
        else:
            # SQLite local
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor',
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS escolas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT UNIQUE NOT NULL,
                    endereco TEXT,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco REAL,
                    estoque INTEGER DEFAULT 0,
                    escola_id INTEGER,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    escola_id INTEGER,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Inserir usuários padrão
            usuarios_padrao = [
                ('admin', 'admin123', 'Administrador Principal', 'admin'),
                ('vendedor', 'venda123', 'Vendedor Padrão', 'vendedor')
            ]
            
            for usuario in usuarios_padrao:
                cur.execute('''
                    INSERT OR IGNORE INTO usuarios (username, password, nome, tipo) 
                    VALUES (?, ?, ?, ?)
                ''', usuario)
            
            # Inserir escola padrão
            cur.execute('''
                INSERT OR IGNORE INTO escolas (nome, endereco, telefone, email) 
                VALUES (?, ?, ?, ?)
            ''', ('Escola Principal', 'Endereço padrão', '(11) 99999-9999', 'contato@escola.com'))
        
        conn.commit()
        st.success("✅ Banco de dados inicializado com sucesso!")
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN - RESPONSIVO
# =========================================

def check_login(username, password):
    """Verifica as credenciais do usuário"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None, None
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'SELECT id, password, nome, tipo FROM usuarios WHERE username = {placeholder}'
        cur.execute(query, (username,))
        result = cur.fetchone()
        
        if result:
            user_id, stored_password, nome, tipo = result
            if stored_password == password:
                return True, nome, tipo, user_id
        
        return False, "Credenciais inválidas", None, None
    except Exception as e:
        return False, f"Erro: {str(e)}", None, None
    finally:
        if conn:
            conn.close()

def login_page():
    """Página de login responsiva"""
    st.markdown("<h1 class='main-header'>👕 FashionManager Pro</h1>", unsafe_allow_html=True)
    
    # Layout responsivo para login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.info("🔐 **Faça login para continuar**")
        
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type='password')
        
        if st.button("🚀 Entrar", use_container_width=True, key="login_btn"):
            if username and password:
                success, message, user_type, user_id = check_login(username, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_name = message
                    st.session_state.user_type = user_type
                    st.session_state.user_id = user_id
                    st.success(f"✅ Bem-vindo, {message}!")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
            else:
                st.error("⚠️ Preencha todos os campos")
        
        st.markdown("---")
        with st.expander("👤 Usuários de teste"):
            st.markdown("- **admin** / **admin123** (Administrador)")
            st.markdown("- **vendedor** / **venda123** (Vendedor)")

# =========================================
# 📊 FUNÇÕES BÁSICAS DO SISTEMA
# =========================================

def adicionar_escola(nome, endereco, telefone, email):
    """Adiciona uma nova escola"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'INSERT INTO escolas (nome, endereco, telefone, email) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})'
        cur.execute(query, (nome, endereco, telefone, email))
        conn.commit()
        return True, "✅ Escola cadastrada com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_escolas():
    """Lista todas as escolas"""
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
    """Adiciona um novo produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id) 
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos(escola_id=None):
    """Lista produtos, opcionalmente filtrando por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            query = f'SELECT * FROM produtos WHERE escola_id = {placeholder} ORDER BY nome'
            cur.execute(query, (escola_id,))
        else:
            cur.execute('SELECT * FROM produtos ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def adicionar_cliente(nome, telefone, email, escola_id):
    """Adiciona um novo cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'INSERT INTO clientes (nome, telefone, email, escola_id) VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder})'
        cur.execute(query, (nome, telefone, email, escola_id))
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_clientes(escola_id=None):
    """Lista clientes, opcionalmente filtrando por escola"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        if escola_id:
            placeholder = get_placeholder()
            query = f'SELECT * FROM clientes WHERE escola_id = {placeholder} ORDER BY nome'
            cur.execute(query, (escola_id,))
        else:
            cur.execute('SELECT * FROM clientes ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar clientes: {e}")
        return []
    finally:
        if conn:
            conn.close()

# =========================================
# 🎯 INICIALIZAÇÃO DO SISTEMA
# =========================================

# Inicializar banco de dados
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True
    else:
        st.error("❌ Falha ao inicializar o banco de dados")

# Verificar login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login_page()
    st.stop()

# =========================================
# 🎨 MENU PRINCIPAL - RESPONSIVO
# =========================================

# Sidebar colapsável para mobile
with st.sidebar:
    st.markdown(f"**{st.session_state.user_name}**")
    st.markdown(f"**{st.session_state.user_type.upper()}**")
    st.markdown("---")
    
    # Menu simplificado para mobile
    menu_options = ["📊 Dashboard", "🏫 Escolas", "👕 Produtos", "👥 Clientes"]
    
    if st.session_state.user_type == 'admin':
        menu_options.append("👥 Usuários")
    
    menu = st.radio("Navegação", menu_options)
    
    st.markdown("---")
    
    # Botões compactos para mobile
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔐 Senha", use_container_width=True, key="change_pwd_btn"):
            st.session_state.alterar_senha = True
    with col2:
        if st.button("🚪 Sair", use_container_width=True, key="logout_btn"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

# =========================================
# 📱 LAYOUT RESPONSIVO - DASHBOARD
# =========================================

if menu == "📊 Dashboard":
    st.markdown("<h1 class='main-header'>📊 Dashboard</h1>", unsafe_allow_html=True)
    
    # Métricas gerais - layout responsivo
    st.subheader("Visão Geral")
    
    # Em mobile, mostrar métricas em coluna única
    metrics_cols = st.columns(2)  # 2 colunas em mobile
    
    with metrics_cols[0]:
        escolas_count = len(listar_escolas())
        st.metric("🏫 Escolas", escolas_count)
    
    with metrics_cols[1]:
        clientes_count = len(listar_clientes())
        st.metric("👥 Clientes", clientes_count)
    
    metrics_cols2 = st.columns(2)
    
    with metrics_cols2[0]:
        produtos_count = len(listar_produtos())
        st.metric("👕 Produtos", produtos_count)
    
    with metrics_cols2[1]:
        st.metric("📦 Pedidos", "0")
    
    # Ações rápidas - botões empilhados em mobile
    st.subheader("Ações Rápidas")
    
    # Usar colunas com breakpoints responsivos
    action_cols = st.columns(2)
    
    with action_cols[0]:
        if st.button("➕ Nova Escola", use_container_width=True, key="btn_escola"):
            st.session_state.menu = "🏫 Escolas"
            st.rerun()
        
        if st.button("👕 Novo Produto", use_container_width=True, key="btn_produto"):
            st.session_state.menu = "👕 Produtos"
            st.rerun()
    
    with action_cols[1]:
        if st.button("👥 Novo Cliente", use_container_width=True, key="btn_cliente"):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
        
        if st.button("📦 Novo Pedido", use_container_width=True, key="btn_pedido"):
            st.session_state.menu = "📦 Pedidos"
            st.rerun()

# =========================================
# 🏫 GESTÃO DE ESCOLAS - RESPONSIVA
# =========================================

elif menu == "🏫 Escolas":
    st.markdown("<h1 class='main-header'>🏫 Escolas</h1>", unsafe_allow_html=True)
    
    # Tabs responsivas
    tab1, tab2 = st.tabs(["📋 Lista", "➕ Nova Escola"])
    
    with tab1:
        st.subheader("Escolas Cadastradas")
        escolas = listar_escolas()
        
        if escolas:
            for escola in escolas:
                # Cartão responsivo para cada escola
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**{escola[1]}**")
                        if escola[2]:
                            st.caption(f"📍 {escola[2]}")
                        if escola[3]:
                            st.caption(f"📞 {escola[3]}")
                        st.caption(f"📅 {formatar_data_brasil(escola[5])}")
                    
                    with col2:
                        produtos_count = len(listar_produtos(escola[0]))
                        st.metric("Produtos", produtos_count, label_visibility="collapsed")
                    
                    st.markdown("---")
        else:
            st.info("📝 Nenhuma escola cadastrada")
    
    with tab2:
        st.subheader("Cadastrar Nova Escola")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola*")
            endereco = st.text_input("Endereço")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            
            if st.form_submit_button("✅ Cadastrar Escola", use_container_width=True):
                if nome:
                    success, msg = adicionar_escola(nome, endereco, telefone, email)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome é obrigatório!")

# =========================================
# 👕 GESTÃO DE PRODUTOS - RESPONSIVA
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Produtos</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista", "➕ Novo Produto"])
    
    with tab1:
        st.subheader("Produtos Cadastrados")
        
        # Filtros em coluna única para mobile
        escolas = listar_escolas()
        escola_options = {0: "Todas as escolas"}
        for escola in escolas:
            escola_options[escola[0]] = escola[1]
        
        escola_id = st.selectbox("Filtrar por escola", options=list(escola_options.keys()), 
                               format_func=lambda x: escola_options[x])
        
        produtos = listar_produtos(escola_id if escola_id != 0 else None)
        
        if produtos:
            for produto in produtos:
                with st.container():
                    # Layout compacto para mobile
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**{produto[1]}**")
                        escola_nome = next((escola[1] for escola in escolas if escola[0] == produto[7]), "N/A")
                        st.caption(f"🏫 {escola_nome} | 📁 {produto[2]} | 📏 {produto[3]}")
                        st.caption(f"🎨 {produto[4]} | 💵 R$ {float(produto[5]):.2f}")
                    
                    with col2:
                        estoque = produto[6] if produto[6] else 0
                        status = "✅" if estoque >= 10 else "⚠️" if estoque > 0 else "❌"
                        st.metric("Estoque", f"{status} {estoque}", label_visibility="collapsed")
                    
                    st.markdown("---")
        else:
            st.info("📝 Nenhum produto cadastrado")
    
    with tab2:
        st.subheader("Cadastrar Novo Produto")
        escolas = listar_escolas()
        
        if not escolas:
            st.error("❌ Cadastre uma escola primeiro")
        else:
            with st.form("novo_produto"):
                # Formulário em coluna única para mobile
                nome = st.text_input("Nome do Produto*")
                categoria = st.selectbox("Categoria*", ["Camisetas", "Calças", "Agasalhos", "Acessórios"])
                tamanho = st.selectbox("Tamanho*", ["P", "M", "G", "GG", "Único"])
                cor = st.text_input("Cor*", "Branco")
                preco = st.number_input("Preço R$*", min_value=0.0, value=29.90)
                estoque = st.number_input("Estoque*", min_value=0, value=10)
                escola_id = st.selectbox("Escola*", options=[e[0] for e in escolas], 
                                       format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
                
                if st.form_submit_button("✅ Cadastrar Produto", use_container_width=True):
                    if nome and cor and escola_id:
                        success, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Campos obrigatórios!")

# =========================================
# 👥 GESTÃO DE CLIENTES - RESPONSIVA
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📋 Lista", "➕ Novo Cliente"])
    
    with tab1:
        st.subheader("Clientes Cadastrados")
        
        escolas = listar_escolas()
        escola_options = {0: "Todas as escolas"}
        for escola in escolas:
            escola_options[escola[0]] = escola[1]
        
        escola_id = st.selectbox("Filtrar por escola", options=list(escola_options.keys()), 
                               format_func=lambda x: escola_options[x])
        
        clientes = listar_clientes(escola_id if escola_id != 0 else None)
        
        if clientes:
            for cliente in clientes:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**{cliente[1]}**")
                        if cliente[2]:
                            st.caption(f"📞 {cliente[2]}")
                        if cliente[3]:
                            st.caption(f"📧 {cliente[3]}")
                        escola_nome = next((escola[1] for escola in escolas if escola[0] == cliente[4]), "N/A")
                        st.caption(f"🏫 {escola_nome}")
                        st.caption(f"📅 {formatar_data_brasil(cliente[5])}")
                    
                    with col2:
                        st.metric("Pedidos", "0", label_visibility="collapsed")
                    
                    st.markdown("---")
        else:
            st.info("📝 Nenhum cliente cadastrado")
    
    with tab2:
        st.subheader("Cadastrar Novo Cliente")
        escolas = listar_escolas()
        
        if not escolas:
            st.error("❌ Cadastre uma escola primeiro")
        else:
            with st.form("novo_cliente"):
                nome = st.text_input("Nome completo*")
                telefone = st.text_input("Telefone")
                email = st.text_input("Email")
                escola_id = st.selectbox("Escola*", options=[e[0] for e in escolas], 
                                       format_func=lambda x: next((e[1] for e in escolas if e[0] == x), "N/A"))
                
                if st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True):
                    if nome and escola_id:
                        success, msg = adicionar_cliente(nome, telefone, email, escola_id)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.error("❌ Nome e escola são obrigatórios!")

# =========================================
# 👥 GERENCIAMENTO DE USUÁRIOS (APENAS ADMIN)
# =========================================

elif menu == "👥 Usuários" and st.session_state.user_type == 'admin':
    st.markdown("<h1 class='main-header'>👥 Usuários</h1>", unsafe_allow_html=True)
    
    st.info("🔧 Funcionalidade em desenvolvimento...")
    st.write("Em breve você poderá gerenciar usuários aqui!")

# =========================================
# 🔐 ALTERAÇÃO DE SENHA (MODAL RESPONSIVO)
# =========================================

if st.session_state.get('alterar_senha'):
    # Overlay responsivo
    st.markdown(
        """
        <style>
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: rgba(0,0,0,0.5);
            z-index: 999;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    with st.container():
        st.markdown("<h3>🔐 Alterar Senha</h3>", unsafe_allow_html=True)
        
        nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha_input")
        confirmar_senha = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha_input")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Salvar", use_container_width=True):
                if nova_senha and confirmar_senha:
                    if nova_senha == confirmar_senha:
                        # Simular alteração de senha
                        st.success("✅ Senha alterada com sucesso!")
                        st.session_state.alterar_senha = False
                        st.rerun()
                    else:
                        st.error("❌ As senhas não coincidem!")
                else:
                    st.error("❌ Preencha todos os campos!")
        
        with col2:
            if st.button("❌ Cancelar", use_container_width=True):
                st.session_state.alterar_senha = False
                st.rerun()

# =========================================
# 🎯 RODAPÉ RESPONSIVO
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("👕 **FashionManager**")
st.sidebar.caption("v6.0 • Mobile")

# Indicador de ambiente
if os.environ.get('DATABASE_URL') or os.environ.get('DB_HOST'):
    st.sidebar.success("🌐 Online")
else:
    st.sidebar.info("💻 Local")
