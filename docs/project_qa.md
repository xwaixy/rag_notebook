# 项目问题与解答整理

本文档整理了围绕本项目开发、模型接入、RAG 检索、前后端交互、部署和 Docker 化过程中讨论过的问题与解答，便于后续复习、答辩、排错和继续开发。

## 1. Python 环境与依赖管理

### 1.1 安装依赖前是否需要先进入虚拟环境？

如果使用传统 `pip`，一般建议先激活虚拟环境：

```bash
source .venv/bin/activate
pip install xxx
```

这样依赖会安装到当前项目的 `.venv` 中，不会污染系统 Python。

如果使用 `uv`，不一定需要手动激活虚拟环境。`uv run`、`uv sync`、`uv add` 会自动识别或创建项目虚拟环境，并把命令运行在该环境中。

例如：

```bash
uv run python main.py
uv add langchain-openai
uv sync
```

这也是推荐用 `uv` 的原因：它把“创建虚拟环境、安装依赖、运行命令”整合起来了。

### 1.2 为什么用 uv 就不需要激活虚拟环境？

因为 `uv` 会根据当前目录的 `pyproject.toml` 自动管理项目环境。它会优先使用项目下的 `.venv`，没有则创建。

比如：

```bash
uv run python -V
```

这条命令不是直接调用系统 Python，而是调用当前项目虚拟环境里的 Python。

所以 `uv` 的常见使用方式是：

