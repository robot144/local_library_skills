# Concepts

::: {.callout-note}
Demo page — for the full picture (encryption, caching, server-side
operations, backend-specific options, and everything else), see the
real docs: [rclone.org/docs](https://rclone.org/docs/).
:::

## Remotes

A **remote** is a named, configured connection to a storage backend —
an S3 bucket, a Google Drive account, an SFTP server, or plain local
disk. You create one interactively:

```bash
rclone config
```

which walks through picking a backend type and its credentials, then
saves it under a name you choose (e.g. `myremote`) in rclone's config
file (`~/.config/rclone/rclone.conf` on Linux/macOS by default).

## Path syntax

Once a remote exists, you address it the same way you'd address a local
path, just with a `remote:` prefix:

```text
myremote:path/to/folder
myremote:                 # the remote's root
/local/path                # a plain local path - no colon, no remote
```

Every rclone command that takes a path accepts either form, in either
position — copying local-to-remote, remote-to-local, or even
remote-to-remote (server-side, when the backend supports it).

## copy vs. sync vs. move

These three look similar but have very different blast radii:

| Command | Behavior |
|---|---|
| `copy` | Copies anything new/changed from source to dest. Never deletes. |
| `sync` | Makes dest *identical* to source — can delete files from dest that aren't in source. |
| `move` | Like `copy`, then deletes the originals from source once copied. |

**`sync` is destructive on the destination side** — always run it with
`--dry-run` first on anything you're not sure about:

```bash
rclone sync --dry-run /local/path myremote:backup/
```
