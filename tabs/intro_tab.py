import streamlit as st

def intro_detail():
    st.header("Introduction")
    st.write("This is a web application to help you design your plate layout and sample order for mass spectrometry.")
    st.write("The application will help you design the plate layout, injection order, and SDRF file.")
    st.write("Please fill in the necessary information in the sidebar to get started.")
    st.subheader("Related links")
    st.markdown("1. [Xcalibur](https://www.thermofisher.com/order/catalog/product/OPTON-30900)")
    st.markdown("2. [EVOSEP One](https://www.evosep.com/wp-content/uploads/2024/03/Evosep-One-User-Guide-v20-1.pdf)")
    st.markdown("3. [ProteomEdge SRM kit](https://proteomedge.com/?utm_source=google&utm_medium=cpc&utm_campaign=Brand&utm_id=21365304429&gad_source=1&gad_campaignid=21365304429&gbraid=0AAAAA9y8PtBsyDttZ6yULoNWs-UmrJ6ag&gclid=CjwKCAjw3tzHBhBREiwAlMJoUghlTAMhy4TIMGH_yulPSZRXZtj4zmd0FYp-ACp-5Xp6mMaQxh_AWBoCefUQAvD_BwE)")
    st.markdown("4. [SDRF Proteomics](https://sdrf.quantms.org/)")
    st.subheader("Contributions")
    col1, col2 = st.columns(2)
    with col1:
        st.link_button("🌐  Web App", "https://ms-experiment.streamlit.app/", use_container_width=True)
    with col2:
        st.link_button("🐙  GitHub", "https://github.com/thanadol-git/FE_MS_lab_web", use_container_width=True)