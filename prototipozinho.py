import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import plotly.express as px

# Configurações Supabase (seu projeto)
SUPABASE_URL = 'https://adzsxryzybpuoowpeyjb.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFkenN4cnl6eWJwdW9vd3BleWpiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MTc4OTcsImV4cCI6MjA3MTk5Mzg5N30.-vKcQWGX4zdRToU9EAtcuhS-dtx7xS2Q8OyIo5OMf8w'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    st.title('Login no CliniTrials')
    email = st.text_input('E-mail')
    password = st.text_input('Senha', type='password')
    login_button = st.button('Entrar')
    if login_button:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            st.session_state.logged_in = True
            st.session_state.user = response.user
            st.experimental_rerun()  # reinicia para atualizar estado
        else:
            st.error('Usuário ou senha inválidos.')

def logout():
    supabase.auth.sign_out()
    st.session_state.logged_in = False
    st.session_state.user = None
    st.experimental_rerun()


def get_clinical_trials():
    response = supabase.from_('estudos_clinicos').select('*').order('created_at', desc=True).execute()
    if response.data is None:
        st.error('Erro ao buscar estudos clínicos.')
        return []
    return response.data

def add_clinical_trial(data):
    user_id = st.session_state.user.id
    data['created_by'] = user_id
    response = supabase.from_('estudos_clinicos').insert(data).execute()
    return response.data

def count_potential_cases(cid_list):
    total_cases = 0
    breakdown = {}
    for cid in cid_list:
        cid = cid.strip()
        if not cid:
            continue
        response = supabase.from_('anotacoes_clinicas').select('id', count='exact').ilike('summary', f'%{cid}%').execute()
        count = getattr(response, 'count', None)
        if count is None and response.data is not None:
            count = len(response.data)
        if count is None:
            count = 0
        breakdown[cid] = count
        total_cases += count
    return total_cases, breakdown

def get_annotation_stats():
    response = supabase.from_('anotacoes_clinicas').select('*').execute()
    if response.data is None:
        return {}
    df = pd.DataFrame(response.data)
    if 'patient_confirmed' in df:
        df['patient_confirmed'] = df['patient_confirmed'].astype(str).str.lower()
        df['patient_confirmed'] = df['patient_confirmed'].map({'true': True, 'false': False})
        df['patient_confirmed'] = df['patient_confirmed'].fillna(False)
    stats = {
        'total': len(df),
        'confirmadas': df['patient_confirmed'].sum() if 'patient_confirmed' in df else 0,
        'tipos': df['type'].value_counts().to_dict() if 'type' in df else {},
    }
    return stats

