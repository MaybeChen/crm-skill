---
name: enrich-soap-xsd-descriptions
description: Add missing bilingual Chinese and English xs:documentation annotations to a copied working version of SOAP XML Schema (XSD) files without modifying the original inputs or changing any pre-existing bytes, using supplied Word, PDF, Excel, HTML, or text specifications as the primary source and context-based inference only when no explicit description exists. Use when processing a directory tree that contains service-specific XSD subdirectories plus shared root-level schemas, especially when long documents cover several services, identical field names occur in different services or nesting levels, and source evidence must be matched by service, operation, direction, type, and full field path.
---

# Enrich SOAP XSD Descriptions

为目标目录中 SOAP 协议的所有 XSD 字段补充中英文 `xs:documentation`。把源文档视为权威依据；只有确认文档没有明确说明后才允许推断。

## 工作边界

- 递归处理目标目录下的 `.xsd` 文件。将服务子目录中的 XSD 视为服务专属协议，将根目录或明确标记为 common/shared/base 的 XSD 视为公共对象。
- 只允许增加缺失的字段描述。不得改写或删除已有描述，也不得改变字段名、命名空间、类型、引用、出现次数、默认值、固定值、枚举、导入关系、空白、换行或其他任何内容。
- 将 `xs:element` 和 `xs:attribute` 的声明视为字段；同时覆盖全局字段、局部字段、匿名复杂类型中的字段和数组元素声明。不要把 `xs:complexType`、`xs:simpleType`、`xs:sequence` 等类型或结构节点误计为字段，除非用户明确要求描述类型。
- **绝对禁止修改输入文件。** 开始处理前必须复制完整输入目录，后续扫描以原目录为基准，所有写入只发生在副本中；即使用户要求原地修改，也先明确告知本 skill 只交付副本。
- 默认将副本创建为输入目录同级的 `<输入目录名>.enriched`；用户可指定其他输出路径。输出路径已存在时立即停止并报告，禁止覆盖、合并或复用旧副本。复制时保留目录结构、文件名、权限和符号链接语义，使相对 import/include 继续有效。
- 复制完成、编辑开始前，记录原目录所有文件的相对路径、大小和 SHA-256；交付前重新计算并逐项比较，必须证明原输入没有变化。
- 保留输入文件的编码、BOM、换行、缩进、空白、命名空间前缀、注释和节点顺序。模式可能使用 `xsd:` 或其他前缀，不要强制改成 `xs:`。禁止使用会序列化、重排或格式化整个 XML 的写回方式；解析器只用于读取和验证，写入采用定位明确的最小文本插入。
- 不得因为字段同名就复用描述。匹配单位是“服务 + 操作 + 请求/响应 + 类型链 + 完整字段路径”。

## 工作流程

### 1. 盘点协议和文档

1. 列出所有 XSD、源文档及其相对路径，记录文件格式、大小、页数、工作表或章节结构。
2. 读取每个 schema 的 `targetNamespace`、`xs:import`、`xs:include`、全局 element/type、局部字段和现有 annotation。解析 QName 时同时使用当前节点的命名空间绑定；不要仅按字符串前缀匹配。
3. 从服务的入口 element 或 WSDL 消息（若提供）沿 `type`、`ref`、匿名类型、extension/restriction、group 和 attributeGroup 递归建立字段使用路径。记录循环引用并停止该分支，不能无限展开。
4. 为每个字段记录：
   - XSD 文件和可稳定定位的 XML 路径；
   - 声明位置与完整业务路径；
   - 所属服务、操作、请求/响应方向和类型链；
   - 是否为共享声明，以及被哪些服务路径引用；
   - 现有中文、英文或无语言标记的 documentation。
5. 不要把 include/import、消息包装层或类型名擅自写入业务字段路径；这些信息作为独立上下文保存。数组字段保留字段名，不追加 `items` 一类虚构路径段。

#### 识别请求和响应外壳对象

