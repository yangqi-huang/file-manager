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
const diagramKind = document.querySelector("#diagram-kind");
const diagramStage = document.querySelector("#diagram-stage");
const diagramPreview = document.querySelector("#diagram-preview");
const zoomOutButton = document.querySelector("#zoom-out");
const zoomInButton = document.querySelector("#zoom-in");
const zoomFitButton = document.querySelector("#zoom-fit");
const zoomResetButton = document.querySelector("#zoom-reset");
const zoomLevel = document.querySelector("#zoom-level");
const treePreview = document.querySelector("#tree-preview");
const textPreview = document.querySelector("#text-preview");
const SVG_NS = "http://www.w3.org/2000/svg";
const PREVIEW_WIDTH = 1100;
const PREVIEW_HEIGHT = 620;
const MIN_ZOOM = 0.18;
const MAX_ZOOM = 3.5;
const ZOOM_STEP = 1.18;
let diagramCanvas;
let diagramLayout;
let viewState = { scale: 1, x: 0, y: 0 };
let dragState = null;
const TYPE_LABELS = {
  mindmap: "思维导图",
  flowchart: "流程图",
  orgchart: "组织图",
  knowledge: "知识树",
};

zoomInButton.addEventListener("click", () => zoomDiagram(ZOOM_STEP));
zoomOutButton.addEventListener("click", () => zoomDiagram(1 / ZOOM_STEP));
zoomFitButton.addEventListener("click", fitDiagram);
zoomResetButton.addEventListener("click", resetDiagram);
diagramStage.addEventListener("wheel", (event) => {
  if (!diagramCanvas) {
    return;
  }
  event.preventDefault();
  const factor = event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP;
  zoomDiagram(factor, stagePoint(event.clientX, event.clientY));
}, { passive: false });
diagramStage.addEventListener("pointerdown", beginDiagramDrag);
diagramStage.addEventListener("pointermove", continueDiagramDrag);
diagramStage.addEventListener("pointerup", endDiagramDrag);
diagramStage.addEventListener("pointercancel", endDiagramDrag);

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
  diagramKind.textContent = TYPE_LABELS[result.spec.diagram_type] || "结构图";
  renderDiagram(result.spec);
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

function renderDiagram(spec) {
  diagramPreview.replaceChildren();
  diagramLayout = normalizeLayout(
    ["mindmap", "knowledge"].includes(spec.diagram_type)
      ? layoutMindMap(spec.root)
      : layoutTopDown(spec.root),
  );
  diagramPreview.setAttribute("viewBox", `0 0 ${PREVIEW_WIDTH} ${PREVIEW_HEIGHT}`);
  diagramPreview.setAttribute("aria-label", `${TYPE_LABELS[spec.diagram_type] || "结构图"}：${spec.title}`);
  addDiagramDefinitions();
  diagramCanvas = svgElement("g", { class: "diagram-canvas" });
  diagramPreview.appendChild(diagramCanvas);
  diagramLayout.edges.forEach((edge) => drawEdge(edge, spec.diagram_type));
  diagramLayout.nodes.forEach((node) => drawNode(node, spec.diagram_type));
  fitDiagram();
}

function layoutMindMap(root) {
  const horizontalGap = 232;
  const rowGap = 24;
  const left = [];
  const right = [];
  (root.children || []).forEach((node, index) => (index % 2 ? left : right).push(node));
  const rootMetrics = measureNode(root, true);
  const width = 1080;
  const centerX = width / 2;
  const centerY = Math.max(forestHeight(left, rowGap), forestHeight(right, rowGap), 240) / 2 + 46;
  const nodes = [{
    node: root,
    x: centerX,
    y: centerY,
    ...rootMetrics,
    depth: 0,
    root: true,
  }];
  const edges = [];

  function placeSide(branches, side) {
    let nextY = centerY - forestHeight(branches, rowGap) / 2;

    function place(node, depth, y, parent) {
      const children = node.children || [];
      const metrics = measureNode(node, false);
      const positioned = { node, x: centerX + side * depth * horizontalGap, y, ...metrics, depth };
      nodes.push(positioned);
      if (parent) {
        edges.push({ from: parent, to: positioned, side });
      }
      if (children.length) {
        let childTop = y - forestHeight(children, rowGap) / 2;
        children.forEach((child) => {
          const childHeight = subtreeHeight(child, rowGap);
          place(child, depth + 1, childTop + childHeight / 2, positioned);
          childTop += childHeight + rowGap;
        });
      }
      return positioned;
    }

    branches.forEach((branch) => {
      const height = subtreeHeight(branch, rowGap);
      place(branch, 1, nextY + height / 2, nodes[0]);
      nextY += height + rowGap;
    });
  }

  placeSide(right, 1);
  placeSide(left, -1);
  return { width, height: centerY * 2, nodes, edges };
}

