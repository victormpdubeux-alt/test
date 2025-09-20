import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime

# Configurações Supabase
SUPABASE_URL = 'https://adzsxryzybpuoowpeyjb.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFkenN4cnl6eWJwdW9vd3BleWpiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY0MTc4OTcsImV4cCI6MjA3MTk5Mzg5N30.-vKcQWGX4zdRToU9EAtcuhS-dtx7xS2Q8OyIo5OMf8w'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def login():
    st.session_state.logged_in = False
    st.title('Login')
    email = st.text_input('E-mail')
    password = st.text_input('Senha', type='password')
    login_button = st.button('Entrar')
    if login_button:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            st.session_state.logged_in = True
            st.session_state.user = response.user
            st.experimental_rerun()
        else:
            st.error('Usuário ou senha inválidos.')

def logout():
    supabase.auth.sign_out()
    st.session_state.logged_in = False
    st.session_state.user = None
    st.experimental_rerun()

def get_clinical_trials():
    response = supabase.from_('estudos_clinicos').select('*').order('created_at', desc=True).execute()
    data = response.data
    if data is None:
        st.error('Erro ao buscar estudos clínicos.')
        return []
    return data

def add_clinical_trial(data):
    user_id = st.session_state.user.id
    data['created_by'] = user_id
    response = supabase.from_('estudos_clinicos').insert(data).execute()
    return response.data

def count_potential_cases(cid_list):
    total_cases = 0
    for cid in cid_list:
        cid = cid.strip()
        if not cid:
            continue
        response = supabase.from_('anotacoes_clinicas').select('id', count='exact').ilike('summary', f'%{cid}%').execute()
        if response.data is not None:
            count = getattr(response, 'count', None)
            if count is None:
                count = len(response.data)
            total_cases += count
    return total_cases

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
        st.header('Dashboard de Ensaios Clínicos')
        trials = get_clinical_trials()
        st.write(f'Total de estudos: {len(trials)}')
        if trials:
            df = pd.DataFrame(trials)
            st.dataframe(df)

    elif menu == 'Novo Estudo':
        st.header('Cadastrar Novo Estudo Clínico')
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
                    total_cases = count_potential_cases(cid_list)
                    st.info(f"Boa notícia! Já identificamos {total_cases} casos no nosso banco de dados que são potencialmente compatíveis com o seu estudo.")

    elif menu == 'Estudos Cadastrados':
        st.header('Estudos Cadastrados')
        trials = get_clinical_trials()
        if trials:
            for trial in trials:
                with st.expander(f"{trial['titulo']}"):
                    st.write(f"Descrição: {trial.get('descricao', 'Sem descrição')}")
                    st.write(f"CID-10: {trial.get('CID-10', 'N/A')}")
                    st.write(f"Ativo: {'Sim' if trial.get('ativo', False) else 'Não'}")
                    st.write("Critérios de Inclusão:")
                    st.write('\n'.join(trial.get('criterios_inclusao', [])))
                    st.write("Critérios de Exclusão:")
                    st.write('\n'.join(trial.get('criterios_exclusao', [])))
                    st.write(f"Link para inscrição: {trial.get('link_para_inscricao', 'N/A')}")

if __name__ == '__main__':
    main()
