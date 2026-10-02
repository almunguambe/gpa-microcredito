import streamlit as st
import psycopg2
import pandas as pd
import hashlib
from datetime import datetime
from fpdf import FPDF
import base64

# ------------------------------------------------------------------
# 0. ESTÉTICA DE BANCO DIGITAL (GLASSMORPHISM DE ELITE)
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
# 1. BASE DE DADOS, SEGURANÇA E MOTOR GLOBAL
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
        c.execute("INSERT INTO cr_auditoria (utilizador, acao, detalhes) VALUES (%s, %s, %s)", (user, acao, detalhes))
        conn.close()
    except:
        pass

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS cr_usuarios (id SERIAL PRIMARY KEY, nome TEXT, usuario TEXT UNIQUE, senha TEXT, papel TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cr_clientes (id SERIAL PRIMARY KEY, nome TEXT, bi TEXT UNIQUE, nuit TEXT, telefone TEXT, morada TEXT, local_trabalho TEXT, num_conta TEXT, bi_foto_b64 TEXT, data_registo TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cr_contratos (id SERIAL PRIMARY KEY, cliente_id INTEGER, capital REAL, tipo_juro TEXT, taxa_juro REAL, prazo INTEGER DEFAULT 1, tipo_pagamento TEXT, permite_parcial BOOLEAN, valor_total_esperado REAL, estado TEXT DEFAULT 'Pendente', score_risco TEXT DEFAULT 'Standard', data_contrato TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(cliente_id) REFERENCES cr_clientes(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS cr_garantias (id SERIAL PRIMARY KEY, contrato_id INTEGER, descricao TEXT, valor_estimado REAL, estado TEXT DEFAULT 'Sob Custódia', FOREIGN KEY(contrato_id) REFERENCES cr_contratos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS cr_pagamentos (id SERIAL PRIMARY KEY, contrato_id INTEGER, valor_pago REAL, data_pagamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP, tipo_recibo TEXT, FOREIGN KEY(contrato_id) REFERENCES cr_contratos(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS cr_auditoria (id SERIAL PRIMARY KEY, utilizador TEXT, acao TEXT, detalhes TEXT, data_acao TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Garantir colunas essenciais se a tabela já existir
    try: c.execute("ALTER TABLE cr_clientes ADD COLUMN bi_foto_b64 TEXT")
    except: pass
    try: c.execute("ALTER TABLE cr_clientes ADD COLUMN num_conta TEXT")
    except: pass
    try: c.execute("ALTER TABLE cr_contratos ADD COLUMN score_risco TEXT DEFAULT 'Standard'")
    except: pass

    c.execute("SELECT * FROM cr_usuarios WHERE usuario='gestor'")
    if not c.fetchone():
        c.execute("INSERT INTO cr_usuarios (nome, usuario, senha, papel) VALUES (%s, %s, %s, %s)", ('Administração GPA', 'gestor', hash_senha('admin123'), 'Gestor'))
    c.execute("SELECT * FROM cr_usuarios WHERE usuario='promotor'")
    if not c.fetchone():
        c.execute("INSERT INTO cr_usuarios (nome, usuario, senha, papel) VALUES (%s, %s, %s, %s)", ('Agente Promotor', 'promotor', hash_senha('promo123'), 'Promotor'))
    conn.close()

def login_user(usuario, senha):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, nome, papel FROM cr_usuarios WHERE usuario=%s AND senha=%s", (usuario, hash_senha(senha)))
    data = c.fetchone()
    conn.close()
    return data

def gerar_contrato_pdf(id_contrato, nome, bi, morada, conta, capital, prazo, pagamento, total, risco):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"CONTRATO DE MUTUO INTERNACIONAL N. {id_contrato} - GPA", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 10, f"Classificacao de Risco: {risco} | Conta Destino: {conta}", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 11)
    
    texto = f"""
Entre GPA - Sociedade Unipessoal, Lda, doravante designada por CREDORA.

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
    pdf.cell(90, 10, "A CREDORA (GPA Unipessoal)", ln=False, align='C')
    pdf.cell(90, 10, "O(A) DEVEDOR(A)", ln=True, align='C')
    
    file_name = f"Contrato_Global_{id_contrato}.pdf"
    pdf.output(file_name)
    return file_name

def gerar_recibo_pdf(nome, valor, id_contrato):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RECIBO OFICIAL DE QUITACAO - GPA", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.cell(0, 10, f"Cliente: {nome}", ln=True)
    pdf.cell(0, 10, f"Valor Liquidado: {valor:,.2f} MT", ln=True)
    pdf.cell(0, 10, f"Referente ao Contrato N. {id_contrato}", ln=True)
    pdf.ln(20)
    pdf.cell(0, 10, "________________________________________________", ln=True, align='C')
    pdf.cell(0, 10, "Certificado Digital GPA FinTech", ln=True, align='C')
    file_name = f"Recibo_Oficial_{id_contrato}.pdf"
    pdf.output(file_name)
    return file_name

# ------------------------------------------------------------------
# 2. INTERFACE PRINCIPAL MULTI-NÍVEL
# ------------------------------------------------------------------
def view_app():
    conn = get_conn()
    papel = st.session_state['user_role']
    
    st.markdown(f"<h2 style='text-align: center; color: #64ffda;'>🌐 GPA Microcrédito Pro - Core Global</h2>", unsafe_allow_html=True)
    st.markdown("---")
    
    if papel == 'Gestor':
        tabs = st.tabs(["📊 Dashboard Executivo", "⚖️️ Aprovações", "👥 Clientes (KYC)", "📝 Simulador SAC", "🔒 Penhores", "💰 Tesouraria", "🛡️ Auditoria"])
        tab_dashboard, tab_aprovacoes, tab_clientes, tab_contratos, tab_garantias, tab_pagamentos, tab_audit = tabs
    else:
        tabs = st.tabs(["👥 Clientes (KYC)", "📝 Simulação & Pedido"])
        tab_clientes, tab_contratos = tabs

    # --- DASHBOARD EXECUTIVO ---
    if papel == 'Gestor':
        with tab_dashboard:
            c = conn.cursor()
            c.execute("SELECT SUM(capital), SUM(valor_total_esperado - capital) FROM cr_contratos WHERE estado='Ativo'")
            totais = c.fetchone()
            cap_ativo = totais[0] if totais[0] else 0.0
            jur_ativo = totais[1] if totais[1] else 0.0
            
            c.execute("SELECT SUM(valor_pago) FROM cr_pagamentos")
            recebido = c.fetchone()[0]
            recebido_total = recebido if recebido else 0.0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Capital Global na Rua", f"{cap_ativo:,.2f} MT")
            col2.metric("Lucro Bruto Projetado", f"{jur_ativo:,.2f} MT")
            col3.metric("Entradas de Tesouraria", f"{recebido_total:,.2f} MT")

        # --- APROVAÇÕES ---
        with tab_aprovacoes:
            query_pendentes = """
                SELECT c.id, cl.nome, cl.bi, cl.morada, cl.num_conta, c.capital, c.valor_total_esperado, c.prazo, c.tipo_pagamento, c.score_risco
                FROM cr_contratos c JOIN cr_clientes cl ON c.cliente_id = cl.id WHERE c.estado = 'Pendente'
            """
            df_pendentes = pd.read_sql_query(query_pendentes, conn)
            
            if not df_pendentes.empty:
                for index, row in df_pendentes.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**Cliente:** {row['nome']} | **Risco:** `{row['score_risco']}` | **Capital:** {row['capital']:,.2f} MT")
                        st.markdown(f"📱 **Conta / M-Pesa Destino:** `{row['num_conta'] if row['num_conta'] else 'Não registada'}`")
                        st.markdown(f"**Total a Devolver:** {row['valor_total_esperado']:,.2f} MT | **Prazo:** {row['prazo']} ({row['tipo_pagamento']})")
                        
                        colA, colB, colC = st.columns([1,1,2])
                        if colA.button("✅ Aprovar & Emitir", key=f"apr_{row['id']}"):
                            c = conn.cursor()
                            c.execute("UPDATE cr_contratos SET estado='Ativo' WHERE id=%s", (row['id'],))
                            conn.commit()
                            registar_auditoria("APROVAÇÃO DE CRÉDITO", f"Contrato #{row['id']} aprovado para {row['nome']} (Destino: {row['num_conta']})")
                            
                            pdf_path = gerar_contrato_pdf(row['id'], row['nome'], row['bi'], row['morada'], str(row['num_conta']), row['capital'], row['prazo'], row['tipo_pagamento'], row['valor_total_esperado'], row['score_risco'])
                            with open(pdf_path, "rb") as f:
                                st.download_button("📄 Descarregar Contrato PDF", f, pdf_path, "application/pdf")
                            st.success(f"Crédito ativado! Enviar fundos para: {row['num_conta']}")
                            
                        if colB.button("❌ Rejeitar", key=f"rej_{row['id']}"):
                            c = conn.cursor()
                            c.execute("UPDATE cr_contratos SET estado='Rejeitado' WHERE id=%s", (row['id'],))
                            conn.commit()
                            registar_auditoria("REJEIÇÃO DE CRÉDITO", f"Contrato #{row['id']} rejeitado.")
                            st.rerun()
            else:
                st.success("Sem pendências no sistema.")
                
    # --- CLIENTES & KYC DIGITAL ---
    with tab_clientes:
        with st.container(border=True):
            st.subheader("Registo KYC (Com Conta de Desembolso e Cofre)")
            c1, c2 = st.columns(2)
            n_nome = c1.text_input("Nome Completo")
            n_bi = c2.text_input("Número de BI")
            c3, c4 = st.columns(2)
            n_telefone = c3.text_input("Telefone Principal")
            n_conta = c4.text_input("N.º de Conta / M-Pesa / e-Mola (Destino dos Fundos)")
            c5, c6 = st.columns(2)
            n_morada = c5.text_input("Morada")
            n_trabalho = c6.text_input("Local de Trabalho (Opcional)")
            n_nuit = st.text_input("NUIT (Opcional)")
            
            foto_bi = st.file_uploader("Carregar Cópia do BI (Imagem)", type=["png", "jpg", "jpeg"])
            foto_b64_str = ""
            if foto_bi:
                foto_b64_str = base64.b64encode(foto_bi.read()).decode()
            
            if st.button("Guardar Cliente no Cofre"):
                if n_nome and n_bi and n_conta:
                    try:
                        c = conn.cursor()
                        c.execute("INSERT INTO cr_clientes (nome, bi, nuit, telefone, morada, local_trabalho, num_conta, bi_foto_b64) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                                  (n_nome, n_bi, n_nuit, n_telefone, n_morada, n_trabalho, n_conta, foto_b64_str))
                        conn.commit()
                        registar_auditoria("NOVO CLIENTE", f"Cliente {n_nome} registado com conta {n_conta}.")
                        st.success("Cliente registado com sucesso no cofre!")
                        st.rerun()
                    except:
                        conn.rollback(); st.error("Erro: BI já registado.")
                else:
                    st.warning("O Nome, o BI e o Número de Conta/M-Pesa são obrigatórios para o desembolso.")
                        
        st.markdown("<br><h4>📋 Base de Dados de Clientes & Contas</h4>", unsafe_allow_html=True)
        df_cli_all = pd.read_sql_query('SELECT id as "ID", nome as "Nome", bi as "BI", telefone as "Telefone", num_conta as "Conta / M-Pesa" FROM cr_clientes ORDER BY id DESC', conn)
        st.dataframe(df_cli_all, use_container_width=True, hide_index=True)

    # --- SIMULADOR & PEDIDOS ---
    with tab_contratos:
        df_cli = pd.read_sql_query("SELECT id, nome, bi, num_conta FROM cr_clientes", conn)
        if not df_cli.empty:
            with st.container(border=True):
                df_cli['nome_completo'] = df_cli['nome'] + " (Conta: " + df_cli['num_conta'].fillna('N/D') + ")"
                cliente_sel = st.selectbox("Cliente:", df_cli['nome_completo'])
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
                if capital > 50000:
                    score_risco = "Alto Risco (Requer Análise Extrema)"
                elif capital <= 15000:
                    score_risco = "Baixo Risco (Perfil VIP/Ouro)"
                
                juros = capital * (taxa / 100) if tipo_juro == "Taxa Fixa Global" else capital * (taxa / 100) * prazo
                total = capital + juros
                
                st.info(f"📊 **Scoring:** `{score_risco}` | Capital: **{capital:,.2f} MT** | Total a Devolver: **{total:,.2f} MT**")
                
                texto_botao = "🚀 Submeter para Aprovação" if papel == 'Promotor' else "✅ Aprovar Crédito Imediatamente"
                estado_reg = 'Pendente' if papel == 'Promotor' else 'Ativo'
                
                if st.button(texto_botao):
                    c = conn.cursor()
                    c.execute("INSERT INTO cr_contratos (cliente_id, capital, tipo_juro, taxa_juro, prazo, tipo_pagamento, permite_parcial, valor_total_esperado, estado, score_risco) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                              (int(id_cliente), capital, tipo_juro, taxa, prazo, tipo_pagamento, permite_parcial, total, estado_reg, score_risco))
                    conn.commit()
                    registar_auditoria("NOVO PEDIDO", f"Crédito de {capital} MT submetido para o cliente ID {id_cliente}")
                    st.success("Operação registada com sucesso!")
        else:
            st.warning("Cadastre clientes primeiro.")

    # --- PENHORES, TESOURARIA E AUDITORIA (SÓ GESTOR) ---
    if papel == 'Gestor':
        df_ativos = pd.read_sql_query("SELECT c.id, cl.nome, cl.num_conta, c.valor_total_esperado FROM cr_contratos c JOIN cr_clientes cl ON c.cliente_id=cl.id WHERE c.estado='Ativo'", conn)
        
        with tab_garantias:
            if not df_ativos.empty:
                st.subheader("Gestão Avançada de Penhores")
                with st.container(border=True):
                    df_ativos['exibicao'] = "Contrato #" + df_ativos['id'].astype(str) + " - " + df_ativos['nome']
                    contrato_sel = st.selectbox("Contrato Associado:", df_ativos['exibicao'])
                    id_cont = df_ativos[df_ativos['exibicao'] == contrato_sel]['id'].values[0]
                    
                    desc = st.text_input("Ativo Penhorado (Ex: Viatura, Equipamento, Imóvel)")
                    valor_bem = st.number_input("Avaliação de Mercado (MT)", min_value=0.0, step=1000.0)
                    if st.button("🔒 Bloquear Garantia no Cofre"):
                        c = conn.cursor()
                        c.execute("INSERT INTO cr_garantias (contrato_id, descricao, valor_estimado) VALUES (%s, %s, %s)", (int(id_cont), desc, valor_bem))
                        conn.commit()
                        registar_auditoria("PENHOR REGISTADO", f"Garantia registada para o contrato #{id_cont}")
                        st.success("Garantia vinculada com sucesso!")
            else:
                st.info("Nenhum contrato ativo disponível para penhor.")

        with tab_pagamentos:
            if not df_ativos.empty:
                st.subheader("Balcão de Tesouraria e Amortizações")
                with st.container(border=True):
                    pag_contrato_sel = st.selectbox("Selecione o Contrato Ativo:", df_ativos['exibicao'], key="pag_global")
                    id_pag_cont = df_ativos[df_ativos['exibicao'] == pag_contrato_sel]['id'].values[0]
                    nome_cliente_pag = df_ativos[df_ativos['exibicao'] == pag_contrato_sel]['nome'].values[0]
                    valor_total_pag = df_ativos[df_ativos['exibicao'] == pag_contrato_sel]['valor_total_esperado'].values[0]
                    
                    c = conn.cursor()
                    c.execute("SELECT SUM(valor_pago) FROM cr_pagamentos WHERE contrato_id=%s", (int(id_pag_cont),))
                    ja_pago = c.fetchone()[0]
                    ja_pago = ja_pago if ja_pago else 0.0
                    saldo_devedor = valor_total_pag - ja_pago
                    
                    st.warning(f"**Saldo Devedor Atual:** {saldo_devedor:,.2f} MT")
                    
                    if saldo_devedor > 0:
                        valor_recebido = st.number_input("Valor Entregue pelo Cliente (MT)", min_value=0.0, max_value=float(saldo_devedor), step=100.0)
                        if st.button("💰 Baixa de Tesouraria & Gerar Recibo"):
                            c.execute("INSERT INTO cr_pagamentos (contrato_id, valor_pago) VALUES (%s, %s)", (int(id_pag_cont), valor_recebido))
                            if (saldo_devedor - valor_recebido) <= 0:
                                c.execute("UPDATE cr_contratos SET estado='Liquidado' WHERE id=%s", (int(id_pag_cont),))
                            conn.commit()
                            registar_auditoria("PAGAMENTO", f"Recebimento de {valor_recebido} MT no contrato #{id_pag_cont}")
                            
                            pdf_recibo = gerar_recibo_pdf(nome_cliente_pag, valor_recebido, id_pag_cont)
                            with open(pdf_recibo, "rb") as f:
                                st.download_button("🖨️ Descarregar Recibo Oficial", f, pdf_recibo, "application/pdf")
                            st.success("Transação registada e cofre atualizado!")
                    else:
                        st.success("Este contrato encontra-se totalmente liquidado.")
            else:
                st.info("Nenhum contrato ativo para cobranças.")

        with tab_audit:
            st.subheader("🛡️ Registo de Auditoria Global (Audit Trail)")
            df_audit = pd.read_sql_query('SELECT id as "ID", utilizador as "Utilizador", acao as "Ação", detalhes as "Detalhes", data_acao as "Data e Hora" FROM cr_auditoria ORDER BY id DESC LIMIT 50', conn)
            st.dataframe(df_audit, use_container_width=True, hide_index=True)

    conn.close()

# ------------------------------------------------------------------
# 3. AUTENTICAÇÃO E SESSÃO
# ------------------------------------------------------------------
def main():
    st.set_page_config(page_title="GPA Microcrédito Core", page_icon="🌐", layout="wide")
    aplicar_tema_bancario()
    init_db()

    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h1 style='text-align: center; color: #64ffda; font-weight: 800; font-size: 3rem;'>GPA GLOBAL CORE</h1>", unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("<h4 style='text-align: center;'>Acesso Corporativo Seguro</h4><br>", unsafe_allow_html=True)
                usuario = st.text_input("ID de Utilizador")
                senha = st.text_input("Palavra-Passe", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔐 Autenticar", use_container_width=True):
                    user_data = login_user(usuario, senha)
                    if user_data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user_data[0]
                        st.session_state['user_name'] = user_data[1]
                        st.session_state['user_role'] = user_data[2]
                        registar_auditoria("LOGIN", f"Utilizador {user_data[1]} entrou no sistema.")
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