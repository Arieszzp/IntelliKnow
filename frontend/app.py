"""
Main Streamlit application for IntelliKnow KMS Admin UI
"""
import streamlit as st
import requests
from datetime import datetime
import pandas as pd
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="IntelliKnow KMS",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .streaming-text {
        animation: fadeIn 0.3s ease-in;
    }
    @keyframes fadeIn {
        from { opacity: 0.5; }
        to { opacity: 1; }
    }
    .typing-cursor::after {
        content: '▋';
        animation: blink 1s step-end infinite;
    }
    @keyframes blink {
        50% { opacity: 0; }
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application"""

    # Sidebar
    st.sidebar.title("IntelliKnow KMS 🤖")
    st.sidebar.markdown("---")

    page = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "🔌 Frontend Integration", "📚 Knowledge Base",
         "🎯 Intent Configuration", "📈 Analytics"],
        label_visibility="collapsed"
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Version:** 1.0.0")
    st.sidebar.markdown(f"**API:** {API_BASE_URL}")

    # Render selected page
    if page == "📊 Dashboard":
        show_dashboard()
    elif page == "🔌 Frontend Integration":
        show_frontend_integration()
    elif page == "📚 Knowledge Base":
        show_knowledge_base()
    elif page == "🎯 Intent Configuration":
        show_intent_configuration()
    elif page == "📈 Analytics":
        show_analytics()


from app_kms_chunks import show_semantic_search, show_chunk_management

def show_knowledge_base():
    """Knowledge base management with chunk editing and semantic search"""
    st.markdown('<h1 class="main-header">📚 Knowledge Base Management</h1>', unsafe_allow_html=True)

    # Initialize session state for chunk management
    if 'selected_document_id' not in st.session_state:
        st.session_state.selected_document_id = None
    if 'selected_chunk_index' not in st.session_state:
        st.session_state.selected_chunk_index = None
    if 'chunk_search_query' not in st.session_state:
        st.session_state.chunk_search_query = ''

    # Tab navigation for Knowledge Base
    kb_tab = st.tabs(["📄 Documents", "🔍 Semantic Search", "✏️ Chunk Management"])

    with kb_tab[0]:
        # Documents section (existing functionality)
        show_documents_management()

    with kb_tab[1]:
        # Semantic Search section (new)
        show_semantic_search()

    with kb_tab[2]:
        # Chunk Management section (new)
        show_chunk_management()


def stream_response(text: str, speed: float = 0.015):
    """
    Stream text response with typing effect

    Args:
        text: The complete text to display
        speed: Speed of typing effect in seconds per character
    """
    placeholder = st.empty()

    full_text = ""
    for i, char in enumerate(text):
        full_text += char

        # Update progress indicator
        progress = (i + 1) / len(text)
        if i % 5 == 0:  # Update every 5 characters
            placeholder.markdown(f'<div class="streaming-text typing-cursor">{full_text}</div>',
                              unsafe_allow_html=True)
            time.sleep(speed)

    # Final display without cursor
    placeholder.markdown(f'<div class="streaming-text">{full_text}</div>', unsafe_allow_html=True)


def show_dashboard():
    """Dashboard overview page"""
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)

    # Get analytics data
    try:
        response = requests.get(f"{API_BASE_URL}/api/analytics/dashboard")
        if response.status_code == 200:
            data = response.json()
        else:
            data = None
    except:
        data = None

    if data:
        # Metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Total Queries",
                value=data['total_queries'],
                delta=""
            )

        with col2:
            st.metric(
                label="Total Documents",
                value=data['total_documents'],
                delta=""
            )

        with col3:
            st.metric(
                label="Avg Response Time",
                value=f"{data['avg_response_time']:.0f}ms",
                delta=""
            )

        with col4:
            st.metric(
                label="Classification Accuracy",
                value=f"{data['classification_accuracy']:.1f}%",
                delta=""
            )

        st.markdown("---")

        # Test Query Section
        st.subheader("🧪 Test Query")

        with st.form("test_query_form"):
            col1, col2 = st.columns(2)

            with col1:
                test_query = st.text_input("Enter your question")

            with col2:
                test_platform = st.selectbox("Platform", ["web", "teams", "telegram", "dingtalk"])

            test_submitted = st.form_submit_button("Submit Query")

            if test_submitted and test_query:
                with st.spinner("Processing query..."):
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/api/bot/test/query",
                            json={"query": test_query, "platform": test_platform}
                        )

                        if response.status_code == 200:
                            result = response.json()

                            st.success("✅ Query processed successfully!")

                            # Display results
                            col1, col2 = st.columns(2)

                            with col1:
                                st.markdown("### 📝 Query")
                                st.write(test_query)

                                st.markdown("### 🎯 Classification")
                                st.write(f"**Intent:** {result['intent_space']['name']}")
                                st.write(f"**Confidence:** {result['intent_space']['confidence']:.2%}")

                                st.markdown("### ⏱️ Performance")
                                st.write(f"**Response Time:** {result['response_time_ms']} ms")
                                st.write(f"**Status:** {result['response_status']}")

                            with col2:
                                st.markdown("### 💬 Response")
                                # Use streaming effect for response
                                stream_response(result['response'], speed=0.008)

                                if result.get('results'):
                                    st.markdown("### 📚 Sources")
                                    for idx, res in enumerate(result['results'][:3]):
                                        st.markdown(f"**{idx + 1}.** {res['document_name']}")
                                        st.write(f"   *Relevance:* {res['relevance_score']:.2f}")
                                        st.write(f"   *{res['excerpt'][:100]}...")
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Queries by Intent Space")
            if data['queries_by_intent']:
                intent_df = pd.DataFrame(data['queries_by_intent'])
                st.bar_chart(intent_df.set_index('intent_space'))
            else:
                st.info("No data available")

        with col2:
            st.subheader("Top Documents")
            if data['top_documents']:
                top_docs_df = pd.DataFrame(data['top_documents'])
                st.dataframe(
                    top_docs_df[['name', 'format', 'access_count']],
                    use_container_width=True
                )
            else:
                st.info("No data available")

    else:
        st.error("Unable to fetch dashboard data. Please ensure that API is running.")


def show_frontend_integration():
    """Frontend integration management"""
    st.markdown('<h1 class="main-header">🔌 Frontend Integration</h1>', unsafe_allow_html=True)

    # Platform configuration information
    platform_config = {
        "telegram": {
            "name": "Telegram Bot",
            "icon": "📱",
            "description": "Connect your KMS to Telegram for instant responses via bot commands.",
            "required_configs": [
                "**TELEGRAM_BOT_TOKEN** - Your Telegram Bot Token from @BotFather (唯一必需配置)"
            ],
            "setup_steps": [
                "1. **打开 Telegram 并搜索** `@BotFather`",
                "2. **发送命令** `/newbot` 创建新机器人",
                "3. **按照提示设置**：",
                "   - 输入机器人名称（显示名称）",
                "   - 输入机器人用户名（以 bot 结尾，如 IntelliKnow_bot）",
                "4. **复制 Bot Token** - @BotFather 会提供类似这样的 Token：",
                "   ```",
                "   723456789:AAH-YourTokenHere-XXXXXXXXXX",
                "   ```",
                "5. **将 Token 添加到环境变量** `TELEGRAM_BOT_TOKEN`"
            ],
            "webhook_config": "### Webhook 配置说明",
            "webhook_url": "**Webhook URL 格式：**",
            "webhook_example": "https://your-domain.com/api/bots/telegram/webhook",
            "webhook_notes_intro": "**注意事项：**",
            "webhook_notes": [
                "- 必须使用 HTTPS 协议",
                "- 域名需要有有效的 SSL 证书",
                "- 使用 Cloudflare Tunnel 等内网穿透工具可无需公网 IP",
                "- 配置后需要调用 Telegram API 设置 webhook"
            ]
        },
        "teams": {
            "name": "Microsoft Teams",
            "icon": "💼",
            "description": "Integrate with Microsoft Teams for enterprise communication and collaboration.",
            "required_configs": [
                "**TEAMS_APP_ID** - Your Microsoft Teams App ID from Azure AD (必需)",
                "**TEAMS_APP_PASSWORD** - App client secret/password from Azure AD (必需)"
            ],
            "setup_steps": [
                "1. **登录 Azure Portal** - [portal.azure.com](https://portal.azure.com)",
                "2. **导航至** Azure Active Directory > App registrations",
                "3. **点击** New registration",
                "4. **填写应用信息**：",
                "   - Name: 输入应用名称（如 IntelliKnow KMS）",
                "   - Supported account types: 选择账户类型",
                "   - Click Register",
                "5. **获取 Application (client) ID** - 这是 `TEAMS_APP_ID`",
                "6. **创建 Client Secret**：",
                "   - 左侧菜单选择 Certificates & secrets",
                "   - 点击 New client secret",
                "   - 输入描述，选择过期时间，点击 Add",
                "   - 复制生成的 Value（只显示一次）- 这是 `TEAMS_APP_PASSWORD`"
            ],
            "webhook_config": "### Webhook 配置说明",
            "webhook_url": "**使用 Incoming Webhook：**",
            "webhook_example": "https://your-domain.com/api/bots/teams/webhook",
            "webhook_notes_intro": "**配置步骤：**",
            "webhook_notes": [
                "- 在 Teams 频道中选择 Connector > Incoming Webhook",
                "- 为 webhook 命名并创建",
                "- 复制生成的 webhook URL",
                "- 配置时需要 Azure AD 的 Tenant ID"
            ]
        },
        "dingtalk": {
            "name": "DingTalk (钉钉)",
            "icon": "💬",
            "description": "Connect to DingTalk for seamless communication with your team in China.",
            "required_configs": [
                "无需额外配置 - 只需在钉钉中创建自定义机器人"
            ],
            "setup_steps": [
                "1. **打开钉钉**，进入需要添加机器人的群聊",
                "2. **点击右上角** 群设置 > 智能群助手 > 添加机器人",
                "3. **选择** 自定义（通过 Webhook 接入自定义服务）",
                "4. **填写机器人信息**：",
                "   - 机器人名称（如 IntelliKnow）",
                "   - 安全设置（建议选择「自定义关键词」，如「help」或「query」）",
                "5. **点击完成**，复制 Webhook URL"
            ],
            "webhook_config": "### Webhook 配置说明",
            "webhook_url": "**Webhook URL 格式：**",
            "webhook_example": "https://oapi.dingtalk.com/robot/send?access_token=XXXXXXXXXX",
            "webhook_notes_intro": "**注意事项：**",
            "webhook_notes": [
                "- 复制完整的 webhook URL（包含 access_token）",
                "- 如设置了安全关键词，发送消息时需包含关键词",
                "- 钉钉机器人每小时最多发送 20 条消息",
                "- 可在钉钉开发者平台申请更高的频率限制"
            ]
        },
        "feishu": {
            "name": "Feishu (飞书)",
            "icon": "✈️",
            "description": "Integrate with Feishu/Lark for enterprise collaboration and knowledge sharing.",
            "required_configs": [
                "**FEISHU_APP_ID** - 飞书应用 ID (必需)",
                "**FEISHU_APP_SECRET** - 飞书应用密钥 (必需)",
                "**FEISHU_VERIFICATION_TOKEN** - 验证令牌 (推荐)"
            ],
            "setup_steps": [
                "1. **访问飞书开放平台** - [open.feishu.cn](https://open.feishu.cn/)",
                "2. **创建应用**：",
                "   - 登录后点击「创建应用」",
                "   - 选择「企业自建应用」",
                "   - 输入应用名称（如 IntelliKnow KMS）",
                "3. **获取凭证**：",
                "   - 在应用管理页面找到「凭证与基础信息」",
                "   - 复制 `App ID` - 这是 `FEISHU_APP_ID`",
                "   - 复制 `App Secret` - 这是 `FEISHU_APP_SECRET`",
                "4. **配置权限**：",
                "   - 在「权限管理」中添加权限：",
                "   - `im:message` - 接收消息",
                "   - `im:message:send_as_bot` - 以机器人身份发送消息",
                "5. **配置事件订阅**：",
                "   - 在「事件订阅」中添加事件：`im.message.receive_v1`",
                "   - 设置 Request URL：`https://your-domain.com/api/bot/feishu/webhook`",
                "   - 设置验证令牌：`FEISHU_VERIFICATION_TOKEN`"
            ],
            "webhook_config": "### Webhook 配置说明",
            "webhook_url": "**Webhook URL 格式：**",
            "webhook_example": "https://your-domain.com/api/bot/feishu/webhook",
            "webhook_notes_intro": "**配置步骤：**",
            "webhook_notes": [
                "- 必须使用 HTTPS 协议（飞书强制要求）",
                "- 设置 Request URL 后，飞书会发送验证请求",
                "- 系统会自动处理 URL 验证",
                "- 可选：设置 Encrypt Key 进行消息加密",
                "- 配置完成后需要在「机器人配置」中启用机器人",
                "- 将机器人添加到群聊或私聊中使用"
            ]
        }
    }

    # Get integrations
    try:
        response = requests.get(f"{API_BASE_URL}/api/frontends")
        if response.status_code == 200:
            integrations = response.json()
        else:
            integrations = []
    except:
        integrations = []

    # Add new integration
    with st.expander("➕ Add New Integration", expanded=False):
        with st.form("add_integration"):
            platform = st.selectbox("Select Platform", ["telegram", "teams", "dingtalk", "feishu"], format_func=lambda x: platform_config[x]['name'])

            # Display platform overview
            config = platform_config[platform]
            st.markdown(f"### {config['icon']} {config['name']}")
            st.caption(config['description'])

            # Required configurations
            st.markdown("#### 📋 Required Environment Variables")
            for config_item in config['required_configs']:
                st.markdown(f"- {config_item}")

            # Setup instructions
            st.markdown("#### 🚀 Setup Instructions")
            for step in config['setup_steps']:
                st.markdown(f"{step}")

            # Webhook configuration
            st.markdown(f"#### {config['webhook_config']}")
            st.markdown(config['webhook_url'])

            # Display webhook URL as code block
            st.code(config['webhook_example'], language='bash')

            if 'webhook_notes_intro' in config:
                st.markdown(config['webhook_notes_intro'])

            st.markdown("⚠️ **Important Notes:**")
            for note in config['webhook_notes']:
                st.markdown(f"- {note}")

            st.markdown("---")
            st.markdown("### 💡 After Configuration")
            st.markdown("1. Add required environment variables to your `.env` file")
            st.markdown("2. Restart the backend server to load new configuration")
            st.markdown("3. Click **Create Integration** below to register the platform")
            st.markdown("4. Use **Test** button to verify the connection")

            is_active = st.checkbox("Active", value=True)
            submitted = st.form_submit_button("🔌 Create Integration")

            if submitted:
                try:
                    payload = {
                        "platform": platform,
                        "is_active": is_active
                    }
                    response = requests.post(
                        f"{API_BASE_URL}/api/frontends/",
                        json=payload
                    )
                    if response.status_code == 200:
                        st.success("✅ Integration created successfully!")
                        st.info("📝 Don't forget to configure environment variables and restart your backend!")
                        st.rerun()
                    elif response.status_code == 400:
                        error_detail = response.json().get('detail', 'Unknown error')
                        if 'already exists' in error_detail.lower():
                            st.warning(f"⚠️ {platform_config[platform]['name']} integration already exists!")
                        else:
                            st.error(f"Error: {error_detail}")
                    else:
                        st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

    st.markdown("---")

    # Display integrations
    if integrations:
        st.subheader("Configured Integrations")

        for integration in integrations:
            platform = integration.get('platform', 'unknown')
            config = platform_config.get(platform, {})

            with st.container():
                # Header with platform info
                col1, col2, col3 = st.columns([3, 2, 1])

                with col1:
                    status_color = "🟢 Active" if integration.get('is_active') else "🔴 Inactive"
                    st.markdown(f"### {config.get('icon', '🔌')} {config.get('name', platform.upper())}")
                    if config.get('description'):
                        st.caption(config['description'])

                with col2:
                    status_badge = "✅ Connected" if integration.get('test_status') == "success" else "❌ Not Tested"
                    st.metric("Status", status_badge)

                with col3:
                    if col3.button("🔄 Test", key=f"test_{integration.get('id')}"):
                        try:
                            response = requests.post(
                                f"{API_BASE_URL}/api/frontends/{integration['id']}/test"
                            )
                            if response.status_code == 200:
                                st.success("Test successful!")
                                st.rerun()
                            else:
                                st.error("Test failed")
                        except Exception as e:
                            st.error(f"Test error: {str(e)}")

                # Additional info row
                col1, col2, col3 = st.columns(3)

                with col1:
                    if integration.get('last_tested_at'):
                        st.markdown(f"**Last Tested:** {integration['last_tested_at'][:19].replace('T', ' ')}")
                    else:
                        st.markdown("**Last Tested:** Never")

                with col2:
                    st.markdown(f"**Created:** {integration.get('created_at', 'N/A')[:10]}")

                with col3:
                    # Configuration checklist
                    st.markdown("**Configuration:**")

                # Display required configuration checklist with webhook details
                with st.expander(f"🔧 {config.get('name', platform.upper())} Configuration & Webhook", expanded=False):
                    # Required Environment Variables
                    st.markdown("### Required Environment Variables")
                    for config_item in config.get('required_configs', []):
                        st.markdown(f"- {config_item}")

                    # Setup Instructions
                    st.markdown("### Setup Instructions")
                    for step in config.get('setup_steps', []):
                        st.markdown(f"{step}")

                    # Webhook Configuration
                    st.markdown(f"### {config.get('webhook_config', 'Webhook Configuration')}")
                    st.markdown(config.get('webhook_url', ''))

                    # Display webhook URL as code block
                    if config.get('webhook_example'):
                        st.code(config.get('webhook_example'), language='bash')

                    if config.get('webhook_notes_intro'):
                        st.markdown(config.get('webhook_notes_intro'))

                    st.markdown("⚠️ **Important Notes:**")
                    for note in config.get('webhook_notes', []):
                        st.markdown(f"- {note}")

                    st.markdown("---")
                    st.markdown("### 💡 Configuration Steps")
                    st.markdown("1. Add required environment variables to your `.env` file:")

                    # Dynamic env example based on platform
                    if platform == 'telegram':
                        env_example = """# Example .env configuration for Telegram
TELEGRAM_BOT_TOKEN=your_telegram_token_here"""
                    elif platform == 'teams':
                        env_example = """# Example .env configuration for Teams
TEAMS_APP_ID=your_teams_app_id_here
TEAMS_APP_PASSWORD=your_teams_app_password_here"""
                    else:  # dingtalk
                        env_example = """# DingTalk requires no additional configuration
:# Just copy webhook URL from DingTalk"""

                    st.code(env_example, language="bash")

                    st.markdown("2. Restart backend server:")
                    st.code("python -m backend.main", language="bash")

                    st.markdown("3. Configure webhook URL in respective platform:")
                    webhook_url = config.get('webhook_example', 'your-webhook-url-here')
                    st.code(webhook_url, language="bash")

                st.markdown("---")
    else:
        st.info("No integrations configured yet. Add your first integration above to get started.")


def show_documents_management():
    """Documents upload and management"""
    st.subheader("📄 Upload and Manage Documents")

    # Initialize upload state
    if 'upload_success' not in st.session_state:
        st.session_state.upload_success = False

    with st.expander("Upload Document", expanded=True):
        with st.form("upload_document", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Document Name", key="upload_name")
                uploaded_file = st.file_uploader(
                    "Choose a file",
                    type=["pdf", "docx", "xlsx"]
                )

            with col2:
                # Get intent spaces
                try:
                    response = requests.get(f"{API_BASE_URL}/api/intent-spaces")
                    if response.status_code == 200:
                        intent_spaces = response.json()
                        intent_space_options = {
                            ispace['name']: ispace['id']
                            for ispace in intent_spaces
                        }
                    else:
                        intent_space_options = {}
                except:
                    intent_space_options = {}

                intent_space_id = st.selectbox(
                    "Intent Space",
                    options=list(intent_space_options.keys()),
                    format_func=lambda x: x,
                    key="upload_intent_space"
                )

            submitted = st.form_submit_button("Upload & Process")

            if submitted and uploaded_file and name:
                try:
                    # Show progress
                    with st.spinner("Processing document... This may take a moment..."):
                        files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                        params = {
                            "name": name,
                            "intent_space_id": intent_space_options[intent_space_id]
                        }
                        response = requests.post(
                            f"{API_BASE_URL}/api/documents/upload",
                            files=files,
                            params=params
                        )
                        if response.status_code == 200:
                            st.success("Document uploaded and processed successfully!")
                            # Clear the file uploader by setting it to None
                            uploaded_file = None
                            # Store success message in session state
                            st.session_state.upload_success = True
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

            # Display success message if upload was successful
            if st.session_state.upload_success:
                st.success("✅ Document uploaded successfully!")
                st.session_state.upload_success = False  # Clear the flag after displaying
            else:
                if not uploaded_file or not name:
                    st.warning("Please provide both a name and file")

    # Document list with search and filters
    st.subheader("Documents")

    # Search and Filter
    col1, col2, col3 = st.columns(3)

    with col1:
        search_term = st.text_input("🔍 Search documents...", key="doc_search")

    with col2:
        format_filter = st.multiselect("Filter by Format", ["pdf", "docx", "xlsx"], key="doc_format_filter")

    with col3:
        # Get intent spaces for filter
        try:
            response = requests.get(f"{API_BASE_URL}/api/intent-spaces")
            if response.status_code == 200:
                intent_spaces = response.json()
                intent_names = ["All"] + [ispace['name'] for ispace in intent_spaces]
            else:
                intent_names = ["All"]
        except:
            intent_names = ["All"]

        intent_filter = st.selectbox("Filter by Intent Space", intent_names, key="doc_intent_filter")

    # Load documents
    try:
        response = requests.get(f"{API_BASE_URL}/api/documents/")
        if response.status_code == 200:
            documents = response.json()

            if documents:
                df = pd.DataFrame(documents)
                df['uploaded_at'] = pd.to_datetime(df['uploaded_at']).dt.strftime('%Y-%m-%d')
                df['size_mb'] = df['file_size'] / (1024 * 1024)

                # Apply filters
                if search_term:
                    df = df[df['name'].str.contains(search_term, case=False, na=False)]

                if format_filter:
                    df = df[df['file_format'].isin(format_filter)]

                if intent_filter != "All":
                    try:
                        response = requests.get(f"{API_BASE_URL}/api/intent-spaces")
                        if response.status_code == 200:
                            intent_spaces = response.json()
                            intent_space_map = {ispace['name']: ispace['id'] for ispace in intent_spaces}
                            if intent_filter in intent_space_map:
                                df = df[df['intent_space_id'] == intent_space_map[intent_filter]]
                    except:
                        pass

                if not df.empty:
                    display_df = df[['name', 'file_format', 'size_mb', 'status', 'uploaded_at', 'id']]
                    display_df = display_df.rename(columns={
                        'name': 'Document Name',
                        'file_format': 'Format',
                        'size_mb': 'Size (MB)',
                        'status': 'Status',
                        'uploaded_at': 'Upload Date',
                        'id': 'ID'
                    })

                    # Display with action buttons
                    for idx, row in display_df.iterrows():
                        # Create an expander for each document
                        with st.expander(f"📄 {row['Document Name']}", expanded=False):
                            col1, col2 = st.columns([2, 1])

                            with col1:
                                st.markdown(f"**Format:** {row['Format']}")
                                st.markdown(f"**Size:** {row['Size (MB)']:.2f} MB")
                                st.markdown(f"**Upload Date:** {row['Upload Date']}")
                                st.markdown(f"**Status:** {'✅ Processed' if row['Status'] == 'processed' else '❌ Error'}")

                            with col2:
                                # Action buttons
                                st.markdown("**Actions:**")

                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if st.button("🔄 Reprocess", key=f"reprocess_{row['ID']}", use_container_width=True):
                                        try:
                                            with st.spinner("Reprocessing document..."):
                                                response = requests.post(
                                                    f"{API_BASE_URL}/api/documents/{row['ID']}/reprocess"
                                                )
                                                if response.status_code == 200:
                                                    st.success("Document reprocessed successfully!")
                                                    time.sleep(1)
                                                    st.rerun()
                                                else:
                                                    st.error(f"Failed to reprocess: {response.json().get('detail', 'Unknown error')}")
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")

                                with col_b:
                                    if st.button("🗑️ Delete", key=f"delete_{row['ID']}", use_container_width=True):
                                        # Store document ID for deletion confirmation
                                        st.session_state['delete_doc_id'] = row['ID']
                                        st.session_state['delete_doc_name'] = row['Document Name']

                        st.divider()

                    # Show delete confirmation dialog at the bottom if a deletion is pending
                    if 'delete_doc_id' in st.session_state and st.session_state['delete_doc_id']:
                        st.markdown("---")
                        st.error(f"⚠️ Are you sure you want to delete '{st.session_state['delete_doc_name']}'?")
                        st.warning("This action cannot be undone. The document and all its data will be permanently removed.")

                        col1, col2 = st.columns(2)

                        with col1:
                            if st.button("✅ Confirm Delete", type="primary", use_container_width=True):
                                try:
                                    with st.spinner("Deleting document..."):
                                        doc_id = st.session_state['delete_doc_id']
                                        response = requests.delete(
                                            f"{API_BASE_URL}/api/documents/{doc_id}"
                                        )
                                        if response.status_code == 200:
                                            st.success("Document deleted successfully!")
                                            # Clear session state
                                            del st.session_state['delete_doc_id']
                                            del st.session_state['delete_doc_name']
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to delete: {response.json().get('detail', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")

                        with col2:
                            if st.button("❌ Cancel", use_container_width=True):
                                # Clear session state without deleting
                                del st.session_state['delete_doc_id']
                                del st.session_state['delete_doc_name']
                                st.rerun()
                else:
                    st.info("No documents match your filters.")
            else:
                st.info("No documents uploaded yet.")
        else:
            st.error("Failed to fetch documents")
    except Exception as e:
        st.error(f"Error: {str(e)}")


def show_intent_configuration():
    """Intent space configuration"""
    st.markdown('<h1 class="main-header">🎯 Intent Configuration</h1>', unsafe_allow_html=True)

    # Use tabs for better organization
    tab1, tab2 = st.tabs(["📋 Intent Spaces", "📜 Recent Queries"])

    with tab1:
        # Create new intent space
        with st.expander("Create Intent Space", expanded=False):
            with st.form("create_intent"):
                name = st.text_input("Intent Space Name", key="create_name")
                description = st.text_area("Description", key="create_description")
                keywords = st.text_input("Keywords (comma-separated)", key="create_keywords")
                submitted = st.form_submit_button("Create")

                if submitted and name:
                    try:
                        payload = {
                            "name": name,
                            "description": description,
                            "keywords": keywords
                        }
                        response = requests.post(
                            f"{API_BASE_URL}/api/intent-spaces/",
                            json=payload
                        )
                        if response.status_code == 200:
                            st.success("Intent space created successfully!")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

        # Intent spaces list
        st.subheader("Manage Intent Spaces")

        try:
            response = requests.get(f"{API_BASE_URL}/api/intent-spaces/")
            if response.status_code == 200:
                intent_spaces = response.json()

                if intent_spaces:
                    for space in intent_spaces:
                        with st.container():
                            # Header with name and description
                            st.markdown(f"### {space['name']}")
                            if space['description']:
                                st.caption(space['description'])

                            # Metrics row
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Documents", space['document_count'])
                            with col2:
                                st.metric("Accuracy", f"{space['classification_accuracy']:.1f}%")
                            with col3:
                                status = "🔒 Default" if space.get('is_default') else "✅ Active" if space['document_count'] > 0 else "🔘 Inactive"
                                st.metric("Status", status)

                            # Keywords and actions
                            col1, col2, col3 = st.columns([3, 1, 1])

                            with col1:
                                if space['keywords']:
                                    st.markdown(f"**Keywords:** {space['keywords']}")
                                else:
                                    st.caption("No keywords defined")

                            with col2:
                                # Disable edit button for default spaces
                                if space.get('is_default'):
                                    st.button("🔒 Locked", key=f"locked_{space['id']}", use_container_width=True, disabled=True, help="Cannot edit default intent spaces")
                                else:
                                    if st.button("✏️ Edit", key=f"edit_{space['id']}", use_container_width=True):
                                        st.session_state[f"editing_{space['id']}"] = True

                            with col3:
                                if st.button("🗑️ Delete", key=f"delete_{space['id']}", use_container_width=True):
                                    st.session_state.delete_space_id = space['id']
                                    st.session_state.delete_space_name = space['name']
                                    st.rerun()

                            # Edit form in expander - shown when editing
                            if st.session_state.get(f"editing_{space['id']}", False):
                                with st.expander(f"📝 Edit: {space['name']}", expanded=True):
                                    with st.form(f"edit_form_{space['id']}"):
                                        edit_name = st.text_input(
                                            "Intent Space Name",
                                            value=space['name'],
                                            key=f"edit_name_{space['id']}"
                                        )
                                        edit_description = st.text_area(
                                            "Description",
                                            value=space['description'] or '',
                                            key=f"edit_desc_{space['id']}",
                                            height=100
                                        )
                                        edit_keywords = st.text_input(
                                            "Keywords (comma-separated)",
                                            value=space['keywords'] or '',
                                            key=f"edit_keys_{space['id']}"
                                        )

                                        col1, col2 = st.columns(2)
                                        with col1:
                                            save_btn = st.form_submit_button("💾 Save", type="primary")
                                        with col2:
                                            cancel_btn = st.form_submit_button("❌ Cancel")

                                        if save_btn:
                                            if edit_name:
                                                try:
                                                    payload = {
                                                        "name": edit_name,
                                                        "description": edit_description,
                                                        "keywords": edit_keywords
                                                    }
                                                    response = requests.put(
                                                        f"{API_BASE_URL}/api/intent-spaces/{space['id']}",
                                                        json=payload
                                                    )
                                                    if response.status_code == 200:
                                                        st.success("✅ Updated successfully!")
                                                        del st.session_state[f"editing_{space['id']}"]
                                                        time.sleep(0.5)
                                                        st.rerun()
                                                    else:
                                                        st.error(f"❌ {response.json().get('detail', 'Unknown error')}")
                                                except Exception as e:
                                                    st.error(f"❌ {str(e)}")
                                            else:
                                                st.warning("⚠️ Name is required!")

                                        if cancel_btn:
                                            if f"editing_{space['id']}" in st.session_state:
                                                del st.session_state[f"editing_{space['id']}"]
                                            st.rerun()

                            st.markdown("---")

                            st.markdown("---")

                    # Show delete confirmation dialog at the bottom if a deletion is pending
                    if st.session_state.get('delete_space_id'):
                        st.markdown("---")
                        st.error("⚠️ **Delete Confirmation**")

                        delete_id = st.session_state.get('delete_space_id')
                        delete_name = st.session_state.get('delete_space_name')

                        # Check if this space has documents
                        space_with_docs = next((s for s in intent_spaces if s['id'] == delete_id), None)

                        if space_with_docs and space_with_docs['document_count'] > 0:
                            st.warning(f"⚠️ This intent space has {space_with_docs['document_count']} associated documents.")
                            st.info("💡 You cannot delete it until all documents are removed or reassigned.")
                            if st.button("❌ Cancel Deletion", use_container_width=True):
                                del st.session_state.delete_space_id
                                del st.session_state.delete_space_name
                                st.rerun()
                        else:
                            col1, col2, col3 = st.columns([1, 1, 1])

                            with col1:
                                st.info(f"Target: **{delete_name}**")

                            with col2:
                                if st.button("✅ Confirm Delete", type="primary", use_container_width=True):
                                    try:
                                        with st.spinner("Deleting intent space..."):
                                            response = requests.delete(
                                                f"{API_BASE_URL}/api/intent-spaces/{delete_id}"
                                            )
                                            if response.status_code == 200:
                                                st.success("Intent space deleted successfully!")
                                                del st.session_state.delete_space_id
                                                del st.session_state.delete_space_name
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error(f"Failed to delete: {response.json().get('detail', 'Unknown error')}")
                                    except Exception as e:
                                        st.error(f"Error: {str(e)}")

                            with col3:
                                if st.button("❌ Cancel", use_container_width=True):
                                    del st.session_state.delete_space_id
                                    del st.session_state.delete_space_name
                                    st.rerun()
                else:
                    st.info("No intent spaces configured yet. Create your first intent space above.")
            else:
                st.error("Failed to fetch intent spaces")
        except Exception as e:
            st.error(f"Error: {str(e)}")

    with tab2:
        st.subheader("Recent Query Activity")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            limit = st.selectbox("Show queries", [10, 20, 50, 100], index=0)
        with col2:
            status_filter = st.selectbox("Filter by status", ["All", "success", "failed", "no_match", "need_clarification"])

        try:
            response = requests.get(f"{API_BASE_URL}/api/analytics/query-logs?limit={limit}")
            if response.status_code == 200:
                logs = response.json()

                if logs:
                    # Apply status filter
                    if status_filter != "All":
                        logs = [log for log in logs if log.get('response_status') == status_filter]

                    if logs:
                        for log in logs:
                            # Create a card for each query
                            with st.container():
                                # Query text
                                st.markdown(f"**Q:** {log['query_text'][:150]}{'...' if len(log['query_text']) > 150 else ''}")

                                # Metrics row
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    intent_color = {
                                        'success': '🟢',
                                        'failed': '🔴',
                                        'no_match': '🟡',
                                        'need_clarification': '🟠'
                                    }.get(log.get('response_status', ''), '⚪')

                                    st.markdown(f"{intent_color} **Intent:** {log['intent_space']}")
                                with col2:
                                    st.markdown(f"**Confidence:** {log['confidence_score']:.2%}")
                                with col3:
                                    st.markdown(f"**Status:** `{log['response_status']}`")

                                # Platform and timestamp
                                col1, col2 = st.columns(2)
                                with col1:
                                    platform_icon = {
                                        'telegram': '📱',
                                        'teams': '💼',
                                        'web': '🌐',
                                        'dingtalk': '💬'
                                    }.get(log.get('platform', 'web'), '🌐')
                                    st.markdown(f"{platform_icon} **Platform:** {log.get('platform', 'web').upper()}")
                                with col2:
                                    st.caption(f"**Time:** {log['created_at'][:19].replace('T', ' ')}")

                                st.markdown("---")
                    else:
                        st.info(f"No queries match the selected filter.")
                else:
                    st.info("No query history available yet.")
            else:
                st.error("Failed to fetch query logs")
        except Exception as e:
            st.error(f"Error: {str(e)}")


def show_analytics():
    """Analytics dashboard"""
    st.markdown('<h1 class="main-header">📈 Analytics</h1>', unsafe_allow_html=True)

    try:
        response = requests.get(f"{API_BASE_URL}/api/analytics/dashboard")
        if response.status_code == 200:
            data = response.json()

            # Key metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Queries", data['total_queries'])
            with col2:
                st.metric("Total Documents", data['total_documents'])
            with col3:
                st.metric("Avg Response Time", f"{data['avg_response_time']:.0f}ms")

            st.markdown("---")

            # Queries by intent
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Queries by Intent Space")
                if data['queries_by_intent']:
                    intent_df = pd.DataFrame(data['queries_by_intent'])
                    st.bar_chart(intent_df.set_index('intent_space'))
                else:
                    st.info("No data available")

            with col2:
                st.subheader("Top Accessed Documents")
                if data['top_documents']:
                    top_docs_df = pd.DataFrame(data['top_documents'])
                    st.dataframe(
                        top_docs_df[['name', 'format', 'access_count']],
                        use_container_width=True
                    )
                else:
                    st.info("No data available")

            # Query history
            st.subheader("Query History")

            response = requests.get(f"{API_BASE_URL}/api/analytics/query-logs?limit=20")
            if response.status_code == 200:
                logs = response.json()
                logs_df = pd.DataFrame(logs)

                if not logs_df.empty:
                    logs_df['created_at'] = pd.to_datetime(logs_df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                    display_cols = [
                        'query_text', 'intent_space', 'confidence_score',
                        'response_status', 'platform', 'response_time_ms', 'created_at'
                    ]
                    logs_df = logs_df[display_cols].rename(columns={
                        'query_text': 'Query',
                        'intent_space': 'Intent',
                        'confidence_score': 'Confidence',
                        'response_status': 'Status',
                        'platform': 'Platform',
                        'response_time_ms': 'Time (ms)',
                        'created_at': 'Time'
                    })

                    st.dataframe(logs_df, use_container_width=True)

                    # Export functionality
                    st.markdown("---")
                    st.subheader("📥 Export Data")

                    col1, col2 = st.columns(2)

                    with col1:
                        csv_data = logs_df.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Download Query Logs (CSV)",
                            data=csv_data,
                            file_name=f'query_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                            mime='text/csv'
                        )

                    with col2:
                        # Export summary statistics
                        summary_data = f"""Query Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total Queries: {len(logs_df)}
Successful Queries: {len(logs_df[logs_df['Status'] == 'success'])}
Failed Queries: {len(logs_df[logs_df['Status'] == 'failed'])}
No Match Queries: {len(logs_df[logs_df['Status'] == 'no_match'])}

By Platform:
{logs_df['Platform'].value_counts().to_string()}

By Intent Space:
{logs_df['Intent'].value_counts().to_string()}

Average Response Time: {logs_df['Time (ms)'].mean():.0f}ms
Average Confidence: {logs_df['Confidence'].mean():.2%}
"""
                        st.download_button(
                            label="Download Summary Report (TXT)",
                            data=summary_data,
                            file_name=f'summary_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                            mime='text/plain'
                        )

                else:
                    st.info("No query history available")
        else:
            st.error("Failed to fetch analytics data")
    except Exception as e:
        st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()
