#!/usr/bin/env bash
set -euo pipefail

ensure_swap() {
  local size="${1:-2G}"
  if swapon --show | grep -q "/swapfile"; then
    echo "Swapfile already active."
    return 0
  fi

  echo "Configuring ${size} swapfile..."
  fallocate -l "${size}" /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=2048
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile

  if ! grep -q "/swapfile" /etc/fstab; then
    echo "/swapfile swap swap defaults 0 0" >> /etc/fstab
  fi
  echo "Swapfile activated."
}

create_service_user() {
  if ! id -u lectify >/dev/null 2>&1; then
    echo "Creating system user lectify..."
    useradd -r -s /sbin/nologin -d /opt/lectify lectify
  fi
  mkdir -p /opt/lectify
  chown -R lectify:lectify /opt/lectify
}

install_python311() {
  echo "Installing Python 3.11..."
  dnf install -y python3.11 python3.11-pip
}

install_node20() {
  echo "Installing Node.js 20..."
  dnf install -y nodejs20
  local node_bin
  node_bin="$(command -v node-20 || command -v node)"
  ln -sf "${node_bin}" /usr/local/bin/node
}

fetch_asset() {
  local bucket="$1"
  local key="$2"
  local dest="$3"
  local is_archive="${4:-true}"

  echo "Fetching asset s3://${bucket}/${key} -> ${dest}..."
  mkdir -p "$(dirname "${dest}")"

  if [ "${is_archive}" = "true" ]; then
    local tmp_zip="/tmp/asset-$$.zip"
    aws s3 cp "s3://${bucket}/${key}" "${tmp_zip}"
    mkdir -p "${dest}"
    unzip -q -o "${tmp_zip}" -d "${dest}"
    rm -f "${tmp_zip}"
  else
    aws s3 cp "s3://${bucket}/${key}" "${dest}"
  fi
}

write_env_file() {
  local dest="$1"
  echo "Writing environment file to ${dest}..."
  mkdir -p "$(dirname "${dest}")"
  cat > "${dest}"
  chmod 0640 "${dest}"
  chown root:lectify "${dest}" 2>/dev/null || true
}

make_venv() {
  local venv_path="$1"
  local req_path="$2"
  echo "Creating virtualenv at ${venv_path}..."
  python3.11 -m venv "${venv_path}"
  "${venv_path}/bin/pip" install --no-cache-dir -r "${req_path}"
  chown -R lectify:lectify "${venv_path}"
}

install_units() {
  local units_dir="$1"
  echo "Installing systemd units from ${units_dir}..."
  cp -f "${units_dir}"/*.service /etc/systemd/system/
  systemctl daemon-reload
}
