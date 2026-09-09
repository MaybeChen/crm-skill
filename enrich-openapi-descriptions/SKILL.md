---
name: enrich-openapi-descriptions
description: Enrich Swagger/OpenAPI YAML by locating missing service, operation/method, parameter, response, schema, and field descriptions, grounding additions in supplied Excel, Word, PDF, or other business documents, and applying defined context-based fallbacks when documentation has no match. Use when an agent with computer-use capabilities must reconcile API specifications with one or many source documents, especially when the documents are long, search-heavy, or cannot be loaded into context at once, while preserving YAML structure and distinguishing sourced text from inference.
---

# Enrich OpenAPI Descriptions

补全 YAML 中缺失的描述，同时保持原有接口契约不变。优先使用文档；确认文档无对应说明后，才按本 skill 的回退规则推断。

## 工作原则

- 只修改描述性键，除非用户明确要求修正契约。不得改动路径、方法、字段名、类型、必填项、引用、枚举或示例。
- 优先补全现有空值（`description: ""`、`description:`、`x-description-zh: ""`）；仅在目标对象完全缺少描述键且用户要求覆盖该类对象时新增键。
- 沿 `$ref` 解析字段归属。请求/响应包装层、业务对象和复用 definition 必须分别处理。
- 文档命中项必须可追溯到文档位置。文档未命中项必须标记为“推断”，并严格采用下述回退规则，不能伪装成文档原文。
- 保留原 YAML 的格式、引号、键顺序、注释、换行符和编码；优先做最小文本编辑。
- 默认沿用 YAML 已有描述的语言、术语、句式和详细程度。`x-description-zh` 写中文；`description` 沿用相邻内容的主语言。

## 流程

### 1. 盘点输入与目标

1. 找到 YAML 和所有候选文档，记录文件名、格式、大小、页数或工作表。
2. 运行：

   ```bash
   python scripts/find_missing_descriptions.py api.yaml --format markdown
   ```

3. 将结果分为：
   - 服务：通常为 `info.description`；必要时包括 tag 描述。
   - 方法：`paths` 下各 HTTP operation 的 `description` 或约定扩展字段。
   - 字段：parameters、responses、definitions/schemas 及其嵌套 properties 的描述。
4. 查看相邻非空描述，确定目标键、语言和风格。若一个文件主要使用 `x-description-zh` 表达字段含义，不要机械新增平行的 `description`；已有哪个空键就补哪个键。`info.description` 和 operation `description` 仍按 Swagger 标准键处理。
5. 先区分 operation、body parameter、消息包装字段、业务字段、response 和 definition，避免把同一句描述写到多个层级。Swagger 2.0 的节点映射与本例类型的处理方式见 [references/openapi2-node-mapping.md](references/openapi2-node-mapping.md)。若用户仅要求服务、方法和字段，不扩展修改范围。

### 2. 建立文档索引，避免整份长文塞入上下文

使用 computer use 打开 Office/PDF 应用。先读目录、标题、书签、工作表名、表头和可搜索文本，再按需跳转；不要从第一页线性通读长文。

- **Excel**：逐工作表确认表头，定位接口清单、请求参数、响应参数、数据字典；保留工作表名与单元格/行号。
- **Word**：使用导航窗格、标题结构和全文搜索；保留章节标题、页码或表格行。
- **PDF**：先判断是否有文本层。可搜索时使用目录与全文搜索；扫描件使用 OCR，并对关键字段回看页面图像。保留页码、章节和表格行。
- 搜索顺序：精确 operationId/路径 → 业务对象名 → 精确字段名 → 去前后缀或分词后的别名 → 中文业务术语。
- 对常见短字段名（如 `id`、`type`、`status`）必须结合所属对象、接口方向和附近字段消歧，不能使用孤立命中。

长文或多文件任务按 operation/业务对象分批。每批维护证据表并及时保存；切换批次前记录尚未解决项。详细匹配规则见 [references/matching-and-quality.md](references/matching-and-quality.md)。

### 3. 建立证据表

先在工作区创建临时 CSV/Markdown 证据表，不要直接边读边改 YAML：

| YAML 位置 | 对象类型 | 候选描述 | 来源位置 | 置信度 | 状态 |
|---|---|---|---|---|---|
| `info.description` | 服务 | … | 文件/章节/页 | 高 | 待写入 |