```bash
cd backend
uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 1.3 uv 没安装时怎么办？

如果执行：

```bash
uv --version
```

提示 `uv: command not found`，说明 uv 没有安装或没有加入 PATH。

安装后如果仍然找不到，可以临时加入 PATH：

```bash
export PATH="$HOME/.local/bin:$PATH"
uv --version
```

如果能看到版本号，例如：

```text
uv 0.11.19
```

说明 uv 已经可用。

### 1.4 为什么 uv add langchain-openai 会出现 requests 依赖冲突？

原因不是 `langchain-openai` 本身冲突，而是 uv 会对项目声明支持的所有 Python 版本进行依赖解析。

当项目没有限制 Python 上限时，uv 会尝试解析未来 Python 版本，例如 Python 3.14。某些依赖在这些版本或特定索引源下不可用，就会出现解析失败。

解决方式是在 `backend/pyproject.toml` 中限制 Python 版本：

```toml
requires-python = ">=3.12,<3.14"
```

另外项目里使用了 PyTorch CUDA 源，uv 默认会优先从第一个包含包名的索引解析依赖。为了避免 `requests` 等普通包被错误地限制在 PyTorch 源里，需要把 PyTorch 源设置为显式源：

```toml
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true
```

这样普通依赖会从 PyPI/清华源解析，只有 torch 相关包才走 PyTorch 源。

### 1.5 改依赖解析配置后，未来运行项目会不会有别的冲突？

限制 `requires-python = ">=3.12,<3.14"` 通常不会增加冲突，反而会减少未来版本导致的不确定性。

这个项目实际使用的是 Python 3.12，所以声明只支持 3.12 到 3.13 以内是合理的。

真正容易产生冲突的地方主要有：

- PyTorch CUDA 版本和显卡驱动版本不匹配。
- `langchain`、`langchain-core`、`langchain-openai` 版本跨度太大。
- 本地模型依赖 `sentence-transformers`、`transformers`、`torch`，这些包升级后可能改变行为。
- Docker 内和本机 Python 版本不一致。

建议后续统一使用：

```bash
uv sync
uv run ...
```

不要混用系统 pip 和项目 uv 环境。

### 1.6 为什么有些包之前下载过，现在又下载了一遍？

常见原因有：

1. 不同虚拟环境之间依赖不共享。

例如：

```text
backend/.venv
DjangoUserService/.venv
```

这是两个环境，互相看不到对方安装过的包。

2. uv 有自己的缓存，但安装到新虚拟环境时仍然需要解压和链接。

即使包已经在缓存中，uv 也要把依赖同步到当前 `.venv`。

3. CUDA 版 PyTorch 体积很大。

类似这些包：

```text
nvidia-cublas-cu12
nvidia-cudnn-cu12
nvidia-cusparse-cu12
torch
triton
```

是 PyTorch CUDA 运行所需依赖，体积较大，看起来像“又下载了很多”。

### 1.7 怎么查看项目里有哪些虚拟环境？

可以查找 `pyvenv.cfg`：

```bash
find /home/wyl/LangChain-RAG-FastAPI-Service -name pyvenv.cfg
```

如果输出：

```text
backend/.venv/pyvenv.cfg
DjangoUserService/.venv/pyvenv.cfg
```

说明这两个目录各自有一个虚拟环境。

### 1.8 DjangoUserService 的虚拟环境里没有 pip 怎么办？

如果执行：

```bash
DjangoUserService/.venv/bin/python -m pip list
```

提示：

```text
No module named pip
```

说明这个虚拟环境是 uv 创建的，里面可能没有安装 pip。可以直接用 uv 查看依赖：

```bash
cd DjangoUserService
uv pip list
```

或者：

```bash
uv run python -m pip list
```

如果确实需要 pip，可以安装：

```bash
uv pip install pip
```

### 1.9 怎么查看系统 Python 装了哪些包？

先看系统 Python 路径：

```bash
which python
which python3
```

再查看包：

```bash
python3 -m pip list
```

如果系统 Python 没有 pip，可以尝试：

```bash
python3 -m ensurepip --upgrade
```

但不建议把项目依赖装到系统 Python。项目依赖应放在项目虚拟环境中。

## 2. 显卡与本地向量模型

### 2.1 怎么查看显卡配置？

可以使用：

```bash
nvidia-smi
```

也可以在项目环境中验证 PyTorch 是否能识别 CUDA：

```bash
cd backend
uv run python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no cuda')"
```

如果输出类似：

```text
2.12.0+cu126
True
NVIDIA GeForce GTX 1650
```

说明 PyTorch 已经可以使用显卡。

### 2.2 GTX 1650 适合跑本地向量模型吗？

可以跑轻量级向量模型，但不适合跑很大的模型。

GTX 1650 通常显存为 4GB，适合：

- Qwen3-Embedding-0.6B
- bge-small-zh
- bge-base-zh
- m3e-small
- m3e-base

不太适合：

- 大尺寸 reranker
- 大语言模型推理
- 多个模型同时常驻显存

建议：

- 向量模型可以放 GPU。
- Reranker 可以先关闭。
- 如果 Docker 内没有配置 GPU 访问，Docker 部署时可以先用 CPU 跑向量模型。

### 2.3 推荐什么免费可下载的本地向量模型？

适合这个项目的免费本地 Embedding 模型：

1. `Qwen3-Embedding-0.6B`

优点：

- 中文效果好。
- 体积相对可控。
- 适合个人知识库。

缺点：

- 比 small/base 模型更吃资源。

2. `BAAI/bge-small-zh-v1.5`

优点：

- 小、快、省内存。
- 适合低配置服务器。

缺点：

- 语义效果弱于更大的模型。

3. `BAAI/bge-base-zh-v1.5`

优点：

- 中文检索效果稳定。
- 资源占用适中。

缺点：

- 比 small 更慢一些。

如果本机 GTX 1650，本地开发推荐 `Qwen3-Embedding-0.6B`；如果云服务器只有 2C2G，推荐 `bge-small-zh-v1.5` 或直接用在线 Embedding API。

### 2.4 向量模型在线 API 是不是很烧 token？

Embedding API 会按输入文本 token 计费，但通常比聊天模型便宜很多。

它主要在两种场景消耗 token：

1. 文档入库时。

上传文档后，每个切片都要生成向量，所以文档越大，消耗越多。

2. 用户提问时。

每次问题会生成查询向量，这部分通常很少。

真正成本较高的是大量文档首次入库，而不是日常提问。

如果资料量不大，在线 Embedding 成本通常可接受；如果要长期上传大量文档，本地向量模型更划算。

## 3. OpenAI / 中转站模型接入

### 3.1 项目原来为什么不支持 LLM_TYPE=OPENAI？

原来的模型工厂只支持：

```text
ALIYUN
OLLAMA
```

所以配置：

```env
LLM_TYPE=OPENAI
```

启动时会报：

```text
不支持的LLM_TYPE: OPENAI，可选值: ALIYUN, OLLAMA
```

需要在 `backend/app/utils/factory.py` 中新增 OpenAI 分支，并安装：

```bash
uv add langchain-openai
```

然后通过 `ChatOpenAI` 接入 OpenAI 兼容接口。

### 3.2 中转站应该怎么配置到项目里？

Codex CLI 的配置不能直接给项目用。项目运行时只读取项目自己的 `.env`。

如果中转站提供 OpenAI 兼容接口，应在 `backend/.env` 或 `backend/.env.docker` 中配置：

```env
LLM_TYPE=OPENAI
OPENAI_API_KEY=你的中转站API_KEY
OPENAI_BASE_URL=https://你的中转站地址/v1
OPENAI_MODEL_NAME=gpt-5.5
```

注意：

- 不要把 API Key 写进 README 或提交到 Git。
- 中转站如果要求 OpenAI 兼容接口，`base_url` 通常要带 `/v1`。
- 如果中转站只支持 Responses API，需要对应启用 Responses API 模式。

### 3.3 为什么代理地址 socks://127.0.0.1:7890 会报错？

错误：

```text
Unknown scheme for proxy URL URL('socks://127.0.0.1:7890')
```

说明底层 HTTP 客户端不识别 `socks://` 这个写法。

