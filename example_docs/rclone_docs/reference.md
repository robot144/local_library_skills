# Command reference

::: {.callout-note}
Demo page, essentials only. For the complete, authoritative command
list and every flag, see [rclone.org/commands](https://rclone.org/commands/).
:::

| Command | What it does |
|---|---|
| `rclone config` | Interactive setup/editing of remotes. |
| `rclone copy SRC DST` | Copy new/changed files SRC → DST. Never deletes. |
| `rclone sync SRC DST` | Make DST identical to SRC. Can delete from DST. |
| `rclone move SRC DST` | Copy then delete from SRC. |
| `rclone ls REMOTE:PATH` | List files under PATH with size. |
| `rclone lsd REMOTE:` | List directories only. |
| `rclone lsl REMOTE:PATH` | List files with size, modification time, and path. |
| `rclone delete REMOTE:PATH` | Delete files under PATH (not the directory itself). |
| `rclone check SRC DST` | Compare SRC and DST, report differences without transferring. |
| `rclone mount REMOTE: /mnt/point` | Mount a remote as a local filesystem (Linux/macOS, needs FUSE). |
| `rclone version` | Print the installed version. |

## Useful flags

| Flag | Effect |
|---|---|
| `--dry-run` | Show what would happen, change nothing — always try this before a real `sync`. |
| `--interactive` | Prompt for confirmation before each destructive change. |
| `-P`, `--progress` | Show a live transfer progress display. |
| `--exclude PATTERN` | Skip files matching PATTERN. |

## Full reference

This table is deliberately short. For everything else — all commands,
every flag, and backend-specific options — see
[rclone.org/commands](https://rclone.org/commands/) and
[rclone.org/docs](https://rclone.org/docs/).
