import streamlit as st
from datetime import datetime, date, timedelta
import json
import os
import hashlib
import sqlite3
import csv
from io import StringIO
import pytz

# Configuração da página
st.set_page_config(
    page_title="Sistema de Gestão",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Função para obter data/hora do Brasil
def get_brasil_datetime():
    tz_brasil = pytz.timezone('America/Sao_Paulo')
    return datetime.now(tz_brasil)

# Função para formatar data no padrão BR
def format_date_br(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        except:
            return dt
    return dt.strftime("%d/%m/%Y %H:%M")

# Sistema de Autenticação
def init_db():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Tabela de usuários
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  nivel TEXT,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de clientes
    c.execute('''CREATE TABLE IF NOT EXISTS clientes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT NOT NULL,
                  telefone TEXT,
                  email TEXT,
                  cpf TEXT,
                  endereco TEXT,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de escolas
    c.execute('''CREATE TABLE IF NOT EXISTS escolas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT,
                  telefone TEXT,
                  email TEXT,
                  endereco TEXT,
                  responsavel TEXT,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de produtos
    c.execute('''CREATE TABLE IF NOT EXISTS produtos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  nome TEXT,
                  descricao TEXT,
                  preco REAL,
                  custo REAL,
                  estoque_minimo INTEGER,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Tabela de estoque por escola
    c.execute('''CREATE TABLE IF NOT EXISTS estoque_escolas
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  escola_id INTEGER,
                  produto_id INTEGER,
                  quantidade INTEGER,
                  FOREIGN KEY(escola_id) REFERENCES escolas(id),
                  FOREIGN KEY(produto_id) REFERENCES produtos(id))''')
    
    # Tabela de pedidos
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  cliente_id INTEGER,
                  escola_id INTEGER,
                  status TEXT,
                  total REAL,
                  desconto REAL,
                  custo_total REAL,
                  lucro_total REAL,
                  margem_lucro REAL,
                  criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(cliente_id) REFERENCES clientes(id),
                  FOREIGN KEY(escola_id) REFERENCES escolas(id))''')
    
    # Tabela de itens do pedido
    c.execute('''CREATE TABLE IF NOT EXISTS itens_pedido
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  pedido_id INTEGER,
                  produto_id INTEGER,
                  quantidade INTEGER,
                  preco_unitario REAL,
                  custo_unitario REAL,
                  lucro_unitario REAL,
                  margem_lucro REAL,
                  FOREIGN KEY(pedido_id) REFERENCES pedidos(id),
                  FOREIGN KEY(produto_id) REFERENCES produtos(id))''')
    
    # Inserir usuário admin padrão se não existir
    c.execute("SELECT COUNT(*) FROM usuarios WHERE username='admin'")
    if c.fetchone()[0] == 0:
        senha_hash = hashlib.sha256("admin123".encode()).hexdigest()
        c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (?, ?, ?)",
                 ('admin', senha_hash, 'admin'))
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()
    
    if user and user[2] == hash_password(password):
        return user
    return None

# Funções de Gestão de Clientes
def add_cliente(nome, telefone, email, cpf, endereco):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO clientes (nome, telefone, email, cpf, endereco)
                     VALUES (?, ?, ?, ?, ?)''', (nome, telefone, email, cpf, endereco))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_clientes():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM clientes ORDER BY nome")
    clientes = c.fetchall()
    conn.close()
    return clientes

def update_cliente(cliente_id, nome, telefone, email, cpf, endereco):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''UPDATE clientes SET nome=?, telefone=?, email=?, cpf=?, endereco=?
                 WHERE id=?''', (nome, telefone, email, cpf, endereco, cliente_id))
    conn.commit()
    conn.close()

def delete_cliente(cliente_id):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("DELETE FROM clientes WHERE id=?", (cliente_id,))
    conn.commit()
    conn.close()

# Funções de Gestão de Escolas
def add_escola(nome, telefone, email, endereco, responsavel):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''INSERT INTO escolas (nome, telefone, email, endereco, responsavel)
                 VALUES (?, ?, ?, ?, ?)''', (nome, telefone, email, endereco, responsavel))
    conn.commit()
    conn.close()

def get_escolas():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM escolas ORDER BY nome")
    escolas = c.fetchall()
    conn.close()
    return escolas

# Funções de Gestão de Produtos
def add_produto(nome, descricao, preco, custo, estoque_minimo):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''INSERT INTO produtos (nome, descricao, preco, custo, estoque_minimo)
                 VALUES (?, ?, ?, ?, ?)''', (nome, descricao, preco, custo, estoque_minimo))
    produto_id = c.lastrowid
    conn.commit()
    conn.close()
    return produto_id

def get_produtos():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT * FROM produtos ORDER BY nome")
    produtos = c.fetchall()
    conn.close()
    return produtos

def update_produto(produto_id, nome, descricao, preco, custo, estoque_minimo):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''UPDATE produtos SET nome=?, descricao=?, preco=?, custo=?, estoque_minimo=?
                 WHERE id=?''', (nome, descricao, preco, custo, estoque_minimo, produto_id))
    conn.commit()
    conn.close()

def delete_produto(produto_id):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("DELETE FROM produtos WHERE id=?", (produto_id,))
    c.execute("DELETE FROM estoque_escolas WHERE produto_id=?", (produto_id,))
    conn.commit()
    conn.close()

# Funções de Gestão de Estoque por Escola
def get_estoque_escola(escola_id):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''SELECT e.id, p.nome, e.quantidade, p.estoque_minimo, p.preco, p.custo, p.id as produto_id
                 FROM estoque_escolas e
                 JOIN produtos p ON e.produto_id = p.id
                 WHERE e.escola_id = ?''', (escola_id,))
    estoque = c.fetchall()
    conn.close()
    return estoque

