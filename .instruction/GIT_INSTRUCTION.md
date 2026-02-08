# 🔒 Git Safety Instructions for AI Assistant

## ❌ FORBIDDEN GIT COMMANDS - NEVER RUN THESE!

**AI Assistant MUST NEVER execute these commands under ANY circumstances:**

```bash
❌ git pull --force
❌ git reset --hard origin/main
❌ git reset --hard origin/master
❌ git reset --hard HEAD
❌ git checkout -- .
❌ git clean -fd
❌ git pull (without explicit confirmation)
❌ git clone (that would overwrite existing workspace)
❌ git fetch --force
❌ git rebase --force
❌ git checkout -f
❌ git restore --source=HEAD --worktree .
```

### ⚠️ Why These Are Dangerous:

1. **`git pull --force`** - Overwrites local changes with remote
2. **`git reset --hard`** - Permanently deletes uncommitted changes
3. **`git checkout -- .`** - Discards all local modifications
4. **`git clean -fd`** - Deletes untracked files and directories

**Result:** Loss of local work, code overwrites, potential data loss

---

## ✅ ALLOWED GIT COMMANDS (Read-Only & Safe)

AI Assistant MAY use these commands as they don't modify local files:

```bash
✅ git status          # Check repository status
✅ git log             # View commit history
✅ git log --oneline   # Compact commit history
✅ git diff            # Show uncommitted changes
✅ git diff --cached   # Show staged changes
✅ git branch          # List branches
✅ git branch -a       # List all branches
✅ git remote -v       # Show remote repositories
✅ git show <commit>   # Show specific commit
```

---

## 🛡️ AI Assistant Responsibilities

### What AI CAN Do:
- ✅ Read local files with `read_file` tool
- ✅ Edit local files with `replace_string_in_file` tool
- ✅ Create new files with `create_file` tool
- ✅ Run builds: `python`, `docker-compose`, `PyInstaller`
- ✅ Monitor logs and status
- ✅ Execute read-only git commands (status, log, diff)

### What AI CANNOT Do:
- ❌ Pull/fetch code from remote
- ❌ Reset or checkout files
- ❌ Clean untracked files
- ❌ Force-push or force any git operation
- ❌ Overwrite local source code from remote

---

## 📋 Safe Workflow for Developer

### Before Pushing to Git:

```bash
# 1. Check what changed
git status

# 2. Optional: Create backup
copy apps\pos\views.py apps\pos\views.py.backup
copy pos_launcher_qt\local_api.py pos_launcher_qt\local_api.py.backup

# 3. Add changes
git add .

# 4. Commit
git commit -m "feat: your commit message"

# 5. Push
git push origin main
```

### Handling Conflicts (Developer Only):

```bash
# If pull needed:
git fetch origin
git status

# Review conflicts manually
# Resolve using VS Code or merge tool
# NEVER use --force or --hard
```

---

## 🎯 Critical Files Modified in This Project

1. `apps/pos/views.py` - Receipt printing function
2. `apps/core/models.py` - POSTerminal print_to field
3. `apps/core/api_terminal.py` - Terminal config API
4. `pos_launcher_qt/local_api.py` - Local receipt API with date folders
5. `apps/core/migrations/0005_add_posterminal_print_to.py` - Database migration

**These files must NEVER be overwritten by git operations!**

---

## 📌 Summary

**AI Assistant Promise:**
> "I will ONLY read, edit, and create files locally. I will NEVER pull, reset, checkout, or clean files from git that could overwrite your local work."

**Developer Control:**
> You maintain full control over git operations. AI assists with code editing only.

---

**Last Updated:** February 8, 2026  
**Status:** 🔒 ENFORCED