常见解决方式：

1. 改成：

```env
HTTPS_PROXY=socks5://127.0.0.1:7890
HTTP_PROXY=socks5://127.0.0.1:7890
```

2. 安装 socks 支持：

```bash
uv add socksio
```

3. 如果不希望 OpenAI 客户端读取系统代理，可以配置：

```env
OPENAI_TRUST_ENV=false
```

### 3.4 为什么请求被中转站拦截？

错误：

```text
openai.PermissionDeniedError: Your request was blocked.
```

这不是项目代码报错，而是上游中转站拒绝了请求。

可能原因：

- API Key 无权限。
- 模型名不支持。
- 中转站不支持当前接口类型。
- 请求头或 User-Agent 被拦截。
- 内容或地域规则被拦截。

可以尝试：

- 确认模型名是否真的是中转站支持的模型。
- 切换 Chat Completions 模式或 Responses API 模式。
- 配置 User-Agent。
- 用 curl 单独测试中转站接口。

### 3.5 为什么 HyDE 成功了，但最终回答阶段又报 Upstream service temporarily unavailable？

因为 HyDE 和最终回答是两次不同的模型调用。

流程大致是：

1. 调用模型生成 HyDE 假设性文档。
2. 执行向量检索。
3. 调用模型总结检索结果。
4. 调用 Agent 生成最终回答。

HyDE 成功只能说明第一次模型请求成功，不代表后续请求也一定成功。

`Upstream service temporarily unavailable` 通常表示中转站或上游模型临时不可用，与本地代码关系不大。

可以优化：

- 减少多次 LLM 总结。
- 降低检索文档数量。
- 给 HyDE 和摘要设置超时。
- 对最终模型调用增加重试或失败提示。

## 4. 项目启动命令

### 4.1 本地启动 FastAPI 服务