def get_estoque_produto_escola(escola_id, produto_id):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''SELECT quantidade FROM estoque_escolas 
                 WHERE escola_id = ? AND produto_id = ?''', (escola_id, produto_id))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else 0

def update_estoque_escola(escola_id, produto_id, quantidade):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Verificar se já existe estoque para esta escola/produto
    c.execute('''SELECT id FROM estoque_escolas 
                 WHERE escola_id = ? AND produto_id = ?''', (escola_id, produto_id))
    existe = c.fetchone()
    
    if existe:
        c.execute('''UPDATE estoque_escolas SET quantidade = ?
                     WHERE escola_id = ? AND produto_id = ?''', 
                  (quantidade, escola_id, produto_id))
    else:
        c.execute('''INSERT INTO estoque_escolas (escola_id, produto_id, quantidade)
                     VALUES (?, ?, ?)''', (escola_id, produto_id, quantidade))
    
    conn.commit()
    conn.close()

# Função para vincular produto a todas as escolas automaticamente
def vincular_produto_todas_escolas(produto_id, quantidade_inicial=0):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Buscar todas as escolas
    c.execute("SELECT id FROM escolas")
    escolas = c.fetchall()
    
    # Vincular produto a cada escola
    for escola in escolas:
        escola_id = escola[0]
        c.execute('''INSERT OR REPLACE INTO estoque_escolas (escola_id, produto_id, quantidade)
                     VALUES (?, ?, ?)''', (escola_id, produto_id, quantidade_inicial))
    
    conn.commit()
    conn.close()

# Funções de Gestão de Pedidos
def add_pedido(cliente_id, escola_id, itens, desconto=0):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Calcular totais
    total_venda = sum(item['quantidade'] * item['preco'] for item in itens)
    total_custo = sum(item['quantidade'] * item['custo'] for item in itens)
    total_com_desconto = total_venda - (total_venda * desconto / 100)
    lucro_total = total_com_desconto - total_custo
    margem_lucro = (lucro_total / total_com_desconto * 100) if total_com_desconto > 0 else 0
    
    # Inserir pedido
    c.execute('''INSERT INTO pedidos (cliente_id, escola_id, status, total, desconto, custo_total, lucro_total, margem_lucro)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
              (cliente_id, escola_id, 'Pendente', total_com_desconto, desconto, total_custo, lucro_total, margem_lucro))
    
    pedido_id = c.lastrowid
    
    # Inserir itens do pedido e atualizar estoque
    for item in itens:
        lucro_unitario = item['preco'] - item['custo']
        margem_unitario = (lucro_unitario / item['preco'] * 100) if item['preco'] > 0 else 0
        
        c.execute('''INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario, custo_unitario, lucro_unitario, margem_lucro)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                  (pedido_id, item['produto_id'], item['quantidade'], item['preco'], item['custo'], lucro_unitario, margem_unitario))
        
        # Atualizar estoque - reduzir quantidade
        estoque_atual = get_estoque_produto_escola(escola_id, item['produto_id'])
        nova_quantidade = estoque_atual - item['quantidade']
        update_estoque_escola(escola_id, item['produto_id'], nova_quantidade)
    
    conn.commit()
    conn.close()
    return pedido_id

def get_pedidos():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''SELECT p.*, c.nome as cliente_nome, e.nome as escola_nome 
                 FROM pedidos p
                 LEFT JOIN clientes c ON p.cliente_id = c.id
                 LEFT JOIN escolas e ON p.escola_id = e.id
                 ORDER BY p.criado_em DESC''')
    pedidos = c.fetchall()
    conn.close()
    return pedidos

def update_pedido_status(pedido_id, novo_status):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    conn.commit()
    conn.close()

# Funções de Gestão de Usuários
def add_usuario(username, password, nivel):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    try:
        senha_hash = hash_password(password)
        c.execute("INSERT INTO usuarios (username, password, nivel) VALUES (?, ?, ?)",
                 (username, senha_hash, nivel))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_usuarios():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("SELECT id, username, nivel, criado_em FROM usuarios ORDER BY username")
    usuarios = c.fetchall()
    conn.close()
    return usuarios

def delete_usuario(usuario_id):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE id=?", (usuario_id,))
    conn.commit()
    conn.close()

def update_usuario_password(usuario_id, nova_senha):
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    nova_senha_hash = hash_password(nova_senha)
    c.execute("UPDATE usuarios SET password=? WHERE id=?", (nova_senha_hash, usuario_id))
    conn.commit()
    conn.close()

