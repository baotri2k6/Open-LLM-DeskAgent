const esbuild = require("esbuild");
const path = require("path");
const fs = require("fs");

function getFilesRecursively(dir) {
  let results = [];
  if (!fs.existsSync(dir)) return results;
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat && stat.isDirectory()) {
      results = results.concat(getFilesRecursively(fullPath));
    } else if (file.endsWith(".ts")) {
      results.push(fullPath);
    }
  });
  return results;
}

const srcDir = path.join(__dirname, "..", "src", "renderer");
const entryPoints = getFilesRecursively(srcDir);

if (entryPoints.length === 0) {
  console.log("No renderer TS files to compile.");
  process.exit(0);
}

console.log("Compiling renderer TS files:", entryPoints);

esbuild.build({
  entryPoints,
  outdir: path.join(__dirname, "..", "renderer"),
  bundle: false,
  platform: "browser",
  format: "esm",
  target: ["es2022"],
}).then(() => {
  console.log("Renderer build successful!");
}).catch(err => {
  console.error("Renderer build failed:", err);
  process.exit(1);
});
