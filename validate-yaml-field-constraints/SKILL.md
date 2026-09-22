---
name: validate-yaml-field-constraints
description: Validate and minimally correct field constraints in YAML API or service schemas against supplied long-form specifications, including simple-field type and maxLength values and complex-type required child lists. Use when reconciling Swagger/OpenAPI or similar YAML with Word, PDF, Excel, HTML, or text documentation where service-specific and common sections must be searched, exact nested field paths must be disambiguated, and uncertain values must remain unchanged.
---

# Validate YAML Field Constraints

依据文档校验 YAML 字段约束，只修改有明确文档证据且路径完全匹配的值。文档无法确定时保留 YAML 原值。

## 工作边界

- 简单类型字段只校验 `type` 和 `maxLength`。
- 复杂类型只校验其直接子字段组成的 `required` 集合。
- 不修改字段名、路径、描述、格式、枚举、示例、默认值、引用或其他契约内容，除非用户另有明确要求。
- 不根据字段名、业务常识、示例值、编程语言习惯或历史检查结果猜测类型、长度或必填性。
- 保留 YAML 的格式、注释、引号、键顺序、换行符和编码；优先做最小文本编辑。
- 除非用户明确要求原地修改，否则先创建不覆盖已有文件的工作副本，并只编辑副本。

## 流程

### 1. 盘点 YAML

1. 识别服务信息，例如 `info.title`、服务名、tags、paths、operationId、schema 名和命名空间。
2. 为每个待校验字段记录**规范路径**，路径必须包含所有层级，并区分 schema、请求/响应、数组元素和嵌套对象。示例：
   - `definitions.CreateOrder.properties.customer.properties.id`
   - `paths./orders.post.parameters.body.schema.properties.customer.properties.id`
   - `definitions.Order.properties.lines.items.properties.id`
3. 将节点分类：
   - 简单字段：文档描述一个标量值，可校验 `type`，并在满足规则时校验 `maxLength`。
   - 复杂类型：包含 `properties` 的对象、由 `$ref` 指向的对象，或包含复杂元素的容器；在定义其子字段的对象层校验 `required`。
4. 沿 `$ref` 定位真正定义字段的位置。不要把引用使用位置和被引用 schema 的字段混为同一路径。

### 2. 在长文档中定位证据

先用目录、标题、书签、工作表名和全文搜索缩小范围，不要线性通读整份文档。按以下顺序检索：

1. 与 YAML 服务信息对应的服务章节。
2. 对应 path、operationId、请求/响应对象或 schema 的章节。
3. 文档明确标为公共、通用、基础对象或数据字典的章节。
4. 精确字段名，并结合其完整父级链和请求/响应方向消歧。

服务专属章节与公共章节冲突时，优先采用对该服务或接口更具体的说明，但要在结果中报告冲突。文档中的字段只有在完整层级、所属对象、接口方向和语境均与 YAML 路径一致时才算命中。孤立的同名字段不是证据。

为每项建立证据记录：YAML 规范路径、现值、文档值、文档位置、匹配依据、决定。低置信度、冲突或只有同名匹配的项目保持不变。

### 3. 校验简单字段的 `type`

只在文档明确给出类型且字段路径完全匹配时，按下表规范化：

| 文档类型（忽略大小写） | YAML `type` |
|---|---|
| `string`, `varchar`, `varchar2`, `char`, `text` | `string` |
| `datetime`, `timestamp`, `date` | `dateTime` |
| `boolean`, `bool` | `boolean` |
| `number`, `numeric`, `money`, `bigdecimal` | `decimal` |
| `integer`, `int`, `smallint`, `tinyint`, `byte`, `short` | `int` |
| `long`, `bigint` | `long` |
| `decimal` | `decimal` |
| `float`, `real` | `float` |
| `double` | `double` |

严格遵守以下限制：

- `integer` 仅是输入关键字，最终输出禁止出现 `type: integer`。
- 文档类型为 `number` 时必须输出 `decimal`。不得因字段名、业务语义、示例值、历史检查结果或语言习惯改成 `int`、`long`、`float` 或 `double`。
- 先去除类型文本首尾空白，再对上表中的完整类型关键字做不区分大小写的匹配。对于 `string(N)`，将基础类型识别为 `string`，并按下一节单独处理长度。
- 带有未定义修饰词、联合类型或无法映射的类型不做改动；不要自行扩展映射表。

### 4. 校验简单字段的 `maxLength`

仅从文档的字段长度描述或文档类型中的有效 `string(N)` 得出长度：

- `string` 关键字忽略大小写。
- 关键字与左括号之间、括号内部允许任意空白。
- 等价识别正则为 `^string\s*\(\s*(\d+)\s*\)$`。
- 捕获值必须是大于 `0` 的十进制整数，写入 YAML 时使用整数值。
- `string(20)`、`String (20)`、`STRING ( 20 )` 均得到 `maxLength: 20`。
- `string(0)`、`string(-1)`、`string(10.5)`、`string(abc)` 以及没有明确长度的 `string` 均不产生长度证据。
- 未识别到有效长度时，保留现有 `maxLength`，既不删除也不改写。

文档若在独立的“长度”列明确给出大于 `0` 的十进制整数，也可作为 `maxLength` 证据。不要从示例值字符数、数据库展示宽度或其他字段的长度推断。

### 5. 校验复杂类型的 `required`

1. 在文档对应的复杂对象中，收集被明确标记为必填的**直接子字段**。
2. 使用 YAML 中子字段的精确键名组成 `required` 数组；不得使用显示名、别名或点路径。
3. 仅当文档能确定该复杂类型全部直接子字段的必填状态时，才将 `required` 校正为完整集合，包括删除文档明确为非必填的旧成员。
4. 若文档只明确说明部分字段必填、但无法判断其余字段，则只能安全地补充已确认的必填项，不得删除现有成员。
5. 文档明确确认没有直接必填子字段时，遵循目标规范现有风格删除 `required` 或设为空数组；不要把空集合放到某个子字段上。
6. 嵌套对象分别处理：父对象的 `required` 只包含其直接子字段；孙字段应写入定义孙字段的嵌套对象的 `required`。
7. 不要将 `required: true/false` 写在属性节点上，也不要把请求参数层的 `required` 与 schema 对象的 `required` 混淆。

### 6. 编辑与验证

1. 先完成证据表，再批量做最小编辑；不要边搜索边凭印象修改。
2. 使用可用的 YAML 解析器确认结果可解析；若是 OpenAPI，再使用可用的 OpenAPI 校验器。
3. 检查 diff，确认只发生有证据支持的 `type`、`maxLength` 和对象级 `required` 变化。
4. 搜索最终文件中的 `type: integer`（包括等价的空白和引号形式），确保没有遗留；若该值不在本次证据覆盖范围内，将其报告为待确认，不要在无文档依据时擅自映射。
5. 对每个修改项反向核对完整 YAML 路径和文档位置，重点复核同名字段、嵌套对象、数组元素、公共对象和请求/响应重名对象。

## 交付

交付修改后的 YAML 工作副本，并报告：

- `type`、`maxLength`、`required` 各修改多少项。
- 每项修改的 YAML 完整路径、旧值、新值和文档位置。
- 因无匹配、路径歧义、无映射、无有效长度、必填集合不完整或来源冲突而保持不变的项目。
- YAML/OpenAPI 解析、禁止类型扫描和 diff 检查的命令与结果。

不要声称未修改项“正确”；只能说明文档证据不足，因此按规则保持不变。