# Sistema de IA - Previsões baseadas em dados reais
def previsao_vendas():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    
    # Buscar dados históricos dos últimos 6 meses
    c.execute('''SELECT strftime('%Y-%m', criado_em) as mes, SUM(total) as total_mes
                 FROM pedidos 
                 WHERE criado_em >= date('now', '-6 months')
                 GROUP BY mes
                 ORDER BY mes''')
    dados_historicos = c.fetchall()
    
    conn.close()
    
    if dados_historicos:
        # Calcular previsão baseada na média com crescimento de 10%
        ultimo_mes = dados_historicos[-1][1]
        previsao_base = ultimo_mes * 1.1  # 10% de crescimento
        
        meses = ['Próximo Mês', '2° Mês', '3° Mês', '4° Mês', '5° Mês', '6° Mês']
        previsoes = [previsao_base * (1 + 0.1 * i) for i in range(6)]
        
        return meses, previsoes
    else:
        # Dados simulados caso não haja histórico
        meses = ['Próximo Mês', '2° Mês', '3° Mês', '4° Mês', '5° Mês', '6° Mês']
        previsoes = [12000, 15000, 18000, 22000, 25000, 29000]
        return meses, previsoes

def alertas_estoque():
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute('''SELECT e.escola_id, esc.nome as escola_nome, p.nome as produto_nome, 
                        e.quantidade, p.estoque_minimo
                 FROM estoque_escolas e
                 JOIN produtos p ON e.produto_id = p.id
                 JOIN escolas esc ON e.escola_id = esc.id
                 WHERE e.quantidade <= p.estoque_minimo''')
    alertas = c.fetchall()
    conn.close()
    return alertas

# Funções para resetar dados
def resetar_dados_ai():
    """Remove apenas dados de pedidos para resetar as previsões da AI"""
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("DELETE FROM itens_pedido")
    c.execute("DELETE FROM pedidos")
    conn.commit()
    conn.close()

def resetar_dados_completos():
    """Remove todos os dados exceto usuários"""
    conn = sqlite3.connect('gestao.db')
    c = conn.cursor()
    c.execute("DELETE FROM itens_pedido")
    c.execute("DELETE FROM pedidos")
    c.execute("DELETE FROM estoque_escolas")
    c.execute("DELETE FROM clientes")
    c.execute("DELETE FROM escolas")
    c.execute("DELETE FROM produtos")
    conn.commit()
    conn.close()

# Interface Principal
def main():
    init_db()
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if not st.session_state.user:
        show_login()
    else:
        show_main_app()

