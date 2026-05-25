#!/usr/bin/env node

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const packageRoot = path.resolve(__dirname, "..");
const skillName = process.env.PINGCODE_SKILL_NAME || "pingcode";
const aliasName = "pingcode-ctx";
const sourceEntries = [
  "SKILL.md",
  "README.md",
  "agents",
  "references",
  "scripts",
  "bin/pingcode-ctx.js",
];
const aliasSkillEntries = ["skills/pingcode-ctx/SKILL.md"];

const AGENT_KEYS = ["codex", "claude", "openclaw", "hermes"];

function defaultAgentRoots() {
  const home = os.homedir();
  const codexHome = process.env.CODEX_HOME
    ? path.resolve(process.env.CODEX_HOME)
    : path.join(home, ".codex");
  return {
    codex: {
      label: "Codex",
      skillsRoot: path.join(codexHome, "skills"),
    },
    claude: {
      label: "Claude Code",
      skillsRoot: path.join(home, ".claude", "skills"),
    },
    openclaw: {
      label: "OpenClaw",
      skillsRoot: path.join(home, ".openclaw", "skills"),
    },
    hermes: {
      label: "Hermes",
      skillsRoot: path.join(home, ".hermes", "skills", "project-management"),
    },
  };
}

function usage() {
  return [
    "Usage: npx pingcode-skill [--force] [--target <dir>]",
    "                          [--codex-only|--claude-only|--openclaw-only|--hermes-only]",
    "",
    "Default behavior installs the PingCode skill and pingcode-ctx alias",
    "into every supported agent's user-level skill home in one shot:",
    "  Codex:     ~/.codex/skills/pingcode (and pingcode-ctx)",
    "  Claude:    ~/.claude/skills/pingcode (and pingcode-ctx)",
    "  OpenClaw:  ~/.openclaw/skills/pingcode (and pingcode-ctx)",
    "  Hermes:    ~/.hermes/skills/project-management/pingcode (and pingcode-ctx)",
    "",
    "Options:",
    "  --force            Overwrite existing installs in every selected root",
    "  --target DIR       Install only into DIR (skips the multi-root flow)",
    "  --codex-only       Install only into the Codex skills root",
    "  --claude-only      Install only into the Claude Code skills root",
    "  --openclaw-only    Install only into the OpenClaw skills root",
    "  --hermes-only      Install only into the Hermes project-management root",
    "  -h, --help         Show this help",
    "",
    "CODEX_HOME overrides the Codex root only.",
  ].join("\n");
}

function parseArgs(argv) {
  const options = {
    force: false,
    target: null,
    only: null,
    help: false,
  };
  const onlyFlags = {
    "--codex-only": "codex",
    "--claude-only": "claude",
    "--openclaw-only": "openclaw",
    "--hermes-only": "hermes",
  };
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
    } else if (Object.prototype.hasOwnProperty.call(onlyFlags, arg)) {
      if (options.only && options.only !== onlyFlags[arg]) {
        throw new Error(
          "Only one of --codex-only / --claude-only / --openclaw-only / --hermes-only may be set",
        );
      }
      options.only = onlyFlags[arg];
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  if (options.target && options.only) {
    throw new Error("--target cannot be combined with --codex-only / --claude-only / --openclaw-only / --hermes-only");
  }
  return options;
}

function copyEntry(name, destinationRoot) {
  const source = path.join(packageRoot, name);
  const sourceStat = fs.statSync(source);
  const destination = sourceStat.isDirectory()
    ? path.join(destinationRoot, name)
    : path.join(destinationRoot, path.dirname(name), path.basename(name));
  fs.mkdirSync(path.dirname(destination), { recursive: true });
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
  const ctxCommand = `python3 ${shellQuote(path.join(destinationRoot, "scripts", "pingcode_ctx.py"))}`;
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
    const rewritten = original
      .replaceAll("python3 scripts/pingcode_ctx.py", ctxCommand)
      .replaceAll("python3 scripts/pingcode.py", cliCommand);
    if (rewritten !== original) {
      fs.writeFileSync(file, rewritten);
    }
  }
}

