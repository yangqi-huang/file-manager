import { readFileSync } from "node:fs";
import vm from "node:vm";

const noOpElement = {
  addEventListener() {},
  appendChild() {},
  classList: { add() {}, remove() {}, toggle() {} },
  replaceChildren() {},
  setAttribute() {},
  textContent: "",
};

const context = {
  document: {
    querySelector() {
      return noOpElement;
    },
    createElement() {
      return noOpElement;
    },
    createElementNS() {
      return { ...noOpElement };
    },
  },
  File: class File {},
  FileReader: class FileReader {},
  globalThis: {},
};
context.globalThis = context;
vm.createContext(context);
vm.runInContext(readFileSync("static/app.js", "utf8"), context);

const api = context.__officeDiagramPreviewTest;
const paragraph = "这是一段较长的操作说明，需要在节点中完整显示并且统一左对齐，避免阅读时视线来回跳动。";

const textLayout = api.textAlignmentFor({
  ...api.measureNode({ label: paragraph }, false),
  paragraph: true,
  root: false,
  side: -1,
});
if (textLayout.anchor !== "start") {
  throw new Error(`Expected long text to be left aligned, got ${textLayout.anchor}`);
}

const layout = api.normalizeLayout(api.layoutMindMap({
  label: "根节点",
  children: [
    { label: "一级节点 A", children: [{ label: paragraph }, { label: "短句" }] },
    { label: "一级节点 B", children: [{ label: paragraph }, { label: "短句 B" }] },
    { label: "一级节点 C", children: [{ label: paragraph }, { label: "短句 C" }] },
    { label: "一级节点 D", children: [{ label: paragraph }, { label: "短句 D" }] },
  ],
}));

const byDepthAndSide = new Map();
for (const node of layout.nodes.filter((item) => !item.root)) {
  const key = `${node.depth}:${node.side}`;
  const list = byDepthAndSide.get(key) || [];
  list.push(node);
  byDepthAndSide.set(key, list);
}

for (const list of byDepthAndSide.values()) {
  list.sort((a, b) => a.y - b.y);
  for (let index = 1; index < list.length; index += 1) {
    const previous = list[index - 1];
    const current = list[index];
    const gap = current.y - current.height / 2 - (previous.y + previous.height / 2);
    if (gap < -0.01) {
      throw new Error(`Detected vertical overlap: ${previous.node.label} / ${current.node.label}`);
    }
  }
}