def main():
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        login()
        return

    st.sidebar.title(f"Bem-vindo, {st.session_state.user.email}")
    if st.sidebar.button('Sair'):
        logout()
        return

    menu = st.sidebar.radio('Menu', ['Dashboard', 'Novo Estudo', 'Estudos Cadastrados'])

    if menu == 'Dashboard':
        st.title("Dashboard CliniTrials")

        studies = get_clinical_trials()
        total_studies = len(studies)
        active_studies = len([s for s in studies if s.get('ativo')])
        annotation_stats = get_annotation_stats()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric('Total de Estudos Clínicos', total_studies)
        with col2:
            st.metric('Estudos Clínicos Ativos', active_studies)
        with col3:
            st.metric('Total de Anotações', annotation_stats.get('total', 0))

        st.subheader("Resumo das Anotações Clínicas")
        st.write(f"Anotações confirmadas por pacientes: **{annotation_stats.get('confirmadas', 0)}**")

        tipos = annotation_stats.get('tipos', {})
        if tipos:
            df_tipos = pd.DataFrame(list(tipos.items()), columns=['Tipo', 'Quantidade'])
            fig = px.pie(df_tipos, values='Quantidade', names='Tipo',
                         color_discrete_sequence=px.colors.qualitative.Set3,
                         title='Distribuição por Tipo de Anotação')
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Nenhum dado de tipos disponível.")

        total_cases_all = 0
        for study in studies:
            cids = study.get("CID-10") or ""
            cid_list = [cid.strip() for cid in cids.split(",") if cid.strip()]
            cases, _ = count_potential_cases(cid_list)
            total_cases_all += cases
        media_cases = total_cases_all / total_studies if total_studies > 0 else 0
        st.metric("Média de casos potenciais por estudo", f"{media_cases:.1f}")

        st.subheader("Últimos 5 Estudos com casos potenciais")
        for study in studies[:5]:
            cid_str = study.get("CID-10") or ""
            cid_list = [cid.strip() for cid in cid_str.split(",") if cid.strip()]
            cases, breakdown = count_potential_cases(cid_list)
            with st.expander(f"{study.get('titulo')} - {cases} casos potenciais"):
                st.write(f"Descrição: {study.get('descricao', 'Sem descrição')}")
                st.write(f"CID-10: {cid_str}")
                st.write(f"Ativo: {'Sim' if study.get('ativo') else 'Não'}")
                st.write("Critérios de Inclusão:")
                st.write('\n'.join(study.get('criterios_inclusao', [])))
                st.write("Critérios de Exclusão:")
                st.write('\n'.join(study.get('criterios_exclusao', [])))
                st.write(f"Link para inscrição: {study.get('link_para_inscricao', 'N/A')}")
                st.write("Casos potenciais por CID-10:")
                for cid, count in breakdown.items():
                    st.write(f"- {cid}: {count}")

    elif menu == 'Novo Estudo':
        st.title('Cadastrar Novo Estudo Clínico')
        with st.form('new_study'):
            titulo = st.text_input('Título do Estudo')
            descricao = st.text_area('Descrição do Estudo')
            cid_list_text = st.text_area('Lista de CID-10 (separe por vírgula)').strip()
            criterios_inclusao = st.text_area('Critérios de Inclusão (um por linha)').split('\n')
            criterios_exclusao = st.text_area('Critérios de Exclusão (um por linha)').split('\n')
            ativo = st.checkbox('Estudo ativo?', value=True)
            link_para_inscricao = st.text_input('Link para inscrição (URL)')
            submitted = st.form_submit_button('Salvar Estudo')

            if submitted:
                cid_list = [cid.strip() for cid in cid_list_text.split(',') if cid.strip()]
                study_data = {
                    "titulo": titulo,
                    "descricao": descricao,
                    "CID-10": ','.join(cid_list),
                    "criterios_inclusao": [ci.strip() for ci in criterios_inclusao if ci.strip()],
                    "criterios_exclusao": [ce.strip() for ce in criterios_exclusao if ce.strip()],
                    "ativo": ativo,
                    "created_at": datetime.utcnow().isoformat(),
                    "link_para_inscricao": link_para_inscricao
                }
                created = add_clinical_trial(study_data)
                if created:
                    st.success('Estudo clínico criado com sucesso!')
                    total_cases, breakdown = count_potential_cases(cid_list)
                    st.info(f"Boa notícia! Já identificamos {total_cases} casos no nosso banco de dados que são potencialmente compatíveis com o seu estudo.")

    elif menu == 'Estudos Cadastrados':
        st.title('Estudos Cadastrados')
        studies = get_clinical_trials()
        if studies:
            for study in studies:
                with st.expander(study['titulo']):
                    st.write(f"Descrição: {study.get('descricao', 'Sem descrição')}")
                    st.write(f"CID-10: {study.get('CID-10', 'N/A')}")
                    st.write(f"Ativo: {'Sim' if study.get('ativo', False) else 'Não'}")
                    st.write("Critérios de Inclusão:")
                    st.write('\n'.join(study.get('criterios_inclusao', [])))
                    st.write("Critérios de Exclusão:")
                    st.write('\n'.join(study.get('criterios_exclusao', [])))
                    st.write(f"Link para inscrição: {study.get('link_para_inscricao', 'N/A')}")

if __name__ == '__main__':
    main()

