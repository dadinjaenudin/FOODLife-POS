import sqlite3
import os

db_path = 'd:/YOGYA-Kiosk/pos-django-htmx-main/db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("🔧 Removing UNIQUE constraint from core_product.sku...")
    
    # Get current data
    cursor.execute("SELECT * FROM core_product")
    products = cursor.fetchall()
    print(f"📊 Found {len(products)} products")
    
    # Get column names
    cursor.execute("PRAGMA table_info(core_product)")
    columns = cursor.fetchall()
    print(f"📋 Columns: {[col[1] for col in columns]}")
    
    # Create new table without unique constraint on sku
    cursor.execute("""
        CREATE TABLE core_product_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            sku VARCHAR(50) NOT NULL,
            category_id INTEGER,
            price DECIMAL(12,2) NOT NULL,
            cost DECIMAL(12,2) DEFAULT 0,
            image VARCHAR(100),
            description TEXT,
            printer_target VARCHAR(20) DEFAULT 'kitchen',
            is_active BOOLEAN DEFAULT 1,
            track_stock BOOLEAN DEFAULT 0,
            stock_quantity INTEGER DEFAULT 0,
            low_stock_alert INTEGER DEFAULT 10,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(category_id) REFERENCES core_category(id)
        )
    """)
    print("✅ New table created")
    
    # Copy data
    cursor.execute("INSERT INTO core_product_new SELECT * FROM core_product")
    print("✅ Data copied")
    
    # Drop old table
    cursor.execute("DROP TABLE core_product")
    print("✅ Old table dropped")
    
    # Rename new table
    cursor.execute("ALTER TABLE core_product_new RENAME TO core_product")
    print("✅ Table renamed")
    
    # Create index on sku
    cursor.execute("CREATE INDEX core_product_sku_idx ON core_product(sku)")
    print("✅ Index created on SKU")
    
    # Commit changes
    conn.commit()
    print("\n🎉 SUCCESS! SKU unique constraint removed, duplicate SKUs now allowed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    conn.close()