def show_login():
    st.title("🔐 Sistema de Gestão - Login")
    
    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")
        
        if submit:
            user = verify_login(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

def show_main_app():
    st.sidebar.title(f"👋 Bem-vindo, {st.session_state.user[1]}")
    st.sidebar.write(f"**Nível:** {st.session_state.user[3]}")
    st.sidebar.write(f"**Data:** {format_date_br(get_brasil_datetime())}")
    
    # Menu lateral baseado no nível de usuário
    menu_options = ["📊 Dashboard", "👥 Gestão de Clientes", "🏫 Gestão de Escolas", 
                   "📦 Gestão de Produtos", "📦 Sistema de Pedidos", "📈 Relatórios", "🤖 Sistema A.I."]
    
    if st.session_state.user[3] == 'admin':
        menu_options.append("🔐 Administração")
    
    choice = st.sidebar.selectbox("Navegação", menu_options)
    
    if choice == "📊 Dashboard":
        show_dashboard()
    elif choice == "👥 Gestão de Clientes":
        show_client_management()
    elif choice == "🏫 Gestão de Escolas":
        show_school_management()
    elif choice == "📦 Gestão de Produtos":
        show_product_management()
    elif choice == "📦 Sistema de Pedidos":
        show_order_management()
    elif choice == "📈 Relatórios":
        show_reports()
    elif choice == "🤖 Sistema A.I.":
        show_ai_system()
    elif choice == "🔐 Administração":
        show_admin_panel()
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.user = None
        st.rerun()

def show_dashboard():
    st.title("📊 Dashboard Principal")
    
    # Métricas rápidas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        clientes = get_clientes()
        st.metric("Total de Clientes", len(clientes))
    
    with col2:
        escolas = get_escolas()
        st.metric("Escolas Parceiras", len(escolas))
    
    with col3:
        pedidos = get_pedidos()
        st.metric("Pedidos Realizados", len(pedidos))
    
    with col4:
        total_vendas = sum(pedido[4] for pedido in pedidos)
        st.metric("Faturamento Total", f"R$ {total_vendas:,.2f}")
    
    # Gráficos simplificados sem Plotly
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Previsão de Vendas")
        meses, vendas = previsao_vendas()
        
        for i, (mes, venda) in enumerate(zip(meses, vendas)):
            st.write(f"**{mes}:** R$ {venda:,.2f}")
            st.progress(min(venda / 30000, 1.0))
    
    with col2:
        st.subheader("Status dos Pedidos")
        pedidos = get_pedidos()
        status_count = {}
        for pedido in pedidos:
            status = pedido[3]
            status_count[status] = status_count.get(status, 0) + 1
        
        for status, count in status_count.items():
            st.write(f"**{status}:** {count} pedidos")

def show_client_management():
    st.title("👥 Gestão de Clientes")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Cliente", "Lista de Clientes", "Buscar/Editar"])
    
    with tab1:
        st.subheader("Novo Cliente")
        with st.form("novo_cliente"):
            nome = st.text_input("Nome Completo *")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            cpf = st.text_input("CPF (Opcional)")
            endereco = st.text_area("Endereço")
            
            if st.form_submit_button("Cadastrar Cliente"):
                if nome:
                    if add_cliente(nome, telefone, email, cpf, endereco):
                        st.success("Cliente cadastrado com sucesso!")
                    else:
                        st.error("Erro ao cadastrar cliente")
                else:
                    st.error("Nome é obrigatório")
    
    with tab2:
        st.subheader("Lista de Clientes")
        clientes = get_clientes()
        
        for cliente in clientes:
            with st.expander(f"{cliente[1]} - {cliente[4] or 'Sem CPF'}"):
                st.write(f"**Telefone:** {cliente[2]}")
                st.write(f"**Email:** {cliente[3]}")
                st.write(f"**Endereço:** {cliente[5]}")
                st.write(f"**Cadastrado em:** {format_date_br(cliente[6])}")
                
                if st.button(f"Excluir", key=f"del_{cliente[0]}"):
                    delete_cliente(cliente[0])
                    st.rerun()
    
    with tab3:
        st.subheader("Buscar e Editar Clientes")
        search_term = st.text_input("Buscar por nome ou CPF")
        
        clientes = get_clientes()
        if search_term:
            clientes_filtrados = [c for c in clientes if search_term.lower() in c[1].lower() or (c[4] and search_term in c[4])]
        else:
            clientes_filtrados = clientes
            
        for cliente in clientes_filtrados:
            with st.form(f"edit_{cliente[0]}"):
                st.write(f"Editando: {cliente[1]}")
                nome = st.text_input("Nome *", value=cliente[1], key=f"nome_{cliente[0]}")
                telefone = st.text_input("Telefone", value=cliente[2], key=f"tel_{cliente[0]}")
                email = st.text_input("Email", value=cliente[3], key=f"email_{cliente[0]}")
                cpf = st.text_input("CPF", value=cliente[4] or "", key=f"cpf_{cliente[0]}")
                endereco = st.text_area("Endereço", value=cliente[5], key=f"end_{cliente[0]}")
                
                if st.form_submit_button("Atualizar"):
                    update_cliente(cliente[0], nome, telefone, email, cpf, endereco)
                    st.success("Cliente atualizado!")
                    st.rerun()

def show_school_management():
    st.title("🏫 Gestão de Escolas")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Escola", "Lista de Escolas", "Estoque por Escola"])
    
    with tab1:
        st.subheader("Nova Escola Parceira")
        with st.form("nova_escola"):
            nome = st.text_input("Nome da Escola *")
            telefone = st.text_input("Telefone")
            email = st.text_input("Email")
            endereco = st.text_area("Endereço")
            responsavel = st.text_input("Responsável")
            
            if st.form_submit_button("Cadastrar Escola"):
                if nome:
                    add_escola(nome, telefone, email, endereco, responsavel)
                    st.success("Escola cadastrada com sucesso!")
                else:
                    st.error("Nome da escola é obrigatório")
    
    with tab2:
        st.subheader("Escolas Parceiras")
        escolas = get_escolas()
        
        for escola in escolas:
            with st.expander(f"{escola[1]}"):
                st.write(f"**Telefone:** {escola[2]}")
                st.write(f"**Email:** {escola[3]}")
                st.write(f"**Endereço:** {escola[4]}")
                st.write(f"**Responsável:** {escola[5]}")
                st.write(f"**Cadastrado em:** {format_date_br(escola[6])}")
    
    with tab3:
        st.subheader("Estoque por Escola")
        escolas = get_escolas()
        produtos = get_produtos()
        
        if not escolas:
            st.warning("Nenhuma escola cadastrada. Cadastre uma escola primeiro.")
            return
            
        if not produtos:
            st.warning("Nenhum produto cadastrado. Cadastre produtos primeiro.")
            return
        
        escola_selecionada = st.selectbox("Selecione a Escola", 
                                         [f"{e[0]} - {e[1]}" for e in escolas])
        
        if escola_selecionada:
            escola_id = int(escola_selecionada.split(' - ')[0])
            escola_nome = escola_selecionada.split(' - ')[1]
            
            st.write(f"### Estoque da Escola: {escola_nome}")
            
            # Mostrar estoque atual
            estoque = get_estoque_escola(escola_id)
            
            if not estoque:
                st.info("Nenhum produto vinculado a esta escola ainda.")
            else:
                for item in estoque:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"**{item[1]}**")
                        st.write(f"Preço: R$ {item[4]:.2f} | Custo: R$ {item[5]:.2f}")
                    with col2:
                        st.write(f"**Estoque:** {item[2]}")
                    with col3:
                        if item[2] <= item[3]:
                            st.error(f"⚠️ Mín: {item[3]}")
                        else:
                            st.success(f"✅ Mín: {item[3]}")
            
            st.markdown("---")
            st.subheader("Ajustar Estoque")
            
            # Formulário para ajustar estoque
            produto_ajuste = st.selectbox("Selecione o Produto", 
                                         [f"{p[0]} - {p[1]}" for p in produtos])
            quantidade_atual = 0
            
            if produto_ajuste:
                produto_id = int(produto_ajuste.split(' - ')[0])
                quantidade_atual = get_estoque_produto_escola(escola_id, produto_id)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Estoque atual: **{quantidade_atual}**")
                with col2:
                    nova_quantidade = st.number_input("Nova quantidade", 
                                                     min_value=0, 
                                                     value=quantidade_atual,
                                                     key=f"ajuste_{produto_id}")
                
                if st.button("Atualizar Estoque", key=f"btn_ajuste_{produto_id}"):
                    update_estoque_escola(escola_id, produto_id, nova_quantidade)
                    st.success(f"Estoque de {produto_ajuste.split(' - ')[1]} atualizado para {nova_quantidade}!")
                    st.rerun()

