# RAGFlow + FastGPT 代码开发说明

## 1. 开发目标

本实现采用「FastGPT + 适配器服务 + RAGFlow」三层结构。FastGPT 专注流程编排和客户经理交互；RAGFlow 专注文档解析、知识库管理和检索；适配器服务负责把客户数据 API 与 RAGFlow 检索结果标准化，降低 FastGPT 工作流复杂度。

## 2. 代码结构

```text
digital-customer-agent/
  adapter/
    app/
      config.py            # 环境变量配置
      customer_client.py   # 客户数据 API 客户端
      ragflow_client.py    # RAGFlow 检索 API 客户端
      models.py            # 请求、响应、引用数据模型
      main.py              # FastAPI 服务入口
    Dockerfile
    requirements.txt
    .env.example
  docs/
    architecture.md
    development.md
    deployment.md
  deploy/
    adapter/docker-compose.yml
    fastgpt/fastgpt-workflow.md
    ragflow/ragflow-kb-plan.md
```

## 3. 适配器 API 设计

### 3.1 健康检查

```http
GET /health
```

返回：

```json
{
  "status": "ok",
  "service": "digital-customer-agent-adapter"
}
```

### 3.2 获取客户风险营销上下文

```http
POST /api/v1/customer-risk-context
Content-Type: application/json

{
  "customer_id": "CUST_10086",
  "customer_name": "华东XX纺织有限公司",
  "question": "请给出该客户的风险营销建议"
}
```

返回：

```json
{
  "status": "ok",
  "message": "已生成客户数据与知识库引用上下文。",
  "customer_profile": {},
  "retrieval_queries": [],
  "citations": [],
  "prompt_context": ""
}
```

## 4. 状态码与业务状态

| HTTP 状态 | 业务状态 | 含义 | FastGPT 处理建议 |
| --- | --- | --- | --- |
| 200 | `ok` | 客户数据和知识库引用均已返回 | 进入最终回答节点 |
| 200 | `missing_industry` | 客户 API 未返回行业编码或名称 | 提示补充行业字段，不生成行业化建议 |
| 200 | `no_evidence` | RAGFlow 未检索到足够依据 | 提示依据不足，不输出确定结论 |
| 400 | - | 请求缺少客户号或客户名称 | 提示客户经理补充客户信息 |
| 5xx | - | 内部系统异常 | 提示稍后重试并记录告警 |

## 5. 客户数据 API 对接

适配器默认调用：

```http
GET {CUSTOMER_API_BASE_URL}/api/v1/customer/profile?customer_id={customer_id}&customer_name={customer_name}
```

如果企业内部客户 API 路径不同，只需修改 `adapter/app/customer_client.py`。

客户 API 必须返回：

- `basic_info.industry_code`；
- `basic_info.industry_name`；
- `basic_info.industry_tags`；
- `quant_profile.risk_level`；
- `risk_tags`；
- `marketing_tags`。

其中行业编码和行业名称是强制字段。缺失时适配器返回 `missing_industry`。

## 6. RAGFlow 检索对接

适配器默认调用 RAGFlow HTTP API：

```http
POST {RAGFLOW_BASE_URL}/api/v1/retrieval
Authorization: Bearer {RAGFLOW_API_KEY}
Content-Type: application/json
```

请求体示例：

```json
{
  "question": "纺织业 传统制造业 出口敏感 行业特征 授信策略 风险特征 营销策略",
  "dataset_ids": ["industry_policy_dataset", "risk_policy_dataset"],
  "top_k": 8,
  "similarity_threshold": 0.2
}
```

适配器会把 RAGFlow 返回的 chunk 标准化为：

```json
{
  "content": "引用片段内容",
  "score": 0.86,
  "dataset_id": "industry_policy_dataset",
  "document_id": "doc_001",
  "document_name": "纺织业授信策略2026",
  "page": 12,
  "section": "第4.2节",
  "location": "第12页 第4.2节",
  "source_url": ""
}
```

## 7. 检索 Query 生成策略

适配器会基于客户 API 字段生成三类检索 query：

1. 行业策略 query：行业名称、行业标签、行业特征、行业周期、授信策略；
2. 风控政策 query：风险等级、风险标签、授信准入、司法风险、征信风险、担保风险；
3. 营销产品 query：营销标签、风险等级、结算、票据、供应链金融、现金管理、合规话术。

该策略位于 `adapter/app/ragflow_client.py` 的 `build_retrieval_queries` 函数。

## 8. FastGPT 最终 Prompt 模板

FastGPT 的最终 AI 节点建议使用以下系统提示词：

```text
你是企业数字客户智能体，负责根据客户数据 API、知识库引用和风控营销规则，为客户经理生成风险营销建议。

重要规则：
1. 不允许自行识别或猜测客户行业。
2. 客户行业必须以客户数据 API 返回的 industry_code、industry_name、industry_tags 为准。
3. 如果 API 未返回行业信息，应提示客户行业信息缺失，不得自行推断。
4. 所有风险判断和营销建议必须基于客户 API 数据、RAGFlow 检索内容、风控政策和营销产品规则。
5. 对关键结论必须提供引用依据。
6. 如果知识库未检索到依据，应明确说明依据不足，不得编造政策或行业结论。
7. 不得承诺授信额度、审批结果、收益率或营销成功率。
8. 最终授信、准入、压降、退出等决策应以风控审批系统为准。
```

用户上下文输入：

```text
{{adapter_response.prompt_context}}

请输出：
1. 客户基本判断；
2. 行业特点；
3. 风险等级和风险原因；
4. 建议营销产品；
5. 不建议动作；
6. 客户经理行动清单；
7. 合规话术；
8. 引用依据。
```

## 9. 本地开发

```bash
cd digital-customer-agent/adapter
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

健康检查：

```bash
curl http://localhost:8080/health
```

## 10. 单元级检查

当前示例代码未绑定真实企业 API，可先做语法和容器构建检查：

```bash
python -m py_compile app/*.py
```

生产接入后建议补充：

- 客户 API mock 测试；
- RAGFlow 检索 mock 测试；
- FastGPT 工作流回归测试；
- 高风险客户提示词安全测试；
- 引用缺失和行业缺失兜底测试。
