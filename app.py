import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import os
import hashlib
import psycopg2
import urllib.parse

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
    """Detecta o tipo de banco de dados"""
    return 'postgresql' if os.environ.get('DATABASE_URL') else 'sqlite'

def get_placeholder():
    """Retorna o placeholder correto para o banco"""
    return '%s' if get_db_type() == 'postgresql' else '?'

def get_connection():
    """Conexão com PostgreSQL do Render"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        
        if database_url:
            # Parse da URL do Render
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
            # Para desenvolvimento local - usar SQLite
            import sqlite3
            conn = sqlite3.connect('local.db', check_same_thread=False)
            conn.row_factory = sqlite3.Row  # Para acesso por nome de coluna
            return conn
            
    except Exception as e:
        st.error(f"❌ Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa o banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Verificar se estamos usando PostgreSQL ou SQLite
        db_type = get_db_type()
        
        if db_type == 'postgresql':
            # Tabela de usuários - PostgreSQL
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
                )
            ''')
            
            # Tabela de produtos - PostgreSQL
            cur.execute('''
                CREATE TABLE IF NOT EXISTS produtos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    categoria TEXT,
                    tamanho TEXT,
                    cor TEXT,
                    preco DECIMAL(10,2),
                    estoque INTEGER DEFAULT 0,
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabela de clientes - PostgreSQL
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id SERIAL PRIMARY KEY,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            # Inserir usuário admin padrão
            cur.execute('''
                INSERT INTO usuarios (username, password, nome, tipo) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            ''', ('admin', 'admin123', 'Administrador', 'admin'))
        else:
            # SQLite
            cur.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    nome TEXT,
                    tipo TEXT DEFAULT 'vendedor'
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
                    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cur.execute('''
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    telefone TEXT,
                    email TEXT,
                    data_cadastro DATE DEFAULT CURRENT_DATE
                )
            ''')
            
            cur.execute('''
                INSERT OR IGNORE INTO usuarios (username, password, nome, tipo) 
                VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin123', 'Administrador', 'admin'))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"❌ Erro ao criar tabelas: {str(e)}")
        return False
    finally:
        conn.close()

# =========================================
# 🔐 SISTEMA DE LOGIN
# =========================================

def check_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'SELECT password, nome, tipo FROM usuarios WHERE username = {placeholder}'
        cur.execute(query, (username,))
        result = cur.fetchone()
        
        if result:
            # Converter para dicionário se for SQLite Row
            if hasattr(result, '_asdict'):
                result_dict = result._asdict()
            elif hasattr(result, 'keys'):
                result_dict = dict(zip([desc[0] for desc in cur.description], result))
            else:
                # Para PostgreSQL tupla simples
                result_dict = {
                    'password': result[0],
                    'nome': result[1],
                    'tipo': result[2]
                }
            
            if result_dict['password'] == password:
                return True, result_dict['nome'], result_dict['tipo']
        
        return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        conn.close()

def login_page():
    """Página de login"""
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
# 📊 FUNÇÕES DO SISTEMA
# =========================================

def adicionar_produto(nome, categoria, tamanho, cor, preco, estoque):
    """Adiciona novo produto"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque)
            VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, categoria, tamanho, cor, preco, estoque))
        conn.commit()
        return True, "✅ Produto cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_produtos():
    """Lista todos os produtos"""
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('SELECT * FROM produtos ORDER BY nome')
        return cur.fetchall()
    except Exception as e:
        st.error(f"❌ Erro ao listar produtos: {e}")
        return []
    finally:
        conn.close()

def adicionar_cliente(nome, telefone, email):
    """Adiciona novo cliente"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        placeholder = get_placeholder()
        
        query = f'''
            INSERT INTO clientes (nome, telefone, email)
            VALUES ({placeholder}, {placeholder}, {placeholder})
        '''
        cur.execute(query, (nome, telefone, email))
        conn.commit()
        return True, "✅ Cliente cadastrado com sucesso!"
    except Exception as e:
        conn.rollback()
        return False, f"❌ Erro: {str(e)}"
    finally:
        conn.close()

def listar_clientes():
    """Lista todos os clientes"""
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
        conn.close()

# =========================================
# 🎯 INICIALIZAÇÃO
# =========================================

# Inicializar banco
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
        "👕 Produtos", 
        "👥 Clientes",
        "📦 Estoque"
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
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        produtos_count = len(listar_produtos())
        st.markdown(f"""
        <div class='metric-card'>
            <div style='font-size: 2rem; font-weight: bold;'>{produtos_count}</div>
            <div>👕 Produtos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        clientes_count = len(listar_clientes())
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);'>
            <div style='font-size: 2rem; font-weight: bold;'>{clientes_count}</div>
            <div>👥 Clientes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        produtos = listar_produtos()
        estoque_baixo = len([p for p in produtos if p[6] < 5])
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);'>
            <div style='font-size: 2rem; font-weight: bold;'>{estoque_baixo}</div>
            <div>⚠️ Alertas</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Gráfico de produtos por categoria
    st.subheader("📈 Produtos por Categoria")
    produtos = listar_produtos()
    if produtos:
        categorias = {}
        for produto in produtos:
            cat = produto[2] or "Sem categoria"
            categorias[cat] = categorias.get(cat, 0) + 1
        
        if categorias:
            df = pd.DataFrame(list(categorias.items()), columns=['Categoria', 'Quantidade'])
            fig = px.pie(df, values='Quantidade', names='Categoria', title='Distribuição por Categoria')
            st.plotly_chart(fig, use_container_width=True)