function installAliasSkill(destinationRoot) {
  const aliasRoot = path.join(path.dirname(destinationRoot), aliasName);
  fs.rmSync(aliasRoot, { recursive: true, force: true });
  fs.mkdirSync(aliasRoot, { recursive: true });
  for (const entry of aliasSkillEntries) {
    const source = path.join(packageRoot, entry);
    const destination = path.join(aliasRoot, path.basename(entry));
    fs.copyFileSync(source, destination);
  }
  const cliCommand = `python3 ${shellQuote(path.join(destinationRoot, "scripts", "pingcode.py"))}`;
  const ctxCommand = `python3 ${shellQuote(path.join(destinationRoot, "scripts", "pingcode_ctx.py"))}`;
  const skillDoc = path.join(aliasRoot, "SKILL.md");
  const original = fs.readFileSync(skillDoc, "utf8");
  fs.writeFileSync(
    skillDoc,
    original
      .replaceAll("python3 scripts/pingcode_ctx.py", ctxCommand)
      .replaceAll("python3 scripts/pingcode.py", cliCommand),
  );
  return aliasRoot;
}

function installToTarget(targetDir, options) {
  if (fs.existsSync(targetDir) && !options.force) {
    const error = new Error(
      `PingCode skill already exists at ${targetDir}. Re-run with --force to overwrite it.`,
    );
    error.code = "EEXIST_TARGET";
    throw error;
  }
  fs.rmSync(targetDir, { recursive: true, force: true });
  fs.mkdirSync(targetDir, { recursive: true });
  for (const entry of sourceEntries) {
    copyEntry(entry, targetDir);
  }
  rewriteInstalledDocs(targetDir);
  const aliasTarget = installAliasSkill(targetDir);
  return { mainTarget: targetDir, aliasTarget };
}

function printCredentialGuidance() {
  console.log("");
  console.log("Configure PingCode credentials before use:");
  console.log('  export PINGCODE_CLIENT_ID="..."');
  console.log('  export PINGCODE_CLIENT_SECRET="..."');
  console.log("");
  console.log('For "my" requests, also configure:');
  console.log('  export PINGCODE_USER_ID="..."');
  console.log('  export PINGCODE_USER_NAME="..."');
}

function runMultiRootInstall(options) {
  const roots = defaultAgentRoots();
  const keys = options.only ? [options.only] : AGENT_KEYS;
  const successes = [];
  const failures = [];

  for (const key of keys) {
    const root = roots[key];
    const mainTarget = path.join(root.skillsRoot, skillName);
    try {
      const result = installToTarget(mainTarget, options);
      successes.push({
        key,
        label: root.label,
        mainTarget: result.mainTarget,
        aliasTarget: result.aliasTarget,
      });
    } catch (error) {
      failures.push({
        key,
        label: root.label,
        target: mainTarget,
        message: error.message,
      });
    }
  }

  console.log("Install summary:");
  for (const item of successes) {
    console.log(`  [ok]   ${item.label}: ${item.mainTarget}`);
    console.log(`         ${item.label} (pingcode-ctx): ${item.aliasTarget}`);
  }
  for (const item of failures) {
    console.error(`  [fail] ${item.label}: ${item.target}`);
    console.error(`         ${item.message}`);
  }

  if (successes.length > 0) {
    printCredentialGuidance();
  }

  if (failures.length === 0) {
    return 0;
  }
  if (successes.length === 0) {
    return 1;
  }
  // Partial success: surface a non-zero exit so CI / agents can detect it.
  return 2;
}

function runSingleTargetInstall(options) {
  const target = options.target;
  try {
    const result = installToTarget(target, options);
    console.log(`Installed PingCode skill to ${result.mainTarget}`);
    console.log(`Installed PingCode context skill to ${result.aliasTarget}`);
    printCredentialGuidance();
    return 0;
  } catch (error) {
    if (error.code === "EEXIST_TARGET") {
      console.error(error.message);
      return 1;
    }
    throw error;
  }
}

function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage());
    return 0;
  }
  if (options.target) {
    return runSingleTargetInstall(options);
  }
  return runMultiRootInstall(options);
}

try {
  process.exitCode = main();
} catch (error) {
  console.error(`error: ${error.message}`);
  console.error("");
  console.error(usage());
  process.exitCode = 1;
}
