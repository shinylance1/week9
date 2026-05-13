# RAGFlow + FastGPT 部署运维文档

## 1. 部署目标

在企业内网部署 RAGFlow + FastGPT + 数字客户智能体适配器，支持客户经理基于客户数据和知识库引用获取风险营销建议。部署应满足私有化、可审计、可扩展、低运维成本和高并发调优要求。

## 2. 推荐部署拓扑

```text
内网访问层
  ├─ Nginx / API Gateway
  └─ SSO / 统一认证，可选

应用层
  ├─ FastGPT
  ├─ digital-customer-agent-adapter
  └─ RAGFlow

模型层
  ├─ LLM 服务：vLLM / Ollama / Xinference
  ├─ Embedding 服务
  └─ Rerank 服务

数据层
  ├─ FastGPT 数据库与向量库
  ├─ RAGFlow 数据库、对象存储、搜索/向量组件
  ├─ Redis / Mongo / PostgreSQL，按官方 compose 配置
  └─ MinIO / 企业对象存储

业务系统
  ├─ 客户数据 API
  ├─ CRM
  ├─ 司法数据
  ├─ 征信数据
  ├─ 风控评分
  └─ 营销产品目录
```

## 3. 主机建议

### 3.1 PoC 环境

| 组件 | 建议配置 |
| --- | --- |
| FastGPT | 4C / 16G / 200G |
| RAGFlow | 8C / 32G / 500G，复杂 PDF 较多时提高磁盘和内存 |
| 模型服务 | 1 张 24G 以上 GPU，或调用已有内网模型平台 |
| 适配器 | 2C / 4G |

### 3.2 生产环境

| 组件 | 建议配置 |
| --- | --- |
| FastGPT | 至少 2 副本，独立数据库和向量库 |
| RAGFlow | 独立部署，文档解析任务与在线检索分开规划资源 |
| 模型服务 | vLLM 多副本，按并发和模型大小规划 GPU |
| 适配器 | 至少 2 副本，网关负载均衡 |
| 数据库 | 主备或集群，高可用备份 |
| 监控 | Prometheus + Grafana + Loki / ELK |

## 4. 部署步骤

### 4.1 部署 RAGFlow

1. 参考 RAGFlow 官方 Docker Compose 文档准备配置。
2. 配置内网模型服务地址，包括 LLM、Embedding 和 Rerank。
3. 创建知识库：行业策略库、风控政策库、营销产品库、合规话术库、司法风险规则库、征信解读库。
4. 导入文档，确认文档解析、切片和页码/章节元数据可用。
5. 创建 RAGFlow API Key。
6. 记录 dataset ids，配置到适配器 `RAGFLOW_DATASET_IDS`。

RAGFlow HTTP API 参考：https://ragflow.com.cn/docs/http_api_reference

### 4.2 部署 FastGPT

1. 参考 FastGPT 官方 Docker Compose 部署文档获取配置文件。
2. 配置模型供应商，可指向本地模型网关或 vLLM / Ollama / Xinference。
3. 配置数据库、向量库、对象存储和必要密钥。
4. 创建数字客户智能体应用。
5. 在工作流中增加 HTTP 节点，调用适配器服务。
6. 配置最终 AI 节点 Prompt 和引用展示格式。

FastGPT Docker Compose 部署参考：https://doc.fastgpt.io/en/docs/self-host/deploy/docker

FastGPT 环境变量参考：https://doc.fastgpt.io/en/self-host/config/env

### 4.3 部署适配器服务

```bash
cd digital-customer-agent/deploy/adapter
cp ../../adapter/.env.example .env
vi .env
docker compose up -d --build
```

健康检查：

```bash
curl http://localhost:8080/health
```

### 4.4 FastGPT HTTP 节点配置

请求方式：

```http
POST http://digital-customer-agent-adapter:8080/api/v1/customer-risk-context
Content-Type: application/json
```

请求体：

```json
{
  "customer_id": "{{customer_id}}",
  "customer_name": "{{customer_name}}",
  "question": "{{user_question}}"
}
```

条件分支：

- `status == ok`：进入最终 AI 节点；
- `status == missing_industry`：提示客户行业缺失；
- `status == no_evidence`：提示知识库依据不足；
- HTTP 异常：提示系统繁忙并记录日志。

## 5. 知识库上线清单

上线前至少准备以下文档：

- 重点行业授信策略；
- 重点行业营销策略；
- 风控准入和压降规则；
- 对外担保、司法涉诉、征信异常处理规则；
- 供应链金融、票据、结算、现金管理产品手册；
- 合规话术和禁止承诺清单；
- 典型风险案例和成功营销案例。

每份文档建议补充元数据：

```text
业务线、行业编码、行业名称、风险等级、产品类型、生效日期、失效日期、版本号、审批状态、适用区域。
```

## 6. 高并发调优建议

### 6.1 FastGPT

根据官方环境变量文档，重点关注：

- `DB_MAX_LINK`：数据库连接池；
- `WORKFLOW_PARALLEL_MAX_CONCURRENCY`：工作流并发节点限制；
- 模型供应商连接池和超时；
- 文件和对象存储访问延迟。

### 6.2 RAGFlow

重点关注：

- 文档解析任务与在线检索任务隔离；
- 检索 TopK 不宜过大，建议 5 到 12；
- Embedding 和 Rerank 服务独立部署；
- 大规模知识库按行业、业务线、区域拆分 dataset；
- 对常见行业策略和产品规则设置缓存。

### 6.3 适配器服务

建议：

- 至少 2 副本；
- 配置 API Gateway 超时和重试；
- 客户数据 API 设置短缓存，避免频繁访问核心系统；
- 对 RAGFlow 检索结果按 `customer_id + policy_version + query_hash` 做短 TTL 缓存；
- 所有请求记录 trace id。

## 7. 安全与合规

- FastGPT、RAGFlow、适配器全部部署在内网；
- 客户数据 API、RAGFlow API Key 使用网关密钥或 Vault 管理；
- 禁止在日志中打印完整征信原文、身份证号、手机号等敏感字段；
- 输出中不得承诺审批结果、固定额度、收益率；
- 所有模型输入输出必须审计留痕；
- 高风险客户建议必须带人工复核标记。

## 8. 验收测试

建议准备 30 到 100 个客户样本，覆盖：

- 行业较好、客户风险低；
- 行业夕阳、客户风险高；
- 行业较好但征信异常；
- 行业一般但结算价值高；
- 司法涉诉多但无被执行；
- 对外担保偏高；
- 行业字段缺失；
- 知识库无依据。

验收指标：

- 行业完全以 API 字段为准；
- 风险建议引用准确率；
- 无依据拒答率；
- 高风险客户激进营销拦截率；
- 客户经理采纳率；
- 平均响应时间；
- 并发下错误率。