def show_product_management():
    st.title("📦 Gestão de Produtos")
    
    tab1, tab2, tab3 = st.tabs(["Cadastrar Produto", "Lista de Produtos", "Editar Produtos"])
    
    with tab1:
        st.subheader("Novo Produto")
        with st.form("novo_produto"):
            nome = st.text_input("Nome do Produto *")
            descricao = st.text_area("Descrição")
            col1, col2, col3 = st.columns(3)
            with col1:
                preco = st.number_input("Preço de Venda (R$)", min_value=0.0, value=0.0, step=0.01)
            with col2:
                custo = st.number_input("Custo (R$)", min_value=0.0, value=0.0, step=0.01)
            with col3:
                estoque_minimo = st.number_input("Estoque Mínimo", min_value=0, value=5)
            
            # Opção para vincular automaticamente às escolas
            escolas = get_escolas()
            if escolas:
                vincular_escolas = st.checkbox("Vincular este produto a todas as escolas automaticamente", value=True)
                estoque_inicial = st.number_input("Estoque inicial nas escolas", min_value=0, value=0)
            else:
                st.warning("Cadastre escolas primeiro para vincular produtos")
                vincular_escolas = False
                estoque_inicial = 0
            
            if st.form_submit_button("Cadastrar Produto"):
                if nome and preco > 0:
                    produto_id = add_produto(nome, descricao, preco, custo, estoque_minimo)
                    st.success("Produto cadastrado com sucesso!")
                    
                    # Vincular automaticamente às escolas
                    if vincular_escolas and escolas:
                        vincular_produto_todas_escolas(produto_id, estoque_inicial)
                        st.success(f"Produto vinculado automaticamente a {len(escolas)} escolas com estoque inicial de {estoque_inicial} unidades")
                    
                    # Calcular margem automática
                    if preco > 0 and custo > 0:
                        margem = ((preco - custo) / preco) * 100
                        st.info(f"Margem de lucro: {margem:.1f}%")
                else:
                    st.error("Nome e preço são obrigatórios")
    
    with tab2:
        st.subheader("Lista de Produtos")
        produtos = get_produtos()
        
        for produto in produtos:
            with st.expander(f"{produto[1]} - R$ {produto[3]:.2f}"):
                st.write(f"**Descrição:** {produto[2]}")
                st.write(f"**Preço:** R$ {produto[3]:.2f}")
                st.write(f"**Custo:** R$ {produto[4]:.2f}")
                st.write(f"**Estoque Mínimo:** {produto[5]}")
                
                # Calcular margem
                if produto[3] > 0 and produto[4] > 0:
                    margem = ((produto[3] - produto[4]) / produto[3]) * 100
                    lucro_unitario = produto[3] - produto[4]
                    st.write(f"**Margem:** {margem:.1f}%")
                    st.write(f"**Lucro Unitário:** R$ {lucro_unitario:.2f}")
                
                # Mostrar estoque total por escola
                st.write("**Estoque por Escola:**")
                escolas = get_escolas()
                tem_estoque = False
                for escola in escolas:
                    estoque = get_estoque_produto_escola(escola[0], produto[0])
                    if estoque > 0:
                        st.write(f"- {escola[1]}: {estoque} unidades")
                        tem_estoque = True
                
                if not tem_estoque:
                    st.write("Nenhum estoque em nenhuma escola")
                
                if st.button(f"Excluir", key=f"del_prod_{produto[0]}"):
                    delete_produto(produto[0])
                    st.rerun()
    
    with tab3:
        st.subheader("Editar Produtos")
        produtos = get_produtos()
        
        for produto in produtos:
            with st.form(f"edit_prod_{produto[0]}"):
                st.write(f"Editando: {produto[1]}")
                nome = st.text_input("Nome", value=produto[1], key=f"prod_nome_{produto[0]}")
                descricao = st.text_area("Descrição", value=produto[2], key=f"prod_desc_{produto[0]}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    preco = st.number_input("Preço", value=float(produto[3]), key=f"prod_preco_{produto[0]}")
                with col2:
                    custo = st.number_input("Custo", value=float(produto[4]), key=f"prod_custo_{produto[0]}")
                with col3:
                    estoque_minimo = st.number_input("Estoque Mínimo", value=produto[5], key=f"prod_est_min_{produto[0]}")
                
                if st.form_submit_button("Atualizar"):
                    update_produto(produto[0], nome, descricao, preco, custo, estoque_minimo)
                    st.success("Produto atualizado!")
                    st.rerun()

def show_order_management():
    st.title("📦 Sistema de Pedidos")
    
    tab1, tab2 = st.tabs(["Novo Pedido", "Histórico de Pedidos"])
    
    with tab1:
        st.subheader("Criar Novo Pedido")
        
        clientes = get_clientes()
        escolas = get_escolas()
        produtos = get_produtos()
        
        if not clientes:
            st.warning("Cadastre clientes primeiro para criar pedidos")
            return
            
        if not escolas:
            st.warning("Cadastre escolas primeiro para criar pedidos")
            return
            
        if not produtos:
            st.warning("Cadastre produtos primeiro para criar pedidos")
            return
        
        with st.form("novo_pedido"):
            col1, col2 = st.columns(2)
            
            with col1:
                cliente_selecionado = st.selectbox("Cliente *", 
                                                  [f"{c[0]} - {c[1]}" for c in clientes])
                escola_selecionada = st.selectbox("Escola *", 
                                                 [f"{e[0]} - {e[1]}" for e in escolas])
                desconto = st.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=0.0)
            
            st.subheader("Itens do Pedido")
            
            itens = []
            escola_id = int(escola_selecionada.split(' - ')[0]) if escola_selecionada else None
            
            # Mostrar apenas produtos com estoque na escola selecionada
            produtos_com_estoque = []
            for produto in produtos:
                if escola_id:
                    estoque = get_estoque_produto_escola(escola_id, produto[0])
                    if estoque > 0:
                        produtos_com_estoque.append(produto)
            
            for i in range(3):  # Permite até 3 itens
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    if produtos_com_estoque:
                        produto_opcoes = [f"{p[0]} - {p[1]} (Estoque: {get_estoque_produto_escola(escola_id, p[0])})" for p in produtos_com_estoque]
                        produto_selecionado = st.selectbox(f"Produto {i+1}", [""] + produto_opcoes, key=f"prod_{i}")
                    else:
                        st.warning("Nenhum produto com estoque")
                        produto_selecionado = None
                
                with col2:
                    if produto_selecionado:
                        produto_id = int(produto_selecionado.split(' - ')[0])
                        estoque_disponivel = get_estoque_produto_escola(escola_id, produto_id)
                        quantidade = st.number_input(f"Qtd {i+1}", min_value=1, max_value=estoque_disponivel, value=1, key=f"qtd_{i}")
                    else:
                        quantidade = 0
                
                with col3:
                    if produto_selecionado:
                        produto_info = next(p for p in produtos if p[0] == produto_id)
                        preco = st.number_input(f"Preço {i+1}", min_value=0.0, value=float(produto_info[3]), key=f"preco_{i}")
                        custo = produto_info[4]
                    else:
                        preco = 0.0
                        custo = 0.0
                
                with col4:
                    if produto_selecionado and preco > 0 and custo > 0:
                        lucro_unitario = preco - custo
                        margem = (lucro_unitario / preco * 100) if preco > 0 else 0
                        st.write(f"Margem: {margem:.1f}%")
                
                if produto_selecionado and quantidade > 0:
                    itens.append({
                        'produto_id': produto_id,
                        'quantidade': quantidade,
                        'preco': preco,
                        'custo': custo
                    })
            
            # Resumo do pedido
            if itens:
                st.subheader("Resumo do Pedido")
                total_venda = sum(item['quantidade'] * item['preco'] for item in itens)
                total_custo = sum(item['quantidade'] * item['custo'] for item in itens)
                total_com_desconto = total_venda - (total_venda * desconto / 100)
                lucro_total = total_com_desconto - total_custo
                margem_lucro = (lucro_total / total_com_desconto * 100) if total_com_desconto > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Venda", f"R$ {total_venda:.2f}")
                with col2:
                    st.metric("Total com Desconto", f"R$ {total_com_desconto:.2f}")
                with col3:
                    st.metric("Lucro Total", f"R$ {lucro_total:.2f}")
                with col4:
                    st.metric("Margem", f"{margem_lucro:.1f}%")
            
            if st.form_submit_button("Criar Pedido"):
                if not cliente_selecionado or not escola_selecionada:
                    st.error("Selecione cliente e escola")
                elif not itens:
                    st.error("Adicione pelo menos um item ao pedido")
                else:
                    cliente_id = int(cliente_selecionado.split(' - ')[0])
                    escola_id = int(escola_selecionada.split(' - ')[0])
                    
                    pedido_id = add_pedido(cliente_id, escola_id, itens, desconto)
                    st.success(f"Pedido #{pedido_id} criado com sucesso!")
                    
                    # Mostrar resumo final
                    st.info(f"""
                    **Resumo do Pedido #{pedido_id}:**
                    - Total: R$ {total_com_desconto:.2f}
                    - Desconto: {desconto}%
                    - Custo Total: R$ {total_custo:.2f}
                    - Lucro: R$ {lucro_total:.2f}
                    - Margem: {margem_lucro:.1f}%
                    """)
    
    with tab2:
        st.subheader("Histórico de Pedidos")
        pedidos = get_pedidos()
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("Filtrar por status", ["Todos", "Pendente", "Confirmado", "Enviado", "Entregue", "Cancelado"])
        with col2:
            search_pedido = st.text_input("Buscar por ID ou cliente")
        
        for pedido in pedidos:
            # Aplicar filtros
            if status_filter != "Todos" and pedido[3] != status_filter:
                continue
            if search_pedido and (search_pedido not in str(pedido[0]) and search_pedido.lower() not in pedido[6].lower()):
                continue
                
            with st.expander(f"Pedido #{pedido[0]} - {pedido[6]} - R$ {pedido[4]:.2f} - {pedido[3]}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Cliente:** {pedido[6]}")
                    st.write(f"**Escola:** {pedido[7]}")
                    st.write(f"**Status:** {pedido[3]}")
                    st.write(f"**Data:** {format_date_br(pedido[9])}")
                with col2:
                    st.write(f"**Total:** R$ {pedido[4]:.2f}")
                    st.write(f"**Desconto:** {pedido[5]}%")
                    st.write(f"**Custo Total:** R$ {pedido[6]:.2f}")
                    st.write(f"**Lucro:** R$ {pedido[7]:.2f}")
                    st.write(f"**Margem:** {pedido[8]:.1f}%")
                
                # Botões para alterar status
                st.write("**Alterar Status:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Confirmar", key=f"confirm_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Confirmado")
                        st.rerun()
                with col2:
                    if st.button("🚚 Enviar", key=f"enviar_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Enviado")
                        st.rerun()
                with col3:
                    if st.button("📦 Entregue", key=f"entregue_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Entregue")
                        st.rerun()
                with col4:
                    if st.button("❌ Cancelar", key=f"cancelar_{pedido[0]}"):
                        update_pedido_status(pedido[0], "Cancelado")
                        st.rerun()

