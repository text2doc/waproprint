#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status messages
status() {
    echo -e "${GREEN}[*]${NC} $1"
}

error() {
    echo -e "${RED}[!] Error: $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[!] Warning: $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    warning "Not running as root. Some commands might need sudo privileges."
    SUDO=""
else
    SUDO="sudo"
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
else
    error "Could not detect Linux distribution. This script supports Debian/Ubuntu and RedHat/CentOS."
fi

# Install system dependencies
status "Detected OS: $OS $VER"

# Remove any existing Microsoft repository to prevent conflicts
$SUDO rm -f /etc/apt/sources.list.d/mssql-release.list \
           /etc/apt/sources.list.d/msprod.list \
           /etc/apt/trusted.gpg.d/microsoft* \
           /usr/share/keyrings/microsoft* \
           /etc/apt/sources.list.d/microsoft* \
           /etc/apt/trusted.gpg.d/microsoft* \
           /etc/apt/trusted.gpg.d/prod_* \
           /etc/apt/sources.list.d/prod_*

status "Updating package lists..."
$SUDO apt-get update

status "Installing system dependencies..."
if [[ "$OS" == *"Debian"* ]] || [[ "$OS" == *"Ubuntu"* ]]; then
    # Install FreeTDS as the ODBC driver (works with SQL Server)
    status "Installing FreeTDS ODBC driver..."
    $SUDO apt-get install -y tdsodbc unixodbc unixodbc-dev freetds-dev freetds-bin
    
    # Configure FreeTDS
    if [ -f "/etc/odbcinst.ini" ]; then
        status "Configuring ODBC driver..."
        cat <<EOF | $SUDO tee /etc/odbcinst.ini > /dev/null
[FreeTDS]
Description=FreeTDS Driver
Driver=/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so
Setup=/usr/lib/x86_64-linux-gnu/odbc/libtdsS.so
UsageCount=1
EOF
    fi
    
    # Verify installation
    if odbcinst -q -d -n "FreeTDS" &> /dev/null; then
        status "ODBC driver configured successfully"
    else
        warning "Failed to verify ODBC driver configuration. Manual configuration may be needed."
        warning "See: https://www.freetds.org/userguide/odbcconnattr.html"
    fi

    # Install other system dependencies
    $SUDO apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        build-essential \
        python3-dev \
        libmariadb-dev \
        libpq-dev \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        wget \
        curl \
        llvm \
        libncurses5-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libffi-dev \
        liblzma-dev \
        python3-openssl \
        git \
        unixodbc \
        unixodbc-dev \
        freetds-dev \
        tdsodbc \
        wkhtmltopdf \
        libmagickwand-dev \
        ghostscript \
        libcups2-dev
elif [[ "$OS" == *"Red Hat"* ]] || [[ "$OS" == *"CentOS"* ]] || [[ "$OS" == *"Fedora"* ]]; then
    $SUDO dnf install -y \
        python3 \
        python3-pip \
        python3-venv \
        gcc \
        python3-devel \
        mariadb-devel \
        postgresql-devel \
        openssl-devel \
        zlib-devel \
        bzip2-devel \
        readline-devel \
        sqlite-devel \
        wget \
        curl \
        llvm \
        ncurses-devel \
        xz \
        tk-devel \
        libffi-devel \
        xz-devel \
        git \
        unixODBC \
        unixODBC-devel \
        freetds \
        freetds-devel \
        wkhtmltopdf \
        ImageMagick \
        ghostscript \
        cups-devel
else
    warning "Unsupported distribution. You may need to install dependencies manually."
fi

# Setup Python virtual environment
status "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    status "Virtual environment created."
else
    warning "Virtual environment already exists. Using existing one."
fi

# Activate virtual environment
status "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and setuptools
status "Upgrading pip and setuptools..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
status "Installing Python dependencies..."
pip install -r requirements.txt

# Install the package in development mode
status "Installing waproprint in development mode..."
pip install -e .

# Verify installation
status "Verifying installation..."
if command -v waproprint &> /dev/null; then
    status "Installation completed successfully!"
    echo -e "\nTo start using waproprint, first activate the virtual environment with:"
    echo -e "${GREEN}source venv/bin/activate${NC}\n"
    echo -e "Then you can run: ${GREEN}waproprint --help${NC} to see available commands."
else
    warning "Installation completed, but 'waproprint' command not found in PATH."
    echo -e "You can still run the tool using: ${GREEN}python -m sql2html${NC}"
fi

echo -e "\n${GREEN}Installation complete!${NC}"
