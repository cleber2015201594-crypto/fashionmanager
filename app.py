import streamlit as st
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import numpy as np
import io
import csv

# =========================================
# 🎯 CONFIGURAÇÃO
# =========================================

st.set_page_config(
    page_title="Sistema Fardamentos + A.I.",
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
    .admin-card { border-left: 4px solid #dc3545; }
    .gestor-card { border-left: 4px solid #ffc107; }
    .vendedor-card { border-left: 4px solid #28a745; }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 0.5rem 0;
    }
    .ai-insight-positive { 
        border-left: 4px solid #28a745;
        background: #f8fff9;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-insight-warning { 
        border-left: 4px solid #ffc107;
        background: #fffbf0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    .ai-insight-danger { 
        border-left: 4px solid #dc3545;
        background: #fff5f5;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================================
# 🇧🇷 FUNÇÕES DE FORMATAÇÃO BRASILEIRA
# =========================================

def formatar_data_brasil(data_string):
    """Converte data do banco (YYYY-MM-DD) para formato brasileiro (DD/MM/YYYY)"""
    if not data_string:
        return "N/A"
    
    try:
        # Se for objeto date/datetime
        if isinstance(data_string, (date, datetime)):
            return data_string.strftime("%d/%m/%Y")
            
        # Se já estiver no formato brasileiro, retorna como está
        if '/' in str(data_string):
            return str(data_string)
            
        # Converte do formato do banco para brasileiro
        if isinstance(data_string, str) and len(data_string) >= 10:
            partes = data_string.split('-')
            if len(partes) >= 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
        
        return str(data_string)
    except:
        return str(data_string)

def formatar_datahora_brasil(datahora_string):
    """Converte data/hora para formato brasileiro"""
    if not datahora_string:
        return "N/A"
    
    try:
        # Para datetime completo
        if ' ' in str(datahora_string):
            data_part, hora_part = str(datahora_string).split(' ', 1)
            data_brasil = formatar_data_brasil(data_part)
            # Formatar hora (remove segundos se necessário)
            hora_part = hora_part[:5]  # Mantém apenas HH:MM
            return f"{data_brasil} {hora_part}"
        else:
            return formatar_data_brasil(datahora_string)
    except:
        return str(datahora_string)

def data_atual_brasil():
    """Retorna data atual no formato brasileiro"""
    return datetime.now().strftime("%d/%m/%Y")

def hora_atual_brasil():
    """Retorna hora atual no formato brasileiro"""
    return datetime.now().strftime("%H:%M")

# =========================================
# 🔐 SISTEMA DE AUTENTICAÇÃO
# =========================================

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def get_connection():
    """Conexão com SQLite"""
    try:
        conn = sqlite3.connect('sistema_fardamentos.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        st.error(f"Erro de conexão: {str(e)}")
        return None

def init_db():
    """Inicializa banco de dados"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nome_completo TEXT,
                tipo TEXT DEFAULT 'vendedor',
                ativo INTEGER DEFAULT 1
            )
        ''')
        
        # Tabela de escolas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS escolas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                endereco TEXT,
                telefone TEXT
            )
        ''')
        
        # Tabela de clientes (SEM VÍNCULO COM ESCOLA)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_cadastro DATE DEFAULT CURRENT_DATE
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                categoria TEXT,
                tamanho TEXT,
                cor TEXT,
                preco REAL,
                estoque INTEGER DEFAULT 0,
                escola_id INTEGER,
                data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nome, tamanho, cor, escola_id),
                FOREIGN KEY (escola_id) REFERENCES escolas (id)
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                status TEXT DEFAULT 'Pendente',
                data_pedido TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_entrega_prevista DATE,
                data_entrega_real DATE,
                valor_total REAL DEFAULT 0,
                observacoes TEXT,
                FOREIGN KEY (cliente_id) REFERENCES clientes (id)
            )
        ''')
        
        # Tabela de itens do pedido
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pedido_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER,
                produto_id INTEGER,
                quantidade INTEGER,
                preco_unitario REAL,
                subtotal REAL,
                FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
                FOREIGN KEY (produto_id) REFERENCES produtos (id)
            )
        ''')
        
        # Usuários padrão
        usuarios_padrao = [
            ('admin', make_hashes('admin123'), 'Administrador Sistema', 'admin'),
            ('gestor', make_hashes('gestor123'), 'Gestor Comercial', 'gestor'),
            ('vendedor', make_hashes('vendedor123'), 'Vendedor Principal', 'vendedor')
        ]
        
        for username, password_hash, nome, tipo in usuarios_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO usuarios (username, password_hash, nome_completo, tipo) 
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, nome, tipo))
        
        # Escolas padrão
        escolas_padrao = [
            ('Escola Municipal', 'Rua Principal, 123', '(11) 9999-8888'),
            ('Colégio Desperta', 'Av. Central, 456', '(11) 7777-6666'),
            ('Instituto São Tadeu', 'Praça da Matriz, 789', '(11) 5555-4444')
        ]
        
        for nome, endereco, telefone in escolas_padrao:
            cursor.execute('INSERT OR IGNORE INTO escolas (nome, endereco, telefone) VALUES (?, ?, ?)', 
                         (nome, endereco, telefone))
        
        # Produtos de exemplo
        produtos_padrao = [
            ('Camiseta Polo', 'Camiseta', 'M', 'Branco', 29.90, 50, 1),
            ('Calça Jeans', 'Calça', '42', 'Azul', 89.90, 30, 1),
            ('Agasalho', 'Agasalho', 'G', 'Verde', 129.90, 20, 2),
            ('Short', 'Short', 'P', 'Preto', 39.90, 40, 2),
            ('Camiseta Regata', 'Camiseta', 'G', 'Vermelho', 24.90, 25, 3),
        ]
        
        for nome, categoria, tamanho, cor, preco, estoque, escola_id in produtos_padrao:
            cursor.execute('''
                INSERT OR IGNORE INTO produtos (nome, categoria, tamanho, cor, preco, estoque, escola_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nome, categoria, tamanho, cor, preco, estoque, escola_id))
        
        conn.commit()
        return True
        
    except Exception as e:
        st.error(f"Erro ao inicializar banco: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def verificar_login(username, password):
    """Verifica cred