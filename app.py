import streamlit as st
import requests

st.title("📁 TailorTalk - Google Drive AI Agent")

question = st.text_input("Ask something about your files")

if st.button("Search"):

    if question:

        res = requests.post(
            "http://127.0.0.1:8000/ask",
            json={"question": question}
        )

        data = res.json()

        st.subheader("Generated Query")
        st.code(data.get("generated_query", "No query"))

        st.subheader("Results")

        results = data.get("results")

        if isinstance(results, list):
            for r in results:
                st.markdown(f"""
**📄 {r['name']}**  
Type: `{r['type']}`  
🔗 [Open File]({r['link']})
""")
        else:
            st.write(results)