- XSD 中名为 `xxxRequest` 的复杂对象通常是对应方法**整个请求体的外壳对象**；名为 `xxxResponse` 的复杂对象通常是对应方法**整个响应体的外壳对象**。如果实际协议将 `Response` 误拼为 `Resonse` 或使用类似变体，仍按其结构和使用位置识别，不要擅自改名。
- 外壳对象可能直接来自源文档，也可能是根据接口结构自行创建的协议包装。先在对应服务和方法章节中查找其原文定义；找不到时，不要因为文档未出现同名对象就否定其外壳角色，也不要跨服务搜索同名包装对象。
- 不能只凭 `Request`/`Response` 后缀判断。必须同时核对它是否位于方法请求/响应入口、是否包裹该方向的全部业务字段，以及 WSDL 消息、element/type 引用关系。若证据仍不足，将其标记为未决。
- 记录业务字段路径时，将已确认的外壳对象作为请求/响应上下文，而不是业务字段路径的一段。例如 `CreateOrderRequest.customer.id` 记为 `request.customer.id`，`CreateOrderResponse.result.code` 记为 `response.result.code`。外壳对象自身需要描述且文档无原文时，可以基于方法和方向补充“某方法的请求体”或“某方法的响应体”一类说明，并标记为 `inferred from XSD context`；其内部字段仍须逐项按文档匹配或推断。

### 2. 按服务建立文档检索范围

先读目录、标题、书签、工作表名和表头，再检索目标内容；不要将长文档从头到尾线性读取，也不要一次性把整份长文塞入上下文。

按以下顺序查找每个字段：

1. 对应服务章节；
2. 对应操作、接口名或消息名；
3. 对应请求或响应表；
4. 对应复杂类型或父对象；
5. 完整层级中的精确字段名；
6. 只有目标声明确认为公共对象时，才查公共对象、基础类型或数据字典章节。

服务专属字段禁止从另一个服务章节取描述，即使字段名和类型名相同。公共声明可以跨服务章节检索，但只有各服务的语义一致时才能写入共享声明；若不同服务给出的含义冲突，不要选择其中一个覆盖公共 XSD，保留原描述或列为歧义。

对 `id`、`type`、`status`、`code`、`name` 等常见名称，以及同一接口不同层级重复的名称，必须同时核对父对象、完整路径、操作和方向。孤立的全文搜索命中不能作为证据。

### 3. 建立证据表

在编辑 XSD 前创建临时 CSV 或 Markdown 表：

| 服务/操作/方向 | 完整字段路径 | XSD 声明位置 | 中文候选 | 英文候选 | 文档位置 | 来源类型 | 决定 |
|---|---|---|---|---|---|---|---|

- 文档位置至少包含文件名以及章节、页码、工作表/行或可复查的锚点。
- `来源类型` 只能写 `document`、`inferred from XSD context` 或 `conflict/unresolved`。
- 文档明确说明字段含义时，逐字忠实采用其描述，仅做 XML/CDATA 所需的转义处理；不要用更流畅的自行改写替代权威措辞。
- 文档分别提供中英文时分别采用。只有中文明确描述时，英文节点复用完全相同的中文描述；不得擅自翻译。只有英文而无中文时，忠实翻译为中文，并在证据表中注明翻译。
- 文档无明确描述时，完成上述检索顺序后才根据字段名、完整路径、父类型、相邻字段、服务、操作及请求/响应方向生成简洁中文描述，并在中英文节点中复用该中文描述。
- 不从类型、长度、示例值或枚举臆造业务规则、单位、格式、条件必填、隐私属性或生命周期。
- 上下文仍支持多个合理含义时不要猜测；保留现状并列入歧义清单。

### 4. 写入 annotation

对没有 annotation 的字段，将 annotation 作为字段声明允许的第一个子节点插入，使用当前 schema 已有的 XML Schema 前缀。例如前缀为 `xs` 时：

```xml
<xs:annotation>
    <xs:documentation xml:lang="zh"><![CDATA[账户余额通知标识。balanceNotifyId的组成是:前缀+序列值，前缀根据beId和partyId计算生成。]]></xs:documentation>
    <xs:documentation xml:lang="en"><![CDATA[账户余额通知标识。balanceNotifyId的组成是:前缀+序列值，前缀根据beId和partyId计算生成。]]></xs:documentation>
</xs:annotation>
```

