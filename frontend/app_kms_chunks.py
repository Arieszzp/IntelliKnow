"""
Additional functions for KMS chunk management and semantic search
These functions integrate with the existing app.py
"""
import streamlit as st
import requests
import pandas as pd
import time


def show_semantic_search():
    """Semantic search within documents"""
    st.subheader("🔍 Semantic Search")

    # Search query input
    with st.form("semantic_search_form"):
        col1, col2 = st.columns(2)

        with col1:
            search_query = st.text_input("Search query", help="Enter question to search within document chunks")

        with col2:
            # Document selection for filtering
            try:
                import requests
                response = requests.get("http://localhost:8000/api/documents/")
                if response.status_code == 200:
                    documents = response.json()
                    doc_options = {"All Documents": 0}
                    for doc in documents:
                        doc_options[doc['name']] = doc['id']
                    doc_select = st.selectbox("Search within Document", ["All Documents"] + list(doc_options.keys()))
                else:
                    doc_select = "All Documents"
                    doc_options = {}
            except:
                doc_select = "All Documents"
                doc_options = {}

            top_k = st.slider("Top K Results", min_value=5, max_value=20, value=5,
                               help="Number of chunks to return")

            search_button = st.form_submit_button("🔎 Search")

    if search_button and search_query:
        try:
            document_id = doc_options.get(doc_select, None) if doc_select != "All Documents" else None

            # Build API URL
            api_url = f"http://localhost:8000/api/chunks/document/{document_id}/search" if document_id else f"http://localhost:8000/api/chunks/search"
            params = {"query": search_query, "top_k": top_k}

            # Call API
            with st.spinner("Searching..."):
                response = requests.get(api_url, params=params)

            if response.status_code == 200:
                results = response.json()

                if results:
                    st.success(f"Found {len(results)} relevant chunks")

                    # Display results
                    for idx, result in enumerate(results, 1):
                        with st.expander(f"Result {idx}: Relevance {result['score']:.2f}", expanded=False):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown(f"**Chunk Index:** {result.get('chunk_index', 'N/A')}")
                                st.markdown(f"**Page:** {result.get('page_number', 'N/A')}")
                                st.markdown(f"**Type:** {result.get('type', 'text').title()}")

                            with col2:
                                st.markdown(f"**Score:** {result['score']:.4f}")
                                st.code(result['text'][:500] + ("..." if len(result['text']) > 500 else ""),
                                       language="text")

                            st.markdown("---")
                            st.markdown(f"**Full Content:**")
                            st.write(result['text'])

                            # Action button to view document chunks
                            if result.get('index') is not None:
                                if st.button(f"View All Chunks", key=f"view_chunks_{result['index']}"):
                                    st.session_state.selected_document_id = document_id
                                    st.rerun()
                else:
                    st.warning("No results found. Try a different query.")
        except Exception as e:
            st.error(f"Error during search: {str(e)}")


def show_chunk_management():
    """Chunk management with edit and re-parse capabilities"""
    st.subheader("✏️ Chunk Management")

    # Document selection
    st.markdown("### Select Document")
    try:
        import requests
        response = requests.get("http://localhost:8000/api/documents/")
        if response.status_code == 200:
            documents = response.json()
            doc_options = {doc['name']: doc['id'] for doc in documents}
            selected_doc_name = st.selectbox("Choose Document to Manage", [""] + list(doc_options.keys()))

            if selected_doc_name and doc_options[selected_doc_name]:
                document_id = doc_options[selected_doc_name]
                st.session_state.selected_document_id = document_id

                # Display document info
                st.info(f"Managing: **{selected_doc_name}** (ID: {document_id})")

                # Tab-based chunk operations
                chunk_tab = st.tabs(["📋 View Chunks", "✏️ Edit Chunk", "➕ Add Chunk", "🔄 Re-parse", "📊 Statistics", "✅ Validate"])

                # Tab 1: View all chunks
                with chunk_tab[0]:
                    show_chunks_view(document_id)

                # Tab 2: Edit chunk
                with chunk_tab[1]:
                    show_chunk_editor(document_id)

                # Tab 3: Add new chunk
                with chunk_tab[2]:
                    show_add_chunk(document_id)

                # Tab 4: Re-parse document
                with chunk_tab[3]:
                    show_reparse_document(document_id)

                # Tab 5: Statistics
                with chunk_tab[4]:
                    show_chunk_statistics(document_id)

                # Tab 6: Validate
                with chunk_tab[5]:
                    show_chunk_validation(document_id)
            else:
                st.info("Select a document to manage its chunks")

    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")


