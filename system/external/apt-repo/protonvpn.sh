# ProtonVPN — VPN client
NAME="ProtonVPN"
DESCRIPTION="Proton VPN desktop client"
PACKAGES="proton-vpn-gnome-desktop"
CHECK="proton-vpn-gnome-desktop"

setup_repo() {
  local tmp_deb
  tmp_deb="$(mktemp --suffix=.deb)"
  wget -q -O "$tmp_deb" "https://repo.protonvpn.com/debian/dists/stable/main/binary-all/protonvpn-stable-release_1.0.6_all.deb"
  sudo dpkg --force-confnew -i "$tmp_deb"
  rm -f "$tmp_deb"
  if [ -f /etc/apt/sources.list.d/protonvpn-stable.sources ]; then
    sudo sed -i '/^Enabled:[[:space:]]*no/d' /etc/apt/sources.list.d/protonvpn-stable.sources
  fi
}