# ... (o restante do código permanece igual - reports, ai_system, admin_panel)

def show_reports():
    st.title("📈 Relatórios e Análises")
    
    tab1, tab2, tab3 = st.tabs(["Exportar Dados", "Análise Financeira", "Relatório de Estoque"])
    
    with tab1:
        st.subheader("Exportar Dados")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Exportar Clientes CSV"):
                clientes = get_clientes()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nome', 'Telefone', 'Email', 'CPF', 'Endereço', 'Data_Criacao'])
                writer.writerows(clientes)
                st.download_button("Baixar CSV", output.getvalue(), "clientes.csv", "text/csv")
        
        with col2:
            if st.button("Exportar Pedidos CSV"):
                pedidos = get_pedidos()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Cliente_ID', 'Escola_ID', 'Status', 'Total', 'Desconto', 'Custo_Total', 'Lucro_Total', 'Margem_Lucro', 'Data', 'Cliente_Nome', 'Escola_Nome'])
                writer.writerows(pedidos)
                st.download_button("Baixar CSV", output.getvalue(), "pedidos.csv", "text/csv")
        
        with col3:
            if st.button("Exportar Produtos CSV"):
                produtos = get_produtos()
                output = StringIO()
                writer = csv.writer(output)
                writer.writerow(['ID', 'Nome', 'Descricao', 'Preco', 'Custo', 'Estoque_Minimo', 'Data_Criacao'])
                writer.writerows(produtos)
                st.download_button("Baixar CSV", output.getvalue(), "produtos.csv", "text/csv")
    
    with tab2:
        st.subheader("Análise Financeira")
        pedidos = get_pedidos()
        
        if pedidos:
            total_vendas = sum(pedido[4] for pedido in pedidos)
            total_custo = sum(pedido[6] for pedido in pedidos)
            total_lucro = sum(pedido[7] for pedido in pedidos)
            margem_media = (total_lucro / total_vendas * 100) if total_vendas > 0 else 0
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total de Vendas", f"R$ {total_vendas:,.2f}")
            with col2:
                st.metric("Total de Custos", f"R$ {total_custo:,.2f}")
            with col3:
                st.metric("Lucro Total", f"R$ {total_lucro:,.2f}")
            with col4:
                st.metric("Margem Média", f"{margem_media:.1f}%")
            
            # Vendas por status
            st.subheader("Vendas por Status")
            status_vendas = {}
            for pedido in pedidos:
                status = pedido[3]
                status_vendas[status] = status_vendas.get(status, 0) + pedido[4]
            
            for status, total in status_vendas.items():
                st.write(f"**{status}:** R$ {total:,.2f}")
        else:
            st.info("Nenhum pedido encontrado para análise")
    
    with tab3:
        st.subheader("Relatório de Estoque")
        escolas = get_escolas()
        
        for escola in escolas:
            with st.expander(f"Estoque - {escola[1]}"):
                estoque = get_estoque_escola(escola[0])
                if estoque:
                    for item in estoque:
                        status = "✅ Suficiente" if item[2] > item[3] else "⚠️ Baixo"
                        st.write(f"**{item[1]}**: {item[2]} unidades ({status})")
                else:
                    st.info("Nenhum produto em estoque")