```bash
cd /home/wyl/LangChain-RAG-FastAPI-Service/backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 4.2 本地启动 Django 服务

```bash
cd /home/wyl/LangChain-RAG-FastAPI-Service/DjangoUserService
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8001
```

### 4.3 本地启动前端

```bash
cd /home/wyl/LangChain-RAG-FastAPI-Service/front
npm run dev -- --host 127.0.0.1 --port 3000
```

访问：

```text
http://127.0.0.1:3000
```

### 4.4 Docker 启动

```bash
cd /home/wyl/LangChain-RAG-FastAPI-Service
docker compose build
docker compose up -d
docker compose ps
```

## 5. AI 助手回答问题的完整流程

### 5.1 用户问 AI 助手问题时，项目内部发生了什么？

整体流程如下：

1. 前端发送聊天请求。

用户在 Vue 前端输入问题，前端通过 Axios 或 fetch 请求 FastAPI 的聊天接口。

2. 后端校验身份。

FastAPI 根据 JWT 获取当前用户 ID，保证用户只能访问自己的会话、笔记和知识库。

3. 读取会话历史。

系统从 MySQL 中读取当前会话之前的消息，作为短期记忆。

4. 执行 RAG 检索。

后端基于用户问题检索：

- 用户笔记。
- 用户知识库文档。
- 原始问题检索结果。
- HyDE 假设性文档检索结果。

5. 构造 Prompt。

把系统提示词、会话历史、用户问题、检索上下文一起传给大模型。

6. 调用大模型。

模型根据 Prompt 生成回答。

7. 流式返回前端。

后端通过 SSE 把回答逐步发送给前端，前端边接收边展示。

8. 保存历史。

最终把用户问题和 AI 回答写入 MySQL。

### 5.2 为什么上传了 TXT，问“我叫什么、喜欢吃什么”，AI 还是不知道？

可能原因：

1. 文档没有成功入库。

上传文件不等于已经切片和向量化成功，需要确认知识库处理状态。

2. 检索没有命中相关切片。

如果问题太短，比如“我是谁”“我喜欢什么”，原始查询信息量很少，向量检索可能匹配不到“名字”“喜欢吃面食”等具体内容。

3. Agent 没有主动调用 RAG 工具。

如果 Prompt 没有要求优先检索，模型可能直接凭常识回答，导致不知道上传资料内容。

4. 用户隔离导致查不到。

知识库是按用户隔离的，如果上传文件和提问不是同一个用户 ID，就检索不到。

5. Embedding 模型不一致。

如果文档入库时和查询时使用的向量模型不同，向量维度或语义空间不一致，检索效果会变差，甚至报错。

### 5.3 为什么不建议死板规定“我叫什么/喜欢什么”必须调用某个工具？

因为这种规则太硬，会导致系统只对固定关键词有效。

更自然的做法是：

1. 用户提出任意问题。
2. 系统先生成简短 HyDE 假设性文档。
3. 同时使用原始问题和 HyDE 文档检索笔记与知识库。
4. 如果检索到相关内容，优先基于检索内容回答。
5. 如果没有检索到，再由模型自主回答或说明资料中没有找到。

这样不依赖固定关键词，泛化能力更好。

## 6. HyDE 检索

### 6.1 HyDE 是什么？

HyDE 全称是 Hypothetical Document Embeddings，意思是“假设性文档嵌入”。

它的核心思想是：用户的问题可能很短，不适合直接做向量检索。于是先让大模型根据问题写一段“可能包含答案的假设文档”，再用这段文本去检索。

例如用户问：

```text
我喜欢什么动物？
```

原始问题很短，直接向量检索可能不稳定。

HyDE 会生成类似：

```text
用户的个人偏好资料中可能记录了喜欢的动物，例如狗、猫等。
```

再用这段更丰富的文本去检索，更容易匹配到知识库中“喜欢小狗”这样的内容。

### 6.2 HyDE 在项目中怎么调用？

在本项目中，HyDE 通常发生在 RAG 服务里：

1. 接收用户原始问题。
2. 调用 LLM 生成假设性文档。
3. 使用原始问题进行一次检索。
4. 使用 HyDE 文档再进行一次检索。
5. 合并两路结果。
6. 去重、排序、注入 Prompt。

项目中相关文件主要是：

```text
backend/app/rag/rag_service.py
backend/app/agent/agent.py
```

### 6.3 原始问题检索 + HyDE 检索双路合并后，HyDE 还有作用吗？

有作用。

原始问题检索擅长匹配用户直接说出的关键词；HyDE 检索擅长补全短问题背后的语义。

两者互补：

- 原始问题能保留用户真实意图。
- HyDE 能扩大语义召回。
- 双路合并能降低单一路径检索失败的概率。

特别是“我是谁”“我喜欢什么”“这个项目怎么部署”这类短问题，HyDE 的作用比较明显。

### 6.4 为什么 HyDE 文档太长会导致很慢？

HyDE 太长会带来三个问题：

1. 生成 HyDE 本身耗时更久。
2. 长 HyDE 文档向量化更慢。
3. 检索结果更泛，可能召回很多无关文档。

优化方式：

- 限制 HyDE 输出长度。
- 设置 HyDE 超时时间。
- 减少 HyDE 检索 top_k。
- 对简单问题使用更短的 HyDE Prompt。
- 检索后优先使用原文片段，不一定每次都让 LLM 总结。

## 7. 多线程、异步与记忆

### 7.1 项目里哪里用到了多线程？

项目主要是异步编程为主，同时在一些阻塞任务上使用线程。

典型场景：

```python
await asyncio.to_thread(...)
```

作用是把阻塞型函数放到线程池里执行，避免卡住 FastAPI 的事件循环。

适合放到线程里的任务包括：

- 模型初始化。
- 本地向量模型加载。
- 文档解析。
- CPU 密集或阻塞型库调用。

### 7.2 为什么要用多线程或 asyncio.to_thread？

FastAPI 是异步 Web 框架，如果在主事件循环里直接执行耗时任务，会导致其他请求也被卡住。

例如模型加载可能要几秒甚至几十秒，如果不丢到后台线程，服务启动或请求处理期间会阻塞。

使用 `asyncio.to_thread` 可以让耗时任务在后台线程执行，主事件循环继续处理其他请求。

### 7.3 长期记忆和短期记忆分别怎么实现？

短期记忆：

- 当前会话的聊天历史。
- 存在 MySQL 的 chat history 表中。
- 每次用户继续对话时读取当前 session 的历史消息。

长期记忆：

- 用户上传的知识库文档。
- 用户写过的笔记。
- 文档和笔记经过切片、向量化后进入 ChromaDB。
- 提问时通过 RAG 检索召回。

简单理解：

- 短期记忆解决“刚刚聊了什么”。
- 长期记忆解决“用户资料和知识库里有什么”。

## 8. Prompt 管理

### 8.1 项目里的 Prompt 都在哪里？

主要在：

```text
backend/app/prompt/
```

常见文件：

```text
main_prompt.txt                 # Agent 主提示词
write_assistant_prompt.txt      # 写作助手提示词
autocomplete_prompt.txt         # 自动补全提示词
auto_tag_prompt.txt             # 自动标签提示词
rag_summarize.txt               # RAG 摘要提示词
reorder_prompt.txt              # 重排序提示词
review_question_prompt.txt      # 每日回顾问题生成提示词
report_prompt.txt               # 报告生成提示词
```

Prompt 配置还可能出现在：

```text
backend/app/config/prompt.yaml
backend/app/utils/prompt_loader.py
```

`prompt_loader.py` 负责读取和加载 prompt 文件。

## 9. 前后端数据交互

### 9.1 登录是怎么用 JavaScript 实现前后端交互的？

大致流程：

1. 用户在 Vue 登录页面输入账号密码。
2. 前端使用 Axios 发送 POST 请求到 Django 用户服务。
3. Django 验证账号密码。
4. 验证成功后返回 JWT token。
5. 前端保存 token。
6. 后续请求在请求头中携带：

```http
Authorization: Bearer token
```

7. 后端通过 token 识别当前用户。

### 9.2 数据查询是怎么交互的？

例如查询笔记列表：

1. 前端页面加载时调用接口。
2. Axios 发起 GET 请求。
3. 请求头携带 JWT。
4. 后端根据用户 ID 查询数据库。
5. 返回 JSON 数据。
6. Vue 把 JSON 渲染成页面。

### 9.3 AI 流式回答是怎么交互的？

AI 聊天使用 SSE 流式返回。

流程：

1. 前端发送问题。
2. FastAPI 返回 `text/event-stream`。
3. 后端边生成边推送 token 或事件。
4. 前端不断接收 chunk。
5. 页面实时拼接显示回答。

这种方式比等完整回答生成后再返回体验更好。

## 10. 登录、安全与跨域

### 10.1 为什么推荐 HttpOnly Cookie + SameSite + Secure？

因为它比把 token 放在 localStorage 更安全。

localStorage：

- JavaScript 可以读取。
- 如果发生 XSS，攻击者可以直接偷 token。
- 实现简单，但安全性较弱。

HttpOnly Cookie：

- JavaScript 读不到。
- 可以降低 XSS 偷 token 的风险。
- 浏览器会自动携带 Cookie。

SameSite：

- 限制跨站请求携带 Cookie。
- 可以降低 CSRF 风险。

Secure：

- 只允许 HTTPS 下传输 Cookie。
- 避免明文传输。

如果是学习项目，localStorage 简单可用；如果上线部署，更推荐 HttpOnly Cookie。

### 10.2 CORS 是什么？

CORS 是浏览器的跨域资源共享机制。

当前端地址和后端地址不同源时，就会发生跨域。

例如：

```text
前端：http://127.0.0.1:3000
后端：http://127.0.0.1:8000
```

端口不同，也算跨域。

后端需要允许前端来源，否则浏览器会拦截请求。

### 10.3 CSRF 是什么？

CSRF 是跨站请求伪造。

攻击者诱导用户访问恶意网站，恶意网站利用用户浏览器自动携带 Cookie 的特性，向目标网站发起请求。

防护方式：

- SameSite Cookie。
- CSRF Token。
- 重要操作检查请求来源。

### 10.4 XSS 是什么？

XSS 是跨站脚本攻击。

攻击者把恶意 JavaScript 注入页面，让浏览器执行。

危害：

- 偷 localStorage token。
- 冒充用户发请求。
- 篡改页面内容。

防护方式：

- 不直接渲染不可信 HTML。
- 对 Markdown/HTML 做 sanitize。
- 使用 HttpOnly Cookie。
- 设置 CSP。

## 11. 向量切片、维度与 MD5

### 11.1 向量切片是怎么做的？

文档上传后，不会整篇直接向量化，而是先切成多个小片段。

原因：

- 大模型和向量模型都有长度限制。
- 小片段更容易精准召回。
- 回答时只需要注入相关片段，减少 token。

切片一般会使用：

```text
chunk_size
chunk_overlap
separators
```

例如：

- `chunk_size`：每片最大长度。
- `chunk_overlap`：相邻切片重叠部分，避免语义被切断。
- `separators`：优先按段落、换行、句号等切分。

### 11.2 向量维度是怎么匹配的？

向量维度由 Embedding 模型决定。

例如：

- 模型 A 输出 768 维。
- 模型 B 输出 1024 维。

一个 ChromaDB collection 里不能混用不同维度的向量。

所以必须保证：

```text
文档入库时的 Embedding 模型 == 查询时的 Embedding 模型
```

如果换了 Embedding 模型，建议重建向量库。

### 11.3 MD5 是什么？

MD5 是一种哈希算法，可以把任意文件内容计算成一个固定长度的字符串。

它常用于：

- 判断文件是否重复。
- 判断文件内容是否发生变化。
- 做简单的文件指纹。

在本项目中，MD5 可用于文档去重：如果同一个文件已经上传并入库，就不重复处理。

注意：MD5 不适合安全加密密码，但适合做文件去重标识。

## 12. PDF 处理

### 12.1 项目怎么处理 PDF 文件？

一般流程：

1. 用户上传 PDF。
2. 后端保存文件。
3. 解析 PDF 文本。
4. 如果包含图片或扫描页，可能走多模态或 OCR 处理。
5. 提取出的文本进入切片流程。
6. 切片生成向量。
7. 写入 ChromaDB。
8. 用户提问时检索相关片段。

相关能力通常分布在：

```text
backend/app/rag/document_handler/
backend/app/utils/pdf_multimodal_loader.py
backend/app/utils/image_extractor.py
backend/app/utils/vision_service.py
```

### 12.2 为什么分普通 PDF 和多模态 PDF？

普通 PDF：

- PDF 内部有可复制文本。
- 可以直接提取文字。
- 处理快、成本低。

多模态 PDF：

- 包含图片、图表、扫描页。
- 纯文本提取可能拿不到关键信息。
- 需要 OCR 或视觉模型理解图片内容。

区分两者是为了节省成本和提高效果：能直接提取文本就不要走视觉模型；文本不足时再用 OCR/多模态。

### 12.3 怎么判断是哪种 PDF？

可以结合以下指标：

1. 每页能否提取到文本。
2. 每页是否包含图片。
3. 图片面积是否接近整页。
4. 是否存在大量矢量图形。
5. 提取文本长度是否过短。

简单规则：

- 文本充足：普通 PDF。
- 几乎没文字，但每页有大图：扫描版 PDF。
- 有文字也有大量图片/图表：多模态 PDF。

### 12.4 怎么判断 PDF 有没有图片？

可以用 PyMuPDF：

```python
import fitz

