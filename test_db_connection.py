#!/usr/bin/env python3
"""
Script to test database connection using settings from config.ini
"""
import os
import sys
import logging
import configparser
import pyodbc
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('test_db_connection')

def get_config_path():
    """Find config.ini in common locations"""
    possible_paths = [
        Path('config.ini'),
        Path('config/config.ini'),
        Path('/etc/waproprint/config.ini'),
        Path.home() / '.config/waproprint/config.ini',
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    return None

def test_connection(config_path):
    """Test database connection using settings from config.ini"""
    if not os.path.exists(config_path):
        logger.error(f"Config file not found: {config_path}")
        return False
    
    config = configparser.ConfigParser()
    try:
        config.read(config_path)
        
        # Get database configuration
        db_config = config['DATABASE']
        server = db_config.get('server', '')
        database = db_config.get('database', '')
        username = db_config.get('username', '')
        password = db_config.get('password', '')
        driver = db_config.get('driver', 'FreeTDS')
        
        logger.info(f"Testing connection to server: {server}")
        logger.info(f"Database: {database}")
        logger.info(f"Driver: {driver}")
        
        # Build connection string
        conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        
        if username and password:
            conn_str += f"UID={username};PWD={password};"
        else:
            conn_str += "Trusted_Connection=yes;"
        
        logger.info("Attempting to connect to database...")
        
        # Try to establish connection
        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            cursor = conn.cursor()
            
            # Test query
            cursor.execute("SELECT @@VERSION")
            version = cursor.fetchone()[0]
            
            logger.info("\nCONNECTION SUCCESSFUL!")
            logger.info(f"SQL Server Version: {version}")
            
            # Get database name
            cursor.execute("SELECT DB_NAME()")
            db_name = cursor.fetchone()[0]
            logger.info(f"Connected to database: {db_name}")
            
            # Get tables count
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_type = 'BASE TABLE'""")
            table_count = cursor.fetchone()[0]
            logger.info(f"Number of tables in database: {table_count}")
            
            cursor.close()
            conn.close()
            return True
            
        except pyodbc.Error as e:
            logger.error("\nCONNECTION FAILED!")
            logger.error(f"Error details: {str(e)}")
            logger.error("\nConnection string used: %s", conn_str)
            logger.error("\nTroubleshooting steps:")
            logger.error("1. Verify the SQL Server is running and accessible from this machine")
            logger.error("2. Check if the server name/IP and port are correct")
            logger.error("3. Verify the database name is correct")
            logger.error("4. Check if the SQL Server allows remote connections")
            logger.error("5. Verify the username and password are correct")
            logger.error("6. Check if the SQL Server port (default 1433) is not blocked by firewall")
            logger.error("7. Try running: telnet <server_ip> 1433 to test basic connectivity")
            return False
            
    except Exception as e:
        logger.error(f"Error reading config file: {str(e)}")
        return False

def main():
    print("=== Database Connection Tester ===\n")
    
    # Find config file
    config_path = get_config_path()
    if not config_path:
        print("Error: config.ini not found in any of the expected locations.")
        print("Please make sure the config file exists or specify the path as an argument.")
        print("\nSearched locations:")
        print("- ./config.ini")
        print("- ./config/config.ini")
        print("- /etc/waproprint/config.ini")
        print("- ~/.config/waproprint/config.ini")
        return 1
    
    print(f"Using config file: {config_path}\n")
    
    # Test connection
    success = test_connection(config_path)
    
    if success:
        print("\nConnection test completed successfully!")
        return 0
    else:
        print("\nConnection test failed. See error messages above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
