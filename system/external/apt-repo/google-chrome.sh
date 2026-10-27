# Google Chrome — web browser
NAME="Google Chrome"
DESCRIPTION="Google Chrome stable browser"
PACKAGES="google-chrome-stable"
CHECK="google-chrome-stable"

setup_repo() {
  wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | \
    sudo gpg --dearmor --yes -o /usr/share/keyrings/google-chrome.gpg
  sudo rm -f /etc/apt/sources.list.d/google-chrome.list /etc/apt/sources.list.d/google-chrome.list.disabled
  sudo tee /etc/apt/sources.list.d/google-chrome.sources > /dev/null <<EOF
Types: deb
URIs: https://dl.google.com/linux/chrome/deb/
Suites: stable
Components: main
Architectures: $(dpkg --print-architecture)
Signed-By: /usr/share/keyrings/google-chrome.gpg
EOF
}
