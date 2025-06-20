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

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    warning "Not running as root. Some commands might need sudo privileges."
    SUDO="sudo"
else
    SUDO=""
fi

# Detect Linux distribution
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    OS_ID=$ID
else
    error "Could not detect Linux distribution. This script supports Debian/Ubuntu and RedHat/CentOS."
fi

# Install system dependencies
status "Detected OS: $OS $VER ($OS_ID)"

# Update package lists
status "Updating package lists"
if [ "$OS_ID" = "ubuntu" ] || [ "$OS_ID" = "debian" ]; then
    $SUDO apt-get update
elif [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "centos" ]; then
    $SUDO yum check-update || true
else
    warning "Unsupported distribution. Trying to continue with common packages..."
fi

# Install required system packages
status "Installing required system packages"
if [ "$OS_ID" = "ubuntu" ] || [ "$OS_ID" = "debian" ]; then
    $SUDO apt-get install -y \
        python3-pip \
        python3-venv \
        tdsodbc \
        unixodbc \
        unixodbc-dev \
        freetds-dev \
        freetds-bin \
        wkhtmltopdf \
        imagemagick \
        ghostscript \
        libmagickwand-dev \
        libcups2-dev \
        build-essential \
        libssl-dev \
        libffi-dev \
        python3-dev \
        dnsutils \
        telnet \
        arp-scan \
        netdiscover \
        nmap || warning "Failed to install some packages"
elif [ "$OS_ID" = "rhel" ] || [ "$OS_ID" = "centos" ]; then
    $SUDO yum install -y \
        python3-pip \
        python3-virtualenv \
        unixODBC \
        unixODBC-devel \
        freetds \
        freetds-devel \
        wkhtmltopdf \
        ImageMagick \
        ghostscript \
        gcc \
        openssl-devel \
        libffi-devel \
        python3-devel \
        bind-utils \
        nmap-ncat \
        nmap || warning "Failed to install some packages"
fi

# Configure FreeTDS
status "Configuring FreeTDS"
if [ -f /etc/odbcinst.ini ]; then
    $SUDO cp /etc/odbcinst.ini /etc/odbcinst.ini.bak
fi

$SUDO tee /etc/odbcinst.ini > /dev/null <<EOL
[FreeTDS]
Description = FreeTDS Driver
Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so
Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so
FileUsage = 1
EOL

# Create virtual environment
status "Setting up Python virtual environment"
# Remove existing venv if it exists
if [ -d "venv" ]; then
    status "Removing existing virtual environment"
    rm -rf venv || sudo rm -rf venv
fi

# Create venv with appropriate permissions
python3 -m venv venv || {
    status "Trying with sudo..."
    sudo python3 -m venv venv || error "Failed to create virtual environment"
    sudo chown -R $(whoami):$(id -gn) venv || error "Failed to set permissions on virtual environment"
}

source venv/bin/activate || error "Failed to activate virtual environment"

# Upgrade pip
status "Upgrading pip"
pip install --upgrade pip || warning "Failed to upgrade pip"

# Install Poetry if not installed
if ! command_exists poetry; then
    status "Installing Poetry"
    curl -sSL https://install.python-poetry.org | python3 - || error "Failed to install Poetry"
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install project with Poetry
status "Installing project dependencies with Poetry"
poetry install || error "Failed to install project dependencies"

# Create necessary directories
status "Creating necessary directories"
mkdir -p logs temp

# Set permissions
status "Setting permissions"
chmod +x *.py
chmod +x *.sh

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    status "Creating .env file"
    cat > .env <<EOL
# Database configuration
DB_SERVER=your_server_address
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

# Application settings
TEMP_DIR=./temp
LOG_LEVEL=INFO
EOL
    warning "Created .env file. Please update it with your configuration."
fi

# Create config.ini if it doesn't exist
if [ ! -f config.ini ]; then
    status "Creating config.ini"
    cat > config.ini <<EOL
[DATABASE]
driver = FreeTDS
server = your_server_address
database = your_database_name
trusted_connection = no
username = your_username
password = your_password

[PRINTING]
printer_name = YOUR_PRINTER
temp_folder = ./temp
check_interval = 5
EOL
    warning "Created config.ini. Please update it with your configuration."
fi

# Install systemd service if requested
read -p "Do you want to install as a systemd service? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    status "Installing systemd service"
    
    # Get the current user and working directory
    SERVICE_USER=$(whoami)
    WORKING_DIR=$(pwd)
    
    # Create systemd service file
    $SUDO tee /etc/systemd/system/waproprint.service > /dev/null <<EOL
[Unit]
Description=WaproPrint Service
After=network.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$WORKING_DIR
Environment="PATH=$WORKING_DIR/venv/bin"
ExecStart=$WORKING_DIR/venv/bin/python $WORKING_DIR/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOL

    # Reload systemd and enable service
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable waproprint
    
    echo -e "${GREEN}Service installed and enabled. To start the service, run:${NC}"
    echo "$SUDO systemctl start waproprint"
    echo -e "${GREEN}To view logs:${NC}"
    echo "$SUDO journalctl -u waproprint -f"
fi

# Print success message
echo -e "\n${GREEN}Installation completed successfully!${NC}"
echo -e "To activate the virtual environment, run:${NC}"
echo "source venv/bin/activate"
echo -e "\nTo run the application:${NC}"
echo "python main.py"

if [ -f .env ]; then
    echo -e "${YELLOW}Don't forget to update your .env and config.ini files with your configuration.${NC}"
fi
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
    $SUDO apt-get install -y tdsodbc unixodbc unixodbc-dev freetds-dev freetds-bin dnsutils telnet arp-scan netdiscover nmap
    
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
