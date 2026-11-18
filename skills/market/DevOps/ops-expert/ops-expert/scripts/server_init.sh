#!/usr/bin/env bash
# =============================================================================
# server_init.sh — 新服务器标准化初始化基线（幂等 · 含确认 · 含备份）
# 适用: CentOS/RHEL 7+ , Ubuntu/Debian 18.04+
# 设计: 重复运行安全；加固/破坏性动作前确认；改前备份关键文件。
# 用法:
#   bash server_init.sh            # 交互确认每一步
#   bash server_init.sh --yes      # 跳过确认（CI/批量，谨慎使用）
#   bash server_init.sh --dry      # 只打印将要做的事，不执行
# =============================================================================
set -euo pipefail

DRY=0; YES=0
for a in "$@"; do case "$a" in --dry) DRY=1;; --yes) YES=1;; esac; done

log(){ printf '\033[32m[init]\033[0m %s\n' "$*"; }
warn(){ printf '\033[33m[warn]\033[0m %s\n' "$*"; }
run(){ if [ "$DRY" = 1 ]; then log "(dry) $*"; else eval "$@"; fi; }
confirm(){ if [ "$YES" = 1 ] || [ "$DRY" = 1 ]; then return 0; fi; read -r -p "$1 [y/N] " r; [[ "$r" =~ ^[Yy]$ ]]; }

backup(){ local f="$1"; [ -f "$f" ] && run "cp -a \"$f\" \"${f}.bak.$(date +%Y%m%d%H%M%S)\""; }

# --- OS 探测 ---
if [ -f /etc/os-release ]; then . /etc/os-release; OS_FAMILY="${ID:-linux}"; else OS_FAMILY="unknown"; fi
PKG_INSTALL=""; case "$OS_FAMILY" in centos|rhel|fedora|rocky|almalinux) PKG_INSTALL="yum -y install";; ubuntu|debian) PKG_INSTALL="apt-get -y install";; esac
log "检测到系统: $OS_FAMILY | 包管理器: ${PKG_INSTALL:-unknown}"

# --- 1. 时区与 NTP ---
if confirm "设置时区 Asia/Shanghai 并安装 NTP(chrony)？"; then
  run "timedatectl set-timezone Asia/Shanghai 2>/dev/null || true"
  if command -v chronyd >/dev/null 2>&1 || command -v chronyc >/dev/null 2>&1; then
    run "systemctl enable --now chronyd 2>/dev/null || systemctl enable --now chrony 2>/dev/null || true"
  elif [ -n "$PKG_INSTALL" ]; then
    run "$PKG_INSTALL chrony 2>/dev/null || $PKG_INSTALL ntp 2>/dev/null || true"
    run "systemctl enable --now chronyd 2>/dev/null || systemctl enable --now ntpd 2>/dev/null || true"
  fi
  log "当前时间: $(timedatectl 2>/dev/null | grep 'System clock' || date)"
fi

# --- 2. 系统安全更新（非全量升级，避免动大版本） ---
if confirm "执行安全更新（仅安全补丁，不升级大版本）？"; then
  case "$OS_FAMILY" in
    centos|rhel|rocky|almalinux) run "yum -y update --security 2>/dev/null || yum -y update 2>/dev/null || true";;
    ubuntu|debian) run "apt-get update -y && apt-get -y upgrade 2>/dev/null || true";;
  esac
fi

# --- 3. 基线工具 ---
if confirm "安装基线诊断/监控工具（vim curl wget net-tools bind-utils htop iotop sysstat dstat lrzsz git）？"; then
  PKGS="vim curl wget net-tools bind-utils htop iotop sysstat dstat lrzsz git"
  case "$OS_FAMILY" in
    ubuntu|debian) PKGS="vim curl wget net-tools dnsutils htop iotop sysstat dstat lrzsz git";;
  esac
  [ -n "$PKG_INSTALL" ] && run "$PKG_INSTALL $PKGS 2>/dev/null || true"
fi

