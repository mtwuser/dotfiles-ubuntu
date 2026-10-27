# Google Cloud CLI — gcloud SDK
NAME="Google Cloud CLI"
DESCRIPTION="Google Cloud SDK command-line tools"
PACKAGES="google-cloud-cli"
CHECK="google-cloud-cli"

setup_repo() {
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg | \
    sudo gpg --dearmor --yes -o /usr/share/keyrings/cloud.google.gpg
  sudo rm -f /etc/apt/sources.list.d/google-cloud-sdk.list /etc/apt/sources.list.d/google-cloud-sdk.list.disabled
  sudo tee /etc/apt/sources.list.d/google-cloud-sdk.sources > /dev/null <<EOF
Types: deb
URIs: https://packages.cloud.google.com/apt
Suites: cloud-sdk
Components: main
Signed-By: /usr/share/keyrings/cloud.google.gpg
EOF
}
