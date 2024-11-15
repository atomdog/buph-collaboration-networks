import sqlite3
import math

# Connect to the database
conn = sqlite3.connect('pubmed.db')
cursor = conn.cursor()

# Create Articles Table
def instantiate():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Articles (
        article_id INTEGER PRIMARY KEY AUTOINCREMENT,
        articleTitle TEXT,
        journalTitle TEXT,
        datePublished TEXT,
        abstract TEXT,
        grants TEXT
    )
    ''')

    # Create Authors Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Authors (
        author_id INTEGER PRIMARY KEY AUTOINCREMENT,
        authorName TEXT NOT NULL
    )
    ''')

    # Create Departments Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Departments (
        department_id INTEGER PRIMARY KEY AUTOINCREMENT,
        departmentName TEXT NOT NULL,
        latitude REAL,
        longitude REAL
    )
    ''')

    # Create ArticleAuthors Table (many-to-many relationship)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ArticleAuthors (
        article_id INTEGER,
        author_id INTEGER,
        department_id INTEGER,
        FOREIGN KEY (article_id) REFERENCES Articles(article_id),
        FOREIGN KEY (author_id) REFERENCES Authors(author_id),
        FOREIGN KEY (department_id) REFERENCES Departments(department_id)
    )
    ''')

def insert_article(articleTitle, journalTitle, datePublished, abstract, grants):
    cursor.execute('''
    INSERT INTO Articles (articleTitle, journalTitle, datePublished, abstract, grants)
    VALUES (?, ?, ?, ?, ?)
    ''', (articleTitle, journalTitle, datePublished, abstract, grants))
    conn.commit()
    return cursor.lastrowid

def insert_author(authorName):
    cursor.execute('''
    INSERT INTO Authors (authorName)
    VALUES (?)
    ''', (authorName,))
    conn.commit()
    return cursor.lastrowid

def insert_department(departmentName, latitude, longitude):
    cursor.execute('''
    INSERT INTO Departments (departmentName, latitude, longitude)
    VALUES (?, ?, ?)
    ''', (departmentName, latitude, longitude))
    conn.commit()
    return cursor.lastrowid

def tie_article_author_department(article_id, author_id, department_id):
    cursor.execute('''
    INSERT INTO ArticleAuthors (article_id, author_id, department_id)
    VALUES (?, ?, ?)
    ''', (article_id, author_id, department_id))
    conn.commit()
    return cursor.lastrowid

# Retrieve all articles
def retrieve_all_articles():
    cursor.execute('SELECT * FROM Articles')
    return cursor.fetchall()

# Retrieve article by ID
def retrieve_article_by_id(article_id):
    cursor.execute('SELECT * FROM Articles WHERE article_id = ?', (article_id,))
    return cursor.fetchone()

# Retrieve all authors
def retrieve_all_authors():
    cursor.execute('SELECT * FROM Authors')
    return cursor.fetchall()

# Retrieve author by ID
def retrieve_author_by_id(author_id):
    cursor.execute('SELECT * FROM Authors WHERE author_id = ?', (author_id,))
    return cursor.fetchone()

# Retrieve all departments
def retrieve_all_departments():
    cursor.execute('SELECT * FROM Departments')
    return cursor.fetchall()

# Retrieve department by ID
def retrieve_department_by_id(department_id):
    cursor.execute('SELECT * FROM Departments WHERE department_id = ?', (department_id,))
    return cursor.fetchone()

# Retrieve all articles by a specific author
def retrieve_articles_by_author(author_id):
    cursor.execute('''
    SELECT a.article_id, a.articleTitle, a.journalTitle, a.datePublished, a.abstract
    FROM Articles a
    JOIN ArticleAuthors aa ON a.article_id = aa.article_id
    WHERE aa.author_id = ?
    ''', (author_id,))
    return cursor.fetchall()

# Retrieve all authors of a specific article
def retrieve_authors_by_article(article_id):
    cursor.execute('''
    SELECT au.author_id, au.authorName
    FROM Authors au
    JOIN ArticleAuthors aa ON au.author_id = aa.author_id
    WHERE aa.article_id = ?
    ''', (article_id,))
    return cursor.fetchall()

