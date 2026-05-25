#!/usr/bin/env node

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const packageRoot = path.resolve(__dirname, "..");
const defaultCodexHome = path.join(os.homedir(), ".codex");
const codexHome = process.env.CODEX_HOME
  ? path.resolve(process.env.CODEX_HOME)
  : defaultCodexHome;
const skillName = process.env.PINGCODE_SKILL_NAME || "pingcode";
const targetDir = path.join(codexHome, "skills", skillName);
const sourceEntries = ["SKILL.md", "README.md", "agents", "references", "scripts"];

function usage() {
  return [
    "Usage: npx pingcode-skill [--force] [--target <dir>]",
    "",
    "Installs the PingCode skill to ~/.codex/skills/pingcode by default.",
    "Options:",
    "  --force       Overwrite an existing installed skill",
    "  --target DIR  Install into a custom skill directory",
  ].join("\n");
}

function parseArgs(argv) {
  const options = { force: false, target: targetDir };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--force") {
      options.force = true;
    } else if (arg === "--target") {
      const value = argv[index + 1];
      if (!value) {
        throw new Error("--target requires a directory");
      }
      options.target = path.resolve(value);
      index += 1;
    } else if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  return options;
}

function copyEntry(name, destinationRoot) {
  const source = path.join(packageRoot, name);
  const destination = path.join(destinationRoot, name);
  fs.cpSync(source, destination, {
    recursive: true,
    errorOnExist: false,
    force: true,
  });
}

function shellQuote(value) {
  if (/^[A-Za-z0-9_/:=.,+-]+$/.test(value)) {
    return value;
  }
  return `'${value.replace(/'/g, "'\\''")}'`;
}

function rewriteInstalledDocs(destinationRoot) {
  const cliCommand = `python3 ${shellQuote(path.join(destinationRoot, "scripts", "pingcode.py"))}`;
  const docs = [
    path.join(destinationRoot, "SKILL.md"),
    path.join(destinationRoot, "README.md"),
    path.join(destinationRoot, "references", "workflows.md"),
  ];

  for (const file of docs) {
    if (!fs.existsSync(file)) {
      continue;
    }
    const original = fs.readFileSync(file, "utf8");
    const rewritten = original.replaceAll("python3 scripts/pingcode.py", cliCommand);
    if (rewritten !== original) {
      fs.writeFileSync(file, rewritten);
    }
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage());
    return 0;
  }

  if (fs.existsSync(options.target) && !options.force) {
    console.error(`PingCode skill already exists at ${options.target}`);
    console.error("Re-run with --force to overwrite it.");
    return 1;
  }

  fs.rmSync(options.target, { recursive: true, force: true });
  fs.mkdirSync(options.target, { recursive: true });
  for (const entry of sourceEntries) {
    copyEntry(entry, options.target);
  }
  rewriteInstalledDocs(options.target);

  console.log(`Installed PingCode skill to ${options.target}`);
  console.log("");
  console.log("Configure PingCode credentials before use:");
  console.log('  export PINGCODE_CLIENT_ID="..."');
  console.log('  export PINGCODE_CLIENT_SECRET="..."');
  console.log("");
  console.log('For "my" requests, also configure:');
  console.log('  export PINGCODE_USER_ID="..."');
  console.log('  export PINGCODE_USER_NAME="..."');
  return 0;
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`error: ${error.message}`);
  console.error("");
  console.error(usage());
  process.exitCode = 1;
}