文档命中时，只把“高”置信度项目直接写入：名称/上下文一致，且文档明确陈述含义。中置信度项目需交叉验证。完成规定的检索顺序仍无匹配时，不要无限搜索；将该项标记为“文档未命中”，并使用下一节的确定性回退规则。来源互相冲突的项目不得推断覆盖，保持为空并列入报告。

### 4. 编写描述

- **服务**：概括服务服务于谁、提供什么业务能力；避免把 title 改写成一句空泛文字。
- **方法**：使用动宾结构说明动作、对象和必要条件；区分创建、查询、变更、删除及同步/异步行为。
- **字段**：说明业务含义；仅当文档明确给出时加入单位、格式、取值含义、条件必填或约束。
- 不把 JSON/YAML 类型当作业务描述（例如“字符串字段”），也不把字段名机械翻译当成证据。
- 同一复用 schema 只在 definition 中描述一次；不要为每个 `$ref` 复制可能不一致的字段解释。
- 若文档中只有中文而目标键为英文（或反之），可忠实翻译，但保留产品名、代码值和专有术语，并在报告中注明翻译。

#### 文档未命中时的回退规则

只有在按既定搜索顺序检查所有候选文档后仍找不到对应描述时，才执行以下规则：

1. **服务描述**：结合 `info.title`、tags、paths、operationId、schema 名和已有描述推断服务的核心业务能力。使用一条简洁、具体的描述，不引入上下文无法支持的用户群体、流程、约束或承诺。
2. **请求/响应体描述**：使用固定英文句式，并以 operationId 作为“请求方法名”；没有 operationId 时使用 YAML 中的 HTTP method 与 path 组合：
   - 请求体：`The request params of {请求方法名}`
   - 响应体：`The response params of {请求方法名}`
   不添加句号，不翻译模板；该固定模板覆盖 `x-description-zh` 通常写中文的语言约定。将模板写在直接代表完整请求/响应消息的节点，不要自动同时复制到 body parameter、消息包装字段和 response 三层；已有项目约定时遵循约定，否则优先写消息包装字段（例如 `SendNotificationReqMsg` / `SendNotificationRspMsg`）。单个普通字段不得套用该模板。
3. **字段描述**：根据字段名，并结合完整字段路径、父 schema、所属接口、请求/响应方向、类型、格式、枚举和相邻字段推断。描述业务含义而非仅拆词翻译；不得添加上下文中没有依据的单位、默认值、范围、隐私属性或业务规则。

将所有回退内容在证据表的“来源位置”列记为 `inferred from YAML context`，置信度记为“推断”。如果字段名与上下文仍存在多个合理解释，则不要武断选择，保留空值并列入歧义清单。

### 5. 最小化编辑并验证

1. 先复制备份或使用版本控制查看差异。
2. 只替换目标空值或插入明确要求的描述键。描述含 `:`、`#`、引号或换行时使用合法 YAML 引号/块标量。
3. 再次运行盘点脚本，比较补全前后数量。
4. 使用环境中可用的 YAML/OpenAPI 校验器解析文件；若没有专用校验器，至少检查 diff 和脚本扫描结果。
5. 检查 `git diff --word-diff` 或等效差异，确认没有非描述字段变化。
6. 抽样回查每个 operation，并对所有推断项、低置信度文档命中、重复名称、OCR 命中和冲突项人工复核。

## 交付内容

同时交付：

1. 补全后的 YAML。
2. 简短汇总：服务/方法/字段各补全多少项、仍缺多少项。
3. 未补全、歧义或冲突清单，注明 YAML 路径、检索过的来源和原因。
4. 来源清单或证据表；文档命中项回溯到文件及页码、章节、工作表/行，回退项明确标记为 `inferred from YAML context`。
5. 验证命令和结果。若无法解析某种文档、OCR 质量差或缺少校验工具，明确标注限制。

不要声称“全部有文档依据”。分别统计文档命中、上下文推断、冲突/歧义留空的数量；只有盘点范围内所有空描述都已补全或被明确列为有意留空时，才声称任务全部完成。

## 调试与评估

先运行 `python scripts/smoke_test.py` 验证盘点脚本，再使用小型、答案已知的 YAML 与文档做端到端测试。至少分别覆盖文档命中、文档未命中的三种回退、来源冲突、同名字段消歧和长文档分批续作。具体测试数据、提示词、检查命令和评分表见 [references/debugging.md](references/debugging.md)。
