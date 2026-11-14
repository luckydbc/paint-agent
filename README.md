# 打印店自然语言接单 Agent

用户用自然语言描述打印/排版/装订需求，系统准确提取参数、保留原文证据、对缺失/冲突/歧义进行追问，用确定性代码计费并独立复核，输出可逐项核对的报价单。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

在项目根目录的 `.env` 中配置 DeepSeek API Key 和 API 地址：

```dotenv
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

`.env` 已加入 `.gitignore`，不要提交真实 API Key。

## 运行测试

```bash
python -m pytest -q
```

单测覆盖纯逻辑（计费、校验、证据规则），不依赖 API key 与 LLM。

## 配置（config.json）

```json
{
  "model": "deepseek-chat",
  "temperature": 0,
  "prices": {
    "typesetting_per_source_page": 3.0,
    "printing_per_page": 0.5,
    "binding_per_volume": 20.0
  },
  "defaults": {
    "default_needs_layout": false,
    "default_needs_binding": false
  },
  "rules": {
    "evidence_critic_enabled": true,
    "max_clarify_rounds": 5
  }
}
```

- `prices`：价目，可配置。
- `defaults`：未提及排版/装订时的默认值；默认值会被记录为 `default` 来源并在报价单中显式标注。
- `rules.evidence_critic_enabled`：是否启用 LLM 证据复核（对照原文查遗漏/幻觉/错配/冲突/否定/指代）。
- `rules.max_clarify_rounds`：最多追问轮数。

## 架构

9 节点 LangGraph 工作流，LLM 只负责理解/提取/追问，其余全部由确定性代码完成：

```
parse_intent → extract_parameters → validate_schema → validate_evidence
  → validate_business_rules ─(ok)→ calculate_quote → validate_quote → render_result
                            └(有问题)→ clarify_order → interrupt → 恢复后回到 extract_parameters
```

模块职责见 `agent/` 下各文件：`schemas.py`（值+状态分离、证据字段）、`prompts.py`（含 5 样例 few-shot）、`extractor.py`（LLM 调用）、`validator.py`（确定性校验+默认值）、`pricing.py`（计费+独立复核）、`quotation.py`（渲染）、`clarify.py`（interrupt 追问）、`graph.py`（组装）。

## 已知限制

- 报价完成后再修改订单（“改成 3 份”）当前会作为新订单处理，多轮修改的增量合并留作后续增强。
- 澄清恢复采用「重跑 extract + 全量重校验」，不增量改单字段（更稳健）。
- 状态持久化当前用 `MemorySaver`（进程内）；生产可换 `SqliteSaver` 实现跨重启持久化。
