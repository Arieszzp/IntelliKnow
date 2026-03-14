# Setup Guide - IntelliKnow KMS v1.0

Complete setup and configuration guide for IntelliKnow Knowledge Management System.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Environment Configuration](#environment-configuration)
3. [Service Startup](#service-startup)
4. [Bot Integration Setup](#bot-integration-setup)
5. [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
6. [Configuration Reference](#configuration-reference)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

- **Python 3.9+**
- **pip** package manager
- **DASHSCOPE_API_KEY** from [DashScope Console](https://dashscope.aliyun.com)

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**

   The `.env` file is pre-configured with all necessary settings. Review and update if needed:
   ```bash
   # Required: DashScope API Key (already configured)
   DASHSCOPE_API_KEY=your-api-key-here

   # Optional: Bot integrations (configure as needed)
   TELEGRAM_BOT_TOKEN=your-telegram-token
   TEAMS_APP_ID=your-teams-app-id
   TEAMS_APP_PASSWORD=your-teams-password
   FEISHU_APP_ID=your-feishu-app-id
   FEISHU_APP_SECRET=your-feishu-secret
   ```

3. **Start Services**

   **Option A: Start locally (No Cloudflare Tunnel)**
   ```bash
   start_local.bat
   ```

   **Option B: Start with Cloudflare Tunnel**
   ```bash
   start_all.bat  # Includes Cloudflare Tunnel (if available)
   ```

4. **Access Admin Dashboard**

   - **Web Interface**: http://localhost:8501
   - **API Documentation**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

---

## Environment Configuration

### Required Variables

```bash
# DashScope AI Service (Required)
DASHSCOPE_API_KEY=sk-your-api-key-here
```

**How to get API Key:**
1. Visit https://dashscope.aliyun.com
2. Sign up or sign in
3. Navigate to API Keys section
4. Create new API key
5. Copy key to `.env` file

### Optional Variables

```bash
# Database
DATABASE_URL=sqlite:///./intelliknow.db

# Application
APP_NAME=IntelliKnow KMS
APP_VERSION=1.0.0
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Upload Settings
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=pdf,docx,xlsx

# Vector Store
VECTOR_DB_DIR=./faiss_index
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSION=1024

# LLM Configuration
LLM_MODEL=qwen-turbo  # Options: qwen-turbo, qwen-plus, qwen-max-latest
LLM_TEMPERATURE=0.7
MAX_TOKENS=1500

# Intent Classification
INTENT_CONFIDENCE_THRESHOLD=0.4  # Reduced from 0.7 for better coverage

# LangChain Framework
USE_LANGCHAIN=true  # true=optimized for speed, false=multi-turn conversations

# Bot Integrations (Optional)
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TEAMS_APP_ID=your-teams-app-id-here
TEAMS_APP_PASSWORD=your-teams-app-password-here
FEISHU_APP_ID=your-feishu-app-id-here
FEISHU_APP_SECRET=your-feishu-app-secret-here
FEISHU_VERIFICATION_TOKEN=your-verification-token-here
FEISHU_ENCRYPT_KEY=your-encrypt-key-here
FEISHU_WEBHOOK_URL=https://your-domain.com/api/bot/feishu/webhook
INGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=your-token-here
```

---

## Service Startup

### Local Mode (No External Access)

**Use for:** Development and testing without bot integrations

```bash
start_local.bat
```

**Services Started:**
- Backend API: http://localhost:8000
- Admin UI: http://localhost:8501

### Full Mode (With Cloudflare Tunnel)

**Use for:** Testing bot integrations with external access

**Prerequisites:**
- Download Cloudflare Tunnel (`cloudflared.exe`)
- Place in project root directory

```bash
start_all.bat
```

**Services Started:**
- Backend API: http://localhost:8000
- Admin UI: http://localhost:8501
- Cloudflare Tunnel: HTTPS URL (displayed in console)

**Important:** Copy the HTTPS URL from the console output for bot webhook configuration.

---

## Bot Integration Setup

### Telegram Bot

#### 1. Create Bot
1. Open Telegram and search for **@BotFather**
2. Send `/newbot` command
3. Follow instructions:
   - Choose bot name (display name)
   - Choose bot username (must end in `bot`, e.g., `IntelliKnow_bot`)
4. **Copy Bot Token** provided by BotFather

#### 2. Configure Environment
Add to `.env`:
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

#### 3. Setup Webhook

**With Cloudflare Tunnel:**
1. Start: `start_all.bat`
2. Wait for tunnel URL (e.g., `https://abc123.trycloudflare.com`)
3. Set webhook:
   ```bash
   curl -F "url=https://your-tunnel-url/api/bot/telegram/webhook" \
        https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
   ```

**With Public Server:**
```bash
curl -F "url=https://your-domain.com/api/bot/telegram/webhook" \
     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

#### 4. Test Bot
1. Open Telegram
2. Search for your bot by username
3. Send a message
4. Receive AI-powered response

---

### Microsoft Teams Bot

#### 1. Create Azure Bot Resource
1. Login to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Bot** → **Create**
3. Fill in details:
   - Bot handle: `intelliknow-bot`
   - Pricing tier: Free (F0)
   - Type: Multi-tenant
4. Click **Create**
5. Wait for deployment (~5 minutes)

#### 2. Get App Credentials
1. Open created Bot resource
2. Navigate to **Configuration**
3. Copy **Microsoft App ID** → Add to `.env` as `TEAMS_APP_ID`
4. Click **Manage Password** → Create a new client secret:
   - Description: "IntelliKnow KMS"
   - Expires: 180 days
5. Copy **Value** → Add to `.env` as `TEAMS_APP_PASSWORD`

Add to `.env`:
```bash
TEAMS_APP_ID=12345678-abcd-efgh-1234-567890abcdef
TEAMS_APP_PASSWORD=abc123~XYZ789-abc-def-ghi-jkl-mno123pqrstu
```

#### 3. Configure Messaging Endpoint
1. In Azure Bot → **Configuration**
2. Set **Messaging endpoint** to:
   ```
   https://your-domain.com/api/bot/teams/webhook
   ```
3. Save configuration

#### 4. Add to Teams
1. In Azure Bot → **Channels**
2. Click **Microsoft Teams**
3. Agree to terms and click **Apply**
4. Your bot is now available in Teams

#### 5. Test Bot
1. Open Microsoft Teams
2. Add IntelliKnow bot to a chat or channel
3. @mention the bot with your question
4. Receive response

---

### DingTalk Bot

#### 1. Create Custom Robot
1. Open DingTalk desktop or web app
2. Navigate to a group where you want to add the bot
3. Click group settings → **Smart Group Assistant** → **Add Robot**
4. Select **Custom (via Webhook)**
5. Fill in details:
   - Robot name: `IntelliKnow`
   - Description: `AI-powered knowledge assistant`

#### 2. Configure Security Settings (Optional but Recommended)
Choose one or more:
- **Custom Keywords**: Enter keywords (e.g., `help`, `query`, `kms`)
  - Messages containing these keywords will trigger the bot
- **IP Whitelist**: Add your server IP
- **Signature**: Add a secret for webhook verification

#### 3. Get Webhook URL
1. Click **Finish** after configuration
2. **Copy Webhook URL**:
   ```
   https://oapi.dingtalk.com/robot/send?access_token=XXXXXXXXXX
   ```

#### 4. Configure Environment
Add to `.env`:
```bash
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=your-access-token-here
```

#### 5. Setup Incoming Webhook
For DingTalk to send messages to your server, you need a public endpoint:

**Option A: Cloudflare Tunnel (Development)**
1. Start Cloudflare Tunnel: `start_all.bat`
2. Use tunnel URL: `https://your-tunnel-url/api/bot/dingtalk/webhook`

**Option B: Public Server (Production)**
1. Deploy backend to public server with HTTPS
2. Webhook URL: `https://your-domain.com/api/bot/dingtalk/webhook`

#### 6. Test Bot
1. In DingTalk group, mention the bot or use configured keywords
2. Send your question
3. Receive response

**Note**: DingTalk has rate limiting (20 messages/hour per robot)

---

### Feishu/Lark Bot

#### 1. Create Self-Built App
1. Visit [Lark Open Platform](https://open.feishu.cn/app)
2. Sign up / Sign in
3. Click **Create Self-Built App**
4. Fill in:
   - App Name: `IntelliKnow KMS`
   - App Description: `AI knowledge management system`
5. Click **Create**

#### 2. Get App Credentials
1. In App Management → **Credentials & Basic Information**
2. Copy **App ID** → Add to `.env` as `FEISHU_APP_ID`
3. Click **Generate App Secret** → Copy → Add to `.env` as `FEISHU_APP_SECRET`

Add to `.env`:
```bash
FEISHU_APP_ID=cli_a1234567890
FEISHU_APP_SECRET=your-app-secret-here
```

#### 3. Configure Permissions
1. Navigate to **Permissions**
2. Add required permissions:
   - `contact:user.base:readonly` (read user info)
   - `im:message:send_as_bot` (send messages)
   - `im:message` (receive messages)
3. Click **Save**

#### 4. Create Bot User
1. Navigate to **Permissions** → **Bot User**
2. Click **Add Bot User**
3. Fill in:
   - Bot Name: `IntelliKnow`
   - Bot Avatar: Upload or use default
4. Click **Save**
5. Copy **Verification Token** → Add to `.env` as `FEISHU_VERIFICATION_TOKEN`
6. Copy **Encrypt Key** → Add to `.env` as `FEISHU_ENCRYPT_KEY`

Add to `.env`:
```bash
FEISHU_VERIFICATION_TOKEN=your-verification-token
FEISHU_ENCRYPT_KEY=your-encrypt-key
```

#### 5. Configure Event Subscriptions
1. Navigate to **Event Subscriptions**
2. Enable **Encrypt Key** (use the key copied above)
3. Set **Request URL** to:
   ```
   https://your-domain.com/api/bot/feishu/webhook
   ```
4. Click **Verify**
5. Add subscription events:
   - `im.message.receive_v1` (receive messages)
   - `im.message.read_v1` (read messages)

#### 6. Publish App
1. Navigate to **Version & Publish**
2. Click **Create Version**
3. Click **Publish** → Choose workspace
4. Wait for approval

#### 7. Test Bot
1. In Feishu, search for the bot by name
2. Start a conversation
3. Send a message
4. Receive response

---

## Cloudflare Tunnel Setup

### Installation

1. **Download Cloudflare Tunnel**
   - Visit: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/
   - Download for Windows: `cloudflared-windows-amd64.exe`
   - Rename to: `cloudflared.exe`
   - Place in project root directory

2. **Verify Installation**
   ```bash
   # Check if cloudflared.exe exists
   dir cloudflared.exe
   ```

### Usage

**Automatic Start:**
```bash
start_all.bat  # Starts backend, frontend, and Cloudflare Tunnel
```

**Manual Start:**
```bash
cloudflared tunnel --url http://localhost:8000
```

### Webhook Configuration

Once Cloudflare Tunnel is running, it will display an HTTPS URL:
```
your-url.trycloudflare.com
```

**Configure your bot webhooks with this URL:**

| Platform | Webhook URL |
|----------|-------------|
| Telegram | `https://your-url.trycloudflare.com/api/bot/telegram/webhook` |
| Teams | `https://your-url.trycloudflare.com/api/bot/teams/webhook` |
| DingTalk | `https://your-url.trycloudflare.com/api/bot/dingtalk/webhook` |
| Feishu | `https://your-url.trycloudflare.com/api/bot/feishu/webhook` |

---

## Configuration Reference

### Intent Spaces

**Default Intent Spaces** (Updated for better classification):

1. **General**
   - **Description**: General insurance products, services, and company information for customers and prospects
   - **Keywords**: insurance, life insurance, term, whole life, universal life, health insurance, medical, prescription, drug, coverage, premium, benefit, policy, customer service, support, claims, hotline, account, mobile app, contact, phone, email, website, sales team

2. **Finance**
   - **Description**: Financial policies, budget management, expense tracking, and financial reporting
   - **Keywords**: budget, expense, cost, financial, fiscal, quarterly, annual report, department budget, allocation, Q1, Q2, Q3, Q4, forecast, expense breakdown, category, personnel, technology, software, office, facilities, professional services, travel, entertainment, YTD actual, spend, cost center, variance, projection, financial analysis

3. **HR**
   - **Description**: Human resources policies, employee benefits, leave policies, performance management, and workplace procedures
   - **Keywords**: HR, human resources, employee, benefits, package, health insurance, dental, vision, 401k, retirement, matching, paid time off, vacation, sick leave, holiday, leave policy, accrual, remote work, work from home, manager approval, performance review, appraisal, feedback, self-assessment, goal setting, rating

4. **Legal**
   - **Description**: Legal compliance, regulatory requirements, contract templates, and policy documentation
   - **Keywords**: legal, compliance, regulation, regulatory, GDPR, Sarbanes-Oxley, SOX, HIPAA, PCI-DSS, CCPA, data protection, privacy, security, contract, agreement, template, NDA, MSA, employment agreement, terms of service, privacy policy, terms and conditions, legal counsel, audit, reporting, controls, due date, owner, approval

### Performance Settings

| Setting | Default | Description |
|----------|---------|-------------|
| Confidence Threshold | 0.4 (40%) | Queries below this use classified intent. Lower = more classifications. |
| LLM Model | qwen-turbo | Fast inference. Options: qwen-turbo (fast), qwen-plus (balanced), qwen-max-latest (best) |
| Max Tokens | 1500 | Maximum response tokens |
| Temperature | 0.7 | Creativity level (0.0-1.0). Lower = more deterministic. |
| Retrieval Top-K | 2 | Number of documents to retrieve for context. |

### Document Processing

| Setting | Value | Description |
|----------|-------|-------------|
| Chunk Size | 1000 chars | Maximum characters per chunk |
| Chunk Overlap | 200 chars | Overlap between chunks for context continuity |
| Max File Size | 10MB | Maximum upload file size |
| Supported Formats | PDF, DOCX, XLSX | Document formats for ingestion |

---

## Troubleshooting

### Bot Not Receiving Messages

**Check:**
1. ✅ Webhook URL is correct and accessible
2. ✅ Cloudflare Tunnel is running (for development)
3. ✅ Firewall allows inbound traffic (for production)
4. ✅ Backend logs show webhook requests

**Common Issues:**
- **400 Bad Request on Integration Create**: Integration already exists. Check the existing integration list.
- **Low Confidence Warnings**: Adjust `INTENT_CONFIDENCE_THRESHOLD` in `.env` (try 0.3-0.5)
- **Document Upload Loop**: Fixed in v1.0 - Form now uses `clear_on_submit=True`

### Database Locked Error

**Solution**: Ensure only one backend instance is running
```bash
# Windows
taskkill /F /IM python.exe

# Linux/Mac
pkill -f python
```

### Import Errors

**Solution**:
```bash
pip install -r requirements.txt
```

### DashScope API Errors

**Solution**:
1. ✅ Verify `DASHSCOPE_API_KEY` is correct
2. ✅ Check API key has sufficient quota
3. ✅ Verify network can reach DashScope servers

### Document Upload Issues

**If upload loops:**
- ✅ Restart frontend server (apply updated code)
- ✅ Clear duplicate documents from Knowledge Base page
- ✅ Re-upload document

**If processing fails:**
- ✅ Check file format (PDF/DOCX/XLSX only)
- ✅ Check file size (< 10MB)
- ✅ Check backend logs for specific errors

---

## System Architecture

### Orchestration Modes

**LangChain Mode (USE_LANGCHAIN=true)** - Default:
- ✅ Optimized for speed (< 2s response time)
- ✅ Single-turn queries
- ✅ Uses LangChain framework
- ✅ Best for fast, independent queries

**Original Mode (USE_LANGCHAIN=false)** - Optional:
- ✅ Multi-turn conversations
- ✅ Clarification questions
- ✅ Conversation history (last 5 messages)
- ✅ Best for complex, multi-turn interactions

### Data Flow

```
User Query (Bot/Web)
    ↓
API Endpoint (/api/queries/process or /api/bot/{platform}/webhook)
    ↓
Orchestrator (LangChain or Original)
    ↓
Intent Classification (DashScope AI)
    ↓
Vector Search (FAISS, filtered by intent)
    ↓
Response Generation (RAG with DashScope LLM)
    ↓
Formatted Response (Platform-adaptive)
    ↓
User receives response with citations
```

---

## Key Features

### Document Management
- ✅ Upload PDF, DOCX, XLSX documents
- ✅ Automatic text extraction and chunking
- ✅ AI-powered table extraction from PDFs
- ✅ Semantic search across all documents
- ✅ Document reprocessing and deletion

### Intent Space Management
- ✅ Create custom intent spaces
- ✅ Edit keywords and descriptions
- ✅ View query classification logs
- ✅ Clear classification cache
- ✅ **Fixed**: Default spaces cannot be edited (protected)

### Chunk Management
- ✅ View all document chunks
- ✅ Edit chunk content inline
- ✅ Add new chunks to documents
- ✅ Delete invalid chunks
- ✅ Semantic search within documents
- ✅ Validate chunks for completeness

### Query Processing
- ✅ AI-powered intent classification
- ✅ Confidence-based filtering
- ✅ Automatic fallback to General
- ✅ Multi-turn conversation support (Original mode)
- ✅ Source citations with excerpts
- ✅ Platform-adaptive formatting

### Analytics
- ✅ Dashboard statistics
- ✅ Query history with filters
- ✅ Document access tracking
- ✅ Classification accuracy metrics
- ✅ Export to CSV/JSON

### Bot Integration
- ✅ Telegram bot with webhook
- ✅ Microsoft Teams bot
- ✅ DingTalk bot with keyword support
- ✅ Feishu/Lark bot with event handling
- ✅ Platform-specific response formatting
- ✅ Connection status monitoring

---

## Quick Reference

| Component | Command | URL |
|-----------|----------|------|
| Start All | `start_all.bat` | http://localhost:8501 |
| Start Local | `start_local.bat` | http://localhost:8501 |
| API Docs | - | http://localhost:8000/docs |
| Health Check | - | http://localhost:8000/health |

---

## Support

**Documentation:**
- **README.md** - Main project documentation
- **FEATURES.md** - Complete feature list
- **ARCHITECTURE.md** - System architecture details
- **PROJECT_STRUCTURE.md** - Code structure reference

**For Issues:**
- Check logs in terminal
- Review backend error messages
- Verify configuration in `.env`

---

**Version**: 1.0.0
**Last Updated**: March 14, 2026
**Status**: ✅ Production Ready
