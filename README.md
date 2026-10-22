# PDF Evidence Validator

从自制年度收益说明书提取结构化行，并逐行绑定文件哈希、页码、文本行号与原文。确定性校验通过后还需显式人工确认。

## 运行

```shell
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python make_samples.py
python validator.py samples/normal.pdf --out artifacts/normal
python -m unittest discover -s tests -v
```

用浏览器打开 `artifacts/normal/review.html` 查看原文与候选对照；`result.json` 是机器可读结果。

```shell
python validator.py samples/wrong-ratio.pdf --out artifacts/rejected
# 返回码 2，确定性检查拒绝通过
python validator.py samples/normal.pdf --out artifacts/approved --confirm "Demo Reviewer"
# 人工审阅后执行，reviewStatus 才变为 APPROVED
```

## 五类样例

| 文件 | 预期 |
| --- | --- |
| normal.pdf | 全年完整，PENDING_REVIEW |
| missing-year.pdf | 年度不连续 |
| duplicate-year.pdf | 重复年度 |
| mixed-scenario.pdf | BASE/UPSIDE 混用 |
| wrong-ratio.pdf | 金额与比例不一致 |

对照 `validator.SPEC`：本金 1000 USD，BASE 年度 1—5，期末金额 = 本金 × 比例 / 100，每行 HALF_UP 两位。
这些是演示规则，与实际保险产品无关。规则和表头都限定在 `synthetic-v1`。

## 模拟模型错误

默认 provider 为 deterministic-template：正则读取自制文本模板，无 LLM、无 OCR。
导入候选 JSON 时使用 `--candidates candidates.json`，provider 为 offline-candidate-fixture，仍然不调用模型。
候选数组格式：

```json
[{"scenario":"BASE","year":1,"value":"1100.00","ratio":"110.00","evidence":{"page":1,"line":5,"text":"BASE | 1 | 1100.00 | 110.00"}}]
```

行号仅为结构示例，应从 `result.json` 的 source 取实际行号；数组必须覆盖 PDF 所有数据行。
修改候选页码、原文或金额可观察“来源不存在”“字段与原文不符”等拒绝结果。
`tests/test_validator.py` 可直接复现，无需手工改数据。

## 实现与限制

- 使用 Decimal，检查年度唯一性、连续性、情景隔离、计算关系和来源完整覆盖。
- 输出保留 provider、候选、错误、原文、文件哈希；错误候选不会进入 APPROVED 状态。
- 确认时重新核对文件哈希，防止审阅期间文件变化。
- 行号是 pypdf 提取文本的逻辑行号，不是 PDF 视觉坐标；本版没有框选高亮。
- 扫描件、加密 PDF、任意复杂表格、多币种及真实模型适配未实现。
- 本地 reviewer 是人工审阅标签，不提供审阅人认证或不可篡改审计。
- 样例使用 pypdf 构造简单文本流，无商业文件、字体包或第三方原始文档。

技术参考：[pypdf text extraction](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)。

## 实现与验证说明

本项目为全新演示代码，使用虚构规则和样例，由作者结合业务经验、通过 AI 辅助实现。
已验证项目与受环境限制的检查见 [VERIFICATION.md](VERIFICATION.md)。
