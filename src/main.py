import streamlit as st


st.title("Hello World!")
st.write("If you see this, your Streamlit works!")
if st.button("Tap me"):
     st.success("All works!")