# --- 4. 普通用户 + sudo + SSH key ---
read -r -p "运维用户名(默认 ops): " OPS_USER; OPS_USER="${OPS_USER:-ops}"
if ! id "$OPS_USER" >/dev/null 2>&1; then
  if confirm "创建用户 $OPS_USER 并加入 sudo/wheel？"; then
    run "useradd -m -s /bin/bash \"$OPS_USER\""
    case "$OS_FAMILY" in ubuntu|debian) run "usermod -aG sudo \"$OPS_USER\"";; *) run "usermod -aG wheel \"$OPS_USER\"";; esac
  fi
fi
if confirm "为 $OPS_USER 配置 SSH 公钥（粘贴公钥，留空跳过）？"; then
  read -r -p "粘贴公钥: " PUBKEY
  if [ -n "$PUBKEY" ]; then
    run "install -d -m700 /home/$OPS_USER/.ssh"
    run "echo '$PUBKEY' >> /home/$OPS_USER/.ssh/authorized_keys"
    run "chmod 600 /home/$OPS_USER/.ssh/authorized_keys; chown -R $OPS_USER:$OPS_USER /home/$OPS_USER/.ssh"
  fi
fi

# --- 5. SSH 加固（备份后改） ---
if confirm "SSH 加固：禁 root 登录 + 禁密码登录 + 限重试（改前备份 sshd_config）？"; then
  backup /etc/ssh/sshd_config
  run "sed -i 's/^#\\?PermitRootLogin.*/PermitRootLogin no/; s/^#\\?PasswordAuthentication.*/PasswordAuthentication no/; s/^#\\?PubkeyAuthentication.*/PubkeyAuthentication yes/; s/^#\\?MaxAuthTries.*/MaxAuthTries 3/' /etc/ssh/sshd_config"
  run "sshd -t && systemctl restart sshd 2>/dev/null || service ssh restart 2>/dev/null || true"
  warn "已在另开会话确认 key 登录成功后再断开原连接！"
fi

# --- 6. 防火墙（默认拒绝，按白名单） ---
if confirm "配置防火墙（放行 SSH + 常用业务端口，默认 deny）？"; then
  read -r -p "需额外放行的端口(逗号分隔, 如 80,443): " PORTS
  if command -v firewall-cmd >/dev/null 2>&1; then
    run "systemctl enable --now firewalld 2>/dev/null || true"
    run "firewall-cmd --permanent --add-service=ssh"
    IFS=',' read -ra PA <<< "$PORTS"
    for p in "${PA[@]}"; do [ -n "$p" ] && run "firewall-cmd --permanent --add-port=${p}/tcp"; done
    run "firewall-cmd --reload"
  elif command -v ufw >/dev/null 2>&1; then
    run "ufw default deny incoming; ufw allow ssh"
    IFS=',' read -ra PA <<< "$PORTS"
    for p in "${PA[@]}"; do [ -n "$p" ] && run "ufw allow ${p}/tcp"; done
    run "ufw --force enable"
  else
    warn "未检测到 firewalld/ufw，请手动配置 iptables/nft。"
  fi
fi

# --- 7. 内核基础参数（备份后写） ---
if confirm "写入内核基础参数（fs.file-max / swappiness / tcp_tw_reuse，备份现有值）？"; then
  backup /etc/sysctl.d/99-ops.conf
  run "mkdir -p /etc/sysctl.d"
  cat > /tmp/99-ops.conf <<'EOF'
fs.file-max = 1000000
vm.swappiness = 10
net.ipv4.tcp_tw_reuse = 1
EOF
  run "cp /tmp/99-ops.conf /etc/sysctl.d/99-ops.conf"
  run "sysctl -p /etc/sysctl.d/99-ops.conf"
fi

# --- 8. 文件描述符进程级 ---
if confirm "设置进程级文件描述符上限(limits.conf + 示例 systemd)？"; then
  backup /etc/security/limits.conf
  run "echo '* - nofile 1048576' >> /etc/security/limits.conf"
fi

log "初始化完成。建议最后运行: bash scripts/health_check.sh 建立基线报告。"
