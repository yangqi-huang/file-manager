# AI 办公结构图助手

把办公文档提炼为可导入 XMind 或 draw.io 的结构图文件。应用提供一个本地网页，支持上传 `TXT`、`MD`、`CSV`、`DOCX`、`PPTX`、`XLSX` 和 `PDF` 文档。

## 功能

- 使用 DeepSeek 把原文整理为思维导图、流程图、组织图或知识树。
- 可选择详细、标准或简洁的固定细节程度；相同输入在服务运行期间会复用同一份 AI 结果，以降低重复生成波动。
- 未配置 API Key 时使用本地预览规则，方便先体验上传和导出流程。
- 在网页中直接绘制可视化思维导图或流程/组织图预览，节点文字完整换行展示，并支持缩放、适应窗口与拖动画布浏览大图。
- 生成 XMind 可导入的 Markdown 文件。
- 生成 Mermaid 文件和可直接在 draw.io 打开的 `.drawio` XML 文件。
- DOCX、PPTX、XLSX 使用 Python 标准库提取文本；PDF 支持作为可选能力。

## 安装与启动

本项目需要 Python 3.11 或更高版本。macOS Homebrew 安装的 Python 会保护系统环境，因此请在虚拟环境中安装依赖：

```bash
cd /Users/yangqi_huang/Documents/Codex/2026-05-25/ai-deepseek-xmind-drawio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python server.py
```

然后在浏览器打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。

页面中的“体验示例文档”可在没有 API Key 和本地文档的情况下直接生成一组演示导出文件。

`pypdf` 已包含在 `requirements.txt` 中，安装依赖后即可解析文本型 PDF；扫描版 PDF 仍需要先进行 OCR。

## 配置 DeepSeek

不设置密钥时，页面仍可生成本地演示结果。接入 DeepSeek 时，在启动服务前设置环境变量：

```bash
export DEEPSEEK_API_KEY="sk_your_api_key_here"  # 请替换为新创建的真实密钥
python server.py
```

可选配置：

```bash
export DEEPSEEK_MODEL="deepseek-chat"
export DEEPSEEK_BASE_URL="https://api.deepseek.com/chat/completions"
```

涉及敏感公司文件时，请确认其允许上传到所配置的模型服务，或先做脱敏处理。

不要将真实密钥写入 `.env.example` 或提交到 Git。若页面提示使用了示例占位文字，请确认启动服务的终端中设置的是实际 API Key，而不是 README 中的示例值。

对于同一个文件，请保持“生成类型”和“细节程度”选择一致。应用会关闭思考模式、以零随机性参数请求 DeepSeek，并在本次服务运行期间复用相同输入的首次生成结果；服务重启后的结果仍可能存在轻微模型差异。

## 文件导入

- XMind：选择导出的 `文件名-xmind.md`，在 XMind 中使用 Markdown 导入。
- draw.io：直接打开导出的 `文件名.drawio` 继续编辑。
- Mermaid：`文件名-drawio.mmd` 可复制到支持 Mermaid 的工具中，也可用于留存源代码。

## 测试

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

## 发布到 GitHub

首次发布前，在 GitHub 创建一个空仓库，不要勾选自动生成 README、`.gitignore` 或 License，然后在本目录执行：

```bash
git remote add origin https://github.com/<your-name>/ai-deepseek-xmind-drawio.git
git push -u origin main
```

`.venv`、`.env` 和系统缓存文件已加入忽略规则，不会将本地环境或 API Key 上传到仓库。