遵守以下规则：

- 字段已有 `xs:annotation` 时复用它；XSD 同一声明通常只允许一个 annotation，不要新增第二个。
- 保留 annotation 中的 `xs:appinfo`、其他语言 documentation 和注释。缺少 `zh` 或 `en` 时只补缺少项。
- 若已有 `zh-CN`、`zh_CN`、`en-US` 等语言标签，按项目约定判断是否等价，避免制造语义重复；不得改名、删除或规范化已有语言标签。
- 非空现有描述一律保持原字节不变。即使权威文档与之不一致，也只在证据表中报告冲突，不得更正、补写或规范化已有文本。
- 使用 CDATA 包裹描述。描述包含 `]]>` 时，将其安全拆分为相邻 CDATA 段，保证 XML 合法且解析后的文本不变。
- 模仿所在文件的缩进和换行，不要为了插入注解而格式化整个 XML。
- 对通过 `ref` 使用的字段，优先在实际声明处写一次，不要在每个引用点复制描述。若同一共享声明在不同使用路径含义不同，报告建模冲突，不要写入误导性的统一描述。
- 类型引用不等于字段声明。字段自身需要描述时注解引用该类型的 `xs:element`/`xs:attribute`；不要只给被引用的 complexType 添加说明来替代字段描述。

### 5. 分批处理并复核

长文档按“服务 → 操作 → 请求/响应对象”分批处理。完成一批后保存证据表和未决项，再处理下一批。每批检查：

1. 相同字段名是否按完整路径分别匹配；
2. 请求与响应同名对象是否混用；
3. 服务专属章节是否越界引用；
4. 公共对象是否确实共享且无语义冲突；
5. 每个字段是否恰有一份有效的中文和英文说明，或已明确列为未决。

### 6. 验证

1. 使用 XML 解析器检查所有 XSD 格式正确。
2. 在依赖文件齐全时编译每个 schema，确认 annotation 的位置与数量符合 XSD 语法；缺少外部 import 时区分环境限制与本次修改错误。
3. 重新盘点全部字段，统计：文档命中、上下文推断、保留现值、冲突/歧义、缺少中文、缺少英文。
4. 检查每个新写入的 documentation 都带正确的 `xml:lang`，CDATA 可解析，并且没有重复 annotation。
5. 比较原目录与工作副本。允许的 diff 只有在缺失描述的字段中插入新的 `annotation`，或在既有 `annotation` 中插入缺失的 `documentation`；任何替换、删除、整行重排、尾随空白变化或非描述差异都视为失败，必须撤销并改用更小的文本插入重新处理。
6. 从每个服务至少抽查一个请求、一个响应、一个嵌套同名字段和一个公共对象，并从 XSD 反向回查文档位置。
7. 重新计算原输入的 SHA-256 清单并与编辑前清单比较；只要有一个原文件发生变化，就不得交付结果。
8. 对每个有差异的 XSD 做“仅插入”校验：从副本中按证据表精确移除本次新增的 annotation/documentation 字节后，结果必须与原文件逐字节相同。无法还原为完全相同字节流时，视为修改了描述以外的内容，不得交付。

可优先使用 `xmllint --noout` 做格式检查，并用支持 XML Schema 1.0/1.1 的可用解析器编译 schema。不要仅以 XML 格式正确替代 XSD 语义验证。

## 交付要求

同时交付：

1. 补全后的 XSD 副本目录，以及原输入编辑前后 SHA-256 清单一致的确认；不得将原目录作为交付结果；
2. 按服务和文件统计的字段总数、文档命中数、推断数、保留数和未决数；
3. 可追溯的证据表；
4. 冲突、歧义、断开的引用、循环引用和缺失外部依赖清单；
5. XML/XSD 验证命令、结果和 diff 检查结果。

不要笼统声称“全部来自文档”。只有实际在文档中找到明确说明的项目才计为文档命中；其余必须明确标为推断或未决。