doc = fitz.open("file.pdf")
for page in doc:
    images = page.get_images(full=True)
    if images:
        print("该页包含图片")
```

`get_images(full=True)` 可以检测 PDF 页面中嵌入的位图图片。

### 12.5 是否有图片是调用函数判断的吗？

是的，通常是调用 PDF 解析库提供的函数判断。

例如 PyMuPDF 的：

```python
page.get_images(full=True)
```

它能检测页面中嵌入的图片对象。

### 12.6 图形也能判断出来吗？

可以，但不能只靠 `get_images()`。

PDF 里的图形可能不是图片，而是矢量绘图，例如：

- 线条。
- 矩形。
- 曲线。
- 表格边框。
- 图表形状。

这种内容通常要用：

```python
page.get_drawings()
```

判断是否存在大量矢量绘图对象。

如果页面文本很少，但有大量 drawings，可以认为它可能包含图表或复杂版式，需要更强的解析策略。

### 12.7 扫描版 PDF 整页是一张大图片，这种能不能优化？

可以优化。

扫描版 PDF 的典型特征：

- 每页文本几乎为空。
- 每页有一张接近整页大小的大图片。

优化思路：

1. 检测整页大图。
2. 如果是扫描页，优先走 OCR。
3. OCR 结果再进入切片和向量化。
4. 如果 OCR 文本质量差，再调用视觉模型做图片理解。

这样比所有 PDF 都走多模态更省资源。

## 13. 部署与服务器配置

### 13.1 阿里云服务器买什么配置比较合适？

如果只是学习、演示、小规模使用：

- 2 vCPU / 4 GiB 内存起步。
- 系统盘 40 GiB 以上。
- 带宽 3M 起步。

如果要在服务器上跑本地向量模型：

- 建议 4 vCPU / 8 GiB 以上。
- 如果模型较大或并发较高，建议更高配置。

如果只调用在线 LLM 和在线 Embedding：

- 2 vCPU / 2 GiB 可以勉强跑。
- 但 MySQL、Redis、Django、FastAPI、前端、文档解析一起跑时会比较紧张。

### 13.2 2vCPU 2GiB 经济型 e 可以吗？

可以跑最小演示，但不推荐作为流畅配置。

问题：

- 内存只有 2GiB，Docker 多容器容易吃紧。
- 本地向量模型可能加载失败或很慢。
- 文档解析、PDF 处理、向量化容易卡。

适合：

- 前端。
- Django。
- FastAPI。
- MySQL/Redis 小数据。
- 在线模型 API。

不适合：

- 本地大模型。
- 本地 reranker。
- 大量文档解析。
- 多用户并发。

建议云服务器使用在线 Embedding，或者把向量模型放在本地机器。

### 13.3 可以在本地跑向量模型，然后传到服务器上吗？

可以，但要区分两种情况。

方式一：本地生成向量库，再上传 ChromaDB 数据目录到服务器。

适合静态知识库，缺点是服务器新增文档时仍然需要向量模型。

方式二：服务器通过内网穿透调用本地 Embedding 服务。

适合服务器配置低、本地机器有 GPU 的场景。

缺点：

- 本地电脑必须开机。
- 网络延迟会影响检索。
- 内网穿透要注意安全。

### 13.4 内网穿透是什么意思？

内网穿透是让外网或云服务器访问你本地电脑服务的一种方式。

例如你的本地电脑运行了 Embedding 服务：

```text
http://127.0.0.1:9000
```

云服务器默认访问不到。通过内网穿透，可以让云服务器通过一个公网地址或虚拟内网地址访问它。

常见方案：

- frp。
- Tailscale。
- ZeroTier。
- ngrok。

### 13.5 frp 是什么？

frp 是一个高性能反向代理工具，常用于内网穿透。

结构：

- 云服务器运行 frps。
- 本地电脑运行 frpc。
- frpc 主动连接 frps。
- 外部请求通过云服务器转发到本地服务。

优点：

- 灵活。
- 性能较好。
- 可以暴露 HTTP/TCP 服务。
- 适合有公网服务器的人。

缺点：

- 需要自己配置服务端和客户端。
- 暴露端口要注意安全。
- 维护成本比 Tailscale 高。

### 13.6 Tailscale 是什么？

Tailscale 是基于 WireGuard 的虚拟组网工具。

安装后，本地电脑和云服务器会像在同一个内网里一样互相访问。

优点：

- 配置简单。
- 安全性较好。
- 不需要手动开放公网端口。
- 很适合个人开发和小团队。

缺点：

- 依赖 Tailscale 账号和服务。
- 对公开访问的 Web 服务不如 frp 直观。
- 免费版有设备数量和功能限制。

### 13.7 frp 和 Tailscale 怎么选？

如果只是让云服务器访问你本地向量模型，推荐 Tailscale，简单安全。

如果你希望把本地服务公开给任意用户访问，可以考虑 frp，但要做好鉴权和防火墙。

## 14. 前端开发排错

### 14.1 Vite 启动时报 ENOSPC 是什么原因？

错误：

```text
ENOSPC: System limit for number of file watchers reached
```

意思是系统允许监听的文件数量不够了。

Vite 开发服务器需要监听很多文件变化，当系统 watcher 限制太低时会报错。

临时解决：

```bash
sudo sysctl fs.inotify.max_user_watches=524288
sudo sysctl fs.inotify.max_user_instances=1024
```

永久解决：

```bash
echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf
echo fs.inotify.max_user_instances=1024 | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

