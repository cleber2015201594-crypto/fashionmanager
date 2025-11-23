import streamlit as st
import pandas as pd

st.set_page_config(page_title="FashionManager", page_icon="👕")
st.title("👕 FashionManager Pro")
st.success("✅ Sistema carregado com sucesso!")

# Teste simples
df = pd.DataFrame({"Teste": [1, 2, 3]})
st.dataframe(df)
