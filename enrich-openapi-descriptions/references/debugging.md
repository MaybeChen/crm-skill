# 调试与评估指南

## 目录

- [十分钟快速调试](#十分钟快速调试)
- [1. 先验证工具](#1-先验证工具)
- [2. 建立最小端到端用例](#2-建立最小端到端用例)
- [3. 检查产物](#3-检查产物)
- [4. 定位常见问题](#4-定位常见问题)
- [5. 压测长文档](#5-压测长文档)
- [6. 评分表](#6-评分表)

## 十分钟快速调试

在 `enrich-openapi-descriptions` 目录准备：

```text
test-data/
├── test-api.yaml       # 原始 YAML
└── test-doc.pdf        # 也可以是 docx/xlsx
```

先验证工具：

```bash
python scripts/smoke_test.py
```

接着在具有 computer use 能力、已安装本 skill 的 Agent 中只附加 `test-doc.pdf` 和原始 `test-api.yaml`。**不要手工创建或上传副本；直接发送这一句：**

```text
使用 $enrich-openapi-descriptions，根据 test-doc.pdf 校对并补全 test-api.yaml 中的 description。
```

只要 skill 已成功安装、`$enrich-openapi-descriptions` 能被识别，并且 Agent 能访问这两个输入文件，这条短提示词就足够。`test-api.yaml` 在提示词中表示输入对象，不表示允许原地修改；skill 会自动创建 `test-api.enriched.yaml`，然后只编辑副本。创建副本、只改 `description`、校对非空描述、文档未命中回退、证据记录和验证都属于 skill 内部规则，无需每次在提示词中重复。

调试阶段若要额外强调文件保护和观察分类统计，可使用下面的展开版提示词：

```text
使用 $enrich-openapi-descriptions，根据 test-doc.pdf 校对并补全 test-api.yaml 中的 description。
请自动创建工作副本，保持 test-api.yaml 不变。文档明确时同时纠正已有 description；文档未命中时按 skill 的回退规则处理。
输出证据表，分别统计补充、纠正、保留、推断和未解决项。
```

如果 Agent 报告找不到 skill，说明调用语法或安装位置有问题；如果找不到 `test-doc.pdf` / `test-api.yaml`，请重新附加文件或使用 Agent 可访问的完整路径。这两类问题与提示词长短无关。正常情况下，Agent 应先报告已创建 `test-api.enriched.yaml`，再开始文档检索和编辑。

Agent 完成后运行：

```bash
# 4. 查看剩余缺失项
python scripts/find_missing_descriptions.py test-data/test-api.enriched.yaml --format markdown > after-missing.md

# 5. 比较原件和结果（返回 1 表示两个文件有差异，在此处是预期行为）
git diff --no-index -- test-data/test-api.yaml test-data/test-api.enriched.yaml
```

通过标准：原件未改变；diff 只涉及 `description`；文档明确的旧描述得到纠正；请求/响应回退模板正确；每次写入都有文档来源或 `inferred from YAML context` 标记。若这五项都满足，再换成真实长文档调试。

## 1. 先验证工具

从 skill 目录运行：

```bash
python scripts/smoke_test.py
python scripts/find_missing_descriptions.py --help
python scripts/prepare_working_copy.py --help
```

三条命令都应以退出码 0 结束。smoke test 会验证副本保护、服务/方法/响应/字段的空描述或缺失描述，以及 JSON 与 Markdown 两种输出。

### Windows Python 环境提示

如果命令开头出现 `Could not find platform independent libraries <prefix>`，说明当前 Python 的安装路径、`PYTHONHOME`/`PYTHONPATH` 或标准库可能不一致；这条提示不是 skill 产生的。当前 smoke test 不再使用 `tempfile.TemporaryDirectory`，因此也能避开部分 Windows Python 3.12 环境中 `os` 与 `shutil` 版本不匹配导致的 `_walk_symlinks_as_files` 清理异常。

如果输出是：

```text
Could not find platform independent libraries <prefix>
smoke tests passed
```

则 **skill 的 smoke test 已通过，但 Python 环境并非完全正常**。`smoke tests passed` 只证明扫描器本次的断言和两种 CLI 输出均成功，不能消除 Python 启动时的 `<prefix>` 警告。可以继续调试 skill；在长期使用或运行其他 Python 工具前，仍建议按下述步骤修复环境。

还可以紧接着检查退出码。在 `cmd.exe` 中运行 `echo %ERRORLEVEL%`，在 PowerShell 中运行 `$LASTEXITCODE`；值为 `0` 才表示 smoke test 成功。

若仍出现该提示，在 `cmd.exe` 中运行：

```bat
where python
python -c "import sys, os, shutil; print(sys.executable); print(sys.prefix); print(os.__file__); print(shutil.__file__)"
set PYTHONHOME
set PYTHONPATH
```

在 PowerShell 中可将最后两条替换为：

```powershell
$env:PYTHONHOME
$env:PYTHONPATH
```

`os.py` 与 `shutil.py` 应来自同一个 Python 安装的 `Lib` 目录。若不是，先清除错误的 `PYTHONHOME`/`PYTHONPATH` 或修复 Python 安装，再重新运行 smoke test。

## 2. 建立最小端到端用例

不要一开始就用真实长文档。准备一个约 2 个接口、10 个字段的 YAML，以及一页 Excel/Word/PDF 测试文档。在测试文档中有意设置：

1. 一个明确的服务说明；
2. 一个明确的方法说明；
3. 两个明确的字段说明；
4. 一个文档中不存在的请求体描述；
5. 一个文档中不存在的响应体描述；
6. 一个文档中不存在但可从字段名和父 schema 明确推断的字段；
7. 两个不同 schema 中都叫 `status`、但含义不同的字段；
8. 两处互相冲突的字段说明。

让启用本 skill 的 Agent 对原始 YAML 执行；副本由 skill 创建：

```text
使用 $enrich-openapi-descriptions，根据 test-doc 补全 test-api.yaml；请自动创建工作副本，不得修改原始文件。
保留证据表，并将文档命中、上下文推断、冲突/歧义留空分别统计。
```

预期结果：文档中的描述被准确写入；无文档请求/响应体使用固定模板；可判定字段被合理推断；两个 `status` 不串用；冲突项保持为空并报告。

## 3. 检查产物

运行：

```bash
python scripts/find_missing_descriptions.py test-api.yaml --format json > before.json
python scripts/find_missing_descriptions.py test-api.yaml --include-populated --format json > all-before.json
python scripts/find_missing_descriptions.py test-api.enriched.yaml --format json > after.json
python scripts/find_missing_descriptions.py test-api.enriched.yaml --include-populated --format json > all-after.json
git diff --no-index -- test-api.yaml test-api.enriched.yaml
```

逐项检查：

- diff 只包含标准 `description` 的替换/插入；`x-description-zh` 保持不变；
- 原始 `test-api.yaml` 的内容和哈希保持不变，所有修改只存在于 `test-api.enriched.yaml`；
- `all-before.json` 中的每个非空描述都已与文档核对，需纠正的内容出现在 diff 和证据表中；
- 文档命中项的证据位置可实际跳转；
- 推断项标记为 `inferred from YAML context`；
- 请求体为 `The request params of <方法名>`；
- 响应体为 `The response params of <方法名>`；
- 方法名优先从 operationId 去掉 HTTP 方法前缀，无法得到时使用 path 最后一段；
- 没有杜撰单位、默认值、枚举含义、长度或业务约束；
- after 的缺失数下降，剩余项全部出现在歧义/冲突清单中。

若环境有 OpenAPI 校验器，再运行项目已有的校验命令，确认描述编辑没有破坏 YAML 或接口契约。

## 4. 定位常见问题

| 现象 | 优先检查 | 修正方向 |
|---|---|---|
| 找错同名字段 | 证据表是否包含父 schema 和请求/响应方向 | 用完整字段路径搜索并提高歧义门槛 |
| 一直搜索不进入回退 | 是否记录了所有候选文档与搜索词 | 完成既定搜索顺序后标记“文档未命中” |
| 过早推断 | 是否只做了一次精确搜索 | 继续查 operationId、对象名、别名及业务术语 |
| 请求/响应模板错误 | 节点类型与 operationId | 先识别 body 方向，优先使用 operationId |
| 字段描述只是拆词 | 父 schema、类型、枚举和相邻字段是否参与判断 | 加入完整上下文；仍歧义则留空 |
| 修改了非描述字段 | 最终 diff | 回退非描述改动并重新做最小编辑 |
| 长文后半段质量下降 | 检查点和未决清单 | 缩小批次并按 operation 恢复 |

## 5. 压测长文档

最小用例通过后，再选择一份有目录且超过 100 页或多个工作表的文档。要求 Agent 每个 operation 或约 50 个字段保存一次检查点。中断一次任务，再只提供 YAML、证据表和未决清单要求继续，以验证其不会重新通读全文或重复覆盖已完成项。

## 6. 评分表

每轮记录以下指标，便于比较 skill 修改前后的效果：

| 指标 | 计算方式 | 建议门槛 |
|---|---|---:|
| 文档命中准确率 | 正确文档命中数 / 写入的文档命中数 | 100% |
| 回退模板准确率 | 正确模板数 / 回退请求响应体数 | 100% |
| 字段推断准确率 | 合理推断字段数 / 推断字段总数 | ≥ 95% |
| 非描述改动数 | diff 中非描述键改动数 | 0 |
| 可追溯率 | 有有效来源或推断标记的写入数 / 总写入数 | 100% |
| 遗漏报告率 | 已报告的剩余空项 / 实际剩余空项 | 100% |

出现错误时保存输入文件、Agent 提示词、证据表、输出 YAML 和 diff。一次只调整一条规则，再用同一组用例重跑，避免无法判断是哪项修改产生效果。
