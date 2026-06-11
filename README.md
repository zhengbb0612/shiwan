# 🎮 智能试玩广告生成器 (Playable Ad Generator)

提供玩法描述 + 产品链接 + 素材，AI / 本地模板自动生成三渠道（Unity / AppLovin / Google UAC）试玩 HTML。

## 功能

- **本地秒级模板**（无需 API Key）：涂色、三消、麻将、找不同、箭头解谜、拼图纸牌（JigSolitaire）
- **AI 生成**（需 Anthropic API Key）：其余自定义品类
- 三渠道自动适配，输出 < 5MB 的单文件 HTML
- 拼图纸牌四套模板：核心玩法 / 动图+核心 / 纯动图拼接 / 不规则碎片，上传对应素材即可生成
- 箭头解谜支持上传 Unity `level.json` 关卡

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 http://localhost:8501

可选环境变量（`.env`，参考 `.env.example`）：

```
ANTHROPIC_API_KEY=sk-...
ANTHROPIC_BASE_URL=
ANTHROPIC_MODEL=claude-sonnet-4-6
```

## 部署到 Streamlit Community Cloud

1. 把本仓库推到 GitHub（公开仓库）。
2. 登录 https://share.streamlit.io ，选 **New app** → 选本仓库 → 主文件填 `app.py`。
3. （可选）在 **Advanced settings → Secrets** 里填 API Key：
   ```
   ANTHROPIC_API_KEY = "sk-..."
   ```
   本地模板品类（拼图纸牌/箭头/找不同/三消/麻将/涂色）不需要 Key。
4. Deploy，等待构建完成即得到公开网址。

## 技术栈

Streamlit · Pillow · PyMuPDF · Anthropic SDK

## 辅助工具

- **箭头解谜关卡生成器**：https://10.192.87.4:5173/ （先用此工具生成JSON关卡文件，再上传到本生成器生成试玩）
