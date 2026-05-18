---
name: spell-creator
description: "Create or revise Owl spells: concise SKILL.md files with clear trigger descriptions and optional progressive disclosure."
---

# Spell Creator

Use this spell when creating or updating a spell.

## Workflow

### 1. Capture Intent

Extract what is already known from the conversation or existing files. Ask only
for missing information that changes the spell.

Decide:

- What task the spell helps an agent perform.
- When it should trigger, including user phrases, file types, tools, or project
  contexts.
- What output or workflow the agent should produce.
- What edge cases, dependencies, or validation steps matter.

For an existing spell, preserve the directory name and frontmatter `name` unless
the user explicitly wants a rename.

### 2. Write Frontmatter

A spell is a directory containing `SKILL.md`:

```text
spell-name/
  SKILL.md
```

The file must have YAML frontmatter followed by Markdown:

```markdown
---
name: spell-name
description: "Do X for Y. Use when the user asks for A, mentions B, or needs C."
---

# Spell Title

Core instructions go here.
```

- `name` is required, must match the parent directory, and must use lowercase
  letters, numbers, and single hyphens only.
- `description` is required, non-empty, and should say both what the spell does
  and when to use it. Put trigger terms here, because agents see metadata before
  the body.
- Quote descriptions that contain colons or other YAML-sensitive characters.
- Add optional fields like `compatibility`, `license`, or `metadata` only when
  they carry real information.

Locations:

- User reusable spells: `$OWL_HOME/spells/<relative-path>/SKILL.md`
- Project-local spells: `./.owl/spells/<relative-path>/SKILL.md`
- Built-in Owl spells: `src/owl_spells/<relative-path>/SKILL.md`

Project spells override user spells, and user spells override built-ins by
relative path. Use `OWL_PROJECT_ROOT` when creating a project-local spell from
outside the project root.

### 3. Write Instructions

Make the body an executable operating procedure, not a loose reference note.
Prefer numbered steps over free-form advice.

Include only:

- Entry conditions: what the agent should check before starting.
- The core workflow, in order.
- Decision points that affect the workflow.
- Commands, formats, or examples the agent is likely to need.
- Verification steps and clear completion criteria.
- Short reasons for instructions that would otherwise look arbitrary.

Avoid:

- Generic advice the model already knows.
- README, changelog, or install-guide files inside a spell.
- Rigid all-caps rules unless the failure mode is genuinely severe.

A strong body lets an agent answer: "What do I do first, what do I inspect or
run, how do I choose between paths, how do I know I am done?"

Use progressive disclosure for larger skills:

- Put only routing and core workflow in `SKILL.md`.
- Put deterministic or repeated code in `scripts/`.
- Put detailed docs, schemas, or variant-specific guidance in `references/`.
- Put templates or reusable output resources in `assets/`.
- Link reference files directly from `SKILL.md` and say when to read them.

If every test case makes the agent recreate the same helper code or lookup
table, bundle it once rather than teaching the agent to rewrite it.

### 4. Validate And Iterate

Check that Owl discovers and casts the spell:

```bash
owl spells list <parent-path> --all --format json
owl spells cast <relative-path>
```

Also inspect the frontmatter as YAML. The metadata should be enough for an agent
to decide whether to load the spell without reading the body.

For meaningful changes:

1. Write 2-3 realistic prompts before judging the spell.
2. Include at least one should-trigger case and one near-miss that should not
   trigger.
3. Run or mentally simulate the workflow against those prompts.
4. Revise by removing vague guidance, adding missing edge cases, or moving bulky
   detail into references.