然后重新启动：

```bash
npm run dev -- --host 127.0.0.1 --port 3000
```

## 15. Docker 部署与排错

### 15.1 从安装 Docker 开始，部署项目的大致步骤是什么？

步骤：

1. 安装 Docker。
2. 验证 Docker：

```bash
docker ps
docker run hello-world
```

3. 准备 `.env.docker`：

```bash
cp backend/.env backend/.env.docker
cp DjangoUserService/.env DjangoUserService/.env.docker
```

4. 修改 Docker 环境变量中的服务地址：

```env
MYSQL_HOST=mysql
REDIS_HOST=redis
DJANGO_API_URL=http://django:8001
```

5. 准备 Dockerfile、docker-compose.yml、nginx.conf。
6. 构建镜像：

```bash
docker compose build
```

7. 启动服务：

```bash
docker compose up -d
```

8. 查看状态：

```bash
docker compose ps
docker compose logs -f backend
```

### 15.2 docker run hello-world 拉取超时是什么原因？

错误：

```text
failed to resolve reference docker.io/library/hello-world:latest
i/o timeout
```

说明 Docker 访问 Docker Hub 超时，常见原因是网络慢或 Docker Hub 访问不稳定。

可以配置 Docker 镜像加速源，或者在网络环境较好的情况下重试。

