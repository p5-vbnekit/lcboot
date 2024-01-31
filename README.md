# p5-lcboot
Minimalistic file system for booting guests (qemu, lxc, etc.)

### Motivation
There are many pain with rootless [`libvirt_lxc` containers](https://libvirt.org/drvlxc.html).
They cannot use `/dev/loop`, `overlay`, `user xattr`, etc.
This toolbox was primarily developed as a way to downgrade privileges to rootless inside a rootfull `lxc-libvirt` container.

### Features
- Configurable `/sbin/init` - `p5.lcboot.init` script.
  - hooking in "tolerant" mode - `p5.lcboot.tolerant` script.
  - re-`unshare` namespaces - `uts`, `ipc`, `user` (`uid`/`gid` mapping), `mount`, `cgroup` (isolate it), `network`.
- Trivial `/dev/initctl` provider implementation - `p5.lcboot.initctl` (`/sbin/initctl`) script.
- `/sbin/overlay` - `p5.lcboot.overlay` helper script.
- [`/sbin/mount-idmapped`](https://github.com/brauner/mount-idmapped) binary.

### Typical launch
- Provide `p5.lcboot` image into `/` of your container (read-only if you wish).
- Provide target (next hop, real guest) root into `/mnt/root` of your container (read-only if you wish).
- Provide read/write cache directory (ram, host fs, etc.) into `/mnt/cache` of your container.
- Set container entry point to `/sbin/init`.
- Enjoy.

### Advanced configuration
- Set container entry point to `/bin/sh`.
- Use `--help` key for any `p5.lcboot.*` executable (["python3/scripts" directory in source code](python3/scripts)).
- Check out the [sources](python3), there is nothing complicated there. =)
- Configure boot via your own `/mnt/init.yml`.

#### Example of `/mnt/init.yml`:
```yaml
# "Next hop" root file system path.
#   For example, may be mounted to guest via `/dev/loop` readonly source.
#   And/or may usually be (re)mounted several times during "setup.before" step.
root: /mnt/root # default is {path: "/mnt/root", mode: "pivot"}

# Let's enable uid/gid mapping for unshare system call (disabled by default).
id_map:
  users: 0 1000000 65536
  groups:
  - 0 1000000 # `internal` `external` (size = 1 by default)
  - 1 1000001 1 # `internal` `external` `size`
  - internal: 2
    external: 1000002
    # size: 1 # default too
  - internal: 3
    external: 1000003
    size: 65533

initctl: false # default; replace to `true` if you want to spawn `/dev/initctl` (via `p5.lcboot.initctl`) right now

# First step is "setup".
#   At this step `p5.lcboot.init` will:
#   - mount /mnt/root/proc`;
#   - invoke `unshare` system call;
#   - mount new `/mnt/root/sys`, `/mnt/root/dev`.
#   After this step `p5.lcboot.init` will change root to `/mnt/root` via `pivot_root` system call.
#   You may change root.mode to `chroot` or `none`.
setup:
  # Let's set `setup` mode. Replace it to `none` for skip it and do some in `before` and `exec.before`.
  mode: auto # default

  # Custom "setup" instructions before this step.
  #   In this case we hope that `/mnt/root` is already populated by container owner,
  #   but we want to remap some uids/gids and apply some fs layers.
  before:
  # Let's remap users/groups on `/mnt/root`.
  - mount-idmapped --map-mount=b:0:1000000:65536 /mnt/root /mnt/root

  # Remount `/mnt/root` as `overlayfs` with:
  #   - `lower` ro source layers: `/mnt/root` under `mnt/layers/0` under `/mnt/layers/1`;
  #   - `upper` rw layer: `/mnt/cache/overlay/upper`;
  #   - `workdir`: `/mnt/cache/overlay/temp/w`;
  #   - destination: `/mnt/root`.
  - overlay -- /mnt/layers/0 /mnt/layers/1

# Last step is "exec".
exec:
  # Of course, you can do something before `exec`.
  before:
  - echo "Hello, 'next hop' root!"
  - ["echo", "We are ready to boot `systemd` now."]
  - command: bash -e # we have `bash` on "next hop" root
    input: |
      echo 'Yeah! Only now '"it's"' interpreted by real shell ('"$0"')!'
      echo 'This script received via stdin.'
      echo "Date is `date`"
  - - sh
    - -ec
    - "echo 'This script received via `cli` key.'; echo Shell is \"$0\"; echo \"Date is `date`\""

  # Let's set custom `exec` system call command.
  # Also, you can override it or append arguments via `cli`, use `--help` key.
  command: /lib/systemd/systemd --system # "/sbin/init" by default
```