def show_chunks_view(document_id: int):
    """Display all chunks for a document"""
    st.markdown("### All Chunks")

    try:
        import requests
        response = requests.get(f"http://localhost:8000/api/chunks/document/{document_id}")

        if response.status_code == 200:
            chunks = response.json()

            if not chunks:
                st.info("No chunks found for this document.")
            else:
                st.metric("Total Chunks", len(chunks))

                # Filter by type
                type_filter = st.multiselect("Filter by Type", ["All"] + list(set([c.get('type', 'text') for c in chunks])))

                filtered_chunks = chunks if "All" in type_filter else [c for c in chunks if c.get('type') in type_filter]

                # Display chunks
                for idx, chunk in enumerate(filtered_chunks, 1):
                    chunk_type_icon = "📊" if chunk.get('type') == 'table' else "📝"

                    with st.expander(f"{chunk_type_icon} Chunk {chunk.get('chunk_index', idx)}", expanded=False):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f"**Page:** {chunk.get('page_number', 'N/A')}")
                            st.markdown(f"**Type:** {chunk.get('type', 'text').title()}")
                            char_count = len(chunk.get('text', ''))
                            st.markdown(f"**Length:** {char_count} chars")

                        with col2:
                            # Preview
                            preview_length = 200
                            st.markdown(f"**Preview:**")
                            st.text_area("Content", chunk.get('text', ''), height=100, max_chars=preview_length, key=f"preview_{idx}")

                            if char_count > preview_length:
                                st.caption(f"... and {char_count - preview_length} more characters")

                            # Action buttons
                            st.markdown("**Actions:**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button(f"✏️ Edit", key=f"edit_chunk_{idx}", use_container_width=True):
                                    st.session_state.selected_chunk_index = chunk.get('chunk_index', idx)
                                    st.rerun()

                            with col_b:
                                if st.button(f"🗑️ Delete", key=f"delete_chunk_{idx}", use_container_width=True):
                                    st.session_state.chunk_delete_confirm = {
                                        'index': idx,
                                        'chunk_index': chunk.get('chunk_index', idx)
                                    }
                                    st.rerun()

                # Delete confirmation
                if 'chunk_delete_confirm' in st.session_state:
                    confirm = st.session_state.chunk_delete_confirm
                    st.markdown("---")
                    st.error(f"⚠️ Delete chunk {confirm['chunk_index']}?")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirm", type="primary"):
                            try:
                                response = requests.delete(f"http://localhost:8000/api/chunks/document/{document_id}/chunk/{confirm['chunk_index']}")
                                if response.status_code == 200:
                                    st.success("Chunk deleted!")
                                    del st.session_state.chunk_delete_confirm
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                    with col2:
                        if st.button("❌ Cancel"):
                            del st.session_state.chunk_delete_confirm
                            st.rerun()

        else:
            st.error("Failed to load chunks")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def show_chunk_editor(document_id: int):
    """Edit an existing chunk"""
    st.markdown("### Edit Chunk")

    # Select chunk index
    chunk_index_input = st.number_input("Chunk Index", min_value=0, value=0,
                                       help="Enter the chunk index to edit")

    # Get chunks to display current content
    try:
        import requests
        response = requests.get(f"http://localhost:8000/api/chunks/document/{document_id}")

        if response.status_code == 200:
            chunks = response.json()

            if chunk_index_input < len(chunks):
                chunk = chunks[chunk_index_input]
                st.info(f"Editing Chunk {chunk_index_input} (Page {chunk.get('page_number', 'N/A')}, Type: {chunk.get('type', 'text').title()})")

                # Show current content
                st.markdown("### Current Content")
                st.text_area("Current Text", chunk.get('text', ''), height=150,
                           key=f"current_text_{chunk_index_input}")

                # Edit form
                st.markdown("### New Content")
                new_content = st.text_area("Modified Text", height=150,
                                        help="Make changes to the chunk content")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save Changes", type="primary", use_container_width=True):
                        try:
                            response = requests.put(
                                f"http://localhost:8000/api/chunks/document/{document_id}/update",
                                json={
                                    "chunk_index": chunk_index_input,
                                    "new_text": new_content
                                }
                            )

                            if response.status_code == 200:
                                result = response.json()
                                st.success(result.get('message', 'Changes saved!'))
                                st.info(f"Old length: {result.get('old_length', 0)} chars, New length: {result.get('new_length', 0)} chars")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Error: {result.get('error', 'Update failed')}")

                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                with col2:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.rerun()
            else:
                st.error(f"Chunk index {chunk_index_input} not found. Valid range: 0-{len(chunks)-1}")
        else:
            st.error("Failed to load chunks")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def show_add_chunk(document_id: int):
    """Add a new chunk to a document"""
    st.markdown("### Add New Chunk")

    with st.form("add_chunk_form"):
        chunk_text = st.text_area("Chunk Content", height=150,
                                    help="Enter the text content for the new chunk")

        chunk_type = st.selectbox("Chunk Type", ["text", "table"],
                                     help="Specify the type of content")

        page_number = st.number_input("Page Number", min_value=1, value=1,
                                        help="Associate with a specific page")

        submitted = st.form_submit_button("➕ Add Chunk")

        if submitted:
            try:
                import requests
                response = requests.post(
                    f"http://localhost:8000/api/chunks/document/{document_id}/add",
                    json={
                        "chunk_text": chunk_text,
                        "chunk_type": chunk_type,
                        "page_number": page_number
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get('message', 'Chunk added successfully!'))
                    st.info(f"New chunk index: {result.get('chunk_index', 'N/A')}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Error: {response.json().get('detail', 'Add failed')}")

            except Exception as e:
                st.error(f"Error: {str(e)}")


def show_reparse_document(document_id: int):
    """Re-parse a document with new settings"""
    st.markdown("### Re-parse Document")
    st.warning("⚠️ This will delete all existing chunks and re-process the document.")

    st.markdown("### Re-parse Options")
    force_reparse = st.checkbox("Force Re-parse (even if file hash matches)", value=False,
                                 help="Override file hash check to force re-processing")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Re-parse Document", type="primary", use_container_width=True):
            try:
                import requests
                with st.spinner("Re-parsing document... This may take a few moments..."):
                    response = requests.post(
                        f"http://localhost:8000/api/chunks/document/{document_id}/reparse",
                        params={"force": force_reparse}
                    )

                if response.status_code == 200:
                    result = response.json()
                    st.success(result.get('message', 'Document re-parsed successfully!'))
                    st.info(f"Old chunks: {result.get('old_chunks', 0)}, New chunks: {result.get('new_chunks', 0)}")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Error: {response.json().get('detail', 'Re-parse failed')}")

            except Exception as e:
                st.error(f"Error: {str(e)}")

    with col2:
        st.info("💡 Re-parse uses current chunk settings from `document_processor.py`")
        st.caption("Chunk size: 1000 chars, Overlap: 200 chars")


def show_chunk_statistics(document_id: int):
    """Display chunk statistics"""
    st.markdown("### Chunk Statistics")

    try:
        import requests
        response = requests.get(f"http://localhost:8000/api/chunks/document/{document_id}/statistics")

        if response.status_code == 200:
            stats = response.json()

            # Display metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Chunks", stats.get('total_chunks', 0))

            with col2:
                total = stats.get('total_chunks', 1)
                text_pct = (stats.get('text_chunks', 0) / total * 100 if total > 0 else 0)
                st.metric("Text Chunks", f"{stats.get('text_chunks', 0)} ({text_pct:.1f}%)")

            with col3:
                table_pct = (stats.get('table_chunks', 0) / total * 100 if total > 0 else 0)
                st.metric("Table Chunks", f"{stats.get('table_chunks', 0)} ({table_pct:.1f}%)")

            st.markdown("---")

            # Chunk length statistics
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Chunk Length Distribution")
                st.write(f"**Average:** {stats.get('avg_chunk_length', 0):.1f} characters")
                st.write(f"**Minimum:** {stats.get('min_chunk_length', 0)} characters")
                st.write(f"**Maximum:** {stats.get('max_chunk_length', 0)} characters")

            with col2:
                st.subheader("Coverage")
                st.write(f"**Pages Covered:** {stats.get('pages_covered', 0)}")

                # Quality indicators
                st.markdown("### Quality Indicators")

                avg_len = stats.get('avg_chunk_length', 0)
                if avg_len < 500:
                    st.warning("⚠️ Average chunk length is below 500 chars. Consider reducing chunk_size.")
                elif avg_len > 1500:
                    st.warning("⚠️ Average chunk length is above 1500 chars. Consider increasing chunk_size.")
                else:
                    st.success("✅ Chunk length is within optimal range (500-1500 chars).")

                if stats.get('min_chunk_length', 0) < 50:
                    st.warning("⚠️ Some chunks are too short (<50 chars). May contain incomplete information.")
                elif stats.get('max_chunk_length', 0) > 2000:
                    st.warning("⚠️ Some chunks are too long (>2000 chars). Consider adjusting chunk size.")

        else:
            st.error("Failed to load statistics")

    except Exception as e:
        st.error(f"Error: {str(e)}")


def show_chunk_validation(document_id: int):
    """Validate chunks and show errors/warnings"""
    st.markdown("### Chunk Validation")

    try:
        import requests
        response = requests.get(f"http://localhost:8000/api/chunks/document/{document_id}/validate")

        if response.status_code == 200:
            validation = response.json()

            # Overall status
            if validation.get('valid', False):
                st.success("✅ All chunks are valid!")
            elif validation.get('total_errors', 0) == 0 and validation.get('total_warnings', 0) > 0:
                st.warning(f"⚠️ {validation.get('total_warnings', 0)} warnings found. Review recommended.")
            else:
                st.error(f"❌ {validation.get('total_errors', 0)} errors found!")

            st.markdown("---")

            # Display errors
            if validation.get('errors'):
                st.subheader(f"❌ Errors ({validation.get('total_errors', 0)})")
                for error in validation.get('errors', []):
                    with st.error(error.get('message', 'Unknown error')):
                        st.caption(f"Chunk {error.get('chunk_index', 'N/A')}, Type: {error.get('type', 'unknown')}")
                        if 'length' in error:
                            st.caption(f"Length: {error['length']} chars")

            # Display warnings
            if validation.get('warnings'):
                st.subheader(f"⚠️ Warnings ({validation.get('total_warnings', 0)})")
                for warning in validation.get('warnings', []):
                    with st.warning(warning.get('message', 'Unknown warning')):
                        st.caption(f"Chunk {warning.get('chunk_index', 'N/A')}, Type: {warning.get('type', 'unknown')}")
                        if 'length' in warning:
                            st.caption(f"Length: {warning['length']} chars")

            st.markdown("---")

            # Recommendations
            st.subheader("💡 Recommendations")
            if validation.get('total_errors', 0) > 0:
                st.markdown("- Fix errors before re-parsing or using chunks in queries.")
                st.markdown("- Consider updating the source document if errors persist.")
            if validation.get('total_warnings', 0) > 0:
                st.markdown("- Review warnings and decide if action is needed.")
                st.markdown("- Optimal chunk length: 500-1500 characters.")
                st.markdown("- Re-parse document with adjusted settings if needed.")

            # Quick action buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Re-parse to Fix Issues", type="primary"):
                    st.session_state.selected_document_id = document_id
                    st.rerun()

            with col2:
                if st.button("📊 View Statistics", use_container_width=True):
                    st.session_state.selected_document_id = document_id
                    st.rerun()

        else:
            st.error("Failed to validate chunks")

    except Exception as e:
        st.error(f"Error: {str(e)}")
