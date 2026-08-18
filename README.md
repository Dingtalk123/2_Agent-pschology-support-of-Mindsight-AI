Online demo link:https://2agent-mental-support-nzb.streamlit.app/
Project Overview

This project is the built-in psychological support module of MindSight AI.

Traditional psychological-support chatbots may encounter several problems in scenarios such as emotional support and psychological assistance, where response quality and safety are particularly important:

Responses may sound empathetic but provide little practical help.
Answers may be overly generic or irrelevant to the user's actual concern.
The model may make unreliable psychological or medical judgments based on limited information.
Handling of potentially high-risk content may be inconsistent.

To address these issues, this project introduces an independent supervision layer on top of the conventional single-agent conversational architecture.
Instead of returning the Dialogue Agent's first response directly to the user, the system first sends the candidate response to a Supervisor Agent for review.

The system mainly consists of two agents:
Dialogue Agent: Generates concrete, practical, and context-aware responses.
Supervisor Agent: Reviews candidate responses in terms of relevance, practical usefulness, conversation grounding, privacy, tone, and safety.

If the Supervisor determines that the current response contains a correctable issue, it generates a structured rewrite instruction and uses LangGraph to route the task back to the Dialogue Agent.

Agent Workflow

The project uses LangGraph to manage Agent states and control the execution path between different nodes.

The main workflow is:

User Input
    |
    v
Dialogue Agent
    |
    v
Supervisor Agent
    |
    v
Supervisor decides whether previous
conversation history is needed
    |
    v
    +---- approve ----> END
    |
    +---- rewrite ----> Prepare Rewrite
    |                       |
    |                       v
    |                 Dialogue Agent
    |
    +---- handoff ----> Fallback

Compared with simply calling multiple models in a fixed sequence, MindSight dynamically determines the next execution step according to the Supervisor Agent's structured decision.

Local Setup
1. Clone the Repository
git clone https://github.com/Dingtalk123/2_Agent-pschology-support-of-Mindsight-AI.git
cd 2_Agent-pschology-support-of-Mindsight-AI

2. Create a Virtual Environment
python -m venv .venv
On Windows:.venv\Scripts\activate

3. Install Dependencies
pip install -r requirements.txt

4. Configure the API Key
Create a .env file in the project root:.env
Add your API key:API_KEY=your_api_key
The .env file is included in .gitignore and will not be committed to GitHub.
Do not hard-code API keys or other sensitive credentials in the source code or commit them to a public repository.
Running the Application

5.1 Run with Streamlit
Execute: python -m streamlit run streamlit_app.py
Streamlit will start the local web interface and display the access URL in the terminal.

5.2 Run the FastAPI Backend
The FastAPI backend can also be started independently:
uvicorn main:app --reload
Default API address:http://127.0.0.1:8000
FastAPI automatically generated interactive API documentation:http://127.0.0.1:8000/docs

项目简介
本项目为mindsight AI项目的内置pschology support 模块
针对普通心理支持chatbot在心理支持、情绪陪伴等对回复质量和安全性要求较高的场景中，单次生成可能出现以下问题：
回复听起来具有共情性，但缺少实际帮助；
回答过于泛化或与用户当前问题无关；
根据有限信息进行不可靠的心理或医学判断；
对潜在风险内容的处理缺乏稳定性。

因此,本项目在普通单 Agent 对话模式的基础上增加了一层独立的监督机制。
系统不会直接将 Dialogue Agent 第一次生成的回答返回给用户，而是先交给 Supervisor Agent 进行审核。
系统主要由两个 Agent 组成：
Dialogue Agent：负责生成具体、实用且符合上下文的回复。
Supervisor Agent：负责从相关性、实用性、上下文一致性、隐私、语气和安全性等维度审核候选回复。
如果 Supervisor 判断当前回答存在可以修正的问题，就会生成结构化的重写指令，并通过 LangGraph 将任务重新路由给 Dialogue Agent。

项目使用 LangGraph 管理 Agent 状态以及不同节点之间的执行路径。

主要工作流如下：

User Input
    |
    v
Dialogue Agent
    |
    v
Supervisor Agent
    |
    v
Supervisor决定是否调用以往对话记录辅助分析
    |
    v
    +---- approve ----> END
    |
    +---- rewrite ----> Prepare Rewrite
    |                       |
    |                       v
    |                 Dialogue Agent
    |
    +---- handoff ----> Fallback
相比简单地按照固定顺序调用多个模型，MindSight 会根据 Supervisor 的结构化决策动态决定下一步执行路径。

-------------------------------------------------------------------------------------------------------------
本地运行
1. 克隆项目
git clone https://github.com/Dingtalk123/2_Agent-pschology-support-of-Mindsight-AI.git
cd 2_Agent-pschology-support-of-Mindsight-AI
2. 创建虚拟环境
python -m venv .venv
Windows：
.venv\Scripts\activate
3. 安装依赖
pip install -r requirements.txt

4. 配置 API Key
在项目根目录创建：.env
并写入：API_KEY=your_api_key
.env 已加入 .gitignore，不会被提交至 GitHub。
请勿将 API Key 或其他敏感凭证直接写入源代码或提交至公开仓库。

5.1 启动 Streamlit
执行：python -m streamlit run streamlit_app.py
Streamlit 会启动本地 Web 界面，并在终端中显示浏览器访问地址。

5.2 启动 FastAPI
也可以独立启动 FastAPI 后端：
uvicorn main:app --reload
默认 API 地址：http://127.0.0.1:8000
FastAPI 自动生成的交互式 API 文档：http://127.0.0.1:8000/docs