# Retrieve all departments associated with a specific article
def retrieve_departments_by_article(article_id):
    cursor.execute('''
    SELECT d.department_id, d.departmentName, d.latitude, d.longitude
    FROM Departments d
    JOIN ArticleAuthors aa ON d.department_id = aa.department_id
    WHERE aa.article_id = ?
    ''', (article_id,))
    return cursor.fetchall()

# Retrieve all articles associated with a specific department
def retrieve_articles_by_department(department_id):
    cursor.execute('''
    SELECT a.article_id, a.articleTitle, a.journalTitle, a.datePublished, a.abstract, a.grants
    FROM Articles a
    JOIN ArticleAuthors aa ON a.article_id = aa.article_id
    WHERE aa.department_id = ?
    ''', (department_id,))
    return cursor.fetchall()

# Return a dictionary of all department ids indexed by their actual name.
def get_department_ids_dict():
    cursor.execute('SELECT departmentName, department_id FROM Departments')
    departments = cursor.fetchall()

    department_dict = {dept[0]: dept[1] for dept in departments}
    return department_dict

def get_author_ids_dict():
    cursor.execute('SELECT authorName, author_id FROM Authors')
    authors = cursor.fetchall()
    
    author_dict = {author[0]: author[1] for author in authors}
    return author_dict

def get_department_locations_dict():
    cursor.execute('SELECT departmentName, latitude, longitude FROM Departments')
    departments = cursor.fetchall()
    location_dict = {dept[0]: (dept[1], dept[2]) for dept in departments}
    return location_dict

# Haversine formula to calculate the distance between two points on the Earth's surface
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

# Function to retrieve all departments within a radius
def get_departments_within_radius(center_lat, center_lon, radius):
    cursor.execute('SELECT departmentName, latitude, longitude FROM Departments')
    departments = cursor.fetchall()
    
    nearby_departments = {}
    for dept in departments:
        dept_name, lat, lon = dept
        distance = haversine(center_lat, center_lon, lat, lon)
        if distance <= radius:
            nearby_departments[dept_name] = (lat, lon)
    
    return nearby_departments

# Retrieve all shared articles between departments along with the journal title
def get_article_department_links():
    cursor.execute('''
    SELECT DISTINCT aa1.department_id, aa2.department_id, aa1.article_id, a.journalTitle
    FROM ArticleAuthors aa1
    JOIN ArticleAuthors aa2 ON aa1.article_id = aa2.article_id
    JOIN Articles a ON aa1.article_id = a.article_id
    WHERE aa1.department_id != aa2.department_id
    ''')
    return cursor.fetchall()

# Function to remove articles, departments, and authors associated with departments having coordinates (0.0, 0.0)
def remove_invalid_coordinates():
    cursor.execute('''
    SELECT department_id
    FROM Departments
    WHERE latitude = 0.0 AND longitude = 0.0
    ''')
    departments_to_remove = cursor.fetchall()
    departments_to_remove = [d[0] for d in departments_to_remove]

    if departments_to_remove:
        # Remove from ArticleAuthors table
        cursor.execute('''
        DELETE FROM ArticleAuthors
        WHERE department_id IN ({})
        '''.format(','.join('?' for _ in departments_to_remove)), departments_to_remove)
        conn.commit()

        # Remove from Departments table
        cursor.execute('''
        DELETE FROM Departments
        WHERE department_id IN ({})
        '''.format(','.join('?' for _ in departments_to_remove)), departments_to_remove)
        conn.commit()

        # Optionally, remove authors without any articles (if needed)
        cursor.execute('''
        DELETE FROM Authors
        WHERE author_id NOT IN (
            SELECT DISTINCT author_id
            FROM ArticleAuthors
        )
        ''')
        conn.commit()

        # Optionally, remove articles without any authors (if needed)
        cursor.execute('''
        DELETE FROM Articles
        WHERE article_id NOT IN (
            SELECT DISTINCT article_id
            FROM ArticleAuthors
        )
        ''')
        conn.commit()
        
def purge():
    remove_invalid_coordinates()

if __name__ == "__main__":
    instantiate()
