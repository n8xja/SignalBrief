# Running Signal Brief with Docker: Step-by-Step Guide

This guide assumes you have never used Docker before. Follow the steps in order. Each step
says what to type, what you should see, and what to do if something goes wrong.

**Contents**

1. [What Docker is (and why use it)](#1-what-docker-is-and-why-use-it)
2. [Install Docker](#2-install-docker)
3. [Download the project](#3-download-the-project)
4. [Open a terminal in the project folder](#4-open-a-terminal-in-the-project-folder)
5. [Create your settings file](#5-create-your-settings-file-env)
6. [Build the image](#6-build-the-image)
7. [Run a test (dry run)](#7-run-a-test-dry-run)
8. [Create a WordPress draft](#8-create-a-wordpress-draft)
9. [Optional: use a saved web page](#9-optional-use-a-saved-web-page)
10. [Optional: use Docker Compose](#10-optional-use-docker-compose)
11. [Update to a newer version](#11-update-to-a-newer-version)
12. [Remove everything](#12-remove-everything)
13. [Troubleshooting](#13-troubleshooting)

**On a Mac?** Jump to the [Mac quick reference](#mac-quick-reference) for every command in order.

---

## 1. What Docker is (and why use it)

Docker packages an application together with everything it needs (here, Python and the
libraries the script uses) into a single bundle called an **image**. When you run an image,
Docker starts a **container**: an isolated copy of the application that runs and then goes away.

Using Docker means you don't have to install Python or any libraries on your computer, and the
tool behaves the same on Windows, macOS and Linux.

Two terms you'll see:

| Term | Meaning |
|---|---|
| **Image** | The packaged application. You **build** it once (step 6). |
| **Container** | A running copy of the image. You **run** one each time you summarize an article. |

---

## 2. Install Docker

Pick your operating system.

### Windows 10/11

1. Download **Docker Desktop for Windows** from https://www.docker.com/products/docker-desktop/
2. Run the installer and accept the defaults. If it asks to enable **WSL 2**, say yes. (WSL 2 is
   the Windows feature Docker uses to run Linux containers.)
3. Restart your computer if the installer asks.
4. Open **Docker Desktop** from the Start menu and wait until it says **Engine running**
   (bottom-left corner). Docker Desktop must be running whenever you use Docker.

### macOS

1. Download **Docker Desktop for Mac** from https://www.docker.com/products/docker-desktop/
   Choose **Apple Silicon** for M1/M2/M3/M4 Macs, or **Intel** for older Macs
   ( → About This Mac shows which you have).
2. Open the downloaded `.dmg` and drag **Docker** into **Applications**.
3. Open **Docker** from Applications and wait until the whale icon in the menu bar stops animating.
   Docker must be running whenever you use Docker.

### Linux (Ubuntu, Debian, or an AWS Lightsail server)

Run these commands one at a time:

```bash
# Download and run Docker's official install script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Let your user run Docker without typing sudo every time
sudo usermod -aG docker $USER
```

Then **log out and log back in** (or close and reopen your SSH session) so the group change takes
effect.

### Check that Docker works (all systems)

Open a terminal (see [step 4](#4-open-a-terminal-in-the-project-folder) if you're not sure how) and run:

```bash
docker --version
```

You should see something like `Docker version 27.x.x`. Then run:

```bash
docker run hello-world
```

You should see **"Hello from Docker!"** followed by a few lines of explanation. If you do, Docker
is installed correctly. If not, see [Troubleshooting](#13-troubleshooting).

---

## 3. Download the project

Choose **one** option.

**Option A: Download a ZIP (no Git needed)**

1. Go to https://github.com/n8xja/SignalBrief
2. Click the green **Code** button, then **Download ZIP**.
3. Unzip it somewhere easy to find, such as your Documents folder. You'll get a folder named
   `SignalBrief-main`.

**Option B: Use Git**

```bash
git clone https://github.com/n8xja/SignalBrief.git
```

This creates a folder named `SignalBrief`.

---

## 4. Open a terminal in the project folder

All the remaining commands are typed in a terminal, **from inside the project folder** (the
folder that contains `Dockerfile` and `summarize.py`).

> **Mac users:** use the built-in **Terminal** app. You don't need PowerShell. Every command in
> this guide labeled **macOS** or **macOS / Linux** works in Terminal as written. Skip anything
> labeled **Windows** or **PowerShell**. A complete list of Mac commands is in the
> [Mac quick reference](#mac-quick-reference).

**Windows**

1. Open the project folder in File Explorer.
2. Click in the address bar, type `powershell`, and press **Enter**.
   A PowerShell window opens already in that folder.

**macOS**

1. Open **Terminal**: press **Cmd+Space**, type `Terminal`, and press **Enter**
   (or go to Applications → Utilities → Terminal).
2. Type `cd ` (with a space after it), drag the project folder from Finder into the Terminal
   window, and press **Enter**. Terminal fills in the folder's path for you.

   If the folder is in Downloads, you can instead type:
   - ZIP download: `cd ~/Downloads/SignalBrief-main`
   - git clone: `cd ~/Downloads/SignalBrief`

**Linux**

```bash
cd ~/SignalBrief        # or wherever you put the folder
```

**Check you're in the right place.** Run `ls` (macOS/Linux) or `dir` (Windows). You should see
`Dockerfile`, `summarize.py` and `README.md` in the list.

---

## 5. Create your settings file (`.env`)

The tool reads your keys and WordPress details from a file named `.env`. You'll make it by copying
the template `.env.example`.

**Copy the template**

| System | Command |
|---|---|
| Windows (PowerShell) | `Copy-Item .env.example .env` |
| macOS / Linux | `cp .env.example .env` |

**Open it for editing**

| System | Command |
|---|---|
| Windows | `notepad .env` |
| macOS | `open -e .env` (opens in TextEdit; save with **Cmd+S**) |
| Linux | `nano .env` (save with **Ctrl+O**, **Enter**, exit with **Ctrl+X**) |

> **Mac tip:** Finder hides files whose names start with a dot, so you won't see `.env` there.
> Press **Cmd+Shift+.** (period) in Finder to show hidden files, or just use the Terminal commands
> above. `nano .env` also works on a Mac if you prefer editing inside Terminal.

**Fill in these values**, replacing the placeholders:

```ini
ANTHROPIC_API_KEY=sk-ant-your-real-key
WP_URL=https://your-site.example.com
WP_USER=your-wordpress-username
WP_APP_PASSWORD=abcd efgh ijkl mnop qrst uvwx
```

- **ANTHROPIC_API_KEY:** create one at https://platform.claude.com → **API keys**.
- **WP_APP_PASSWORD:** in WordPress, go to **Users → Profile → Application Passwords**, type a
  name such as "Article summarizer", click **Add New Application Password**, and copy the password
  it shows. (This is not your normal WordPress login password.)
- **WP_USER:** the account only needs the **Contributor** role. The safest setup is a separate
  user just for this tool; see [WordPress user role](../README.md#wordpress-user-role).
- Don't put quotes around the values or spaces around the `=`.

Save and close the file.

> **Keep `.env` private.** It holds your keys. It is never copied into the Docker image and is
> excluded from Git, so don't email it, share it or upload it anywhere.

---

## 6. Build the image

This step turns the project into a Docker image. You only need to do it **once**, and again
whenever you update the project.

Make sure Docker Desktop is running (Windows/macOS), then in the project folder run:

```bash
docker build -t signal-brief .
```

What each part means:

| Part | Meaning |
|---|---|
| `docker build` | Build an image from the `Dockerfile` |
| `-t signal-brief` | Name ("tag") the image `signal-brief` so you can refer to it later |
| `.` | Use the current folder. **Don't forget the dot at the end.** |

**What you'll see:** Docker downloads a small Python base image and installs the libraries. The
first build takes about 1–3 minutes depending on your connection; later builds are much faster.
It ends with lines like:

```
 => exporting to image
 => => naming to docker.io/library/signal-brief
```

**Check that the image exists:**

```bash
docker image ls signal-brief
```

You should see a row with `signal-brief` under **REPOSITORY** and `latest` under **TAG**.

**Check that it starts:**

```bash
docker run --rm signal-brief --help
```

You should see the tool's help text, starting with `usage: summarize.py`. Your image is ready.

---

## 7. Run a test (dry run)

A **dry run** fetches the article and prints the BLUF and key points, but **does not** post anything to
WordPress. Always do this first to check your API key works.

Replace the URL with a real article:

```bash
docker run --rm --env-file .env signal-brief https://example.com/article --dry-run
```

What each part means:

| Part | Meaning |
|---|---|
| `docker run` | Start a container from an image |
| `--rm` | Delete the container when it finishes, so they don't pile up |
| `--env-file .env` | Pass your settings from `.env` into the container |
| `signal-brief` | The image you built in step 6 |
| `https://...` | The article to summarize |
| `--dry-run` | Print only; don't post to WordPress |

**What you'll see** (after 10–30 seconds):

```
Fetched: Article headline (1234 words)

Working Title Written by Claude

BLUF: Bottom Line Up Front
Two or three short sentences: what happened, who is affected, and what to do.

Key Points
  • Point one
  • Point two
  • Point three
  • Point four
  • Point five

Read more <https://example.com/article>
```

---

## 8. Create a WordPress draft

When the dry run looks good, run the same command **without** `--dry-run`:

```bash
docker run --rm --env-file .env signal-brief https://example.com/article
```

The last line shows a link to the new draft:

```
Draft created (post 128): https://your-site.example.com/wp-admin/post.php?post=128&action=edit
```

Open the link, review and edit the post, then publish it from WordPress when you're ready.
The tool never publishes anything itself.

---

## 9. Optional: use a saved web page

Some sites block automated tools or need JavaScript, and the tool will tell you so. In that case,
save the page from your browser and give the tool the saved file.

1. In the project folder, create a folder named `pages`:
   - Windows: `mkdir pages`
   - macOS / Linux: `mkdir -p pages`
2. Save the article into the `pages` folder as `article.html`:

   | Browser | How to save |
   |---|---|
   | Safari (Mac) | **File → Save As…**, set **Format** to **Page Source**, name it `article.html` |
   | Chrome (Mac) | **Cmd+S**, set **Format** to **Webpage, HTML Only** |
   | Firefox (Mac) | **Cmd+S**, set the type to **Web Page, HTML only** |
   | Chrome / Edge (Windows, Linux) | **Ctrl+S**, choose **Webpage, HTML only** |

3. Run the command for your system. The `-v` option lets the container see your `pages` folder.

**macOS (Terminal) / Linux**

```bash
docker run --rm --env-file .env -v "$PWD/pages:/data" \
  signal-brief https://example.com/article --html-file article.html
```

Or as a single line:

```bash
docker run --rm --env-file .env -v "$PWD/pages:/data" signal-brief https://example.com/article --html-file article.html
```

`$PWD` means "the folder I'm in right now", so run this from the project folder.

**Windows (PowerShell)**

```powershell
docker run --rm --env-file .env -v "${PWD}\pages:/data" `
  signal-brief https://example.com/article --html-file article.html
```

Notes:
- Still pass the article's real URL: it's used for the **Read more** link.
- The `\` (macOS/Linux) and `` ` `` (PowerShell) at the end of the first line mean "the command
  continues on the next line". You can also type it all on one line without them.

---

### Or: use copied article text

If the tool says `Only N words of article text were found` and the article is clearly longer, or a
saved page doesn't work, give it the text directly:

1. On the article page, select the article text from the headline to the end (click before the
   headline, then **Shift+click** after the last paragraph) and copy it (**Cmd+C** / **Ctrl+C**).
2. Paste it into a new plain-text file named `article.txt` in the `pages` folder:
   - **Mac:** in Terminal, run `pbpaste > pages/article.txt` right after copying.
   - **Windows:** open Notepad, paste, and save as `article.txt` in the `pages` folder.
   - **Linux:** paste into any text editor and save as `pages/article.txt`.
3. Make sure the headline is on the first line (or add `--title "The headline"` to the command).
4. Run:

**macOS (Terminal) / Linux**

```bash
docker run --rm --env-file .env -v "$PWD/pages:/data" signal-brief https://example.com/article --text-file article.txt --dry-run
```

**Windows (PowerShell)**

```powershell
docker run --rm --env-file .env -v "${PWD}\pages:/data" signal-brief https://example.com/article --text-file article.txt --dry-run
```

---

## 10. Optional: use Docker Compose

Docker Compose comes with Docker Desktop (and with the Linux install script above). It reads the
settings from `docker-compose.yml`, so the commands are shorter: you don't need `--env-file` or
`-v`.

```bash
# Build (once, and after updates)
docker compose build

# Dry run
docker compose run --rm summarize https://example.com/article --dry-run

# Create the draft
docker compose run --rm summarize https://example.com/article

# Saved page (put it in the pages folder first)
docker compose run --rm summarize https://example.com/article --html-file article.html
```

---

## 11. Update to a newer version

1. Get the new code:
   - **ZIP:** download it again (step 3) and copy your `.env` file into the new folder.
   - **Git:** in the project folder, run `git pull`.
2. Rebuild the image:
   ```bash
   docker build -t signal-brief .
   ```

Your `.env` file is not affected by `git pull`.

---

## 12. Remove everything

To delete the image and free the disk space:

```bash
docker image rm signal-brief
```

To also remove the Python base image Docker downloaded during the build:

```bash
docker image prune -a
```

> `docker image prune -a` removes **all** images not used by a container, including ones from
> other projects. Skip it if you use Docker for other things.

---

## Mac quick reference

Every command a Mac user needs, in order. Type or paste them into the **Terminal** app; no
PowerShell needed. Replace `https://example.com/article` with the article you want, and
`~/Downloads/SignalBrief-main` with wherever your project folder is.

> Paste one line at a time. The Mac's Terminal (zsh) doesn't allow `#` comments on pasted lines,
> so the explanations are kept outside the command boxes.

### One-time setup

Install Docker Desktop first (step 2) and make sure it's running: you'll see the whale icon in the
menu bar.

1. Check Docker is installed and working:
   ```bash
   docker --version
   ```
   ```bash
   docker run hello-world
   ```
2. Go to the project folder:
   ```bash
   cd ~/Downloads/SignalBrief-main
   ```
3. Create your settings file, then edit it in TextEdit (save with **Cmd+S**):
   ```bash
   cp .env.example .env
   ```
   ```bash
   open -e .env
   ```
4. Create the folder for saved web pages:
   ```bash
   mkdir -p pages
   ```
5. Build the image (note the dot at the end):
   ```bash
   docker build -t signal-brief .
   ```

### Every time

1. Go to the project folder:
   ```bash
   cd ~/Downloads/SignalBrief-main
   ```
2. Preview the BLUF and key points (nothing is posted):
   ```bash
   docker run --rm --env-file .env signal-brief https://example.com/article --dry-run
   ```
3. Create the WordPress draft:
   ```bash
   docker run --rm --env-file .env signal-brief https://example.com/article
   ```
   If WordPress rejects the login, test only the WordPress connection:
   ```bash
   docker run --rm --env-file .env signal-brief --check-wp
   ```
4. If the site blocks the tool, save the page into `pages` as `article.html` (Safari: **File →
   Save As…**, **Format: Page Source**), then:
   ```bash
   docker run --rm --env-file .env -v "$PWD/pages:/data" signal-brief https://example.com/article --html-file article.html --dry-run
   ```
   Remove `--dry-run` to create the draft.
5. If it warns that only a few words were found, copy the article text instead. Select the article
   in the browser, press **Cmd+C**, then run:
   ```bash
   pbpaste > pages/article.txt
   ```
   ```bash
   docker run --rm --env-file .env -v "$PWD/pages:/data" signal-brief https://example.com/article --text-file article.txt --dry-run
   ```

### After updating the project

If you used `git clone`, get the update, then rebuild:
```bash
git pull
```
```bash
docker build -t signal-brief .
```
If you downloaded the ZIP, download it again, copy your `.env` into the new folder, and rebuild.

---

## 13. Troubleshooting

| Message or problem | What it means and how to fix it |
|---|---|
| `docker: command not found` or `'docker' is not recognized` | Docker isn't installed, or the terminal was opened before installing. Install it (step 2), then close and reopen the terminal. |
| `Cannot connect to the Docker daemon` or `error during connect` | Docker isn't running. On Windows/macOS, open Docker Desktop and wait for it to start. On Linux, run `sudo systemctl start docker`. |
| `permission denied while trying to connect to the Docker daemon socket` (Linux) | Your user isn't in the `docker` group yet. Run `sudo usermod -aG docker $USER`, then log out and back in. |
| `failed to read Dockerfile` or `open Dockerfile: no such file or directory` | You're not in the project folder. Go back to step 4 and use `ls` / `dir` to check you can see `Dockerfile`. |
| `"docker build" requires exactly 1 argument` | The dot at the end is missing. The command is `docker build -t signal-brief .` |
| `Unable to find image 'signal-brief:latest' locally` then `pull access denied` | The image hasn't been built yet, or was built under a different name. Run step 6. |
| `open .env: no such file or directory` | You're not in the project folder, or `.env` hasn't been created. Do step 5 from the project folder. On Windows, make sure Notepad didn't save it as `.env.txt`: run `dir` to check, and `Rename-Item .env.txt .env` if needed. |
| `Error: Missing setting ANTHROPIC_API_KEY` (or another setting) | That line is missing or empty in `.env`, or you forgot `--env-file .env`. |
| `WordPress says the username or password is wrong` or `WordPress did not receive the login` | Run `docker run --rm --env-file .env signal-brief --check-wp`, then follow [Fixing WordPress login errors](../README.md#fixing-wordpress-login-errors). |
| `Error: Could not find enough article text` or `The site refused the request` | The site blocks automated tools or needs JavaScript. Use a saved page or copied text (step 9). |
| `[warning] Only N words of article text were found` | Part of the article was missed. If the article is longer, use copied text with `--text-file` (step 9). |
| `The Claude API rejected the key`, `Model ... was not found`, or `out of credit` | See the [README troubleshooting](../README.md#troubleshooting) table. |
| `Error: The site did not respond in time` (or `Read timed out`) | The site's bot protection is stalling the request rather than refusing it. This isn't a Docker problem. Use a saved page (step 9). |
| `Error: Could not read --html-file` / file not found | The saved page isn't in the `pages` folder, the name doesn't match, or the `-v` part is missing. |
| Build fails while downloading (`TLS`, `timeout`, `connection reset`) | A network or proxy problem. Check your internet connection and try again. On a work network, ask IT whether Docker Hub (`registry-1.docker.io`) is allowed. |
| Mac: `Mounts denied` or `path ... is not shared from the host` | The project folder is outside your home folder (for example on an external drive). Move it into your home folder (Documents or Downloads), or add its location in **Docker Desktop → Settings → Resources → File sharing**. |
| Mac: Safari saved `article.webarchive` | Safari's default format is Web Archive, which the tool can't read. Save again with **Format: Page Source**. |
| Windows: build is very slow or Docker Desktop won't start | Make sure virtualization is enabled and WSL 2 is installed: run `wsl --install` in an administrator PowerShell, then restart. |

Still stuck? [Open an issue](https://github.com/n8xja/SignalBrief/issues) with the exact
command you ran and the full error message. **Remove any keys or passwords before posting.**