function countLeaves(nodes) {
  return nodes.reduce((total, node) => {
    const children = node.children || [];
    return total + (children.length ? countLeaves(children) : 1);
  }, 0);
}

function forestHeight(nodes, rowGap) {
  if (!nodes.length) {
    return 0;
  }
  return nodes.reduce((sum, node) => sum + subtreeHeight(node, rowGap), 0)
    + rowGap * (nodes.length - 1);
}

function subtreeHeight(node, rowGap) {
  const ownHeight = measureNode(node, false).height;
  const children = node.children || [];
  return Math.max(ownHeight, forestHeight(children, rowGap));
}

function layoutTopDown(root) {
  const columnGap = 292;
  const levelGap = 46;
  const nodes = [];
  const edges = [];
  const leaves = Math.max(countLeaves([root]), 1);
  const width = Math.max(740, leaves * columnGap + 90);
  let nextLeaf = 65;
  const levelHeights = [];

  function place(node, depth, parent) {
    const metrics = measureNode(node, depth === 0);
    levelHeights[depth] = Math.max(levelHeights[depth] || 0, metrics.height);
    const children = node.children || [];
    const childPositions = children.map((child) => place(child, depth + 1, null));
    let x;
    if (childPositions.length) {
      x = childPositions.reduce((sum, child) => sum + child.x, 0) / childPositions.length;
    } else {
      x = nextLeaf;
      nextLeaf += columnGap;
    }
    const positioned = { node, x, y: 0, ...metrics, depth, root: depth === 0 };
    childPositions.forEach((child) => edges.push({ from: positioned, to: child }));
    if (parent) {
      edges.push({ from: parent, to: positioned });
    }
    nodes.push(positioned);
    return positioned;
  }

  place(root, 0, null);
  let nextY = 44;
  levelHeights.forEach((height, depth) => {
    const centerY = nextY + height / 2;
    nodes.filter((node) => node.depth === depth).forEach((node) => {
      node.y = centerY;
    });
    nextY += height + levelGap;
  });
  return { width, height: Math.max(360, nextY), nodes, edges };
}

function normalizeLayout(layout) {
  const padding = 42;
  const minX = Math.min(...layout.nodes.map((item) => item.x - item.width / 2));
  const maxX = Math.max(...layout.nodes.map((item) => item.x + item.width / 2));
  const minY = Math.min(...layout.nodes.map((item) => item.y - item.height / 2));
  const maxY = Math.max(...layout.nodes.map((item) => item.y + item.height / 2));
  const offsetX = padding - minX;
  const offsetY = padding - minY;
  layout.nodes.forEach((item) => {
    item.x += offsetX;
    item.y += offsetY;
  });
  return {
    nodes: layout.nodes,
    edges: layout.edges,
    width: maxX - minX + padding * 2,
    height: maxY - minY + padding * 2,
  };
}

function addDiagramDefinitions() {
  const definitions = svgElement("defs");
  const marker = svgElement("marker", {
    id: "diagram-arrow",
    markerWidth: "10",
    markerHeight: "10",
    refX: "8",
    refY: "5",
    orient: "auto",
  });
  marker.appendChild(svgElement("path", { d: "M0,0 L10,5 L0,10 z", class: "diagram-arrow" }));
  definitions.appendChild(marker);
  diagramPreview.appendChild(definitions);
}

function drawEdge(edge, diagramType) {
  let d;
  if (["mindmap", "knowledge"].includes(diagramType)) {
    const side = edge.to.x >= edge.from.x ? 1 : -1;
    const startX = edge.from.x + side * edge.from.width / 2;
    const endX = edge.to.x - side * edge.to.width / 2;
    const middleX = (startX + endX) / 2;
    d = `M ${startX} ${edge.from.y} C ${middleX} ${edge.from.y}, ${middleX} ${edge.to.y}, ${endX} ${edge.to.y}`;
  } else {
    const startY = edge.from.y + edge.from.height / 2;
    const endY = edge.to.y - edge.to.height / 2;
    const middleY = (startY + endY) / 2;
    d = `M ${edge.from.x} ${startY} C ${edge.from.x} ${middleY}, ${edge.to.x} ${middleY}, ${edge.to.x} ${endY}`;
  }
  const attributes = { d, class: "diagram-edge" };
  if (diagramType === "flowchart") {
    attributes["marker-end"] = "url(#diagram-arrow)";
  }
  diagramCanvas.appendChild(svgElement("path", attributes));
}

