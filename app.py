import streamlit as st
import os
import hashlib
import psycopg2
from datetime import datetime, date

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS Mobile
st.markdown("""
<style>
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        .stButton button {
            width: 100%;
            padding: 0.75rem;
        }
        .stTextInput input, .stSelectbox select, .stNumberInput input {
            font-size: 16px;
            padding: 0.75rem;
        }
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🔐 AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Conexão com PostgreSQL"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            conn = psycopg2.connect(database_url, sslmode='require')
            return conn
        st.error("DATABASE_URL não configurada")
        return None
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()
        
        # Tabela de usuários
        cur.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nome_completo VARCHAR(100),
                tipo VARCHAR(20) DEFAULT 'vendedor'
            )
        ''')
        
        # Tabela de escolas
        cur.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(100) UNIQUE NOT NULL
            )
        ''')
        
        # Tabela de clientes
        cur.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                telefone VARCHAR(20),
                email VARCHAR(100),
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabela de produtos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                categoria VARCHAR(100),
                tamanho VARCHAR(10),
                cor VARCHAR(50),
                preco DECIMAL(10,2),
                estoque INTEGER DEFAULT 0,
                escola_id INTEGER REFERENCES escolas(id)
            )
        ''')
        
        # Tabela de pedidos
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER REFERENCES clientes(id),
                status VARCHAR(50) DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                valor_total DECIMAL(10,2),
                observacoes TEXT
            )
        ''')
        
        # Tabela de itens do pedido
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id SERIAL PRIMARY KEY,
                pedido_id INTEGER REFERENCES pedidos(id),
                produto_id INTEGER REFERENCES produtos(id),
                quantidade INTEGER,
                preco_unitario DECIMAL(10,2)
            )
        ''')
        
        # Usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador', 'admin'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cur.execute('''
                INSERT INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            ''', (username, password_hash, nome, tipo))
        
        # Escolas padrão
        escolas_padrao = ['Municipal', 'Desperta', 'São Tadeu']
        for escola in escolas_padrao:
            cur.execute('''
                INSERT INTO escolas (nome) VALUES (%s)
                ON CONFLICT (nome) DO NOTHING
            ''', (escola,))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_login(username, password):
    """Verifica credenciais"""
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão", None
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT password_hash, nome_completo, tipo 
            FROM usuarios WHERE username = %s
        ''', (username,))
        
        resultado = cur.fetchone()
        
        if resultado and check_hashes(password, resultado[0]):
            return True, resultado[1], resultado[2]
        else:
            return False, "Credenciais inválidas", None
            
    except Exception as e:
        return False, f"Erro: {str(e)}", None
    finally:
        if conn:
            conn.close()

# =========================================
# 📱 FUNÇÕES DO SISTEMA
# =========================================

def adicionar_cliente(nome, telefone, email):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nome, telefone, email) VALUES (%s, %s, %s)",
            (nome, telefone, email)
        )
        conn.commit()
        return True, "Cliente cadastrado com sucesso!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
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
        st.error(f"Erro ao listar clientes: {e}")
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
        cur.execute('''
            INSERT INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        conn.commit()
        return True, "Produto cadastrado com sucesso!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

def listar_produtos():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute('''
            SELECT p.*, e.nome as escola_nome 
            FROM produtos p 
            LEFT JOIN escolas e ON p.escola_id = e.id 
            ORDER BY p.nome
        ''')
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar produtos: {e}")
        return []
    finally:
        if conn:
            conn.close()

def listar_escolas():
    conn = get_connection()
    if not conn:
        return []
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM escolas ORDER BY nome")
        return cur.fetchall()
    except Exception as e:
        st.error(f"Erro ao listar escolas: {e}")
        return []
    finally:
        if conn:
            conn.close()

def atualizar_estoque(produto_id, nova_quantidade):
    conn = get_connection()
    if not conn:
        return False, "Erro de conexão"
    
    try:
        cur = conn.cursor()
        cur.execute("UPDATE produtos SET estoque = %s WHERE id = %s", (nova_quantidade, produto_id))
        conn.commit()
        return True, "Estoque atualizado com sucesso!"
    except Exception as e:
        return False, f"Erro: {str(e)}"
    finally:
        if conn:
            conn.close()

# =========================================
# 🚀 APP PRINCIPAL
# =========================================

# Inicialização
if 'db_initialized' not in st.session_state:
    if init_db():
        st.session_state.db_initialized = True

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Página de Login
if not st.session_state.logged_in:
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0;'>
        <h1>👕 Sistema de Fardamentos</h1>
        <p>Faça login para continuar</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("👤 Usuário", placeholder="Digite seu usuário")
        password = st.text_input("🔒 Senha", type="password", placeholder="Digite sua senha")
        
        submitted = st.form_submit_button("🚀 Entrar", use_container_width=True)
        
        if submitted:
            if username and password:
                with st.spinner("Verificando credenciais..."):
                    sucesso, mensagem, tipo_usuario = verificar_login(username, password)
                    if sucesso:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.nome_usuario = mensagem
                        st.session_state.tipo_usuario = tipo_usuario
                        st.success(f"Bem-vindo, {mensagem}!")
                        st.rerun()
                    else:
                        st.error(mensagem)
            else:
                st.error("Por favor, preencha todos os campos")
    st.stop()

# =========================================
# 📱 INTERFACE PRINCIPAL
# =========================================

# Sidebar
st.sidebar.markdown(f"**👤 {st.session_state.nome_usuario}**")
st.sidebar.markdown(f"**🎯 {st.session_state.tipo_usuario}**")

# Menu principal
menu_options = ["📊 Dashboard", "👥 Clientes", "👕 Produtos", "📦 Estoque"]
menu = st.sidebar.radio("Navegação", menu_options)

# Header
st.title(menu)
st.markdown("---")

# Páginas do sistema
if menu == "📊 Dashboard":
    st.header("🎯 Visão Geral do Sistema")
    
    # Métricas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        clientes = listar_clientes()
        st.metric("Total de Clientes", len(clientes))
    
    with col2:
        produtos = listar_produtos()
        st.metric("Total de Produtos", len(produtos))
    
    with col3:
        produtos_baixo_estoque = len([p for p in produtos if p[6] < 5])
        st.metric("Alertas de Estoque", produtos_baixo_estoque)
    
    # Ações Rápidas
    st.header("⚡ Ações Rápidas")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👥 Cadastrar Novo Cliente", use_container_width=True):
            st.session_state.menu = "👥 Clientes"
            st.rerun()
    
    with col2:
        if st.button("👕 Cadastrar Novo Produto", use_container_width=True):
            st.session_state.menu = "👕 Produtos"
            st.rerun()

elif menu == "👥 Clientes":
    tab1, tab2 = st.tabs(["➕ Cadastrar Cliente", "📋 Listar Clientes"])
    
    with tab1:
        st.header("➕ Novo Cliente")
        
        with st.form("form_cliente"):
            nome = st.text_input("👤 Nome completo*")
            telefone = st.text_input("📞 Telefone")
            email = st.text_input("📧 Email")
            
            submitted = st.form_submit_button("✅ Cadastrar Cliente", use_container_width=True)
            
            if submitted:
                if nome:
                    sucesso, msg = adicionar_cliente(nome, telefone, email)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ O nome é obrigatório!")
    
    with tab2:
        st.header("📋 Clientes Cadastrados")
        clientes = listar_clientes()
        
        if clientes:
            for cliente in clientes:
                with st.expander(f"👤 {cliente[1]}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**📞 Telefone:** {cliente[2] or 'Não informado'}")
                    with col2:
                        st.write(f"**📧 Email:** {cliente[3] or 'Não informado'}")
                    st.write(f"**📅 Data de Cadastro:** {cliente[4]}")
        else:
            st.info("👥 Nenhum cliente cadastrado no momento.")

elif menu == "👕 Produtos":
    tab1, tab2 = st.tabs(["➕ Cadastrar Produto", "📋 Listar Produtos"])
    
    with tab1:
        st.header("➕ Novo Produto")
        
        with st.form("form_produto"):
            nome = st.text_input("👕 Nome do produto*")
            categoria = st.selectbox("📦 Categoria", ["Camisetas", "Calças/Shorts", "Agasalhos", "Acessórios"])
            tamanho = st.selectbox("📏 Tamanho", ["PP", "P", "M", "G", "GG", "2", "4", "6", "8", "10", "12"])
            cor = st.text_input("🎨 Cor", value="Branco")
            preco = st.number_input("💰 Preço (R$)", min_value=0.0, value=29.90, step=0.01)
            estoque = st.number_input("📦 Estoque inicial", min_value=0, value=10)
            
            escolas = listar_escolas()
            escola_nome = st.selectbox(
                "🏫 Escola*",
                [e[1] for e in escolas],
                help="Selecione a escola para a qual este produto é destinado"
            )
            
            submitted = st.form_submit_button("✅ Cadastrar Produto", use_container_width=True)
            
            if submitted:
                if nome and escola_nome:
                    escola_id = next(e[0] for e in escolas if e[1] == escola_nome)
                    sucesso, msg = adicionar_produto(nome, categoria, tamanho, cor, preco, estoque, escola_id)
                    if sucesso:
                        st.success(msg)
                        st.balloons()
                    else:
                        st.error(msg)
                else:
                    st.error("❌ Nome do produto e escola são obrigatórios!")
    
    with tab2:
        st.header("📋 Produtos Cadastrados")
        produtos = listar_produtos()
        
        if produtos:
            for produto in produtos:
                with st.expander(f"👕 {produto[1]} - {produto[3]} - {produto[4]}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**📦 Categoria:** {produto[2]}")
                        st.write(f"**💰 Preço:** R$ {produto[5]:.2f}")
                    with col2:
                        st.write(f"**📦 Estoque:** {produto[6]} unidades")
                        st.write(f"**🏫 Escola:** {produto[8]}")
                    
                    # Ação rápida: ajustar estoque
                    novo_estoque = st.number_input(
                        "Ajustar estoque:",
                        min_value=0,
                        value=produto[6],
                        key=f"estoque_{produto[0]}"
                    )
                    
                    if novo_estoque != produto[6]:
                        if st.button("💾 Atualizar Estoque", key=f"btn_{produto[0]}", use_container_width=True):
                            sucesso, msg = atualizar_estoque(produto[0], novo_estoque)
                            if sucesso:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
        else:
            st.info("👕 Nenhum produto cadastrado no momento.")

elif menu == "📦 Estoque":
    st.header("📊 Controle de Estoque")
    
    produtos = listar_produtos()
    
    if produtos:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            categorias = list(set([p[2] for p in produtos]))
            categoria_filtro = st.selectbox("Filtrar por categoria:", ["Todas"] + categorias)
        
        with col2:
            escolas = list(set([p[8] for p in produtos if p[8]]))
            escola_filtro = st.selectbox("Filtrar por escola:", ["Todas"] + escolas)
        
        # Aplicar filtros
        produtos_filtrados = produtos
        if categoria_filtro != "Todas":
            produtos_filtrados = [p for p in produtos_filtrados if p[2] == categoria_filtro]
        if escola_filtro != "Todas":
            produtos_filtrados = [p for p in produtos_filtrados if p[8] == escola_filtro]
        
        # Exibir produtos
        for produto in produtos_filtrados:
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            
            with col1:
                st.write(f"**{produto[1]}**")
                st.write(f"{produto[2]} - {produto[3]} - {produto[4]}")
                st.write(f"Escola: {produto[8]}")
            
            with col2:
                st.write(f"**Estoque:**")
                if produto[6] < 5:
                    st.error(f"❌ {produto[6]}")
                elif produto[6] < 10:
                    st.warning(f"⚠️ {produto[6]}")
                else:
                    st.success(f"✅ {produto[6]}")
            
            with col3:
                st.write(f"**Preço:**")
                st.write(f"R$ {produto[5]:.2f}")
            
            with col4:
                novo_estoque = st.number_input(
                    "Novo valor:",
                    min_value=0,
                    value=produto[6],
                    key=f"estoque_main_{produto[0]}"
                )
                
                if novo_estoque != produto[6]:
                    if st.button("💾", key=f"save_{produto[0]}"):
                        sucesso, msg = atualizar_estoque(produto[0], novo_estoque)
                        if sucesso:
                            st.success("Estoque atualizado!")
                            st.rerun()
                        else:
                            st.error(msg)
            
            st.markdown("---")
    else:
        st.info("👕 Nenhum produto cadastrado para exibir controle de estoque.")

# Logout
st.sidebar.markdown("---")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# Rodapé
st.sidebar.markdown("---")
st.sidebar.markdown("👕 **Sistema de Fardamentos v3.0**")
st.sidebar.markdown("🗄️ **PostgreSQL** | 📱 **Mobile**")
