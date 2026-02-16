# Connect this scat folder to a GitHub repo

Use these steps to push this project to GitHub (or connect an existing folder to a new repo).

## 1. Install Git

If Git is not installed: [Download Git for Windows](https://git-scm.com/download/win). During setup, choose **"Git from the command line and also from 3rd-party software"** so the `git` command works in Command Prompt and PowerShell.

## 2. Open a terminal in the scat folder

In Command Prompt or PowerShell:

```cmd
cd C:\Users\P\OneDrive\Desktop\scat-master
```

(Use your actual path to the `scat-master` folder.)

## 3. Turn the folder into a Git repo (if it isn’t already)

Check if Git is already set up:

```cmd
git status
```

- If you see **"not a git repository"**: initialize and make the first commit:

  ```cmd
  git init
  git add .
  git commit -m "Initial commit: scat with KPI and RACH"
  ```

- If `git status` works (shows files or "nothing to commit"): skip the above and go to step 4.

## 4. Create a new repo on GitHub

1. Go to [github.com](https://github.com) and sign in.
2. Click **"+"** (top right) → **New repository**.
3. Choose a name (e.g. `scat` or `scat-kpi`).
4. Leave **"Add a README"** and **".gitignore"** **unchecked** (you already have them).
5. Click **Create repository**.

## 5. Connect this folder to the GitHub repo

GitHub will show commands; use these (replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repo name):

```cmd
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Example: if your username is `jane` and the repo is `scat-kpi`:

```cmd
git remote add origin https://github.com/jane/scat-kpi.git
git branch -M main
git push -u origin main
```

## 6. If Git asks you to sign in

- **HTTPS:** GitHub no longer accepts account passwords. Use a **Personal Access Token** as the password:
  1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.
  2. **Generate new token**, enable `repo`, copy the token.
  3. When Git asks for a password, paste the token.
- **SSH (optional):** You can instead use an SSH key and a URL like `git@github.com:YOUR_USERNAME/YOUR_REPO.git`.

## Summary

| Step | Command / action |
|------|-------------------|
| 1 | Install Git (git-scm.com) |
| 2 | `cd` to your `scat-master` folder |
| 3 | If needed: `git init`, `git add .`, `git commit -m "Initial commit"` |
| 4 | On GitHub: create a new repo (no README/.gitignore) |
| 5 | `git remote add origin https://github.com/USER/REPO.git` |
| 6 | `git branch -M main` then `git push -u origin main` |

After this, your scat folder is connected to the GitHub repo. Use `git add .`, `git commit -m "message"`, and `git push` to send future changes.