### 15.3 docker ps 权限不足怎么办？

错误：

```text
permission denied while trying to connect to the docker API
```

说明当前用户没有访问 Docker Socket 的权限。

解决：

```bash
sudo usermod -aG docker $USER
```

然后需要重新登录终端，或者重启系统。

如果 `newgrp docker` 不存在，可以安装：

```bash
sudo apt install util-linux-extra
```

也可以直接重新打开终端。

### 15.4 为什么 nano backend/Dockerfile 提示它是目录？

如果 `nano backend/Dockerfile` 提示：

```text
"backend/Dockerfile" 是一个目录
```

说明之前误创建了一个名为 `Dockerfile` 的目录。

可以检查：

```bash
ls -ld backend/Dockerfile
```

如果确实是目录，删除空目录：

```bash
rmdir backend/Dockerfile
```

然后重新创建文件：

```bash
nano backend/Dockerfile
```

### 15.5 docker compose build 报 exclude pattern 语法错误是什么原因？

错误：

```text
failed to match excludepatterns: syntax error in pattern
```

通常是 `.dockerignore` 中写了 Windows 路径，例如：

```text
D:\Hugging_Face\models\...
```

Docker ignore pattern 不支持这种写法。

应该改成更安全的形式：

```text
.venv
__pycache__
*.pyc
.env
.env.docker
data
logs
```

如果要忽略误放进项目里的 Windows 路径目录，可以写：

```text
D:*
```

### 15.6 Docker 构建时 unexpected EOF 是什么原因？

错误：

```text
short read
unexpected EOF
```

