import streamlit as st
import pandas as pd

st.title("Client Portal")
st.write(
    "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
)

dict_d = [{'a':100,'b':18,'c':'March'}, {'a':150,'b':28,'c':'April'},{'a':200,'b':10,'c':'May'}]
df = pd.DataFrame.from_dict(dict_d)
st.bar_chart(df,x="c",y=["a", "b"])