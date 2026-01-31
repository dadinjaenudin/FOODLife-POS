"""
Terminal Configuration Manager
Reads terminal-config.json for persistent terminal settings
"""
import json
import os
from pathlib import Path


class TerminalConfig:
    """Singleton class for terminal configuration"""
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _find_config_file(self):
        """Find terminal-config.json in multiple locations"""
        # Priority order for config file location
        search_paths = [
            # 1. Same directory as manage.py (project root)
            Path(__file__).parent.parent / 'terminal-config.json',
            
            # 2. Next to executable (for frozen app)
            Path(os.path.dirname(os.path.abspath(__file__))).parent / 'terminal-config.json',
            
            # 3. Current working directory
            Path.cwd() / 'terminal-config.json',
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        # If not found, return default path (will create later)
        return search_paths[0]
    
    def _load_config(self):
        """Load configuration from terminal-config.json"""
        self._config_path = self._find_config_file()
        
        if self._config_path.exists():
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Warning: Failed to load terminal-config.json: {e}")
                self._config = self._get_default_config()
        else:
            # Create default config file
            self._config = self._get_default_config()
            self._save_config()
    
    def _get_default_config(self):
        """Get default configuration"""
        return {
            'terminal_id': None,
            'terminal_code': None,
            'terminal_name': None,
            'terminal_type': 'POS',
            'store_id': None,
            'store_code': None,
            'company_id': None,
            'company_name': None,
            'brand_id': None,
            'brand_name': None,
            'setup_completed': False,
            'setup_date': None
        }
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error: Failed to save terminal-config.json: {e}")
            return False
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value and save"""
        self._config[key] = value
        return self._save_config()
    
    def update(self, data):
        """Update multiple values at once"""
        self._config.update(data)
        return self._save_config()
    
    def get_all(self):
        """Get all configuration"""
        return self._config.copy()
    
    def is_configured(self):
        """Check if terminal is configured"""
        return bool(self._config.get('setup_completed') and self._config.get('terminal_id'))
    
    def reset(self):
        """Reset configuration to defaults"""
        self._config = self._get_default_config()
        return self._save_config()


# Create singleton instance
terminal_config = TerminalConfig()


def get_terminal_config():
    """Get terminal configuration instance"""
    return terminal_config