一般表示镜像层下载不完整或网络中断。

解决方式：

- 重新执行构建。
- 配置镜像源。
- 清理失败缓存后再构建。

可以尝试：

```bash
docker compose build --no-cache
```

### 15.7 可以把 Docker 构建源改成清华源吗？

可以分两类：

1. Python 包源。

Dockerfile 中可以设置：

```dockerfile
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple uv
```

2. apt 源。

Debian slim 镜像可以把 apt 源替换为清华源，再执行 `apt-get update`。

这样能加快 apt 包安装速度。

### 15.8 Docker 构建时 apt-get install 是在下载什么？

例如：

```text
RUN apt-get update && apt-get install -y ...
```

它是在给镜像安装系统依赖。

本项目可能需要：

- `build-essential`：编译 Python 包。
- `curl`：下载工具。
- `libmagic1`：文件类型识别。
- `poppler-utils`：PDF 处理。
- `tesseract-ocr`：OCR。
- `libgl1`、`libglib2.0-0`：图像/视觉库依赖。
- `default-libmysqlclient-dev`、`pkg-config`：Django MySQL 依赖。

这些不是 Python 包，是 Linux 系统包。

### 15.9 docker compose build --no-cache 有什么用？

`--no-cache` 表示不使用 Docker 之前构建留下的缓存，所有步骤重新执行。

适合：

- 上次构建失败，缓存可能损坏。
- Dockerfile 改了但没有生效。
- 依赖源改了，需要重新下载。
- 想确认镜像是从干净状态构建的。

缺点：

- 会更慢。
- 会重新下载依赖。

平时不需要每次都加，只有排错时使用。

### 15.10 Redis 端口 6379 被占用怎么办？

错误：

```text
failed to bind host port 0.0.0.0:6379/tcp: address already in use
```

说明宿主机已经有 Redis 在使用 6379 端口。

Docker Compose 里的后端服务访问 Redis 时使用的是容器名：

```text
redis:6379
```

所以通常不需要把 Redis 端口暴露到宿主机。

解决方式：删除 `docker-compose.yml` 中 Redis 的端口映射：

```yaml
redis:
  image: redis:7-alpine
  container_name: rag-redis
  restart: unless-stopped
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

然后重新启动：

```bash
docker compose down
docker compose up -d mysql redis
```

如果 MySQL 的 3306 端口也被占用，同理可以移除 MySQL 的 `ports` 映射。

## 16. 项目可优化方向

### 16.1 RAG 性能优化

可以优化：

- HyDE 输出长度限制。
- 原始问题检索 + HyDE 检索双路合并。
- 减少摘要阶段的 LLM 调用。
- 对检索片段直接拼接，简单问题不做二次总结。
- 调整 BM25 和向量检索权重。
- 控制 top_k，避免召回太多无关文档。

### 16.2 稳定性优化

可以优化：

- OpenAI 中转站请求增加重试。
- 上游不可用时返回友好错误。
- 模型初始化失败时不影响基础服务启动。
- Docker Compose 增加 healthcheck。
- Django 等待 MySQL 就绪后再 migrate。

### 16.3 安全优化

可以优化：

- token 从 localStorage 改为 HttpOnly Cookie。
- 增加 CSRF 防护。
- 限制 CORS 来源。
- `.env` 和 `.env.docker` 不提交 Git。
- 上传文件类型和大小限制。

### 16.4 部署优化

可以优化：

- 前端静态文件用 Nginx。
- MySQL/Redis 不暴露公网端口。
- 本地模型目录用 volume 挂载，不打进镜像。
- 低配服务器关闭 reranker 和视觉模型。
- 日志目录挂载出来，方便排查。

## 17. harness 是什么？项目里有用到吗？

harness 通常指测试框架、评测框架或任务编排框架。

在当前项目里，没有看到专门叫 harness 的模块或框架。

项目主要使用的是：

- FastAPI 处理 AI 服务。
- Django 处理用户服务。
- LangChain 处理模型和 Agent。
- ChromaDB 处理向量库。
- Docker Compose 处理服务编排。

如果以后要做 RAG 自动评测，可以引入类似 RAGAS、LangSmith evaluation 或自定义 test harness。

## 18. 总结

这个项目的核心是一个“用户隔离的个人知识库 AI 助手”。它不是单纯调用大模型聊天，而是把用户上传的资料、个人笔记、会话历史和检索增强结合起来。

项目重点可以概括为：

- 前端负责交互。
- Django 负责用户和文件。
- FastAPI 负责 AI、RAG 和 Agent。
- MySQL 保存结构化数据。
- Redis 支撑缓存和异步任务。
- ChromaDB 保存向量数据。
- Embedding 模型决定检索质量。
- Prompt 和检索策略决定回答是否可靠。
- Docker 部署解决服务编排和环境一致性。
