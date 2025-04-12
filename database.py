# database.py

import mysql.connector
from config import MYSQL_CONFIG

class Database:
    def __init__(self):
        self.conn = mysql.connector.connect(**MYSQL_CONFIG)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        # Tabela wyszukiwań
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS search_links (
                id INT AUTO_INCREMENT PRIMARY KEY,
                url VARCHAR(255) NOT NULL UNIQUE
            )
        """)
        # Tabela ogłoszeń
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                search_link_id INT,
                olx_id VARCHAR(100) NOT NULL,
                title VARCHAR(255),
                price DECIMAL(10,2),
                location VARCHAR(255),
                item_condition VARCHAR(50),
                url VARCHAR(255),
                image_url VARCHAR(255),
                description TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                previous_price DECIMAL(10,2),
                UNIQUE KEY unique_listing (search_link_id, olx_id),
                FOREIGN KEY (search_link_id) REFERENCES search_links(id)
            )
        """)
        # Tabela użytkowników
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
        cursor.close()

    # Operacje na search_links
    def add_search_link(self, url):
        cursor = self.conn.cursor()
        query = "INSERT IGNORE INTO search_links (url) VALUES (%s)"
        cursor.execute(query, (url,))
        self.conn.commit()
        cursor.close()

    def get_search_links(self):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM search_links")
        results = cursor.fetchall()
        cursor.close()
        return results

    # Operacje na listings
    def get_listing_by_olx_id(self, search_link_id, olx_id):
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT * FROM listings WHERE search_link_id = %s AND olx_id = %s"
        cursor.execute(query, (search_link_id, olx_id))
        result = cursor.fetchone()
        cursor.close()
        return result

    def get_listings_for_search_link(self, search_link_id):
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT * FROM listings WHERE search_link_id = %s"
        cursor.execute(query, (search_link_id,))
        results = cursor.fetchall()
        cursor.close()
        return results

    def update_listing_timestamp(self, listing_id):
        cursor = self.conn.cursor()
        query = "UPDATE listings SET last_updated = CURRENT_TIMESTAMP WHERE id = %s"
        cursor.execute(query, (listing_id,))
        self.conn.commit()
        cursor.close()

    def insert_or_update_listing(self, search_link_id, listing):
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT * FROM listings WHERE search_link_id = %s AND olx_id = %s"
        cursor.execute(query, (search_link_id, listing['olx_id']))
        result = cursor.fetchone()
        if result:
            # Jeśli cena uległa zmianie, zapisz starą w previous_price
            if float(listing['price']) != float(result['price']):
                update_query = """
                    UPDATE listings
                    SET previous_price = %s,
                        price = %s,
                        title = %s,
                        description = %s,
                        location = %s,
                        item_condition = %s,
                        url = %s,
                        image_url = %s,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                cursor.execute(update_query, (
                    result['price'],
                    listing['price'],
                    listing['title'],
                    listing['description'],
                    listing['location'],
                    listing.get('item_condition', 'error'),
                    listing['url'],
                    listing.get('image_url'),
                    result['id']
                ))
            else:
                update_query = "UPDATE listings SET last_updated = CURRENT_TIMESTAMP WHERE id = %s"
                cursor.execute(update_query, (result['id'],))
        else:
            query = """
                INSERT INTO listings
                (search_link_id, olx_id, title, price, location, item_condition, url, image_url, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (
                search_link_id,
                listing['olx_id'],
                listing['title'],
                listing['price'],
                listing['location'],
                listing.get('item_condition', 'error'),
                listing['url'],
                listing.get('image_url'),
                listing['description']
            ))
        self.conn.commit()
        cursor.close()

    # Operacje na użytkownikach
    def register_user(self, username, email, hashed_password):
        cursor = self.conn.cursor(dictionary=True)
        query = """
            INSERT INTO users (username, email, password)
            VALUES (%s, %s, %s)
        """
        try:
            cursor.execute(query, (username, email, hashed_password))
            self.conn.commit()
            user_id = cursor.lastrowid
            cursor.close()
            return self.get_user_by_id(user_id)
        except mysql.connector.Error as e:
            print("Błąd rejestracji:", e)
            cursor.close()
            return None

    def get_user_by_username(self, username):
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE username = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        cursor.close()
        return user

    def get_user_by_email(self, email):
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        user = cursor.fetchone()
        cursor.close()
        return user

    def get_user_by_id(self, user_id):
        cursor = self.conn.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        return user

    def update_user_settings(self, user_id, data):
        cursor = self.conn.cursor()
        query = "UPDATE users SET username = %s, email = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        try:
            cursor.execute(query, (
                data.get("username"),
                data.get("email"),
                user_id
            ))
            self.conn.commit()
            cursor.close()
            return True
        except mysql.connector.Error as e:
            print("Błąd aktualizacji ustawień:", e)
            cursor.close()
            return False