function drawNode(positioned, diagramType) {
  const group = svgElement("g", {
    class: `diagram-node ${positioned.root ? "root" : ""} ${diagramType}`,
    transform: `translate(${positioned.x}, ${positioned.y})`,
  });
  group.appendChild(svgElement("rect", {
    x: String(-positioned.width / 2),
    y: String(-positioned.height / 2),
    width: String(positioned.width),
    height: String(positioned.height),
    rx: positioned.root ? "29" : "13",
  }));
  positioned.lines.forEach((line, index) => {
    const text = svgElement("text", {
      x: "0",
      y: String((index - (positioned.lines.length - 1) / 2) * 18 + 5),
      "text-anchor": "middle",
    });
    text.textContent = line;
    group.appendChild(text);
  });
  if (positioned.node.note) {
    const tooltip = svgElement("title");
    tooltip.textContent = positioned.node.note;
    group.appendChild(tooltip);
  }
  diagramCanvas.appendChild(group);
}

function measureNode(node, root) {
  const lineLength = root ? 15 : 14;
  const lines = wrapLabel(node.label, lineLength);
  const longest = Math.max(...lines.map((line) => line.length), 1);
  const width = Math.max(root ? 176 : 154, Math.min(252, longest * 14 + 34));
  const height = Math.max(root ? 58 : 50, lines.length * 18 + 25);
  return { lines, width, height };
}

function wrapLabel(label, lineLength) {
  const normalized = String(label || "").replace(/\s+/g, " ").trim() || "未命名节点";
  const lines = [];
  let remainder = normalized;
  while (remainder.length > lineLength) {
    lines.push(remainder.slice(0, lineLength));
    remainder = remainder.slice(lineLength);
  }
  lines.push(remainder);
  return lines;
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function fitDiagram() {
  if (!diagramLayout) {
    return;
  }
  const padding = 46;
  const scale = Math.min(
    (PREVIEW_WIDTH - padding * 2) / diagramLayout.width,
    (PREVIEW_HEIGHT - padding * 2) / diagramLayout.height,
    1,
  );
  setViewState({
    scale,
    x: (PREVIEW_WIDTH - diagramLayout.width * scale) / 2,
    y: (PREVIEW_HEIGHT - diagramLayout.height * scale) / 2,
  });
}

function resetDiagram() {
  if (!diagramLayout) {
    return;
  }
  setViewState({
    scale: 1,
    x: (PREVIEW_WIDTH - diagramLayout.width) / 2,
    y: (PREVIEW_HEIGHT - diagramLayout.height) / 2,
  });
}

function zoomDiagram(factor, anchor = { x: PREVIEW_WIDTH / 2, y: PREVIEW_HEIGHT / 2 }) {
  if (!diagramCanvas) {
    return;
  }
  const minimum = Math.min(MIN_ZOOM, viewState.scale);
  const nextScale = clamp(viewState.scale * factor, minimum, MAX_ZOOM);
  const ratio = nextScale / viewState.scale;
  setViewState({
    scale: nextScale,
    x: anchor.x - (anchor.x - viewState.x) * ratio,
    y: anchor.y - (anchor.y - viewState.y) * ratio,
  });
}

function setViewState(nextState) {
  viewState = nextState;
  diagramCanvas.setAttribute(
    "transform",
    `translate(${viewState.x} ${viewState.y}) scale(${viewState.scale})`,
  );
  zoomLevel.textContent = `${Math.round(viewState.scale * 100)}%`;
}

function beginDiagramDrag(event) {
  if (!diagramCanvas || event.button !== 0) {
    return;
  }
  const point = stagePoint(event.clientX, event.clientY);
  dragState = {
    pointerId: event.pointerId,
    point,
    x: viewState.x,
    y: viewState.y,
  };
  diagramStage.classList.add("dragging");
  diagramStage.setPointerCapture(event.pointerId);
}

function continueDiagramDrag(event) {
  if (!dragState || dragState.pointerId !== event.pointerId) {
    return;
  }
  const point = stagePoint(event.clientX, event.clientY);
  setViewState({
    ...viewState,
    x: dragState.x + point.x - dragState.point.x,
    y: dragState.y + point.y - dragState.point.y,
  });
}

function endDiagramDrag(event) {
  if (!dragState || dragState.pointerId !== event.pointerId) {
    return;
  }
  diagramStage.classList.remove("dragging");
  diagramStage.releasePointerCapture(event.pointerId);
  dragState = null;
}

function stagePoint(clientX, clientY) {
  const bounds = diagramPreview.getBoundingClientRect();
  return {
    x: (clientX - bounds.left) * PREVIEW_WIDTH / bounds.width,
    y: (clientY - bounds.top) * PREVIEW_HEIGHT / bounds.height,
  };
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
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
