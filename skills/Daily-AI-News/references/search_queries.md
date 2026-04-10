# 搜索查询模板

日期占位符：`{today}` = 当前日期，`{yesterday}` = 昨天，`{week_ago}` = 7天前。
可运行 `scripts/generate_queries.py` 自动生成带真实日期的查询。

---

## 每日简报查询组合（推荐）

```
"AI news today" OR "artificial intelligence breakthrough" after:{yesterday}
"AI research paper" OR "machine learning breakthrough" after:{yesterday}
"AI startup funding" OR "AI company news" after:{week_ago}
"AI product release" OR "new AI tool" after:{yesterday}
```

## 按类别查询

### 通用AI新闻
```
"AI news today" OR "artificial intelligence breakthrough" after:{yesterday}
"latest AI developments" OR "AI advancement" after:{yesterday}
```

### 研究与论文
```
"AI research paper" OR "machine learning breakthrough" after:{yesterday}
arXiv "cs.AI" OR "cs.LG" paper after:{yesterday}
"NeurIPS" OR "ICML" OR "ACL" AI paper {current_year}
```

### 行业与商业
```
"AI startup funding" OR "artificial intelligence investment" after:{week_ago}
"AI acquisition" OR "AI partnership" after:{week_ago}
```

### 产品与工具
```
"AI application launch" OR "new AI tool" after:{yesterday}
"open source AI" OR "AI model release" OR "LLM release" after:{yesterday}
```

### 特定公司
```
"OpenAI announcement" OR "GPT update" OR "ChatGPT news" after:{yesterday}
"Google AI" OR "Gemini update" after:{yesterday}
"Anthropic news" OR "Claude update" after:{yesterday}
"Meta AI" OR "LLaMA update" after:{yesterday}
"Microsoft AI" OR "Copilot update" after:{yesterday}
```

### 专题
```
"AI" AND "healthcare" OR "medical AI" after:{week_ago}
"AI ethics" OR "artificial intelligence safety" after:{week_ago}
"AI regulation" OR "AI policy" after:{week_ago}
```

---

## 搜索技巧

- **始终加日期过滤**：每日用 `after:{yesterday}`，每周用 `after:{week_ago}`
- **从宽到窄**：`"AI news today"` → `"AI product launch"` → `"OpenAI product launch"`
- **排除噪音**：`"AI news" NOT "crypto" NOT "blockchain"`
- **精确短语**：用引号 `"large language model"` 而非散词
- **来源限定**：`site:venturebeat.com AI` / `site:arxiv.org "artificial intelligence"`