def show_ai_system():
    st.title("🤖 Sistema A.I. Inteligente")
    
    tab1, tab2, tab3 = st.tabs(["📈 Previsões de Vendas", "⚠️ Alertas Automáticos", "🔄 Gerenciar Dados"])
    
    with tab1:
        st.subheader("Previsões de Vendas")
        meses, vendas = previsao_vendas()
        
        st.write("**Previsão para os próximos 6 meses:**")
        for mes, venda in zip(meses, vendas):
            st.write(f"- **{mes}:** R$ {venda:,.2f}")
            st.progress(min(venda / 50000, 1.0))
        
        # Análise de tendências
        st.subheader("Análise de Tendências")
        
        pedidos = get_pedidos()
        if pedidos:
            # Calcular crescimento real
            vendas_por_mes = {}
            for pedido in pedidos:
                data = datetime.strptime(pedido[9], '%Y-%m-%d %H:%M:%S')
                mes_ano = data.strftime('%Y-%m')
                vendas_por_mes[mes_ano] = vendas_por_mes.get(mes_ano, 0) + pedido[4]
            
            if len(vendas_por_mes) > 1:
                meses_ordenados = sorted(vendas_por_mes.keys())
                crescimento = ((vendas_por_mes[meses_ordenados[-1]] - vendas_por_mes[meses_ordenados[0]]) / vendas_por_mes[meses_ordenados[0]]) * 100
                st.info(f"**Crescimento real:** {crescimento:.1f}% nos últimos {len(meses_ordenados)} meses")
        
        st.info("""
        **Insights da IA:**
        - Baseado em dados históricos de vendas
        - Considera tendência de crescimento de 10% ao mês
        - Ajusta automaticamente conforme novos pedidos são cadastrados
        - Recomendação: Aumentar estoque em 15% para atender à demanda prevista
        """)
    
    with tab2:
        st.subheader("Alertas Automáticos")
        alertas = alertas_estoque()
        
        if alertas:
            for alerta in alertas:
                st.error(f"""
                ⚠️ **ALERTA DE ESTOQUE BAIXO**
                - Escola: {alerta[1]}
                - Produto: {alerta[2]}
                - Estoque atual: {alerta[3]}
                - Mínimo recomendado: {alerta[4]}
                """)
        else:
            st.success("✅ Nenhum alerta de estoque baixo no momento")
        
        # Alertas de produtos sem estoque
        st.subheader("Produtos Sem Estoque")
        produtos = get_produtos()
        escolas = get_escolas()
        
        produtos_sem_estoque = []
        for produto in produtos:
            tem_estoque = False
            for escola in escolas:
                estoque = get_estoque_produto_escola(escola[0], produto[0])
                if estoque > 0:
                    tem_estoque = True
                    break
            
            if not tem_estoque:
                produtos_sem_estoque.append(produto)
        
        if produtos_sem_estoque:
            for produto in produtos_sem_estoque:
                st.warning(f"📦 **{produto[1]}** - Nenhum estoque em nenhuma escola")
        else:
            st.success("✅ Todos os produtos têm estoque em pelo menos uma escola")
    
    with tab3:
        st.subheader("Gerenciar Dados da A.I.")
        
        st.warning("""
        **Atenção:** 
        - Resetar dados da A.I. apagará todos os pedidos para recalcular previsões
        - Reset completo apagará todos os dados exceto usuários
        - Estas ações não podem ser desfeitas
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Resetar Dados da A.I. (Pedidos)", type="secondary"):
                resetar_dados_ai()
                st.success("Dados da A.I. resetados com sucesso!")
                st.info("As previsões agora serão baseadas em dados novos")
        
        with col2:
            if st.button("🗑️ Resetar Todos os Dados", type="primary"):
                resetar_dados_completos()
                st.success("Todos os dados foram resetados!")
                st.info("Sistema pronto para começar do zero")

def show_admin_panel():
    if st.session_state.user[3] != 'admin':
        st.error("Acesso negado! Apenas administradores podem acessar esta área.")
        return
        
    st.title("🔐 Painel de Administração")
    
    tab1, tab2, tab3 = st.tabs(["Gerenciar Usuários", "Backup de Dados", "Alterar Minha Senha"])
    
    with tab1:
        st.subheader("Gerenciar Usuários")
        
        # Adicionar novo usuário
        with st.form("novo_usuario"):
            st.write("**Adicionar Novo Usuário**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                username = st.text_input("Nome de usuário")
            with col2:
                password = st.text_input("Senha", type="password")
            with col3:
                nivel = st.selectbox("Nível", ["admin", "gestor", "vendedor"])
            
            if st.form_submit_button("Criar Usuário"):
                if username and password:
                    if add_usuario(username, password, nivel):
                        st.success(f"Usuário {username} criado com sucesso!")
                    else:
                        st.error("Erro: Nome de usuário já existe")
                else:
                    st.error("Nome de usuário e senha são obrigatórios")
        
        # Listar usuários existentes
        st.subheader("Usuários do Sistema")
        usuarios = get_usuarios()
        
        for usuario in usuarios:
            with st.expander(f"{usuario[1]} - {usuario[2]}"):
                st.write(f"ID: {usuario[0]}")
                st.write(f"Nível: {usuario[2]}")
                st.write(f"Criado em: {format_date_br(usuario[3])}")
                
                if usuario[1] != "admin":  # Não permite excluir o admin principal
                    if st.button(f"Excluir Usuário", key=f"del_user_{usuario[0]}"):
                        delete_usuario(usuario[0])
                        st.success("Usuário excluído!")
                        st.rerun()
                else:
                    st.info("Usuário admin principal - não pode ser excluído")
    
    with tab2:
        st.subheader("Backup de Dados")
        
        if st.button("Gerar Backup Completo"):
            # Criar backup de todas as tabelas
            conn = sqlite3.connect('gestao.db')
            backup_data = {}
            
            tables = ['usuarios', 'clientes', 'escolas', 'produtos', 'estoque_escolas', 'pedidos', 'itens_pedido']
            for table in tables:
                c = conn.cursor()
                c.execute(f"SELECT * FROM {table}")
                backup_data[table] = c.fetchall()
            
            conn.close()
            
            # Salvar como JSON
            backup_json = json.dumps(backup_data, indent=2, default=str)
            st.download_button(
                "📥 Baixar Backup", 
                backup_json, 
                f"backup_sistema_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json"
            )
            st.success("Backup gerado com sucesso!")
    
    with tab3:
        st.subheader("Alterar Minha Senha")
        
        with st.form("alterar_senha"):
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha = st.text_input("Nova Senha", type="password")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.form_submit_button("Alterar Senha"):
                if nova_senha == confirmar_senha:
                    # Verificar senha atual
                    if verify_login(st.session_state.user[1], senha_atual):
                        update_usuario_password(st.session_state.user[0], nova_senha)
                        st.success("Senha alterada com sucesso!")
                    else:
                        st.error("Senha atual incorreta")
                else:
                    st.error("As novas senhas não coincidem")

if __name__ == "__main__":
    main()