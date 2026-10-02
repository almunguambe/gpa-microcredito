import streamlit as st
import psycopg2
import pandas as pd
import hashlib
from datetime import datetime, timedelta
from fpdf import FPDF
import base64
import os
import io
import urllib.parse

# ------------------------------------------------------------------
# 0. ESTÉTICA DE BANCO DIGITAL (ENTERPRISE EDITION)
# ------------------------------------------------------------------
def aplicar_tema_bancario():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, header, footer {visibility: hidden;}
    .stApp { background-color: #0b0c10; color: #c5c6c7; }
    .stButton>button {
        background: linear-gradient(90deg, #112240 0%, #64ffda 100%);
        color: #0a192f; border: none; border-radius: 8px; padding: 0.5rem 1.5rem; font-weight: 700;
        transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(100, 255, 218, 0.2);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(100, 255, 218, 0.4); color: #0a192f; }
    [data-testid="stMetricValue"] { color: #64ffda !important; font-weight: 800 !important; font-size: 2rem !important; }
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        background: rgba(17, 34, 64, 0.7); border: 1px solid rgba(100, 255, 218, 0.15) !important;
        border-radius: 15px; backdrop-filter: blur(10px); padding: 20px; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.3);
    }
    .stTabs [data-baseweb="tab-list"] { background-color: #112240; border-radius: 10px; padding: 5px; border: none; gap: 5px; }
    .stTabs [data-baseweb="tab"] { color: #c5c6c7; }
    .stTabs [aria-selected="true"] { background-color: #64ffda; color: #0a192f !important; font-weight: 700; border-radius: 8px;}
    .stTextInput input, .stNumberInput input, .stSelectbox > div[data-baseweb="select"] {
        background-color: #0a192f; color: white; border: 1px solid #64ffda; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 1. BASE DE DADOS E ARQUITETURA ENTERPRISE
# ------------------------------------------------------------------
def get_conn():
    conn = psycopg2.connect(st.secrets["DB_URL"])
    conn.autocommit = True 
    return conn

def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def registar_auditoria(acao, detalhes):
    try:
        conn = get_conn()
        c = conn.cursor()
        user = st.session_state.get('user_name', 'Sistema')
        emp_id = st.session_state.get('empresa_id', 1)
        c.execute("INSERT INTO cr_auditoria (empresa_id, utilizador, acao, detalhes) VALUES (%s, %s, %s, %s)", (emp_id, user, acao, detalhes))
        conn.close()
    except:
        pass

def init_db():
    conn = get_conn()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_empresas (
                    id SERIAL PRIMARY KEY, nome TEXT UNIQUE, nuit TEXT, 
                    contacto TEXT, logo_b64 TEXT, plano TEXT DEFAULT 'Standard', 
                    estado TEXT DEFAULT 'Ativa', data_expiracao TEXT DEFAULT '2027-12-31', 
                    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_usuarios (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, nome TEXT, usuario TEXT UNIQUE, 
                    senha TEXT, papel TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_clientes (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, nome TEXT, bi TEXT, nuit TEXT, 
                    telefone TEXT, morada TEXT, local_trabalho TEXT, num_conta TEXT, bi_foto_b64 TEXT, 
                    data_registo TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_contratos (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, cliente_id INTEGER, promotor_id INTEGER, capital REAL,
                    tipo_juro TEXT, taxa_juro REAL, prazo INTEGER DEFAULT 1, tipo_pagamento TEXT, 
                    permite_parcial BOOLEAN, valor_total_esperado REAL, comissao_promotor REAL DEFAULT 0.0, estado TEXT DEFAULT 'Pendente', 
                    score_risco TEXT DEFAULT 'Standard', data_contrato TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_prestacoes (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, contrato_id INTEGER, numero_prestacao INTEGER, 
                    valor_capital REAL, valor_juro REAL, valor_total REAL, data_vencimento TEXT, estado TEXT DEFAULT 'Pendente')''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_garantias (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, contrato_id INTEGER, descricao TEXT, 
                    valor_estimado REAL, estado TEXT DEFAULT 'Sob Custódia')''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_pagamentos (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, contrato_id INTEGER, prestacao_id INTEGER, valor_pago REAL, 
                    data_pagamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP, tipo_recibo TEXT)''')
                    
    c.execute('''CREATE TABLE IF NOT EXISTS cr_auditoria (
                    id SERIAL PRIMARY KEY, empresa_id INTEGER DEFAULT 1, utilizador TEXT, acao TEXT, 
                    detalhes TEXT, data_acao TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    for tabela in ['cr_usuarios', 'cr_clientes', 'cr_contratos', 'cr_prestacoes', 'cr_garantias', 'cr_pagamentos', 'cr_auditoria']:
        try:
            c.execute(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS empresa_id INTEGER DEFAULT 1")
        except:
            pass
            
    try: c.execute("ALTER TABLE cr_empresas ADD COLUMN IF NOT EXISTS logo_b64 TEXT")
    except: pass
    try: c.execute("ALTER TABLE cr_empresas ADD COLUMN IF NOT EXISTS plano TEXT DEFAULT 'Standard'")
    except: pass
    try: c.execute("ALTER TABLE cr_empresas ADD COLUMN IF NOT EXISTS data_expiracao TEXT DEFAULT '2027-12-31'")
    except: pass
    try: c.execute("ALTER TABLE cr_contratos ADD COLUMN IF NOT EXISTS promotor_id INTEGER")
    except: pass
    try: c.execute("ALTER TABLE cr_contratos ADD COLUMN IF NOT EXISTS comissao_promotor REAL DEFAULT 0.0")
    except: pass
    try: c.execute("ALTER TABLE cr_pagamentos ADD COLUMN IF NOT EXISTS prestacao_id INTEGER")
    except: pass
    
    c.execute("SELECT id FROM cr_empresas WHERE id=1")
    if not c.fetchone():
        c.execute("INSERT INTO cr_empresas (id, nome, nuit, contacto, plano) VALUES (1, 'GPA - Sociedade Unipessoal, Lda', '123456789', '+258 840000000', 'Enterprise')")
    
    c.execute("SELECT * FROM cr_usuarios WHERE usuario='superadmin'")
    if not c.fetchone():
        c.execute("INSERT INTO cr_usuarios (empresa_id, nome, usuario, senha, papel) VALUES (1, 'Diretor Master SaaS', 'superadmin', %s, 'SuperAdmin')", (hash_senha('master123'),))

    c.execute("SELECT * FROM cr_usuarios WHERE usuario='gestor'")
    if not c.fetchone():
        c.execute("INSERT INTO cr_usuarios (empresa_id, nome, usuario, senha, papel) VALUES (1, 'Administração GPA', 'gestor', %s, 'Gestor')", (hash_senha('admin123'),))
        
    c.execute("SELECT * FROM cr_usuarios WHERE usuario='promotor'")
    if not c.fetchone():
        c.execute("INSERT INTO cr_usuarios (empresa_id, nome, usuario, senha, papel) VALUES (1, 'Agente Promotor', 'promotor', %s, 'Promotor')", (hash_senha('promo123'),))
        
    conn.close()

def login_user(usuario, senha):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, empresa_id, nome, papel FROM cr_usuarios WHERE usuario=%s AND senha=%s", (usuario, hash_senha(senha)))
    data = c.fetchone()
    conn.close()
    return data

def obter_dados_empresa(empresa_id):
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT nome, logo_b64, estado FROM cr_empresas WHERE id=%s", (empresa_id,))
        res = c.fetchone()
        conn.close()
        if res:
            return res[0], res[1], res[2]
    except:
        pass
    return "GPA Microcrédito", None, "Ativa"

def converter_df_para_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio_GPA')
    processed_data = output.getvalue()
    return processed_data

def gerar_contrato_pdf(id_contrato, empresa_id, nome, bi, morada, conta, capital, prazo, pagamento, total, risco):
    nome_empresa, logo_b64, _ = obter_dados_empresa(empresa_id)
    pdf = FPDF()
    pdf.add_page()
    
    logo_path = None
    if logo_b64:
        try:
            logo_path = f"temp_logo_{empresa_id}.png"
            with open(logo_path, "wb") as fh:
                fh.write(base64.b64decode(logo_b64))
            pdf.image(logo_path, x=10, y=10, w=30)
            pdf.ln(15)
        except:
            pass

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"CONTRATO DE MUTUO - {nome_empresa.upper()}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Classificacao de Risco: {risco} | Conta Destino: {conta}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    
    texto = f"""
Entre {nome_empresa}, doravante designada por CREDORA.

E {nome}, portador(a) do BI n. {bi}, residente em {morada}, doravante designado(a) por DEVEDOR(A).

E celebrado o presente contrato sob os seguintes termos:

CLAUSULA 1: A CREDORA empresta a quantia de {capital:,.2f} MT, a ser desembolsada para a conta/M-Pesa: {conta}.
CLAUSULA 2: O(A) DEVEDOR(A) compromete-se a devolver o total de {total:,.2f} MT.
CLAUSULA 3: Prazo acordado de {prazo} periodo(s) na modalidade {pagamento}. 

Maputo, {datetime.now().strftime('%d/%m/%Y')}
    """
    pdf.multi_cell(0, 8, texto)
    pdf.ln(20)
    pdf.cell(90, 10, "____________________________________", ln=False, align='C')
    pdf.cell(90, 10, "____________________________________", ln=True, align='C')
    pdf.cell(90, 10, "A CREDORA", ln=False, align='C')
    pdf.cell(90, 10, "O(A) DEVEDOR(A)", ln=True, align='C')
    
    file_name = f"Contrato_SaaS_{id_contrato}.pdf"
    pdf.output(file_name)
    if logo_path and os.path.exists(logo_path):
        try: os.remove(logo_path)
        except: pass
    return file_name

def gerar_recibo_pdf(empresa_id, nome, valor, id_contrato):
    nome_empresa, logo_b64, _ = obter_dados_empresa(empresa_id)
    pdf = FPDF()
    pdf.add_page()
    
    logo_path = None
    if logo_b64:
        try:
            logo_path = f"temp_logo_{empresa_id}.png"
            with open(logo_path, "wb") as fh:
                fh.write(base64.b64decode(logo_b64))
            pdf.image(logo_path, x=10, y=10, w=30)
            pdf.ln(15)
        except:
            pass

    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"RECIBO OFICIAL - {nome_empresa.upper()}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Cliente: {nome}", ln=True)
    pdf.cell(0, 10, f"Valor Liquidado: {valor:,.2f} MT", ln=True)
    pdf.cell(0, 10, f"Referente ao Contrato N. {id_contrato}", ln=True)
    pdf.ln(20)
    pdf.cell(0, 10, "________________________________________________", ln=True, align='C')
    pdf.cell(0, 10, f"Certificado Digital - {nome_empresa}", ln=True, align='C')
    
    file_name = f"Recibo_SaaS_{id_contrato}.pdf"
    pdf.output(file_name)
    if logo_path and os.path.exists(logo_path):
        try: os.remove(logo_path)
        except: pass
    return file_name

# ------------------------------------------------------------------
# 2. INTERFACE PRINCIPAL MULTI-TENANT E SUPER-ADMIN
# ------------------------------------------------------------------
def view_app():
    conn = get_conn()
    papel = st.session_state['user_role']
    emp_id = st.session_state['empresa_id']
    user_id = st.session_state['user_id']
    nome_empresa, _, estado_emp = obter_dados_empresa(emp_id)
    
    if estado_emp == 'Suspensa' and papel != 'SuperAdmin':
        st.error("⚠️ A subscrição desta instituição encontra-se suspensa. Por favor, contacte o Administrador Global (SuperAdmin).")
        if st.button("Terminar Sessão"):
            st.session_state.clear()
            st.rerun()
        return

    if papel == 'SuperAdmin':
        st.markdown(f"<h2 style='text-align: center; color: #64ffda;'>⚡ Master SaaS - Painel Global Enterprise</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #8b8e94;'>Gestão de Subscrições, Licenciamento e Inquilinato Cloud</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        tab_admin1, tab_admin2, tab_admin3 = st.tabs(["🏢 Gerir Empresas & Licenças", "➕ Registar Nova Empresa", "⚙️ Controlo de Subscrições"])
        
        with tab_admin1:
            st.subheader("Instituições Parceiras na Plataforma")
            df_empresas = pd.read_sql_query('SELECT id as "ID", nome as "Empresa", nuit as "NUIT", plano as "Plano", estado as "Estado", data_expiracao as "Expiração" FROM cr_empresas', conn)
            st.dataframe(df_empresas, use_container_width=True, hide_index=True)
            
        with tab_admin2:
            st.subheader("Onboarding de Nova Empresa de Microcrédito")
            with st.container(border=True):
                n_emp_nome = st.text_input("Nome da Instituição")
                n_emp_nuit = st.text_input("NUIT")
                n_emp_cont = st.text_input("Contacto")
                n_plano = st.selectbox("Plano de Subscrição", ["Standard", "Advanced", "Enterprise"])
                st.markdown("---")
                n_admin_nome = st.text_input("Nome do Gestor Principal")
                n_admin_user = st.text_input("Username de Acesso")
                n_admin_pass = st.text_input("Palavra-Passe", type="password")
                
                if st.button("🚀 Ativar Instituição na Nuvem", use_container_width=True):
                    if n_emp_nome and n_admin_user and n_admin_pass:
                        try:
                            c = conn.cursor()
                            c.execute("INSERT INTO cr_empresas (nome, nuit, contacto, plano, data_expiracao) VALUES (%s, %s, %s, %s, %s) RETURNING id", 
                                      (n_emp_nome, n_emp_nuit, n_emp_cont, n_plano, (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')))
                            novo_emp_id = c.fetchone()[0]
                            c.execute("INSERT INTO cr_usuarios (empresa_id, nome, usuario, senha, papel) VALUES (%s, %s, %s, %s, 'Gestor')", 
                                      (novo_emp_id, n_admin_nome, n_admin_user, hash_senha(n_admin_pass)))
                            conn.commit()
                            st.success(f"Empresa '{n_emp_nome}' ativada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Erro: {e}")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")
                        
        with tab_admin3:
            st.subheader("Alterar Estado ou Suspender Licenciamento")
            with st.container(border=True):
                df_all_emp = pd.read_sql_query("SELECT id, nome, estado FROM cr_empresas", conn)
                if not df_all_emp.empty:
                    emp_selecionada = st.selectbox("Selecionar Empresa:", df_all_emp['nome'])
                    id_alvo = df_all_emp[df_all_emp['nome'] == emp_selecionada]['id'].values[0]
                    novo_estado = st.selectbox("Novo Estado da Subscrição", ["Ativa", "Suspensa"])
                    
                    if st.button("🔄 Atualizar Estado da Licença"):
                        c = conn.cursor()
                        c.execute("UPDATE cr_empresas SET estado=%s WHERE id=%s", (novo_estado, int(id_alvo)))
                        conn.commit()
                        st.success(f"Estado da empresa '{emp_selecionada}' alterado para {novo_estado}!")
                        st.rerun()
        conn.close()
        return

    st.markdown(f"<h2 style='text-align: center; color: #64ffda;'>🌐 {nome_empresa}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #8b8e94;'>Portal Operacional | Utilizador: {st.session_state['user_name']} ({papel})</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    if papel == 'Gestor':
        tabs = st.tabs(["📊 Dashboard", "⚖️ Aprovações", "👥 Clientes", "📝 Simulador", "🔒 Penhores", "💰 Tesouraria & Prestações", "⚠️ Inadimplência & Aging", "💵 Comissões", "📈 Relatórios & Excel", "⚙️ Perfil & Marca", "🛡️ Auditoria"])
        tab_dashboard, tab_aprovacoes, tab_clientes, tab_contratos, tab_garantias, tab_pagamentos, tab_inadimplencia, tab_comissoes, tab_relatorios, tab_perfil, tab_audit = tabs
    else:
        tabs = st.tabs(["👥 Clientes (KYC)", "📝 Simulação & Pedido", "💵 Minhas Comissões"])
        tab_clientes, tab_contratos, tab_comissoes_promo = tabs

    # --- DASHBOARD EXECUTIVO ---
    if papel == 'Gestor':
        with tab_dashboard:
            c = conn.cursor()
            c.execute(f"SELECT SUM(capital), SUM(valor_total_esperado - capital) FROM cr_contratos WHERE empresa_id={emp_id} AND estado='Ativo'")
            totais = c.fetchone()
            cap_ativo = totais[0] if totais[0] else 0.0
            jur_ativo = totais[1] if totais[1] else 0.0
            
            c.execute(f"SELECT SUM(valor_pago) FROM cr_pagamentos WHERE empresa_id={emp_id}")
            recebido = c.fetchone()[0]
            recebido_total = recebido if recebido else 0.0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Capital na Rua", f"{cap_ativo:,.2f} MT")
            col2.metric("Lucro Projetado", f"{jur_ativo:,.2f} MT")
            col3.metric("Tesouraria Recebida", f"{recebido_total:,.2f} MT")

        # --- APROVAÇÕES & CRIAÇÃO DA TABELA SAC (PRESTAÇÕES) ---
        with tab_aprovacoes:
            query_pendentes = f"""
                SELECT c.id, cl.nome, cl.bi, cl.morada, cl.telefone, cl.num_conta, c.capital, c.valor_total_esperado, c.comissao_promotor, c.prazo, c.tipo_pagamento, c.score_risco
                FROM cr_contratos c JOIN cr_clientes cl ON c.cliente_id = cl.id WHERE c.empresa_id = {emp_id} AND c.estado = 'Pendente'
            """
            df_pendentes = pd.read_sql_query(query_pendentes, conn)
            
            if not df_pendentes.empty:
                for index, row in df_pendentes.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**Cliente:** {row['nome']} | **Risco:** `{row['score_risco']}` | **Capital:** {row['capital']:,.2f} MT")
                        st.markdown(f"💸 **Comissão Promotor:** `{row['comissao_promotor']:,.2f} MT` | 📱 **Conta Destino:** `{row['num_conta'] if row['num_conta'] else 'N/D'}`")
                        st.markdown(f"**Total a Devolver:** {row['valor_total_esperado']:,.2f} MT | **Prazo:** {row['prazo']} ({row['tipo_pagamento']})")
                        
                        colA, colB, colC = st.columns([1,1,2])
                        if colA.button("✅ Aprovar & Gerar Prestações", key=f"apr_{row['id']}"):
                            c = conn.cursor()
                            c.execute(f"UPDATE cr_contratos SET estado='Ativo' WHERE id={row['id']} AND empresa_id={emp_id}")
                            
                            prazo = int(row['prazo'])
                            cap_prest = row['capital'] / prazo
                            juro_prest = (row['valor_total_esperado'] - row['capital']) / prazo
                            total_prest = cap_prest + juro_prest
                            
                            for p in range(1, prazo + 1):
                                data_venc = (datetime.now() + timedelta(days=30 * p)).strftime('%Y-%m-%d')
                                c.execute("""INSERT INTO cr_prestacoes (empresa_id, contrato_id, numero_prestacao, valor_capital, valor_juro, valor_total, data_vencimento, estado) 
                                          VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pendente')""", 
                                          (emp_id, int(row['id']), p, cap_prest, juro_prest, total_prest, data_venc))
                            
                            conn.commit()
                            registar_auditoria("APROVAÇÃO", f"Contrato #{row['id']} aprovado com {prazo} prestações geradas.")
                            
                            pdf_path = gerar_contrato_pdf(row['id'], emp_id, row['nome'], row['bi'], row['morada'], str(row['num_conta']), row['capital'], row['prazo'], row['tipo_pagamento'], row['valor_total_esperado'], row['score_risco'])
                            with open(pdf_path, "rb") as f:
                                st.download_button("📄 Descarregar Contrato PDF", f, pdf_path, "application/pdf")
                            st.success("Crédito ativado e plano de prestações gerado com sucesso!")
                            
                        if colB.button("❌ Rejeitar", key=f"rej_{row['id']}"):
                            c = conn.cursor()
                            c.execute(f"UPDATE cr_contratos SET estado='Rejeitado' WHERE id={row['id']} AND empresa_id={emp_id}")
                            conn.commit()
                            registar_auditoria("REJEIÇÃO", f"Contrato #{row['id']} rejeitado.")
                            st.rerun()
            else:
                st.success("Sem pendências para aprovar.")
                
    # --- CLIENTES & KYC DIGITAL ---
    with tab_clientes:
        with st.container(border=True):
            st.subheader("Registo KYC de Clientes")
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("Nome Completo")
            n_bi = c2.text_input("Número de BI")
            c3, c4 = st.columns(2)
            n_telefone = c3.text_input("Telefone Principal")
            n_conta = c4.text_input("N.º de Conta / M-Pesa (Destino)")
            c5, c6 = st.columns(2)
            n_morada = c5.text_input("Morada")
            n_trabalho = c6.text_input("Local de Trabalho (Opcional)")
            n_nuit = st.text_input("NUIT (Opcional)")
            
            foto_bi = st.file_uploader("Carregar Cópia do BI", type=["png", "jpg", "jpeg"])
            foto_b64_str = base64.b64encode(foto_bi.read()).decode() if foto_bi else ""
            
            if st.button("Guardar Cliente"):
                if n_nome and n_bi and n_conta:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO cr_clientes (empresa_id, nome, bi, nuit, telefone, morada, local_trabalho, num_conta, bi_foto_b64) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                                  (emp_id, n_nome, n_bi, n_nuit, n_telefone, n_morada, n_trabalho, n_conta, foto_b64_str))
                        conn.commit()
                        registar_auditoria("NOVO CLIENTE", f"Cliente {n_nome} registado.")
                        st.success("Cliente guardado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        conn.rollback(); st.error(f"Erro: {e}")
                else:
                    st.warning("Preencha Nome, BI e Conta.")
                        
        st.markdown("<br><h4>📋 Base de Clientes</h4>", unsafe_allow_html=True)
        df_cli_all = pd.read_sql_query(f'SELECT id as "ID", nome as "Nome", bi as "BI", telefone as "Telefone", num_conta as "Conta / M-Pesa" FROM cr_clientes WHERE empresa_id={emp_id} ORDER BY id DESC', conn)
        st.dataframe(df_cli_all, use_container_width=True, hide_index=True)

    # --- SIMULADOR & PEDIDOS ---
    with tab_contratos:
        df_cli = pd.read_sql_query(f"SELECT id, nome, bi, num_conta FROM cr_clientes WHERE empresa_id={emp_id}", conn)
        if not df_cli.empty:
            with st.container(border=True):
                df_cli['nome_completo'] = df_cli['nome'] + " (Conta: " + df_cli['num_conta'].fillna('N/D') + ")"
                cliente_sel = st.selectbox("Selecione o Cliente:", df_cli['nome_completo'])
                id_cliente = df_cli[df_cli['nome_completo'] == cliente_sel]['id'].values[0]
                
                col1, col2 = st.columns(2)
                capital = col1.number_input("Capital Solicitado (MT)", min_value=0.0, step=1000.0)
                prazo = col2.number_input("Prazo (Ciclos/Meses)", min_value=1, value=1)
                
                col3, col4 = st.columns(2)
                tipo_juro = col3.selectbox("Modelo de Juro", ["Mensal", "Semanal", "Taxa Fixa Global"])
                taxa = col4.number_input("Taxa de Juro (%)", min_value=0.0, value=30.0)
                
                col5, col6 = st.columns(2)
                tipo_pagamento = col5.selectbox("Forma de Liquidação", ["Prestações Regulares", "Liquidação Total no Fim"])
                permite_parcial = col6.checkbox("Aceitar Pagamentos Parciais?", value=True)
                
                score_risco = "Standard (Prata)"
                if capital > 50000: score_risco = "Alto Risco"
                elif capital <= 15000: score_risco = "Baixo Risco (VIP)"
                
                juros = capital * (taxa / 100) if tipo_juro == "Taxa Fixa Global" else capital * (taxa / 100) * prazo
                total = capital + juros
                comissao_calculada = capital * 0.025
                
                st.info(f"📊 **Scoring:** `{score_risco}` | Capital: **{capital:,.2f} MT** | Total a Devolver: **{total:,.2f} MT**\n\n💵 **Comissão Promotor (2.5%):** **{comissao_calculada:,.2f} MT**")
                
                texto_botao = "🚀 Submeter para Aprovação" if papel == 'Promotor' else "✅ Aprovar Crédito Imediatamente"
                estado_reg = 'Pendente' if papel == 'Promotor' else 'Ativo'
                
                if st.button(texto_botao):
                    c = conn.cursor()
                    c.execute("""INSERT INTO cr_contratos 
                              (empresa_id, cliente_id, promotor_id, capital, tipo_juro, taxa_juro, prazo, tipo_pagamento, permite_parcial, valor_total_esperado, comissao_promotor, estado, score_risco) 
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id""", 
                              (emp_id, int(id_cliente), int(user_id), capital, tipo_juro, taxa, prazo, tipo_pagamento, permite_parcial, total, comissao_calculada, estado_reg, score_risco))
                    
                    if papel == 'Gestor':
                        novo_id_cont = c.fetchone()[0]
                        prazo_i = int(prazo)
                        cp = capital / prazo_i
                        jp = juros / prazo_i
                        tp = cp + jp
                        for p in range(1, prazo_i + 1):
                            data_venc = (datetime.now() + timedelta(days=30 * p)).strftime('%Y-%m-%d')
                            c.execute("""INSERT INTO cr_prestacoes (empresa_id, contrato_id, numero_prestacao, valor_capital, valor_juro, valor_total, data_vencimento, estado) 
                                      VALUES (%s, %s, %s, %s, %s, %s, %s, 'Pendente')""", 
                                      (emp_id, int(novo_id_cont), p, cp, jp, tp, data_venc))

                    conn.commit()
                    registar_auditoria("PEDIDO DE CRÉDITO", f"Crédito de {capital} MT submetido.")
                    st.success("Submetido com sucesso!")
        else:
            st.warning("Registe clientes primeiro.")

    # --- ABA DE COMISSÕES PARA O PROMOTOR ---
    if papel == 'Promotor':
        with tab_comissoes_promo:
            st.subheader("💵 As Minhas Comissões")
            c = conn.cursor()
            c.execute(f"SELECT SUM(comissao_promotor) FROM cr_contratos WHERE empresa_id={emp_id} AND promotor_id={user_id} AND estado IN ('Ativo', 'Liquidado')")
            res_com_ganha = c.fetchone()[0]
            com_ganha = res_com_ganha if res_com_ganha else 0.0
            
            c.execute(f"SELECT SUM(comissao_promotor) FROM cr_contratos WHERE empresa_id={emp_id} AND promotor_id={user_id} AND estado='Pendente'")
            res_com_pend = c.fetchone()[0]
            com_pendente = res_com_pend if res_com_pend else 0.0
            
            colA, colB = st.columns(2)
            colA.metric("Comissões Ganhas", f"{com_ganha:,.2f} MT")
            colB.metric("Comissões Pendentes", f"{com_pendente:,.2f} MT")
            
            df_com_promo = pd.read_sql_query(f'''
                SELECT c.id as "ID", cl.nome as "Cliente", c.capital as "Capital (MT)", 
                       c.comissao_promotor as "Comissão (MT)", c.estado as "Estado", c.data_contrato as "Data"
                FROM cr_contratos c JOIN cr_clientes cl ON c.cliente_id = cl.id 
                WHERE c.empresa_id = {emp_id} AND c.promotor_id = {user_id} ORDER BY c.id DESC
            ''', conn)
            st.dataframe(df_com_promo, use_container_width=True, hide_index=True)

    # --- PENHORES, TESOURARIA, INADIMPLÊNCIA, RELATÓRIOS EXCEL ---
    if papel == 'Gestor':
        df_ativos = pd.read_sql_query(f"SELECT c.id, cl.nome, cl.telefone, cl.num_conta, c.valor_total_esperado FROM cr_contratos c JOIN cr_clientes cl ON c.cliente_id=cl.id WHERE c.empresa_id={emp_id} AND c.estado='Ativo'", conn)
        
        with tab_garantias:
            if not df_ativos.empty:
                st.subheader("Cofre de Penhores")
                with st.container(border=True):
                    df_ativos['exibicao'] = "Contrato #" + df_ativos['id'].astype(str) + " - " + df_ativos['nome']
                    contrato_sel = st.selectbox("Contrato:", df_ativos['exibicao'])
                    id_cont = df_ativos[df_ativos['exibicao'] == contrato_sel]['id'].values[0]
                    
                    desc = st.text_input("Ativo Penhorado")
                    valor_bem = st.number_input("Avaliação (MT)", min_value=0.0, step=1000.0)
                    if st.button("🔒 Guardar Penhor"):
                        c = conn.cursor()
                        c.execute("INSERT INTO cr_garantias (empresa_id, contrato_id, descricao, valor_estimado) VALUES (%s, %s, %s, %s)", (emp_id, int(id_cont), desc, valor_bem))
                        conn.commit()
                        registar_auditoria("PENHOR", f"Penhor registado para contrato #{id_cont}")
                        st.success("Penhor guardado!")
            else:
                st.info("Nenhum contrato ativo.")

        # --- TESOURARIA & PRESTAÇÕES ---
        with tab_pagamentos:
            if not df_ativos.empty:
                st.subheader("Balcão de Tesouraria (Cobrança por Prestação)")
                with st.container(border=True):
                    pag_contrato_sel = st.selectbox("Selecione o Contrato Ativo:", df_ativos['exibicao'], key="pag_prest")
                    id_pag_cont = df_ativos[df_ativos['exibicao'] == pag_contrato_sel]['id'].values[0]
                    nome_cliente_pag = df_ativos[df_ativos['exibicao'] == pag_contrato_sel]['nome'].values[0]
                    tel_cliente = df_ativos[df_ativos['exibicao'] == pag_contrato_sel]['telefone']
                    tel_cliente = str(tel_cliente.values[0]) if not pd.isna(tel_cliente.values[0]) else ""
                    
                    df_prest = pd.read_sql_query(f"SELECT id, numero_prestacao, valor_total, data_vencimento, estado FROM cr_prestacoes WHERE empresa_id={emp_id} AND contrato_id={int(id_pag_cont)} AND estado='Pendente' ORDER BY numero_prestacao ASC", conn)
                    
                    if not df_prest.empty:
                        st.markdown("##### Prestações Pendentes para Baixa:")
                        st.dataframe(df_prest[['numero_prestacao', 'valor_total', 'data_vencimento']], use_container_width=True, hide_index=True)
                        
                        prest_sel = st.selectbox("Selecione a Prestação a Liquidar:", df_prest['numero_prestacao'])
                        prest_id = df_prest[df_prest['numero_prestacao'] == prest_sel]['id'].values[0]
                        valor_prest = df_prest[df_prest['numero_prestacao'] == prest_sel]['valor_total'].values[0]
                        
                        st.info(f"Valor exato da Prestação #{prest_sel}: **{valor_prest:,.2f} MT**")
                        
                        col_pag1, col_pag2 = st.columns(2)
                        if col_pag1.button("💰 Liquidar Prestação & Gerar Recibo"):
                            c = conn.cursor()
                            c.execute("UPDATE cr_prestacoes SET estado='Liquidada' WHERE id=%s", (int(prest_id),))
                            c.execute("INSERT INTO cr_pagamentos (empresa_id, contrato_id, prestacao_id, valor_pago) VALUES (%s, %s, %s, %s)", 
                                      (emp_id, int(id_pag_cont), int(prest_id), float(valor_prest)))
                            
                            c.execute(f"SELECT COUNT(*) FROM cr_prestacoes WHERE contrato_id={int(id_pag_cont)} AND estado='Pendente'")
                            restantes = c.fetchone()[0]
                            if restantes == 0:
                                c.execute(f"UPDATE cr_contratos SET estado='Liquidado' WHERE id={int(id_pag_cont)}")
                            
                            conn.commit()
                            registar_auditoria("PAGAMENTO PRESTAÇÃO", f"Prestação #{prest_sel} liquidada no contrato #{id_pag_cont}")
                            
                            pdf_recibo = gerar_recibo_pdf(emp_id, nome_cliente_pag, valor_prest, id_pag_cont)
                            with open(pdf_recibo, "rb") as f:
                                st.download_button("🖨️ Descarregar Recibo Oficial", f, pdf_recibo, "application/pdf")
                            st.success("Prestação liquidada e cofre atualizado com sucesso!")
                        
                        if tel_client_clean := "".join(filter(str.isdigit, tel_cliente)):
                            msg_wa = urllib.parse.quote(f"Olá, lembramos que tem uma prestação pendente no valor de {valor_prest:,.2f} MT na {nome_empresa}. Por favor regularize o pagamento.")
                            link_wa = f"https://wa.me/{tel_client_clean}?text={msg_wa}"
                            col_pag2.markdown(f"<br><a href='{link_wa}' target='_blank'><button style='background-color:#25d366; color:white; border:none; padding:10px 20px; border-radius:8px; font-weight:bold;'>💬 Enviar Lembrete WhatsApp</button></a>", unsafe_allow_html=True)
                    else:
                        st.success("🎉 Todas as prestações deste contrato encontram-se totalmente liquidadas!")
            else:
                st.info("Nenhum contrato ativo.")

        # --- INADIMPLÊNCIA & AGING REPORT (CORRIGIDO COM `::date`) ---
        with tab_inadimplencia:
            st.subheader("⚠️ Relatório de Inadimplência & Aging de Risco")
            with st.container(border=True):
                st.markdown("Monitorização de prestações vencidas e classificação de risco por dias de atraso.")
                
                df_aging = pd.read_sql_query(f'''
                    SELECT c.id as "Contrato", cl.nome as "Cliente", cl.telefone as "Telefone", 
                           p.numero_prestacao as "Prestação", p.valor_total as "Valor (MT)", p.data_vencimento as "Vencimento"
                    FROM cr_prestacoes p
                    JOIN cr_contratos c ON p.contrato_id = c.id
                    JOIN cr_clientes cl ON c.cliente_id = cl.id
                    WHERE p.empresa_id = {emp_id} AND p.estado = 'Pendente' AND p.data_vencimento::date < CURRENT_DATE
                    ORDER BY p.data_vencimento ASC
                ''', conn)
                
                if not df_aging.empty:
                    st.warning(f"Foram detetadas **{len(df_aging)}** prestações em incumprimento/atraso.")
                    st.dataframe(df_aging, use_container_width=True, hide_index=True)
                else:
                    st.success("Excelente! Não existem prestações vencidas em atraso na instituição.")

        with tab_comissoes:
            st.subheader("💵 Controlo de Comissões de Promotores")
            with st.container(border=True):
                df_comissoes_gestor = pd.read_sql_query(f'''
                    SELECT u.nome as "Promotor", COUNT(c.id) as "Total Créditos", 
                           SUM(c.capital) as "Capital Total (MT)", SUM(c.comissao_promotor) as "Comissão Total (MT)"
                    FROM cr_contratos c 
                    JOIN cr_usuarios u ON c.promotor_id = u.id 
                    WHERE c.empresa_id = {emp_id} AND c.estado != 'Rejeitado'
                    GROUP BY u.nome
                ''', conn)
                if not df_comissoes_gestor.empty:
                    st.dataframe(df_comissoes_gestor, use_container_width=True, hide_index=True)
                else:
                    st.info("Sem comissões registadas.")

        with tab_relatorios:
            st.subheader("📈 Centro de Relatórios Avançados & Exportação Excel")
            with st.container(border=True):
                df_rel_contratos = pd.read_sql_query(f'''
                    SELECT c.id as "ID Contrato", cl.nome as "Cliente", cl.bi as "BI", cl.num_conta as "Conta Destino", 
                           c.capital as "Capital", c.comissao_promotor as "Comissão Promotor", c.taxa_juro as "Taxa (%)", 
                           c.prazo as "Prazo", c.valor_total_esperado as "Total Esperado", c.estado as "Estado", c.score_risco as "Risco", c.data_contrato as "Data"
                    FROM cr_contratos c JOIN cr_clientes cl ON c.cliente_id = cl.id WHERE c.empresa_id = {emp_id}
                ''', conn)
                
                if not df_rel_contratos.empty:
                    excel_contratos = converter_df_para_excel(df_rel_contratos)
                    st.download_button(
                        label="📥 Descarregar Relatório Geral (Excel)",
                        data=excel_contratos,
                        file_name=f"Relatorio_Geral_{nome_empresa.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.info("Sem dados para exportar.")

        with tab_perfil:
            st.subheader("⚙️ Identidade Visual e Logótipo da Empresa")
            with st.container(border=True):
                novo_logo = st.file_uploader("Carregar Logótipo (PNG / JPG)", type=["png", "jpg", "jpeg"], key="upload_logo")
                if st.button("💾 Guardar Logótipo"):
                    if novo_logo:
                        logo_b64_str = base64.b64encode(novo_logo.read()).decode()
                        c = conn.cursor()
                        c.execute(f"UPDATE cr_empresas SET logo_b64=%s WHERE id={emp_id}", (logo_b64_str,))
                        conn.commit()
                        st.success("Logótipo guardado com sucesso!")
                        st.rerun()
                    else:
                        st.warning("Seleciona uma imagem.")

        with tab_audit:
            st.subheader("🛡️ Auditoria da Empresa")
            df_audit = pd.read_sql_query(f'SELECT id as "ID", utilizador as "Utilizador", acao as "Ação", detalhes as "Detalhes", data_acao as "Data" FROM cr_auditoria WHERE empresa_id={emp_id} ORDER BY id DESC LIMIT 50', conn)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)

    conn.close()

# ------------------------------------------------------------------
# 3. AUTENTICAÇÃO E SESSÃO ENTERPRISE
# ------------------------------------------------------------------
def main():
    st.set_page_config(page_title="GPA SaaS Enterprise", page_icon="🌐", layout="wide")
    aplicar_tema_bancario()
    init_db()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; color: #64ffda; font-weight: 800; font-size: 3rem;'>🌐 GPA ENTERPRISE</h1>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h4 style='text-align: center;'>Plataforma SaaS Multi-Tenant</h4><br>", unsafe_allow_html=True)
                usuario = st.text_input("ID de Utilizador")
                senha = st.text_input("Palavra-Passe", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔐 Autenticar", use_container_width=True):
                    user_data = login_user(usuario, senha)
                    if user_data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user_data[0]
                        st.session_state['empresa_id'] = user_data[1]
                        st.session_state['user_name'] = user_data[2]
                        st.session_state['user_role'] = user_data[3]
                        registar_auditoria("LOGIN", f"Utilizador {user_data[2]} entrou.")
                        st.rerun()
                    else:
                        st.error("Credenciais inválidas.")
    else:
        view_app()
        st.markdown("<br><br>", unsafe_allow_html=True)
        colA, colB, colC = st.columns([1, 2, 1])
        if colB.button("Terminar Sessão / Logout", use_container_width=True):
            registar_auditoria("LOGOUT", f"Utilizador {st.session_state.get('user_name')} saiu.")
            st.session_state.clear()
            st.rerun()

if __name__ == '__main__':
    main()