# =========================================
# 👕 PRODUTOS
# =========================================

elif menu == "👕 Produtos":
    st.markdown("<h1 class='main-header'>👕 Gestão de Produtos</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Lista"])
    
    with tab1:
        st.subheader("Cadastrar Novo Produto")
        
        with st.form("novo_produto"):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Produto*")
                categoria = st.selectbox("Categoria*", ["Camisetas", "Calças", "Agasalhos", "Acessórios"])
                tamanho = st.selectbox("Tamanho*", ["P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"])
            
            with col2:
                cor = st.text_input("Cor*", "Branco")
                preco = st.number_input("Preço R$*", min_value=0.0, value=29.90)
                estoque = st.number_input("Estoque*", min_value=0, value=10)
            
            if st.form_submit_button("✅ Cadastrar Produto"):
                if nome and cor:
                    success, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Campos obrigatórios: Nome e Cor")
    
    with tab2:
        st.subheader("Produtos Cadastrados")
        produtos = listar_produtos()
        
        if produtos:
            dados = []
            for produto in produtos:
                # Acessar por índice já que é uma tupla
                status = "✅" if produto[6] >= 5 else "⚠️" if produto[6] > 0 else "❌"
                dados.append({
                    'ID': produto[0],
                    'Produto': produto[1],
                    'Categoria': produto[2],
                    'Tamanho': produto[3],
                    'Cor': produto[4],
                    'Preço': f"R$ {float(produto[5]):.2f}",
                    'Estoque': f"{status} {produto[6]}",
                    'Data': produto[7]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
            st.metric("Total de Produtos", len(produtos))
        else:
            st.info("📝 Nenhum produto cadastrado")

# =========================================
# 👥 CLIENTES
# =========================================

elif menu == "👥 Clientes":
    st.markdown("<h1 class='main-header'>👥 Gestão de Clientes</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ Cadastrar", "📋 Lista"])
    
    with tab1:
        st.subheader("Cadastrar Novo Cliente")
        
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
    
    with tab2:
        st.subheader("Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            dados = []
            for cliente in clientes:
                dados.append({
                    'ID': cliente[0],
                    'Nome': cliente[1],
                    'Telefone': cliente[2] or 'N/A',
                    'Email': cliente[3] or 'N/A',
                    'Data Cadastro': cliente[4]
                })
            
            st.dataframe(pd.DataFrame(dados), use_container_width=True)
            st.metric("Total de Clientes", len(clientes))
        else:
            st.info("📝 Nenhum cliente cadastrado")

# =========================================
# 📦 ESTOQUE
# =========================================

elif menu == "📦 Estoque":
    st.markdown("<h1 class='main-header'>📦 Controle de Estoque</h1>", unsafe_allow_html=True)
    
    produtos = listar_produtos()
    
    if produtos:
        # Métricas
        col1, col2, col3 = st.columns(3)
        total_estoque = sum(p[6] for p in produtos)
        produtos_baixo = len([p for p in produtos if p[6] < 5])
        
        with col1:
            st.metric("📦 Total Produtos", len(produtos))
        with col2:
            st.metric("🔄 Estoque Total", total_estoque)
        with col3:
            st.metric("⚠️ Estoque Baixo", produtos_baixo)
        
        # Tabela de estoque
        st.subheader("Situação do Estoque")
        dados = []
        for produto in produtos:
            status = "✅ Suficiente" if produto[6] >= 10 else "⚠️ Atenção" if produto[6] >= 5 else "🔴 Crítico"
            dados.append({
                'Produto': produto[1],
                'Categoria': produto[2],
                'Tamanho': produto[3],
                'Cor': produto[4],
                'Estoque': produto[6],
                'Status': status
            })
        
        st.dataframe(pd.DataFrame(dados), use_container_width=True)
        
        # Alertas
        produtos_criticos = [p for p in produtos if p[6] < 5]
        if produtos_criticos:
            st.warning("🚨 **Produtos com estoque crítico:**")
            for produto in produtos_criticos:
                st.error(f"**{produto[1]}** - {produto[3]} - {produto[4]}: apenas **{produto[6]}** unidades")
    else:
        st.info("📝 Nenhum produto cadastrado")

# =========================================
# 🎯 RODAPÉ
# =========================================

st.sidebar.markdown("---")
st.sidebar.markdown("👕 **FashionManager Pro**")
st.sidebar.markdown("v2.0 • Render")
