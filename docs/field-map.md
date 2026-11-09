# 字段映射表（阶段 1）

三个 ATS 的字段对齐到一张统一宽表。**本表由 AI 起草、Marco 逐条核对后生效。**
核对日期：待填

填充率均为实测（见 `src/03_field_survey.py` 与 `src/04_field_traps.py`），不是估计。

---

## 统一字段

| 统一字段 | Ashby (5,247) | Greenhouse (12,939) | Lever (2,183) | 备注 |
|---|---|---|---|---|
| `company` | 外层 key | `company_name` 100% | 外层 key | |
| `ats` | 常量 | 常量 | 常量 | 用于分层检查偏差 |
| `job_id` | `id` 100% | `id` 100% | `id` 100% | |
| `title` | `title` 100% | `title` 100% | **`text`** 100% | Lever 的标题字段名叫 text |
| `department` | `department` 100% | `departments[0].name` 100% | `categories.department` | 雇主自己填的部门，口径各家不同 |
| `team` | `team` 100% | 无 | `categories.team` | |
| `location_raw` | `location` 100% | `location.name` 100% | `categories.location` | **Greenhouse 可含多地，以 `;` 分隔** |
| `country` | `address.postalAddress.addressCountry` | 无，需从文本判 | `country` 100% | Ashby 有 `United States` 与 `USA` 两种拼法 |
| `remote` | `isRemote` 82.8% | 无，需从文本判 | `workplaceType` 100% | |
| `employment_type` | `employmentType` 100% | `employment` 3.3% | `categories.commitment` | Greenhouse 几乎没有，不可用 |
| `posted_at` | `publishedAt` 100% | `first_published` 100% | `createdAt` 100% | Lever 是毫秒时间戳 |
| `url` | `jobUrl` 100% | `absolute_url` 100% | `hostedUrl` 100% | |
| `jd_text` | `descriptionPlain` 100% | `content` 100%，**双重 HTML 转义** | **拼接**，见下 | |
| `salary_raw` | `compensation.scrapeableCompensationSalarySummary` **53.1%** | 无字段，**只能从正文抽** | `salaryRange` **33.7%** | |

---

## 需要特别处理的三处

### 1. Lever 的正文必须拼接

正文被拆在五个字段里，各自的平均长度：

| 字段 | 有值率 | 平均长度 | 是什么 |
|---|---|---|---|
| `descriptionPlain` | 97.6% | 1,341 | 岗位介绍（开头段） |
| **`lists`** | **99.1%** | **3,106** | **要求清单，正文主体** |
| `additionalPlain` | 93.7% | 1,296 | EEO / 法务样板文字 |
| `openingPlain` | 77.0% | 609 | 公司介绍样板 |
| `descriptionBodyPlain` | 63.7% | 732 | 与 descriptionPlain 重叠 |

**只取 `descriptionPlain` 会丢掉 70% 的正文，而且丢掉的正是岗位要求那一段。**

### 2. Greenhouse 的 `content` 是双重 HTML 转义

原样长这样：`&lt;div class=&quot;content-intro&quot;&gt;` —— 要 unescape 两次再去标签。

### 3. 薪资三种来源、三种单位

| 来源 | 形态 | 覆盖 |
|---|---|---|
| Ashby | `"$217K - $260K"` 字符串 | 53.1% |
| Lever | `{min, max, currency, interval}` 结构化 | 33.7%，其中时薪 36 / 年薪 698 / 月薪 1 |
| Greenhouse | 只在正文里，需正则抽取 | 正文含美元区间 52.8%，其中时薪写法 6.1% |

---

## 待 Marco 裁定（阶段 1 闸门）

1. **`jd_text` 包含哪些部分** —— 样板文字（EEO、公司介绍）要不要进？
2. **是否只保留美国岗位**
3. **时薪岗位怎么办** —— 折算年薪还是排除
4. **一条 posting 挂多个城市时怎么计数**

裁定结果写入 `docs/decisions.md`。
