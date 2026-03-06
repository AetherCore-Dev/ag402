# ag402 Commands Reference

钱包管理和支付工具的命令接口文档。

## 目录

- [钱包管理命令](#钱包管理命令)
- [支付工具命令](#支付工具命令)
- [安全支付流程](#安全支付流程)
- [使用示例](#使用示例)
- [错误处理](#错误处理)

---

## 钱包管理命令

### wallet status

查看当前钱包余额和预算信息。

```bash
wallet status
```

**输出示例：**

```
┌─────────────────────────────────────┐
│ 💰 Wallet Status                    │
├─────────────────────────────────────┤
│ 余额:     50.00 USDC                │
│ 预算:     100.00 USDC (每日)        │
│ 已用:     25.00 USDC (今日)         │
│ 剩余:     75.00 USDC                │
└─────────────────────────────────────┘
```

**返回字段：**

| 字段 | 描述 |
|------|------|
| `balance` | 当前钱包 USDC 余额 |
| `daily_budget` | 每日预算上限 |
| `daily_spent` | 今日已消费 |
| `remaining` | 剩余可用金额 |

---

### wallet deposit

充值测试模式 - 向钱包添加测试 USDC。

```bash
wallet deposit [amount]
```

**参数：**

| 参数 | 类型 | 必填 | 默认值 | 描述 |
|------|------|------|--------|------|
| `amount` | number | 否 | 10 | 充值金额 (USDC) |

**使用示例：**

```bash
# 充值默认金额 10 USDC
wallet deposit

# 充值 50 USDC
wallet deposit 50
```

**注意：** 仅在测试环境可用，生产环境需通过 Solana 主网转账。

---

### wallet history

查看交易历史记录。

```bash
wallet history [options]
```

**参数：**

| 参数 | 短选项 | 类型 | 必填 | 默认值 | 描述 |
|------|--------|------|------|--------|------|
| `--limit` | `-l` | number | 否 | 10 | 返回记录数量 |
| `--type` | `-t` | string | 否 | all | 交易类型: `all`, `payment`, `deposit`, `refund` |
| `--days` | `-d` | number | 否 | 7 | 查询天数范围 |

**使用示例：**

```bash
# 查看最近 10 条记录
wallet history

# 查看最近 20 条记录
wallet history --limit 20

# 查看最近 30 天的支付记录
wallet history --type payment --days 30
```

**输出示例：**

```
┌────────────────────────────────────────────────────────────┐
│ 📜 Transaction History (Last 10)                          │
├────────────────────────────────────────────────────────────┤
│ 时间                类型      金额       状态    详情     │
│ 2026-03-05 14:30   payment  -2.50 USDC ✅  API调用     │
│ 2026-03-05 12:15   deposit  +10.00 USDC ✅  测试充值   │
│ 2026-03-04 09:00   payment  -0.75 USDC ✅  API调用     │
│ ...                                                    │
└────────────────────────────────────────────────────────────┘
```

---

## 支付工具命令

### pay

调用付费 API 并完成支付。

```bash
pay <url> [options]
```

**参数：**

| 参数 | 短选项 | 类型 | 必填 | 默认值 | 描述 |
|------|--------|------|------|--------|------|
| `url` | - | string | 是 | - | 付费 API 的 URL |
| `--amount` | `-a` | number | 否 | 自动检测 | 支付金额 (USDC) |
| `--confirm` | `-y` | flag | 否 | false | 强制确认支付 |
| `--header` | `-H` | string | 否 | - | 自定义 HTTP 头 (格式: "Key: Value") |
| `--method` | `-m` | string | 否 | GET | HTTP 方法 |
| `--data` | `-d` | string | 否 | - | 请求体 (JSON 字符串) |

**使用示例：**

```bash
# 自动检测金额并支付
pay https://api.example.com/premium

# 指定支付金额
pay https://api.example.com/premium --amount 5.00

# 强制确认大额支付
pay https://api.example.com/premium --amount 2.50 --confirm

# POST 请求示例
pay https://api.example.com/generate --method POST --data '{"prompt":"hello"}'
```

---

## 安全支付流程

### 自动支付规则

| 金额范围 | 行为 | 确认要求 |
|----------|------|----------|
| < $10.00 | 自动支付 | 无需确认 |
| >= $10.00 | 需要确认 | 需使用 `--confirm` 或交互确认 |

### 预算检查

每次支付前自动检查：

1. **余额检查** - 确保钱包有足够余额
2. **预算检查** - 确保不超过每日预算
3. **异常检测** - 检测异常大额或频繁支付

**预算限制：**

- 每日预算: 默认 100 USDC (可配置)
- 单笔上限: 50 USDC
- 最小金额: 0.01 USDC

### 支付结果记录

所有支付交易都会记录到本地数据库，包含：

- 交易 ID (tx_id)
- 支付金额
- 时间戳
- API 端点
- 支付状态 (success/failed/pending)
- 错误信息 (如有)

---

## 使用示例

### 完整支付流程

```bash
# 1. 先查看钱包状态
wallet status

# 2. 如余额不足，先充值
wallet deposit 50

# 3. 查看交易历史确认充值成功
wallet history

# 4. 调用付费 API
pay https://api.openai.com/v1/chat/completions \
  --amount 0.50 \
  --method POST \
  --data '{"model":"gpt-4","messages":[{"role":"user","content":"hello"}]}'
```

### 交互模式

```bash
# 不带 --confirm，大额支付会提示确认
pay https://api.example.com/premium --amount 2.00
# 输出: ⚠️ 支付 $2.00 USDC 到 api.example.com，确认? (y/n)
```

---

## 错误处理

### 常见错误码

| 错误码 | 描述 | 解决方案 |
|--------|------|----------|
| `INSUFFICIENT_BALANCE` | 余额不足 | 使用 `wallet deposit` 充值 |
| `EXCEEDS_BUDGET` | 超过预算 | 等待明天或调整预算 |
| `PAYMENT_FAILED` | 支付失败 | 检查网络，重试支付 |
| `INVALID_URL` | URL 无效 | 检查 URL 格式 |
| `NETWORK_ERROR` | 网络错误 | 检查网络连接 |
| `WALLET_NOT_FOUND` | 钱包未初始化 | 运行 `wallet deposit` 初始化 |

### 错误输出示例

```
❌ 支付失败: INSUFFICIENT_BALANCE
   当前余额: 0.50 USDC
   所需金额: 2.00 USDC
   提示: 使用 'wallet deposit 10' 充值
```

### 重试机制

支付失败后会自动重试最多 3 次：

1. 首次尝试
2. 3 秒后重试
3. 10 秒后重试

如仍失败，返回最终错误信息。

---

## 配置文件

创建 `~/.ag402/config.json` 自定义设置：

```json
{
  "wallet": {
    "daily_budget": 100.0,       // Hard ceiling: $10,000
    "single_tx_limit": 50.0,    // Hard ceiling: $1,000
    "per_minute_limit": 20.0,  // Hard ceiling: $100
    "max_single_payment": 50.0,
    "auto_confirm_threshold: 10.0
  },
  "network": {
    "rpc_url": "https://api.devnet.solana.com",
    "retry_count": 3,
    "timeout": 30
  },
  "logging": {
    "level": "info",
    "file": "~/.ag402/logs/payments.log"
  }
}
```

---

## 相关命令

- `ag402 setup` - 初始化 ag402
- `ag402 status` - 查看整体状态
- `ag402 config` - 查看/修改配置
