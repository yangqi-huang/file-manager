const form = document.querySelector("#generate-form");
const fileInput = document.querySelector("#file-input");
const dropZone = document.querySelector("#drop-zone");
const fileName = document.querySelector("#file-name");
const submitButton = document.querySelector("#submit-button");
const demoButton = document.querySelector("#demo-button");
const statusText = document.querySelector("#status");
const emptyState = document.querySelector("#empty-state");
const resultContent = document.querySelector("#result-content");
const title = document.querySelector("#diagram-title");
const generatedBy = document.querySelector("#generated-by");
const warnings = document.querySelector("#warnings");
const downloads = document.querySelector("#downloads");
const treePreview = document.querySelector("#tree-preview");
const textPreview = document.querySelector("#text-preview");

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    fileInput.click();
  }
});
fileInput.addEventListener("change", () => showSelectedFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  });
});

dropZone.addEventListener("drop", (event) => {
  const files = event.dataTransfer.files;
  if (!files.length) {
    return;
  }
  fileInput.files = files;
  showSelectedFile(files[0]);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = fileInput.files[0];
  if (!file) {
    setStatus("请先选择一个文件。", true);
    return;
  }
  if (file.size > 12 * 1024 * 1024) {
    setStatus("文件超过 12 MB，请选择较小文件。", true);
    return;
  }
  await generateFromFile(file);
});

demoButton.addEventListener("click", async () => {
  const sample = `# 客户服务系统升级项目启动会

## 项目目标
- 缩短工单受理时间
- 汇总跨团队信息

## 工作分工
- 产品组：梳理流程与需求
- 技术组：搭建环境并开发接口

## 时间节点
- 需求确认
- 首轮测试
- 上线试运行`;
  const file = new File([sample], "项目启动会示例.md", { type: "text/markdown" });
  showSelectedFile(file);
  await generateFromFile(file);
});

async function generateFromFile(file) {
  submitButton.disabled = true;
  demoButton.disabled = true;
  setStatus("正在提取文档内容并生成结构图...");
  try {
    const result = await requestGeneration(file);
    renderResult(result);
    setStatus("生成成功，可以下载并导入目标软件。");
  } catch (error) {
    setStatus(error.message || "生成失败，请稍后重试。", true);
  } finally {
    submitButton.disabled = false;
    demoButton.disabled = false;
  }
}

function showSelectedFile(file) {
  fileName.textContent = file ? `${file.name} (${formatSize(file.size)})` : "尚未选择文件";
}

async function requestGeneration(file) {
  const response = await fetch("/api/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      content_base64: await toBase64(file),
      diagram_type: form.elements.diagram_type.value,
      use_ai: document.querySelector("#use-ai").checked,
    }),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "生成失败。");
  }
  return result;
}

function toBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(",", 2)[1]);
    reader.onerror = () => reject(new Error("读取文件失败。"));
    reader.readAsDataURL(file);
  });
}

function renderResult(result) {
  emptyState.classList.add("hidden");
  resultContent.classList.remove("hidden");
  title.textContent = result.spec.title;
  generatedBy.textContent = `生成方式：${result.generated_by}`;
  textPreview.textContent = result.text_preview;
  renderWarnings(result.warnings || []);
  renderDownloads(result.files);
  treePreview.replaceChildren(buildNodeList(result.spec.root));
}

function renderWarnings(items) {
  warnings.replaceChildren();
  warnings.classList.toggle("hidden", !items.length);
  items.forEach((item) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = item;
    warnings.appendChild(paragraph);
  });
}

function renderDownloads(files) {
  downloads.replaceChildren();
  Object.entries(files).forEach(([name, content]) => {
    const link = document.createElement("a");
    const blob = new Blob([content], { type: downloadType(name) });
    link.href = URL.createObjectURL(blob);
    link.download = name;
    link.className = "download";
    link.textContent = `下载 ${name}`;
    downloads.appendChild(link);
  });
}

function buildNodeList(node) {
  const list = document.createElement("ul");
  const item = document.createElement("li");
  item.textContent = node.label;
  if (node.children && node.children.length) {
    node.children.forEach((child) => item.appendChild(buildNodeList(child)));
  }
  list.appendChild(item);
  return list;
}

function downloadType(name) {
  if (name.endsWith(".drawio")) {
    return "application/xml;charset=utf-8";
  }
  return "text/plain;charset=utf-8";
}

function setStatus(message, error = false) {
  statusText.textContent = message;
  statusText.classList.toggle("error", error);
}

function formatSize(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}
